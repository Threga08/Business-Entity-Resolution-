"""
Prediction CLI script.
Generates candidate pairs and final entity matching results TSVs.
Usage:
    python scripts/predict.py --mode sample
    python scripts/predict.py --mode full
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.pipeline import EntityResolutionPipeline
from src.business_entity_resolution.prediction import load_optimal_threshold

def main():
    parser = argparse.ArgumentParser(description="Run entity resolution prediction on dataset.")
    parser.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    parser.add_argument("--threshold", type=float, default=None, help="Prediction threshold override")
    args = parser.parse_args()
    
    thresh = args.threshold if args.threshold is not None else load_optimal_threshold()
    print(f"=== Running Entity Matching Prediction (Mode: {args.mode}, Threshold: {thresh:.2f}) ===")
    
    pipeline = EntityResolutionPipeline(mode=args.mode)
    pipeline.load_and_preprocess_data()
    pipeline.run_blocking()
    results = pipeline.run_prediction_and_submission(threshold=thresh)
    
    print("\nPrediction Complete!")
    print(f"  Total Source 1 processed:     {results['total_s1']:,}")
    print(f"  Source 1 with matches:        {results['matched_s1_count']:,}")
    print(f"  Total matched targets:        {results['total_matches']:,}")
    print(f"  Saved Matching Results:       {config.MATCHING_RESULTS_TSV}")
    print(f"  Saved Candidate Pairs:        {config.CANDIDATE_PAIRS_TSV}")

if __name__ == "__main__":
    main()
