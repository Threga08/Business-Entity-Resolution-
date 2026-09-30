"""
Training module with data-leakage prevention (grouping by S1 entity),
candidate pair labeling, supervised classifier training, and validation-based threshold optimization.
"""
import os
import json
import random
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any
import numpy as np
import pandas as pd

from . import config
from .features import build_features_matrix, FEATURE_COLUMNS
from .model import create_model, save_model
from .evaluation import evaluate_predictions

logger = config.logger

def train_and_tune_pipeline(
    candidate_dict: Dict[str, Dict[str, Set[str]]],
    flat_candidates: List[Dict[str, Any]],
    s1_records: Dict[str, Dict[str, Any]],
    target_records: Dict[str, Dict[str, Any]],
    ground_truth_map: Dict[str, List[str]],
    model_type: str = "logistic_regression",
    val_ratio: float = 0.20,
    random_seed: int = config.RANDOM_SEED
) -> Dict[str, Any]:
    """
    Splits by Source 1 entity (preventing leakage), trains model, searches threshold grid on validation set.
    """
    logger.info("Starting training and threshold tuning pipeline...")
    random.seed(random_seed)
    
    # ── Step 1: Leakage-proof Entity Split ──
    all_s1_ids = list(candidate_dict.keys())
    random.shuffle(all_s1_ids)
    
    val_size = max(1, int(len(all_s1_ids) * val_ratio))
    val_s1_set = set(all_s1_ids[:val_size])
    train_s1_set = set(all_s1_ids[val_size:])
    
    logger.info(f"Split {len(all_s1_ids):,} S1 entities into {len(train_s1_set):,} train and {len(val_s1_set):,} validation entities.")
    
    # ── Step 2: Separate train & val candidate pairs & label them ──
    train_pairs = []
    val_pairs = []
    
    for pair in flat_candidates:
        s1 = pair["source1_id"]
        tgt = pair["target_id"]
        true_tgts = ground_truth_map.get(s1, [])
        label = 1 if tgt in true_tgts else 0
        pair_with_label = dict(pair)
        pair_with_label["label"] = label
        
        if s1 in train_s1_set:
            train_pairs.append(pair_with_label)
        else:
            val_pairs.append(pair_with_label)
            
    train_pos = sum(p["label"] for p in train_pairs)
    train_neg = len(train_pairs) - train_pos
    val_pos = sum(p["label"] for p in val_pairs)
    val_neg = len(val_pairs) - val_pos
    
    logger.info(f"Train candidate pairs: {len(train_pairs):,} (pos: {train_pos:,}, neg: {train_neg:,})")
    logger.info(f"Validation candidate pairs: {len(val_pairs):,} (pos: {val_pos:,}, neg: {val_neg:,})")
    
    # If no training pairs, handle edge case gracefully
    if not train_pairs:
        raise ValueError("No candidate pairs available for training. Check blocking configuration.")
        
    # ── Step 3: Feature Extraction ──
    logger.info("Extracting features for training pairs...")
    X_train, tr_s1, tr_tgt = build_features_matrix(train_pairs, s1_records, target_records)
    y_train = np.array([p["label"] for p in train_pairs], dtype=np.int32)
    
    logger.info("Extracting features for validation pairs...")
    X_val, val_s1, val_tgt = build_features_matrix(val_pairs, s1_records, target_records)
    y_val = np.array([p["label"] for p in val_pairs], dtype=np.int32)
    
    # ── Step 4: Model Training ──
    logger.info(f"Fitting supervised classifier ({model_type})...")
    model = create_model(model_type=model_type, random_seed=random_seed)
    model.fit(X_train, y_train)
    save_model(model, config.MODEL_PATH)
    
    # ── Step 5: Inference on Validation Candidate Pairs ──
    val_probs = model.predict_proba(X_val)[:, 1] if len(val_pairs) > 0 else np.array([])
    
    # Map probabilities to (s1_id, tgt_id)
    val_pair_probs: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for i in range(len(val_pairs)):
        val_pair_probs[val_s1[i]].append((val_tgt[i], float(val_probs[i])))
        
    # ── Step 6: Threshold Grid Search on Validation Entities ──
    logger.info("Searching optimal classification threshold on validation set...")
    val_entities_list = list(val_s1_set)
    best_threshold = config.DEFAULT_THRESHOLD
    best_f05 = -1.0
    threshold_results = []
    
    print("\n" + "=" * 65)
    print(f"{'Threshold':<12}{'Val Macro F0.5':<18}{'Precision':<15}{'Recall':<15}")
    print("-" * 65)
    
    for thresh in config.THRESHOLDS:
        # Generate predictions for each val entity using current threshold
        preds_at_thresh: Dict[str, List[str]] = {}
        for s1_id in val_entities_list:
            cand_probs = val_pair_probs.get(s1_id, [])
            matched = [tgt for tgt, p in cand_probs if p >= thresh]
            preds_at_thresh[s1_id] = matched
            
        metrics = evaluate_predictions(ground_truth_map, preds_at_thresh, val_entities_list)
        f05 = metrics["macro_f05"]
        p = metrics["macro_precision"]
        r = metrics["macro_recall"]
        
        threshold_results.append({
            "threshold": thresh,
            "macro_f05": f05,
            "macro_precision": p,
            "macro_recall": r
        })
        print(f"{thresh:<12.2f}{f05:<18.4f}{p:<15.4f}{r:<15.4f}")
        
        if f05 > best_f05:
            best_f05 = f05
            best_threshold = thresh
            
    print("=" * 65)
    logger.info(f"Optimal Threshold: {best_threshold:.2f} with Val Macro F0.5 = {best_f05:.4f}")
    
    # Save threshold
    threshold_meta = {
        "best_threshold": best_threshold,
        "validation_macro_f05": best_f05,
        "grid_results": threshold_results
    }
    with open(config.THRESHOLD_PATH, "w", encoding="utf-8") as f:
        json.dump(threshold_meta, f, indent=2)
        
    results = {
        "model_type": model_type,
        "train_pairs_count": len(train_pairs),
        "val_pairs_count": len(val_pairs),
        "train_s1_count": len(train_s1_set),
        "val_s1_count": len(val_s1_set),
        "best_threshold": best_threshold,
        "best_val_f05": best_f05,
        "threshold_grid": threshold_results
    }
    
    with open(config.METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    return results
