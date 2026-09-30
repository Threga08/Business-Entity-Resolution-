"""
Data Sampler module for creating balanced, relationship-preserving samples
from huge multi-million row datasets in seconds using optimized line streaming.
"""
import os
import random
from typing import Dict, Set, List, Tuple, Any

from . import config

logger = config.logger

def create_sample(
    sample_size: int = 100000,
    random_seed: int = config.RANDOM_SEED,
    output_dir: str = config.SAMPLE_DIR,
    distractor_ratio: float = 0.05
) -> Dict[str, Any]:
    """
    Extracts a representative, ground-truth-consistent sample of S1, S2, S3, and ground truth.
    Uses ultra-fast binary/text line streaming without pandas row iteration overhead.
    """
    random.seed(random_seed)
    os.makedirs(output_dir, exist_ok=True)
    
    gt_file = config.RAW_GROUND_TRUTH
    s1_file = config.RAW_SOURCE1
    s2_file = config.RAW_SOURCE2
    s3_file = config.RAW_SOURCE3
    
    logger.info(f"Starting sample creation (target S1 size: {sample_size:,})...")
    
    # ── Step 1: Scan ground truth ──
    logger.info("Scanning ground truth file...")
    matched_s1: List[Tuple[str, str]] = []
    singleton_s1: List[Tuple[str, str]] = []
    
    with open(gt_file, "r", encoding="utf-8", errors="replace") as f:
        header = f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            s1_id = parts[0].strip()
            matches_str = parts[1].strip() if len(parts) > 1 else ""
            if matches_str:
                matched_s1.append((s1_id, matches_str))
            else:
                singleton_s1.append((s1_id, ""))
                
    total_gt = len(matched_s1) + len(singleton_s1)
    logger.info(f"Ground truth records scanned: {total_gt:,} (with matches: {len(matched_s1):,}, singletons: {len(singleton_s1):,})")
    
    # ── Step 2: Reproducibly sample S1 records ──
    target_matched = min(len(matched_s1), int(sample_size * 0.80))
    target_singleton = min(len(singleton_s1), sample_size - target_matched)
    
    if target_matched + target_singleton < sample_size:
        remaining = sample_size - (target_matched + target_singleton)
        if len(matched_s1) > target_matched:
            target_matched = min(len(matched_s1), target_matched + remaining)
        elif len(singleton_s1) > target_singleton:
            target_singleton = min(len(singleton_s1), target_singleton + remaining)
            
    sampled_matched = random.sample(matched_s1, target_matched) if target_matched > 0 else []
    sampled_singletons = random.sample(singleton_s1, target_singleton) if target_singleton > 0 else []
    
    sampled_s1_pairs = sampled_matched + sampled_singletons
    random.shuffle(sampled_s1_pairs)
    
    sampled_s1_ids: Set[str] = {pair[0] for pair in sampled_s1_pairs}
    target_s2_ids: Set[str] = set()
    target_s3_ids: Set[str] = set()
    
    for s1_id, matches_str in sampled_s1_pairs:
        if matches_str:
            for m in matches_str.split(","):
                m = m.strip()
                if m.startswith("S2-") or "-2-" in m:
                    target_s2_ids.add(m)
                else:
                    target_s3_ids.add(m)
                    
    logger.info(f"Sampled {len(sampled_s1_ids):,} Source 1 entities ({len(sampled_matched):,} with matches, {len(sampled_singletons):,} singletons).")
    logger.info(f"Targets required: {len(target_s2_ids):,} S2 IDs, {len(target_s3_ids):,} S3 IDs.")
    
    # ── Step 3: Stream and extract Source 1 records ──
    s1_out_path = os.path.join(output_dir, "source1.tsv")
    s1_count = 0
    with open(s1_file, "r", encoding="utf-8", errors="replace") as in_f, \
         open(s1_out_path, "w", encoding="utf-8", newline="") as out_f:
        header = in_f.readline()
        out_f.write(header if header.endswith("\n") else header + "\n")
        for line in in_f:
            idx = line.find("\t")
            if idx != -1:
                eid = line[:idx].strip()
                if eid in sampled_s1_ids:
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    s1_count += 1
    logger.info(f"Saved {s1_count:,} Source 1 records to {s1_out_path}")
    
    # ── Step 4: Stream and extract Source 2 records ──
    s2_out_path = os.path.join(output_dir, "source2.tsv")
    s2_count = 0
    num_distractors_s2 = int(len(target_s2_ids) * distractor_ratio)
    distractors_s2 = 0
    with open(s2_file, "r", encoding="utf-8", errors="replace") as in_f, \
         open(s2_out_path, "w", encoding="utf-8", newline="") as out_f:
        header = in_f.readline()
        out_f.write(header if header.endswith("\n") else header + "\n")
        for line in in_f:
            idx = line.find("\t")
            if idx != -1:
                eid = line[:idx].strip()
                if eid in target_s2_ids:
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    s2_count += 1
                elif distractors_s2 < num_distractors_s2 and random.random() < 0.005:
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    distractors_s2 += 1
                    s2_count += 1
    logger.info(f"Saved {s2_count:,} Source 2 records ({distractors_s2} distractors) to {s2_out_path}")
    
    # ── Step 5: Stream and extract Source 3 records ──
    s3_out_path = os.path.join(output_dir, "source3.tsv")
    s3_count = 0
    num_distractors_s3 = int(len(target_s3_ids) * distractor_ratio)
    distractors_s3 = 0
    with open(s3_file, "r", encoding="utf-8", errors="replace") as in_f, \
         open(s3_out_path, "w", encoding="utf-8", newline="") as out_f:
        header = in_f.readline()
        out_f.write(header if header.endswith("\n") else header + "\n")
        for line in in_f:
            idx = line.find("\t")
            if idx != -1:
                eid = line[:idx].strip()
                if eid in target_s3_ids:
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    s3_count += 1
                elif distractors_s3 < num_distractors_s3 and random.random() < 0.005:
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    distractors_s3 += 1
                    s3_count += 1
    logger.info(f"Saved {s3_count:,} Source 3 records ({distractors_s3} distractors) to {s3_out_path}")
    
    # ── Step 6: Save sample ground truth ──
    gt_out_path = os.path.join(output_dir, "ground_truth.tsv")
    with open(gt_out_path, "w", encoding="utf-8", newline="") as out_f:
        out_f.write("source1_entity_id\tmatched_entity_ids\n")
        for s1_id, matches_str in sampled_s1_pairs:
            out_f.write(f"{s1_id}\t{matches_str}\n")
    logger.info(f"Saved sample ground truth to {gt_out_path}")
    
    stats = {
        "s1_count": s1_count,
        "s2_count": s2_count,
        "s3_count": s3_count,
        "gt_records": len(sampled_s1_pairs),
        "target_matched_s1": len(sampled_matched),
        "target_singleton_s1": len(sampled_singletons),
        "distractors_s2": distractors_s2,
        "distractors_s3": distractors_s3
    }
    logger.info(f"Sample creation complete! Stats: {stats}")
    return stats
