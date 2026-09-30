"""
Submission module for saving and verifying matching_results.tsv and candidate_pairs.tsv.
Ensures exact column headers, TSV format, duplicate removal, and consistency rules.
"""
import os
import csv
import logging
from typing import Dict, List, Set, Optional

from . import config

logger = config.logger

def save_submission_files(
    predictions_map: Dict[str, List[str]],
    candidates_map: Dict[str, List[str]],
    all_s1_ids: List[str],
    matching_out_path: str = config.MATCHING_RESULTS_TSV,
    candidate_out_path: str = config.CANDIDATE_PAIRS_TSV
) -> None:
    """
    Writes output/matching_results.tsv and output/candidate_pairs.tsv.
    
    Guarantees:
      - Exactly every Source 1 ID present once.
      - TSV delimited with no quoting.
      - Comma-separated matched IDs (or empty string if none).
      - No duplicate target IDs.
      - Every match is a subset of candidates.
    """
    os.makedirs(os.path.dirname(matching_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(candidate_out_path), exist_ok=True)
    
    logger.info(f"Writing matching results to {matching_out_path}...")
    with open(matching_out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["source1_entity_id", "matched_entity_ids"])
        
        for s1 in all_s1_ids:
            matches = predictions_map.get(s1, [])
            # Deduplicate preserving order
            seen = set()
            clean_matches = [m for m in matches if not (m in seen or seen.add(m))]
            # Guarantee every match is in candidates
            cands = set(candidates_map.get(s1, []))
            valid_matches = [m for m in clean_matches if m in cands]
            matches_str = ",".join(valid_matches)
            writer.writerow([s1, matches_str])
            
    logger.info(f"Writing candidate pairs to {candidate_out_path}...")
    with open(candidate_out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["source1_entity_id", "candidate_entity_ids"])
        
        for s1 in all_s1_ids:
            cands = candidates_map.get(s1, [])
            seen = set()
            clean_cands = [c for c in cands if not (c in seen or seen.add(c))]
            cands_str = ",".join(clean_cands)
            writer.writerow([s1, cands_str])
            
    logger.info("Submission files successfully created.")
