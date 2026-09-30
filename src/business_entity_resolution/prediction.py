"""
Prediction and inference module.
Scores candidate pairs using trained model, applies optimal threshold, and outputs one-to-many matches.
"""
import os
import json
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional
import numpy as np

from . import config
from .model import load_model
from .features import build_features_matrix

logger = config.logger

def load_optimal_threshold(threshold_file: str = config.THRESHOLD_PATH) -> float:
    """Loads tuned threshold from threshold.json, defaulting to config.DEFAULT_THRESHOLD."""
    if os.path.exists(threshold_file):
        try:
            with open(threshold_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("best_threshold", config.DEFAULT_THRESHOLD))
        except Exception:
            pass
    return config.DEFAULT_THRESHOLD

def predict_matches(
    flat_candidates: List[Dict[str, Any]],
    s1_records: Dict[str, Dict[str, Any]],
    target_records: Dict[str, Dict[str, Any]],
    all_s1_ids: List[str],
    threshold: Optional[float] = None
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[Tuple[str, float]]]]:
    """
    Runs model inference on candidates and extracts matches passing threshold.
    
    Returns:
        (predicted_matches_map, candidate_pairs_map, scored_candidates_map)
        - predicted_matches_map: {s1_id: [matched_target_ids]}
        - candidate_pairs_map: {s1_id: [candidate_target_ids]}
        - scored_candidates_map: {s1_id: [(target_id, confidence_prob)]}
    """
    if threshold is None:
        threshold = load_optimal_threshold()
        
    logger.info(f"Running inference with threshold = {threshold:.2f} on {len(flat_candidates):,} candidate pairs...")
    
    # Load model
    model = load_model(config.MODEL_PATH)
    
    # Build candidate map
    cand_map: Dict[str, List[str]] = {s1: [] for s1 in all_s1_ids}
    for p in flat_candidates:
        s1 = p["source1_id"]
        tgt = p["target_id"]
        if s1 in cand_map and tgt not in cand_map[s1]:
            cand_map[s1].append(tgt)
            
    # Compute features and probabilities
    scored_map: Dict[str, List[Tuple[str, float]]] = {s1: [] for s1 in all_s1_ids}
    predicted_matches: Dict[str, List[str]] = {s1: [] for s1 in all_s1_ids}
    
    if flat_candidates:
        X, s1_ids, target_ids = build_features_matrix(flat_candidates, s1_records, target_records)
        probs = model.predict_proba(X)[:, 1]
        
        for i in range(len(flat_candidates)):
            s1 = s1_ids[i]
            tgt = target_ids[i]
            prob = float(probs[i])
            scored_map[s1].append((tgt, prob))
            
            if prob >= threshold:
                predicted_matches[s1].append(tgt)
                
    # Deduplicate and sort matches by probability descending
    for s1 in all_s1_ids:
        # Sort scored candidates by confidence
        scored_map[s1].sort(key=lambda x: x[1], reverse=True)
        # Ensure predicted matches are unique and ordered
        seen = set()
        clean_matches = []
        for tgt in predicted_matches[s1]:
            if tgt not in seen:
                seen.add(tgt)
                clean_matches.append(tgt)
        predicted_matches[s1] = clean_matches
        
    match_count = sum(len(m) for m in predicted_matches.values())
    s1_with_matches = sum(1 for m in predicted_matches.values() if len(m) > 0)
    logger.info(f"Prediction complete. Total matches found: {match_count:,} across {s1_with_matches:,} / {len(all_s1_ids):,} S1 entities.")
    
    return predicted_matches, cand_map, scored_map
