"""
Blocking and Candidate Generation Module for scalable Entity Resolution.
Generates candidate pairs using multi-key union blocking, avoiding O(N*M) comparisons.
Tracks blocking rule provenance for feature engineering and evaluates candidate recall.
"""
import os
import json
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional
import numpy as np
import pandas as pd

from . import config

logger = config.logger

STOP_TOKENS = {
    "the", "and", "inc", "llc", "corp", "ltd", "co", "of", "in", "for", "at", "by",
    "services", "company", "group", "enterprises", "solutions", "international", "holdings"
}

class BlockingIndex:
    """Multi-index candidate generation engine across target sources (S2 and S3)."""
    
    def __init__(self, max_candidates_per_entity: int = config.MAX_CANDIDATES_PER_S1):
        self.max_candidates = max_candidates_per_entity
        self.exact_name_idx: Dict[str, List[str]] = defaultdict(list)
        self.suffix_name_idx: Dict[str, List[str]] = defaultdict(list)
        self.name_prefix_idx: Dict[str, List[str]] = defaultdict(list)
        self.country_name_prefix_idx: Dict[str, List[str]] = defaultdict(list)
        self.postal_idx: Dict[str, List[str]] = defaultdict(list)
        self.country_postal_idx: Dict[str, List[str]] = defaultdict(list)
        self.name_token_idx: Dict[str, List[str]] = defaultdict(list)
        self.combined_num_name_idx: Dict[str, List[str]] = defaultdict(list)
        
        self.target_records: Dict[str, Dict[str, Any]] = {}
        
    def build_index(self, target_df: pd.DataFrame) -> None:
        """Indexes all target entities (S2 and S3)."""
        logger.info(f"Building blocking indexes for {len(target_df):,} target entities...")
        
        for _, row in target_df.iterrows():
            eid = str(row[config.ENTITY_ID]).strip()
            norm_name = str(row.get("norm_name", "")).strip()
            name_no_suf = str(row.get("name_no_suffix", "")).strip()
            norm_addr = str(row.get("norm_address", "")).strip()
            ctry = str(row.get("norm_country", "")).strip()
            numbers = set(str(row.get("address_numbers", "")).split()) if row.get("address_numbers") else set()
            postals = set(str(row.get("postal_codes", "")).split()) if row.get("postal_codes") else set()
            
            # Store normalized record
            self.target_records[eid] = {
                "entity_id": eid,
                "norm_name": norm_name,
                "name_no_suffix": name_no_suf,
                "norm_address": norm_addr,
                "norm_country": ctry,
                "address_numbers": numbers,
                "postal_codes": postals,
                "business_name": str(row.get(config.BUSINESS_NAME, "")),
                "business_address": str(row.get(config.BUSINESS_ADDRESS, "")),
                "country": str(row.get(config.COUNTRY, "")),
            }
            
            # 1. Exact normalized name
            if norm_name:
                self.exact_name_idx[norm_name].append(eid)
                
            # 2. Suffix-free name
            if name_no_suf and name_no_suf != norm_name:
                self.suffix_name_idx[name_no_suf].append(eid)
                
            # 3. Name prefix (4 chars)
            if len(norm_name) >= config.NAME_PREFIX_LEN:
                prefix = norm_name[:config.NAME_PREFIX_LEN]
                self.name_prefix_idx[prefix].append(eid)
                if ctry:
                    self.country_name_prefix_idx[f"{ctry}#{prefix}"].append(eid)
                    
            # 4. Postal / PIN codes
            for p in postals:
                if len(p) >= 3:
                    self.postal_idx[p].append(eid)
                    if ctry:
                        self.country_postal_idx[f"{ctry}#{p}"].append(eid)
                        
            # 5. Name tokens (filtered)
            tokens = [t for t in norm_name.split() if len(t) >= 4 and t not in STOP_TOKENS]
            for t in tokens:
                self.name_token_idx[t].append(eid)
                
            # 6. Combined address number + name prefix
            if len(norm_name) >= 3:
                short_pfx = norm_name[:3]
                for num in numbers:
                    self.combined_num_name_idx[f"{num}#{short_pfx}"].append(eid)
                    
        logger.info(f"Index built. Target entities indexed: {len(self.target_records):,}")
        
    def get_candidates_for_entity(
        self,
        s1_id: str,
        norm_name: str,
        name_no_suf: str,
        norm_addr: str,
        ctry: str,
        numbers: Set[str],
        postals: Set[str]
    ) -> Dict[str, Set[str]]:
        """
        Retrieves union candidate set for a single Source 1 entity.
        Returns:
            dict mapping target_id -> set of rule_names that triggered it
        """
        candidates: Dict[str, Set[str]] = defaultdict(set)
        
        # Rule 1: Exact Name
        if norm_name and norm_name in self.exact_name_idx:
            for tid in self.exact_name_idx[norm_name]:
                candidates[tid].add("exact_name")
                
        # Rule 2: Suffix-free Name
        if name_no_suf and name_no_suf in self.suffix_name_idx:
            for tid in self.suffix_name_idx[name_no_suf]:
                candidates[tid].add("suffix_name")
                
        # Rule 3: Combined Number + Name Prefix
        if len(norm_name) >= 3:
            short_pfx = norm_name[:3]
            for num in numbers:
                key = f"{num}#{short_pfx}"
                if key in self.combined_num_name_idx:
                    for tid in self.combined_num_name_idx[key][:100]:
                        candidates[tid].add("combined_num_name")
                        
        # Rule 4: Country + Name Prefix
        if len(norm_name) >= config.NAME_PREFIX_LEN:
            pfx = norm_name[:config.NAME_PREFIX_LEN]
            if ctry:
                cp_key = f"{ctry}#{pfx}"
                if cp_key in self.country_name_prefix_idx:
                    for tid in self.country_name_prefix_idx[cp_key][:150]:
                        candidates[tid].add("country_name_prefix")
            elif pfx in self.name_prefix_idx:
                for tid in self.name_prefix_idx[pfx][:150]:
                    candidates[tid].add("name_prefix")
                    
        # Rule 5: Country + Postal Key
        for p in postals:
            if len(p) >= 3:
                if ctry:
                    cp_key = f"{ctry}#{p}"
                    if cp_key in self.country_postal_idx:
                        for tid in self.country_postal_idx[cp_key][:100]:
                            candidates[tid].add("country_postal")
                elif p in self.postal_idx:
                    for tid in self.postal_idx[p][:100]:
                        candidates[tid].add("postal")
                        
        # Rule 6: Name Token Inverted Index
        tokens = [t for t in norm_name.split() if len(t) >= 4 and t not in STOP_TOKENS]
        for t in tokens:
            if t in self.name_token_idx:
                posting = self.name_token_idx[t]
                if len(posting) <= 200:
                    for tid in posting:
                        candidates[tid].add("name_token")
                        
        # Cap candidates per entity to avoid memory bloat
        if len(candidates) > self.max_candidates:
            sorted_candidates = sorted(candidates.items(), key=lambda item: len(item[1]), reverse=True)
            candidates = dict(sorted_candidates[:self.max_candidates])
            
        return candidates

    def generate_candidate_pairs(
        self,
        s1_df: pd.DataFrame
    ) -> Tuple[Dict[str, Dict[str, Set[str]]], List[Dict[str, Any]]]:
        """
        Generates candidate pairs for all Source 1 entities in s1_df.
        Returns: (candidate_dict, flat_candidate_list)
        """
        logger.info(f"Generating candidate pairs for {len(s1_df):,} Source 1 entities...")
        candidate_dict: Dict[str, Dict[str, Set[str]]] = {}
        flat_pairs: List[Dict[str, Any]] = []
        
        for _, row in s1_df.iterrows():
            s1_id = str(row[config.ENTITY_ID]).strip()
            norm_name = str(row.get("norm_name", "")).strip()
            name_no_suf = str(row.get("name_no_suffix", "")).strip()
            norm_addr = str(row.get("norm_address", "")).strip()
            ctry = str(row.get("norm_country", "")).strip()
            numbers = set(str(row.get("address_numbers", "")).split()) if row.get("address_numbers") else set()
            postals = set(str(row.get("postal_codes", "")).split()) if row.get("postal_codes") else set()
            
            cand_map = self.get_candidates_for_entity(
                s1_id, norm_name, name_no_suf, norm_addr, ctry, numbers, postals
            )
            candidate_dict[s1_id] = cand_map
            
            for tid, rules in cand_map.items():
                flat_pairs.append({
                    "source1_id": s1_id,
                    "target_id": tid,
                    "blocking_rules": list(rules)
                })
                
        logger.info(f"Generated {len(flat_pairs):,} total candidate pairs across {len(candidate_dict):,} S1 entities.")
        return candidate_dict, flat_pairs

def evaluate_blocking(
    candidate_dict: Dict[str, Dict[str, Set[str]]],
    ground_truth_map: Dict[str, List[str]],
    total_target_records: int
) -> Dict[str, Any]:
    """Evaluates candidate recall and reduction ratio."""
    total_true_matches = 0
    true_matches_found = 0
    candidate_counts = []
    
    for s1_id, true_targets in ground_truth_map.items():
        if s1_id not in candidate_dict:
            continue
        cands = candidate_dict[s1_id]
        candidate_counts.append(len(cands))
        
        for tgt in true_targets:
            total_true_matches += 1
            if tgt in cands:
                true_matches_found += 1
                
    recall = (true_matches_found / total_true_matches) if total_true_matches > 0 else 0.0
    num_s1 = len(candidate_dict)
    avg_cands = float(np.mean(candidate_counts)) if candidate_counts else 0.0
    median_cands = float(np.median(candidate_counts)) if candidate_counts else 0.0
    max_cands = int(np.max(candidate_counts)) if candidate_counts else 0
    total_candidates = sum(candidate_counts)
    
    total_cartesian = num_s1 * max(1, total_target_records)
    reduction_ratio = 1.0 - (total_candidates / total_cartesian) if total_cartesian > 0 else 1.0
    
    report = {
        "total_s1_evaluated": num_s1,
        "total_true_matches": total_true_matches,
        "true_matches_found": true_matches_found,
        "candidate_recall": round(recall, 4),
        "candidate_recall_pct": f"{recall * 100:.2f}%",
        "total_candidates_generated": total_candidates,
        "avg_candidates_per_s1": round(avg_cands, 2),
        "median_candidates_per_s1": round(median_cands, 2),
        "max_candidates_per_s1": max_cands,
        "reduction_ratio": round(reduction_ratio, 6),
        "reduction_ratio_pct": f"{reduction_ratio * 100:.4f}%"
    }
    
    with open(config.BLOCKING_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report
