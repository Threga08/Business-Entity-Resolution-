"""
Indexing module for fast Source 1 search and Target (S2/S3) blocking retrieval.
Uses SQLite Full-Text Search (FTS5) for instant sub-millisecond search over Source 1,
and persists preprocessed target indexes for real-time entity matching.
"""
import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from . import config
from .data_loader import load_source_df
from .preprocessing import preprocess_dataframe, normalize_business_name, normalize_address, normalize_country

logger = config.logger

DB_PATH = os.path.join(config.PROCESSED_DIR, "entities_search.db")

def init_search_db(s1_file: str = config.SAMPLE_SOURCE1, db_path: str = DB_PATH) -> str:
    """
    Initializes an SQLite FTS5 database for ultra-fast Source 1 search by ID, name, or address.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create tables
    cur.execute("DROP TABLE IF EXISTS source1;")
    cur.execute("""
        CREATE TABLE source1 (
            entity_id TEXT PRIMARY KEY,
            business_name TEXT,
            business_address TEXT,
            country TEXT,
            norm_name TEXT,
            norm_address TEXT
        );
    """)
    
    cur.execute("DROP TABLE IF EXISTS source1_fts;")
    cur.execute("""
        CREATE VIRTUAL TABLE source1_fts USING fts5(
            entity_id,
            business_name,
            business_address,
            country,
            content='source1',
            content_rowid='rowid'
        );
    """)
    
    if os.path.exists(s1_file):
        logger.info(f"Loading Source 1 records from {s1_file} into SQLite FTS index...")
        df = load_source_df(s1_file)
        
        records = []
        for _, row in df.iterrows():
            eid = str(row.get(config.ENTITY_ID, "")).strip()
            name = str(row.get(config.BUSINESS_NAME, "")).strip()
            addr = str(row.get(config.BUSINESS_ADDRESS, "")).strip()
            ctry = str(row.get(config.COUNTRY, "")).strip()
            n_name, _ = normalize_business_name(name)
            n_addr, _, _ = normalize_address(addr)
            records.append((eid, name, addr, ctry, n_name, n_addr))
            
        cur.executemany("""
            INSERT INTO source1 (entity_id, business_name, business_address, country, norm_name, norm_address)
            VALUES (?, ?, ?, ?, ?, ?);
        """, records)
        
        cur.execute("""
            INSERT INTO source1_fts(rowid, entity_id, business_name, business_address, country)
            SELECT rowid, entity_id, business_name, business_address, country FROM source1;
        """)
        conn.commit()
        logger.info(f"Indexed {len(records):,} Source 1 records in {db_path}")
        
    conn.close()
    return db_path

def search_source1(query: str, limit: int = 15, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Searches Source 1 entities by ID, name, or address using prefix and substring matching.
    """
    if not os.path.exists(db_path):
        init_search_db(db_path=db_path)
        
    q = query.strip()
    if not q:
        # Return recent / top records
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT entity_id, business_name, business_address, country FROM source1 LIMIT ?;", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{"entity_id": r[0], "business_name": r[1], "business_address": r[2], "country": r[3]} for r in rows]
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Direct exact ID match
    cur.execute("SELECT entity_id, business_name, business_address, country FROM source1 WHERE entity_id = ? LIMIT 1;", (q,))
    exact = cur.fetchall()
    if exact:
        conn.close()
        return [{"entity_id": exact[0][0], "business_name": exact[0][1], "business_address": exact[0][2], "country": exact[0][3]}]
        
    # Like / Prefix Search
    like_q = f"%{q}%"
    cur.execute("""
        SELECT entity_id, business_name, business_address, country FROM source1
        WHERE entity_id LIKE ? OR business_name LIKE ? OR business_address LIKE ?
        LIMIT ?;
    """, (like_q, like_q, like_q, limit))
    rows = cur.fetchall()
    conn.close()
    
    return [{"entity_id": r[0], "business_name": r[1], "business_address": r[2], "country": r[3]} for r in rows]

def get_source1_by_id(entity_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves full details for a single Source 1 entity."""
    if not os.path.exists(db_path):
        init_search_db(db_path=db_path)
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT entity_id, business_name, business_address, country FROM source1 WHERE entity_id = ?;", (entity_id.strip(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"entity_id": row[0], "business_name": row[1], "business_address": row[2], "country": row[3]}
    return None
