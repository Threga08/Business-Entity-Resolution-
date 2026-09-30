"""
Flask Web Application for Business Entity Resolution.
Supports:
- Landing Page (/)
- Entity Resolution Workspace (/resolver)
- Side-by-Side Data Source Comparison (/comparison)
- Model Performance & Threshold Tuning (/evaluation)
- Submission & Output Downloads (/output)
- Real-time Entity Resolution APIs
"""
import os
import sys
import json
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.business_entity_resolution import config
from src.business_entity_resolution.indexing import search_source1, get_source1_by_id
from src.business_entity_resolution.matcher import RealTimeMatcher
from src.business_entity_resolution.data_loader import count_lines_fast, load_source_df, load_ground_truth_map

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

# ── Pages ───────────────────────────────────────────────────────────────────

@app.route("/")
@app.route("/search")
@app.route("/matching")
@app.route("/batch")
@app.route("/performance")
@app.route("/resolver")
def page_dashboard():
    return render_template("index.html")

@app.route("/evaluation")
def page_evaluation():
    return render_template("index.html")

@app.route("/output")
def page_output():
    return render_template("index.html")

# ── Real Entity Resolution API Endpoints ────────────────────────────────────

@app.route("/api/source1/search")
def api_source1_search():
    """Searches Source 1 entities by ID, business name, or address."""
    q = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 15))
    results = search_source1(q, limit=limit)
    return jsonify({"success": True, "query": q, "results": results})

@app.route("/api/source1/<entity_id>")
def api_source1_get(entity_id):
    """Retrieves full details for a Source 1 entity."""
    record = get_source1_by_id(entity_id)
    if record:
        return jsonify({"success": True, "record": record})
    return jsonify({"success": False, "error": f"Entity '{entity_id}' not found."}), 404

@app.route("/api/match", methods=["POST"])
def api_match():
    """
    Runs actual real-time entity resolution pipeline:
    Normalization -> Inverted Blocking -> 29 Features -> ML Inference -> Stratified Matches.
    """
    data = request.get_json() or {}
    eid = data.get("entity_id", "").strip()
    bname = data.get("business_name", "").strip()
    baddr = data.get("business_address", "").strip()
    bctry = data.get("country", "").strip()
    thresh_override = data.get("threshold", None)
    if thresh_override is not None:
        try:
            thresh_override = float(thresh_override)
        except ValueError:
            thresh_override = None

    # If only entity_id was provided, look it up
    if eid and (not bname or not baddr):
        rec = get_source1_by_id(eid)
        if rec:
            bname = rec.get("business_name", bname)
            baddr = rec.get("business_address", baddr)
            bctry = rec.get("country", bctry)

    if not bname:
        return jsonify({"success": False, "error": "Business Name is required for matching."}), 400

    matcher = RealTimeMatcher.get_instance()
    try:
        match_result = matcher.match_entity(
            business_name=bname,
            business_address=baddr,
            country=bctry,
            source1_id=eid or "MANUAL-INPUT",
            threshold_override=thresh_override
        )
        return jsonify({"success": True, "data": match_result})
    except Exception as e:
        logger.error(f"Error during entity matching: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/match/<entity_id>")
def api_match_by_id(entity_id):
    """Runs entity resolution for an existing Source 1 ID."""
    rec = get_source1_by_id(entity_id)
    if not rec:
        return jsonify({"success": False, "error": f"Source 1 entity '{entity_id}' not found."}), 404

    matcher = RealTimeMatcher.get_instance()
    try:
        match_result = matcher.match_entity(
            business_name=rec.get("business_name", ""),
            business_address=rec.get("business_address", ""),
            country=rec.get("country", ""),
            source1_id=entity_id
        )
        return jsonify({"success": True, "data": match_result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/model/status")
def api_model_status():
    """Returns actual trained model status, type, and active threshold."""
    has_model = os.path.exists(config.MODEL_PATH)
    threshold = config.DEFAULT_THRESHOLD
    if os.path.exists(config.THRESHOLD_PATH):
        try:
            with open(config.THRESHOLD_PATH, "r", encoding="utf-8") as f:
                threshold = json.load(f).get("best_threshold", config.DEFAULT_THRESHOLD)
        except Exception:
            pass

    matcher = RealTimeMatcher.get_instance()
    return jsonify({
        "model_trained": has_model,
        "model_type": "Logistic Regression (Standardized, L-BFGS, Balanced Class Weight)",
        "features_count": 29,
        "decision_threshold": round(threshold, 2),
        "target_entities_indexed": len(matcher.target_records) if matcher.initialized else 0
    })

@app.route("/api/evaluation")
def api_evaluation():
    """Returns real validation evaluation metrics and threshold grid comparison."""
    if not os.path.exists(config.THRESHOLD_PATH) or not os.path.exists(config.BLOCKING_REPORT_PATH):
        return jsonify({"has_evaluation": False, "message": "Model evaluation has not been run yet."})

    try:
        with open(config.THRESHOLD_PATH, "r", encoding="utf-8") as f:
            t_data = json.load(f)
        with open(config.BLOCKING_REPORT_PATH, "r", encoding="utf-8") as f:
            b_data = json.load(f)
        with open(config.METRICS_PATH, "r", encoding="utf-8") as f:
            m_data = json.load(f)

        return jsonify({
            "has_evaluation": True,
            "candidate_recall": b_data.get("candidate_recall_pct", "--"),
            "candidate_reduction": b_data.get("reduction_ratio_pct", "--"),
            "avg_candidates_per_s1": b_data.get("avg_candidates_per_s1", "--"),
            "macro_f05": t_data.get("validation_macro_f05", 0.0),
            "precision": t_data.get("grid_results", [{}])[-1].get("macro_precision", 0.0),
            "recall": t_data.get("grid_results", [{}])[-1].get("macro_recall", 0.0),
            "selected_threshold": t_data.get("best_threshold", 0.70),
            "threshold_comparison": t_data.get("grid_results", []),
            "train_pairs_count": m_data.get("train_pairs_count", 0),
            "val_pairs_count": m_data.get("val_pairs_count", 0)
        })
    except Exception as e:
        return jsonify({"has_evaluation": False, "error": str(e)})

@app.route("/api/comparison/sample")
def api_comparison_sample():
    """Returns real entities with resolved matches across S1, S2, and S3 for multi-source inspection."""
    if not os.path.exists(config.MATCHING_RESULTS_TSV):
        return jsonify({"samples": []})

    matcher = RealTimeMatcher.get_instance()
    samples = []
    
    # Read first matching entries that have both S2 and S3 matches
    import csv
    with open(config.MATCHING_RESULTS_TSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) == 2 and row[1].strip():
                s1_id = row[0].strip()
                matches = [m.strip() for m in row[1].split(",") if m.strip()]
                s2_m = [m for m in matches if m.startswith("S2-") or "-2-" in m]
                s3_m = [m for m in matches if m.startswith("S3-") or "-3-" in m]
                
                if s2_m and s3_m:
                    s1_rec = get_source1_by_id(s1_id)
                    s2_rec = matcher.target_records.get(s2_m[0], {})
                    s3_rec = matcher.target_records.get(s3_m[0], {})
                    
                    if s1_rec and s2_rec and s3_rec:
                        samples.append({
                            "s1": s1_rec,
                            "s2": {
                                "entity_id": s2_m[0],
                                "business_name": s2_rec.get("business_name", ""),
                                "business_address": s2_rec.get("business_address", ""),
                                "country": s2_rec.get("country", "")
                            },
                            "s3": {
                                "entity_id": s3_m[0],
                                "business_name": s3_rec.get("business_name", ""),
                                "business_address": s3_rec.get("business_address", ""),
                                "country": s3_rec.get("country", "")
                            }
                        })
                    if len(samples) >= 8:
                        break
                        
    return jsonify({"samples": samples})

@app.route("/api/output")
def api_output():
    """Returns status and file metadata for matching_results.tsv and candidate_pairs.tsv."""
    results_path = config.MATCHING_RESULTS_TSV
    cands_path = config.CANDIDATE_PAIRS_TSV
    
    res_exists = os.path.exists(results_path)
    cand_exists = os.path.exists(cands_path)
    
    res_info = None
    if res_exists:
        res_info = {
            "filename": "matching_results.tsv",
            "size_kb": round(os.path.getsize(results_path) / 1024, 1),
            "rows": count_lines_fast(results_path) - 1
        }
        
    cand_info = None
    if cand_exists:
        cand_info = {
            "filename": "candidate_pairs.tsv",
            "size_mb": round(os.path.getsize(cands_path) / (1024 * 1024), 2),
            "rows": count_lines_fast(cands_path) - 1
        }
        
    return jsonify({
        "matching_results": res_info,
        "candidate_pairs": cand_info,
        "has_results": res_exists,
        "has_candidates": cand_exists
    })

@app.route("/api/download/<filename>")
def api_download(filename):
    """Downloads submission TSV files safely."""
    allowed = ["matching_results.tsv", "candidate_pairs.tsv"]
    if filename not in allowed:
        return "File not allowed", 403
    return send_from_directory(config.OUTPUT_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    print("\nStarting Business Entity Resolution Web Studio on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=False)
