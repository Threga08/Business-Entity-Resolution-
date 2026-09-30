"""
Validation script for submission TSVs.
Checks all format, integrity, subset, and uniqueness constraints.
Usage:
    python scripts/validate_submission.py
"""
import os
import sys
import csv
from typing import Set, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.data_loader import detect_delimiter

def validate_submission(
    matching_path: str = config.MATCHING_RESULTS_TSV,
    candidate_path: str = config.CANDIDATE_PAIRS_TSV,
    sample_s1_path: str = config.SAMPLE_SOURCE1
) -> bool:
    print("\n" + "=" * 50)
    print("SUBMISSION VALIDATION")
    print("=" * 50)
    
    errors = []
    
    # 1. Existence check
    if not os.path.exists(matching_path):
        errors.append(f"Matching results file not found: {matching_path}")
    if not os.path.exists(candidate_path):
        errors.append(f"Candidate pairs file not found: {candidate_path}")
        
    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return False
        
    # 2. Check Delimiters
    m_sep = detect_delimiter(matching_path)
    c_sep = detect_delimiter(candidate_path)
    if m_sep != "\t":
        errors.append(f"matching_results.tsv is not tab-separated (detected: {repr(m_sep)})")
    if c_sep != "\t":
        errors.append(f"candidate_pairs.tsv is not tab-separated (detected: {repr(c_sep)})")
        
    # 3. Validate matching_results.tsv
    matching_s1_seen: Set[str] = set()
    s1_to_matches = {}
    
    with open(matching_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        if header != ["source1_entity_id", "matched_entity_ids"]:
            errors.append(f"Invalid matching_results header: {header} (expected: ['source1_entity_id', 'matched_entity_ids'])")
            
        line_num = 1
        for row in reader:
            line_num += 1
            if len(row) != 2:
                errors.append(f"matching_results.tsv line {line_num} does not have exactly 2 columns: {row}")
                continue
                
            s1_id = row[0].strip()
            raw_matches = row[1].strip()
            
            # Check duplicate S1
            if s1_id in matching_s1_seen:
                errors.append(f"Duplicate Source 1 ID in matching_results: {s1_id}")
            matching_s1_seen.add(s1_id)
            
            matches = [m.strip() for m in raw_matches.split(",") if m.strip()]
            
            # Check duplicate matched IDs
            if len(matches) != len(set(matches)):
                errors.append(f"Duplicate matched IDs for S1 {s1_id}: {matches}")
                
            # Check ID validity: no S1 ID inside matches, only S2/S3
            for m in matches:
                if m.startswith("S1-") or m.startswith("s1_"):
                    errors.append(f"Invalid match ID '{m}' in matching_results (contains S1 ID)")
                if not (m.startswith("S2-") or m.startswith("S3-") or "-2-" in m or "-3-" in m):
                    errors.append(f"Unexpected target ID format: '{m}'")
                    
            s1_to_matches[s1_id] = set(matches)
            
    # 4. Validate candidate_pairs.tsv
    candidate_s1_seen: Set[str] = set()
    s1_to_cands = {}
    
    with open(candidate_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        if header != ["source1_entity_id", "candidate_entity_ids"]:
            errors.append(f"Invalid candidate_pairs header: {header} (expected: ['source1_entity_id', 'candidate_entity_ids'])")
            
        line_num = 1
        for row in reader:
            line_num += 1
            if len(row) != 2:
                errors.append(f"candidate_pairs.tsv line {line_num} does not have exactly 2 columns: {row}")
                continue
                
            s1_id = row[0].strip()
            raw_cands = row[1].strip()
            
            # Check duplicate S1
            if s1_id in candidate_s1_seen:
                errors.append(f"Duplicate Source 1 ID in candidate_pairs: {s1_id}")
            candidate_s1_seen.add(s1_id)
            
            cands = [c.strip() for c in raw_cands.split(",") if c.strip()]
            
            # Check duplicate candidate IDs
            if len(cands) != len(set(cands)):
                errors.append(f"Duplicate candidate IDs for S1 {s1_id}: {cands}")
                
            for c in cands:
                if c.startswith("S1-") or c.startswith("s1_"):
                    errors.append(f"Invalid candidate ID '{c}' (contains S1 ID)")
                    
            s1_to_cands[s1_id] = set(cands)
            
    # 5. Check consistency: every Source 1 in matching must exist in candidate pairs and vice versa
    if matching_s1_seen != candidate_s1_seen:
        diff1 = len(matching_s1_seen - candidate_s1_seen)
        diff2 = len(candidate_s1_seen - matching_s1_seen)
        errors.append(f"Mismatch in S1 entities between files ({diff1} in match but not cand, {diff2} in cand but not match)")
        
    # 6. Check that final matches are a strict subset of candidate pairs
    subset_violations = 0
    for s1_id, matches in s1_to_matches.items():
        cands = s1_to_cands.get(s1_id, set())
        invalid_matches = matches - cands
        if invalid_matches:
            subset_violations += 1
            if subset_violations <= 5:
                errors.append(f"S1 {s1_id} has matches not in candidate list: {invalid_matches}")
    if subset_violations > 5:
        errors.append(f"Total {subset_violations} Source 1 entities have matches not in candidates list.")
        
    print(f"Total Source 1 in matching_results: {len(matching_s1_seen):,}")
    print(f"Total Source 1 in candidate_pairs:  {len(candidate_s1_seen):,}")
    print(f"Total matches across dataset:      {sum(len(m) for m in s1_to_matches.values()):,}")
    print(f"Total candidates across dataset:   {sum(len(c) for c in s1_to_cands.values()):,}")
    
    if not errors:
        print("\n" + "=" * 50)
        print("RESULT: PASS")
        print("All submission validation checks passed successfully!")
        print("=" * 50 + "\n")
        return True
    else:
        print("\n" + "=" * 50)
        print(f"RESULT: FAIL ({len(errors)} errors found)")
        print("=" * 50)
        for err in errors[:20]:
            print(f"  [ERROR] {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more errors.")
        print("=" * 50 + "\n")
        return False

if __name__ == "__main__":
    success = validate_submission()
    sys.exit(0 if success else 1)
