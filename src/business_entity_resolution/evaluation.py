"""
Evaluation module implementing the competition Macro F0.5 metric and diagnostics.
Calculates entity-level precision, recall, and F0.5 with exact singleton handling.
"""
from typing import Dict, List, Set, Tuple, Any
import numpy as np

def compute_entity_f05(
    true_set: Set[str],
    pred_set: Set[str]
) -> Tuple[float, float, float]:
    """
    Computes (precision, recall, f05) for a single Source 1 entity.
    
    Special Cases:
      - true empty AND pred empty: f05 = 1.0, precision = 1.0, recall = 1.0
      - true empty AND pred not empty: f05 = 0.0, precision = 0.0, recall = 1.0
      - true not empty AND pred empty: f05 = 0.0, precision = 1.0, recall = 0.0
    """
    # Special singleton / empty cases
    if len(true_set) == 0 and len(pred_set) == 0:
        return 1.0, 1.0, 1.0
    if len(true_set) == 0 and len(pred_set) > 0:
        return 0.0, 1.0, 0.0
    if len(true_set) > 0 and len(pred_set) == 0:
        return 1.0, 0.0, 0.0
        
    intersection = len(true_set & pred_set)
    precision = intersection / len(pred_set)
    recall = intersection / len(true_set)
    
    denom = (0.25 * precision) + recall
    if denom == 0.0:
        f05 = 0.0
    else:
        f05 = (1.25 * precision * recall) / denom
        
    return precision, recall, f05

def evaluate_predictions(
    ground_truth_map: Dict[str, List[str]],
    predictions_map: Dict[str, List[str]],
    s1_entities: List[str]
) -> Dict[str, float]:
    """
    Evaluates predictions against ground truth over a set of Source 1 entities.
    Returns:
        dict with macro_f05, macro_precision, macro_recall, exact_matches, total_evaluated.
    """
    precisions = []
    recalls = []
    f05_scores = []
    exact_matches = 0
    
    for s1_id in s1_entities:
        true_targets = set(ground_truth_map.get(s1_id, []))
        pred_targets = set(predictions_map.get(s1_id, []))
        
        p, r, f05 = compute_entity_f05(true_targets, pred_targets)
        precisions.append(p)
        recalls.append(r)
        f05_scores.append(f05)
        
        if true_targets == pred_targets:
            exact_matches += 1
            
    n = len(s1_entities)
    macro_f05 = float(np.mean(f05_scores)) if n > 0 else 0.0
    macro_p = float(np.mean(precisions)) if n > 0 else 0.0
    macro_r = float(np.mean(recalls)) if n > 0 else 0.0
    
    return {
        "macro_f05": round(macro_f05, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "exact_matches": exact_matches,
        "total_evaluated": n,
        "exact_match_ratio": round(exact_matches / n, 4) if n > 0 else 0.0
    }
