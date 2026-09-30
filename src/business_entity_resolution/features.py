"""
Feature engineering module for candidate pairs.
Extracts comprehensive name, address, country, and blocking rule features using RapidFuzz.
All calculations are self-contained with no external lookups.
"""
from typing import Dict, List, Set, Any, Tuple
import numpy as np
import pandas as pd
from rapidfuzz import fuzz

def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Computes Jaccard index between two sets."""
    if not set1 and not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0

def compute_pair_features(
    s1_rec: Dict[str, Any],
    tgt_rec: Dict[str, Any],
    rules: List[str]
) -> Dict[str, float]:
    """
    Computes all required features for a candidate pair (Source 1 entity, Target entity).
    """
    name1 = s1_rec.get("norm_name", "")
    name2 = tgt_rec.get("norm_name", "")
    
    nosuf1 = s1_rec.get("name_no_suffix", "")
    nosuf2 = tgt_rec.get("name_no_suffix", "")
    
    addr1 = s1_rec.get("norm_address", "")
    addr2 = tgt_rec.get("norm_address", "")
    
    c1 = s1_rec.get("norm_country", "")
    c2 = tgt_rec.get("norm_country", "")
    
    # ── 1. Name Features ──
    exact_name = 1.0 if name1 and name2 and name1 == name2 else 0.0
    exact_nosuf = 1.0 if nosuf1 and nosuf2 and nosuf1 == nosuf2 else 0.0
    
    name_sim = fuzz.ratio(name1, name2) / 100.0 if name1 and name2 else 0.0
    token_set_sim = fuzz.token_set_ratio(name1, name2) / 100.0 if name1 and name2 else 0.0
    token_sort_sim = fuzz.token_sort_ratio(name1, name2) / 100.0 if name1 and name2 else 0.0
    char_sim = fuzz.partial_ratio(name1, name2) / 100.0 if name1 and name2 else 0.0
    nosuf_sim = fuzz.ratio(nosuf1, nosuf2) / 100.0 if nosuf1 and nosuf2 else 0.0
    
    # Name tokens & length
    toks1 = set(name1.split())
    toks2 = set(name2.split())
    name_token_overlap = jaccard_similarity(toks1, toks2)
    
    max_n_len = max(len(name1), len(name2), 1)
    name_len_diff = abs(len(name1) - len(name2)) / max_n_len
    
    # ── 2. Address Features ──
    addr_sim = fuzz.ratio(addr1, addr2) / 100.0 if addr1 and addr2 else 0.0
    addr_tok_set_sim = fuzz.token_set_ratio(addr1, addr2) / 100.0 if addr1 and addr2 else 0.0
    
    # Address tokens & length
    atok1 = set(addr1.split())
    atok2 = set(addr2.split())
    addr_token_overlap = jaccard_similarity(atok1, atok2)
    shared_addr_token_count = float(len(atok1 & atok2))
    
    max_a_len = max(len(addr1), len(addr2), 1)
    addr_len_diff = abs(len(addr1) - len(addr2)) / max_a_len
    
    # Shared numbers & postal codes
    nums1 = s1_rec.get("address_numbers", set())
    nums2 = tgt_rec.get("address_numbers", set())
    num_overlap = jaccard_similarity(nums1, nums2)
    has_shared_number = 1.0 if (nums1 & nums2) else 0.0
    
    post1 = s1_rec.get("postal_codes", set())
    post2 = tgt_rec.get("postal_codes", set())
    has_shared_postal = 1.0 if (post1 & post2) else 0.0
    
    # ── 3. Country & Missing Value Indicators ──
    country_eq = 1.0 if (c1 and c2 and c1 == c2) else 0.0
    country_diff = 1.0 if (c1 and c2 and c1 != c2) else 0.0
    country_missing = 1.0 if (not c1 or not c2) else 0.0
    name_missing = 1.0 if (not name1 or not name2) else 0.0
    addr_missing = 1.0 if (not addr1 or not addr2) else 0.0
    
    # ── 4. Blocking Rule Indicators ──
    rule_set = set(rules) if rules else set()
    r_exact = 1.0 if "exact_name" in rule_set else 0.0
    r_nosuf = 1.0 if "suffix_name" in rule_set else 0.0
    r_pfx = 1.0 if ("country_name_prefix" in rule_set or "name_prefix" in rule_set) else 0.0
    r_postal = 1.0 if ("country_postal" in rule_set or "postal" in rule_set) else 0.0
    r_comb = 1.0 if "combined_num_name" in rule_set else 0.0
    r_tok = 1.0 if "name_token" in rule_set else 0.0
    r_count = float(len(rule_set))
    
    return {
        "feat_exact_name": exact_name,
        "feat_exact_nosuf": exact_nosuf,
        "feat_name_sim": name_sim,
        "feat_token_set_sim": token_set_sim,
        "feat_token_sort_sim": token_sort_sim,
        "feat_char_sim": char_sim,
        "feat_nosuf_sim": nosuf_sim,
        "feat_name_token_overlap": name_token_overlap,
        "feat_name_len_diff": name_len_diff,
        "feat_addr_sim": addr_sim,
        "feat_addr_tok_set_sim": addr_tok_set_sim,
        "feat_addr_token_overlap": addr_token_overlap,
        "feat_shared_addr_tokens": shared_addr_token_count,
        "feat_addr_len_diff": addr_len_diff,
        "feat_num_overlap": num_overlap,
        "feat_has_shared_num": has_shared_number,
        "feat_has_shared_postal": has_shared_postal,
        "feat_country_eq": country_eq,
        "feat_country_diff": country_diff,
        "feat_country_missing": country_missing,
        "feat_name_missing": name_missing,
        "feat_addr_missing": addr_missing,
        "feat_rule_exact": r_exact,
        "feat_rule_nosuf": r_nosuf,
        "feat_rule_pfx": r_pfx,
        "feat_rule_postal": r_postal,
        "feat_rule_comb": r_comb,
        "feat_rule_tok": r_tok,
        "feat_rule_count": r_count,
    }

FEATURE_COLUMNS = [
    "feat_exact_name",
    "feat_exact_nosuf",
    "feat_name_sim",
    "feat_token_set_sim",
    "feat_token_sort_sim",
    "feat_char_sim",
    "feat_nosuf_sim",
    "feat_name_token_overlap",
    "feat_name_len_diff",
    "feat_addr_sim",
    "feat_addr_tok_set_sim",
    "feat_addr_token_overlap",
    "feat_shared_addr_tokens",
    "feat_addr_len_diff",
    "feat_num_overlap",
    "feat_has_shared_num",
    "feat_has_shared_postal",
    "feat_country_eq",
    "feat_country_diff",
    "feat_country_missing",
    "feat_name_missing",
    "feat_addr_missing",
    "feat_rule_exact",
    "feat_rule_nosuf",
    "feat_rule_pfx",
    "feat_rule_postal",
    "feat_rule_comb",
    "feat_rule_tok",
    "feat_rule_count",
]

def build_features_matrix(
    candidate_pairs: List[Dict[str, Any]],
    s1_records: Dict[str, Dict[str, Any]],
    target_records: Dict[str, Dict[str, Any]]
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Constructs 2D numpy feature matrix for a list of candidate pairs.
    Returns:
        (X, s1_ids, target_ids)
    """
    rows = []
    s1_ids = []
    target_ids = []
    
    for pair in candidate_pairs:
        s1_id = pair["source1_id"]
        tid = pair["target_id"]
        rules = pair.get("blocking_rules", [])
        
        s1_rec = s1_records.get(s1_id, {})
        tgt_rec = target_records.get(tid, {})
        
        feats = compute_pair_features(s1_rec, tgt_rec, rules)
        rows.append([feats[col] for col in FEATURE_COLUMNS])
        s1_ids.append(s1_id)
        target_ids.append(tid)
        
    X = np.array(rows, dtype=np.float32) if rows else np.zeros((0, len(FEATURE_COLUMNS)), dtype=np.float32)
    return X, s1_ids, target_ids
