"""
Evaluation CLI script.
Evaluates blocking candidate recall and end-to-end model F0.5 against ground truth.
Usage:
    python scripts/evaluate.py --mode sample
    python scripts/evaluate.py --mode full
"""
import os
import sys
import argparse
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.pipeline import EntityResolutionPipeline
from src.business_entity_resolution.prediction import load_optimal_threshold

def main():
    parser = argparse.ArgumentParser(description="Evaluate Entity Resolution system.")
    parser.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    parser.add_argument("--threshold", type=float, default=None, help="Evaluation threshold override")
    args = parser.parse_args()
    
    thresh = args.threshold if args.threshold is not None else load_optimal_threshold()
    print(f"=== Starting System Evaluation (Mode: {args.mode}, Threshold: {thresh:.2f}) ===")
    
    pipeline = EntityResolutionPipeline(mode=args.mode)
    pipeline.load_and_preprocess_data()
    
    print("\n1. Evaluating Candidate Generation (Blocking)...")
    blocking_report = pipeline.run_blocking()
    
    print("\n2. Evaluating End-to-End Predictions...")
    results = pipeline.run_prediction_and_submission(threshold=thresh)
    
    print("Evaluation Complete.")

if __name__ == "__main__":
    main()
