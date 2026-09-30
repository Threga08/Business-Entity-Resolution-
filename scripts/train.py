"""
Training CLI script.
Usage:
    python scripts/train.py --mode sample
    python scripts/train.py --mode full
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.pipeline import EntityResolutionPipeline

def main():
    parser = argparse.ArgumentParser(description="Train supervised entity matcher.")
    parser.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    parser.add_argument("--model", type=str, choices=["logistic_regression", "lightgbm"], default="logistic_regression")
    args = parser.parse_args()
    
    print(f"=== Starting Training Pipeline (Mode: {args.mode}, Model: {args.model}) ===")
    pipeline = EntityResolutionPipeline(mode=args.mode)
    
    print("1. Loading and preprocessing data...")
    pipeline.load_and_preprocess_data()
    
    print("2. Running blocking and candidate generation...")
    blocking_report = pipeline.run_blocking()
    
    print("3. Training supervised model and searching optimal threshold...")
    train_results = pipeline.run_training(model_type=args.model)
    
    print("\nTraining Pipeline Completed Successfully!")
    print(f"Best Validation Macro F0.5: {train_results['best_val_f05']:.4f} at Threshold: {train_results['best_threshold']:.2f}")

if __name__ == "__main__":
    main()
