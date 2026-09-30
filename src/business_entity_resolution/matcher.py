"""
Real-time Entity Matcher Engine.
Orchestrates normalization, candidate blocking, 29-feature extraction, ML inference,
confidence scoring, and explanation generation for any Source 1 business.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

from . import config
from .preprocessing import normalize_business_name, normalize_address, normalize_country
from .blocking import BlockingIndex
from .features import compute_pair_features, FEATURE_COLUMNS
from .model import load_model
from .data_loader import load_source_df
from .prediction import load_optimal_threshold

logger = config.logger

class RealTimeMatcher:
    """Singleton matcher engine maintaining indexed target sources and loaded ML model."""
    _instance: Optional["RealTimeMatcher"] = None

    def __init__(self, mode: str = "sample"):
        self.mode = mode
        self.model = None
        self.threshold = config.DEFAULT_THRESHOLD
        self.indexer: Optional[BlockingIndex] = None
        self.target_records: Dict[str, Dict[str, Any]] = {}
        self.s2_df: Optional[pd.DataFrame] = None
        self.s3_df: Optional[pd.DataFrame] = None
        self.initialized = False

    @classmethod
    def get_instance(cls, mode: str = "sample") -> "RealTimeMatcher":
        if cls._instance is None:
            cls._instance = RealTimeMatcher(mode=mode)
            cls._instance.initialize()
        return cls._instance

    def initialize(self) -> None:
        """Loads model, threshold, and indexes target datasets."""
        logger.info("Initializing RealTimeMatcher engine...")
        
        # Load Model
        if os.path.exists(config.MODEL_PATH):
            self.model = load_model(config.MODEL_PATH)
        else:
            logger.warning(f"Model file not found at {config.MODEL_PATH}. Matching will require model training first.")
            
        # Load Threshold
        self.threshold = load_optimal_threshold()
        logger.info(f"Loaded decision threshold: {self.threshold:.2f}")

        # Load S2 and S3 target sources
        s2_path = config.SAMPLE_SOURCE2 if self.mode == "sample" else config.RAW_SOURCE2
        s3_path = config.SAMPLE_SOURCE3 if self.mode == "sample" else config.RAW_SOURCE3

        if not os.path.exists(s2_path) or not os.path.exists(s3_path):
            logger.warning("Target source files not found. Run create_sample first.")
            return

        from .preprocessing import preprocess_dataframe
        logger.info("Loading and indexing Source 2 and Source 3...")
        raw_s2 = load_source_df(s2_path)
        raw_s3 = load_source_df(s3_path)

        proc_s2 = preprocess_dataframe(raw_s2)
        proc_s3 = preprocess_dataframe(raw_s3)
        combined_target = pd.concat([proc_s2, proc_s3], ignore_index=True)

        self.indexer = BlockingIndex(max_candidates_per_entity=config.MAX_CANDIDATES_PER_S1)
        self.indexer.build_index(combined_target)
        self.target_records = self.indexer.target_records
        self.initialized = True
        logger.info(f"RealTimeMatcher ready. {len(self.target_records):,} target entities indexed.")

    def match_entity(
        self,
        business_name: str,
        business_address: str,
        country: str,
        source1_id: str = "MANUAL-INPUT",
        threshold_override: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Runs full real pipeline for a single Source 1 business:
        1. Normalization
        2. Inverted Blocking Candidate Generation
        3. 29 Pairwise Feature Calculations
        4. Supervised ML Probability Prediction
        5. Confidence Stratification (High, Likely, Possible)
        6. Detailed Feature Breakdown for Explainability
        """
        if not self.initialized or self.indexer is None:
            self.initialize()

        if self.model is None:
            raise RuntimeError("ML model has not been trained yet. Train the model first.")

        active_threshold = threshold_override if threshold_override is not None else self.threshold

        # Step 1: Normalization
        norm_name, name_no_suf = normalize_business_name(business_name)
        norm_addr, numbers, postals = normalize_address(business_address)
        norm_ctry = normalize_country(country)

        s1_rec = {
            "entity_id": source1_id,
            "norm_name": norm_name,
            "name_no_suffix": name_no_suf,
            "norm_address": norm_addr,
            "norm_country": norm_ctry,
            "address_numbers": numbers,
            "postal_codes": postals,
            "business_name": business_name,
            "business_address": business_address,
            "country": country,
        }

        # Step 2: Blocking
        cand_rules_map = self.indexer.get_candidates_for_entity(
            source1_id, norm_name, name_no_suf, norm_addr, norm_ctry, numbers, postals
        )

        if not cand_rules_map:
            return {
                "source1": s1_rec,
                "has_matches": False,
                "message": "NO RELIABLE MATCH FOUND. The business may be a singleton or the available records may not contain a sufficiently similar candidate.",
                "total_candidates": 0,
                "source2_matches": [],
                "source3_matches": [],
            }

        # Step 3: Feature Calculation
        candidate_ids = list(cand_rules_map.keys())
        features_rows = []
        raw_feats_list = []

        for tid in candidate_ids:
            tgt_rec = self.target_records.get(tid, {})
            rules = list(cand_rules_map[tid])
            feats = compute_pair_features(s1_rec, tgt_rec, rules)
            raw_feats_list.append(feats)
            features_rows.append([feats[col] for col in FEATURE_COLUMNS])

        X = np.array(features_rows, dtype=np.float32)

        # Step 4: ML Model Probability Prediction
        probabilities = self.model.predict_proba(X)[:, 1]

        # Step 5: Rank & Filter Matches
        matched_candidates = []
        for i, tid in enumerate(candidate_ids):
            prob = float(probabilities[i])
            if prob >= active_threshold:
                tgt_rec = self.target_records.get(tid, {})
                f = raw_feats_list[i]

                # Confidence category
                conf_pct = round(prob * 100, 1)
                if conf_pct >= 90.0:
                    badge_class = "badge-high"
                    badge_label = "HIGH CONFIDENCE MATCH"
                elif conf_pct >= 75.0:
                    badge_class = "badge-likely"
                    badge_label = "LIKELY MATCH"
                else:
                    badge_class = "badge-possible"
                    badge_label = "POSSIBLE MATCH"

                matched_candidates.append({
                    "target_id": tid,
                    "target_source": "Source 2" if (tid.startswith("S2-") or "-2-" in tid) else "Source 3",
                    "business_name": tgt_rec.get("business_name", ""),
                    "business_address": tgt_rec.get("business_address", ""),
                    "country": tgt_rec.get("country", ""),
                    "confidence_score": prob,
                    "confidence_pct": conf_pct,
                    "badge_class": badge_class,
                    "badge_label": badge_label,
                    "name_similarity_pct": round(f["feat_name_sim"] * 100, 1),
                    "token_sort_sim_pct": round(f["feat_token_sort_sim"] * 100, 1),
                    "address_similarity_pct": round(f["feat_addr_sim"] * 100, 1),
                    "country_match": "MATCH" if f["feat_country_eq"] == 1.0 else ("DIFFERENT" if f["feat_country_diff"] == 1.0 else "MISSING"),
                    "shared_numbers": list(s1_rec["address_numbers"] & tgt_rec.get("address_numbers", set())),
                    "shared_postal": f["feat_has_shared_postal"] == 1.0,
                    "triggered_rules": list(cand_rules_map[tid]),
                    "features_detail": f
                })

        # Sort descending by confidence
        matched_candidates.sort(key=lambda x: x["confidence_score"], reverse=True)

        s2_matches = [m for m in matched_candidates if m["target_source"] == "Source 2"]
        s3_matches = [m for m in matched_candidates if m["target_source"] == "Source 3"]

        has_matches = len(matched_candidates) > 0

        return {
            "source1": {
                "entity_id": source1_id,
                "business_name": business_name,
                "business_address": business_address,
                "country": country,
                "norm_name": norm_name,
                "norm_address": norm_addr
            },
            "has_matches": has_matches,
            "threshold_used": active_threshold,
            "total_candidates_blocked": len(candidate_ids),
            "total_matches_found": len(matched_candidates),
            "source2_matches": s2_matches,
            "source3_matches": s3_matches,
            "all_matches": matched_candidates,
            "message": "" if has_matches else "NO RELIABLE MATCH FOUND. The business may be a singleton or the available records may not contain a sufficiently similar candidate."
        }
