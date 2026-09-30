"""
Operational SQLite Database for Business Entity Resolution.
Stores reviews, human decisions, review queue, business history, batch jobs, and user settings.
Does NOT modify source TSVs or competition ground truth.
"""
import os
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime

from . import config

DB_PATH = os.path.join(config.PROCESSED_DIR, "app_operational.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_app_db(db_path: str = DB_PATH) -> None:
    """Creates operational tables if they don't already exist."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Decisions table (confirmed, rejected, review_later)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s1_id TEXT NOT NULL,
            s1_name TEXT NOT NULL,
            candidate_id TEXT,
            candidate_source TEXT,
            candidate_name TEXT,
            decision TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            notes TEXT,
            analyst TEXT DEFAULT 'Analyst',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Review queue table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s1_id TEXT UNIQUE NOT NULL,
            s1_name TEXT NOT NULL,
            s1_address TEXT,
            country TEXT,
            candidates_count INTEGER DEFAULT 0,
            highest_confidence REAL DEFAULT 0.0,
            confidence_tier TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Business history audit trail
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            s1_id TEXT,
            business_name TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Batch jobs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            total_records INTEGER DEFAULT 0,
            processed_records INTEGER DEFAULT 0,
            potential_matches INTEGER DEFAULT 0,
            no_matches INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            output_results_file TEXT,
            output_candidates_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
    """)

    # App settings key-value store
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # Default settings
    default_settings = {
        "matching_threshold": str(config.DEFAULT_THRESHOLD),
        "candidate_limit": str(config.MAX_CANDIDATES_PER_S1),
        "search_limit": "20",
        "analyst_name": "Analyst"
    }
    for k, v in default_settings.items():
        cur.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?);", (k, v))

    conn.commit()
    conn.close()

def get_kpis(db_path: str = DB_PATH) -> Dict[str, int]:
    """Returns actual operational KPIs from SQLite database."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Pending reviews
    cur.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'pending';")
    pending = cur.fetchone()[0]

    # Confirmed matches
    cur.execute("SELECT COUNT(*) FROM decisions WHERE decision = 'confirmed';")
    confirmed = cur.fetchone()[0]

    # Rejected matches
    cur.execute("SELECT COUNT(*) FROM decisions WHERE decision = 'rejected';")
    rejected = cur.fetchone()[0]

    # Today's processed records
    cur.execute("""
        SELECT COUNT(*) FROM history 
        WHERE DATE(created_at) = DATE('now')
          AND action_type IN ('confirm_match', 'reject_match', 'review_later');
    """)
    today_processed = cur.fetchone()[0]

    conn.close()
    return {
        "pending_reviews": pending,
        "confirmed_matches": confirmed,
        "rejected_matches": rejected,
        "today_processed": today_processed
    }

def record_decision(
    s1_id: str,
    s1_name: str,
    decision: str,
    candidate_id: Optional[str] = None,
    candidate_source: Optional[str] = None,
    candidate_name: Optional[str] = None,
    confidence: float = 0.0,
    notes: str = "",
    analyst: str = "Analyst",
    db_path: str = DB_PATH
) -> int:
    """Records a decision (confirmed, rejected, review_later) and logs to history."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO decisions (s1_id, s1_name, candidate_id, candidate_source, candidate_name, decision, confidence, notes, analyst)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (s1_id, s1_name, candidate_id, candidate_source, candidate_name, decision, confidence, notes, analyst))
    decision_id = cur.lastrowid

    # If it was in review queue, update its status
    if decision in ("confirmed", "rejected"):
        cur.execute("UPDATE review_queue SET status = 'reviewed' WHERE s1_id = ?;", (s1_id,))
    elif decision == "review_later":
        # Ensure it exists in review queue
        cur.execute("""
            INSERT INTO review_queue (s1_id, s1_name, highest_confidence, status)
            VALUES (?, ?, ?, 'pending')
            ON CONFLICT(s1_id) DO UPDATE SET status = 'pending', highest_confidence = ?;
        """, (s1_id, s1_name, confidence, confidence))

    # Add to business history
    action_type = f"{decision}_match" if decision in ("confirmed", "rejected") else "review_later"
    target_str = f" with {candidate_id} ({candidate_name})" if candidate_id else ""
    details = f"Analyst marked {decision.replace('_', ' ').title()}{target_str} (Conf: {round(confidence * 100, 1)}%)"
    cur.execute("""
        INSERT INTO history (action_type, s1_id, business_name, details)
        VALUES (?, ?, ?, ?);
    """, (action_type, s1_id, s1_name, details))

    conn.commit()
    conn.close()
    return decision_id

def get_review_queue(
    filter_tier: str = "all",
    limit: int = 50,
    offset: int = 0,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Returns items currently pending in the review queue."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = "SELECT * FROM review_queue WHERE status = 'pending'"
    params: List[Any] = []

    if filter_tier == "high":
        query += " AND highest_confidence >= 0.90"
    elif filter_tier == "medium":
        query += " AND highest_confidence >= 0.70 AND highest_confidence < 0.90"
    elif filter_tier == "low":
        query += " AND highest_confidence < 0.70 AND highest_confidence > 0.0"
    elif filter_tier == "no_match":
        query += " AND (highest_confidence = 0.0 OR candidates_count = 0)"
    elif filter_tier == "multiple":
        query += " AND candidates_count > 1"

    query += " ORDER BY highest_confidence DESC, added_at DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    cur.execute(query, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def enqueue_records(records: List[Dict[str, Any]], db_path: str = DB_PATH) -> int:
    """Enqueues Source 1 records into review queue."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    count = 0
    for r in records:
        conf = float(r.get("highest_confidence", 0.0))
        tier = "high" if conf >= 0.9 else ("medium" if conf >= 0.7 else "low")
        cur.execute("""
            INSERT INTO review_queue (s1_id, s1_name, s1_address, country, candidates_count, highest_confidence, confidence_tier, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(s1_id) DO UPDATE SET
                candidates_count = excluded.candidates_count,
                highest_confidence = excluded.highest_confidence,
                confidence_tier = excluded.confidence_tier,
                status = 'pending';
        """, (
            r["s1_id"],
            r["s1_name"],
            r.get("s1_address", ""),
            r.get("country", ""),
            r.get("candidates_count", 0),
            conf,
            tier
        ))
        count += 1

    conn.commit()
    conn.close()
    return count

def get_resolved_entities(
    decision_filter: str = "all",
    limit: int = 50,
    offset: int = 0,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Returns completed decisions for the Resolved Entities view."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = "SELECT * FROM decisions"
    params: List[Any] = []

    if decision_filter in ("confirmed", "rejected", "review_later"):
        query += " WHERE decision = ?"
        params.append(decision_filter)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    cur.execute(query, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_history(limit: int = 50, offset: int = 0, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Returns business action history."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM history ORDER BY created_at DESC LIMIT ? OFFSET ?;", (limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_settings(db_path: str = DB_PATH) -> Dict[str, str]:
    """Retrieves all application settings."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM app_settings;")
    settings = {r["key"]: r["value"] for r in cur.fetchall()}
    conn.close()
    return settings

def update_settings(settings: Dict[str, str], db_path: str = DB_PATH) -> None:
    """Updates settings in SQLite."""
    init_app_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    for k, v in settings.items():
        cur.execute("""
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
        """, (k, str(v)))

    # Log to history
    cur.execute("""
        INSERT INTO history (action_type, s1_id, business_name, details)
        VALUES ('settings_update', '', 'System Settings', 'Operational settings updated');
    """)
    conn.commit()
    conn.close()
