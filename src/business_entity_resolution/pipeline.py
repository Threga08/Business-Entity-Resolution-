"""
End-to-End Orchestration Pipeline for Business Entity Resolution.
Supports '--mode sample' and '--mode full' execution.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
import pandas as pd

from . import config
from .data_loader import load_source_df, load_ground_truth_map
from .preprocessing import preprocess_dataframe
from .blocking import BlockingIndex, evaluate_blocking
from .training import train_and_tune_pipeline
from .prediction import predict_matches, load_optimal_threshold
from .submission import save_submission_files
from .evaluation import evaluate_predictions

logger = config.logger

class EntityResolutionPipeline:
    """Orchestrates end-to-end training, evaluation, and prediction."""
    
    def __init__(self, mode: str = "sample"):
        self.mode = mode
        self.s1_file = config.SAMPLE_SOURCE1 if mode == "sample" else config.RAW_SOURCE1
        self.s2_file = config.SAMPLE_SOURCE2 if mode == "sample" else config.RAW_SOURCE2
        self.s3_file = config.SAMPLE_SOURCE3 if mode == "sample" else config.RAW_SOURCE3
        self.gt_file = config.SAMPLE_GROUND_TRUTH if mode == "sample" else config.RAW_GROUND_TRUTH
        
        self.s1_df: Optional[pd.DataFrame] = None
        self.target_df: Optional[pd.DataFrame] = None
        self.ground_truth_map: Dict[str, list] = {}
        
        self.indexer: Optional[BlockingIndex] = None
        self.candidate_dict: Dict[str, dict] = {}
        self.flat_candidates: list = []
        
    def load_and_preprocess_data(self) -> None:
        """Loads and normalizes S1, S2, S3, and ground truth."""
        logger.info(f"Loading data for mode: {self.mode}...")
        
        if not os.path.exists(self.s1_file):
            raise FileNotFoundError(f"Source 1 file not found: {self.s1_file}. Run create_sample first.")
            
        raw_s1 = load_source_df(self.s1_file)
        raw_s2 = load_source_df(self.s2_file)
        raw_s3 = load_source_df(self.s3_file)
        
        logger.info("Preprocessing Source 1...")
        self.s1_df = preprocess_dataframe(raw_s1)
        
        logger.info("Preprocessing Source 2...")
        proc_s2 = preprocess_dataframe(raw_s2)
        
        logger.info("Preprocessing Source 3...")
        proc_s3 = preprocess_dataframe(raw_s3)
        
        self.target_df = pd.concat([proc_s2, proc_s3], ignore_index=True)
        logger.info(f"Combined target entities (S2 + S3): {len(self.target_df):,}")
        
        if os.path.exists(self.gt_file):
            logger.info("Loading ground truth mapping...")
            self.ground_truth_map = load_ground_truth_map(self.gt_file)
        else:
            logger.warning("No ground truth file found. Operating in unsupervised inference mode.")
            self.ground_truth_map = {}
            
    def run_blocking(self) -> Dict[str, Any]:
        """Indexes target entities and generates candidate pairs for Source 1."""
        if self.s1_df is None or self.target_df is None:
            self.load_and_preprocess_data()
            
        self.indexer = BlockingIndex()
        self.indexer.build_index(self.target_df)
        
        self.candidate_dict, self.flat_candidates = self.indexer.generate_candidate_pairs(self.s1_df)
        
        blocking_report = {}
        if self.ground_truth_map:
            blocking_report = evaluate_blocking(
                self.candidate_dict,
                self.ground_truth_map,
                len(self.target_df)
            )
        return blocking_report
        
    def run_training(self, model_type: str = "logistic_regression") -> Dict[str, Any]:
        """Trains ML model and searches optimal threshold on validation entities."""
        if not self.flat_candidates:
            self.run_blocking()
            
        # Convert s1_df into record lookup
        s1_records = {}
        for _, row in self.s1_df.iterrows():
            eid = str(row[config.ENTITY_ID]).strip()
            s1_records[eid] = {
                "entity_id": eid,
                "norm_name": str(row.get("norm_name", "")),
                "name_no_suffix": str(row.get("name_no_suffix", "")),
                "norm_address": str(row.get("norm_address", "")),
                "norm_country": str(row.get("norm_country", "")),
                "address_numbers": set(str(row.get("address_numbers", "")).split()) if row.get("address_numbers") else set(),
                "postal_codes": set(str(row.get("postal_codes", "")).split()) if row.get("postal_codes") else set(),
            }
            
        target_records = self.indexer.target_records if self.indexer else {}
        
        train_results = train_and_tune_pipeline(
            self.candidate_dict,
            self.flat_candidates,
            s1_records,
            target_records,
            self.ground_truth_map,
            model_type=model_type
        )
        return train_results

    def run_prediction_and_submission(self, threshold: Optional[float] = None) -> Dict[str, Any]:
        """Scores candidate pairs, extracts matches, writes TSVs, and evaluates final performance."""
        if not self.flat_candidates:
            self.run_blocking()
            
        s1_records = {}
        all_s1_ids = []
        for _, row in self.s1_df.iterrows():
            eid = str(row[config.ENTITY_ID]).strip()
            all_s1_ids.append(eid)
            s1_records[eid] = {
                "entity_id": eid,
                "norm_name": str(row.get("norm_name", "")),
                "name_no_suffix": str(row.get("name_no_suffix", "")),
                "norm_address": str(row.get("norm_address", "")),
                "norm_country": str(row.get("norm_country", "")),
                "address_numbers": set(str(row.get("address_numbers", "")).split()) if row.get("address_numbers") else set(),
                "postal_codes": set(str(row.get("postal_codes", "")).split()) if row.get("postal_codes") else set(),
            }
            
        target_records = self.indexer.target_records if self.indexer else {}
        
        preds_map, cands_map, scored_map = predict_matches(
            self.flat_candidates,
            s1_records,
            target_records,
            all_s1_ids,
            threshold=threshold
        )
        
        # Save submission TSVs
        save_submission_files(
            preds_map,
            cands_map,
            all_s1_ids,
            config.MATCHING_RESULTS_TSV,
            config.CANDIDATE_PAIRS_TSV
        )
        
        eval_metrics = {}
        if self.ground_truth_map:
            eval_metrics = evaluate_predictions(self.ground_truth_map, preds_map, all_s1_ids)
            print("\n" + "=" * 50)
            print("FINAL EVALUATION ON DATASET")
            print("=" * 50)
            print(f"Macro F0.5:        {eval_metrics['macro_f05']:.4f}")
            print(f"Macro Precision:   {eval_metrics['macro_precision']:.4f}")
            print(f"Macro Recall:      {eval_metrics['macro_recall']:.4f}")
            print(f"Exact Match Count: {eval_metrics['exact_matches']:,} / {eval_metrics['total_evaluated']:,} ({eval_metrics['exact_match_ratio']*100:.2f}%)")
            print("=" * 50 + "\n")
            
        return {
            "total_s1": len(all_s1_ids),
            "matched_s1_count": sum(1 for m in preds_map.values() if len(m) > 0),
            "total_matches": sum(len(m) for m in preds_map.values()),
            "metrics": eval_metrics
        }
