"""
Master entrypoint for Business Entity Resolution project.
Provides a unified CLI interface to run any pipeline step or start the Flask frontend.

Usage Examples:
    python run.py inspect
    python run.py sample --size 10000
    python run.py preprocess --mode sample
    python run.py train --mode sample
    python run.py evaluate --mode sample
    python run.py predict --mode sample
    python run.py validate
    python run.py frontend
    python run.py all --size 10000
"""
import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Business Entity Resolution CLI Runner")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # inspect
    subparsers.add_parser("inspect", help="Inspect raw data files efficiently")
    
    # sample
    p_sample = subparsers.add_parser("sample", help="Create development sample from raw data")
    p_sample.add_argument("--size", type=int, default=10000, help="Number of Source 1 entities")
    
    # preprocess
    p_pre = subparsers.add_parser("preprocess", help="Preprocess and normalize data")
    p_pre.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    
    # train
    p_train = subparsers.add_parser("train", help="Train supervised matcher & tune threshold")
    p_train.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    p_train.add_argument("--model", type=str, choices=["logistic_regression", "lightgbm"], default="logistic_regression")
    
    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="Evaluate candidate recall and Macro F0.5")
    p_eval.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    
    # predict
    p_pred = subparsers.add_parser("predict", help="Generate submission predictions")
    p_pred.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    
    # validate
    subparsers.add_parser("validate", help="Validate submission TSVs formatting & constraints")
    
    # frontend
    p_front = subparsers.add_parser("frontend", help="Start Flask dashboard")
    p_front.add_argument("--port", type=int, default=5000)
    
    # all (end-to-end)
    p_all = subparsers.add_parser("all", help="Run full pipeline end-to-end on sample")
    p_all.add_argument("--size", type=int, default=10000)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    py_bin = sys.executable
    
    if args.command == "inspect":
        subprocess.run([py_bin, "scripts/inspect_data.py"], check=True)
    elif args.command == "sample":
        subprocess.run([py_bin, "scripts/create_sample.py", "--size", str(args.size)], check=True)
    elif args.command == "preprocess":
        subprocess.run([py_bin, "scripts/preprocess.py", "--mode", args.mode], check=True)
    elif args.command == "train":
        subprocess.run([py_bin, "scripts/train.py", "--mode", args.mode, "--model", args.model], check=True)
    elif args.command == "evaluate":
        subprocess.run([py_bin, "scripts/evaluate.py", "--mode", args.mode], check=True)
    elif args.command == "predict":
        subprocess.run([py_bin, "scripts/predict.py", "--mode", args.mode], check=True)
    elif args.command == "validate":
        subprocess.run([py_bin, "scripts/validate_submission.py"], check=True)
    elif args.command == "frontend":
        subprocess.run([py_bin, "frontend/app.py"], check=True)
    elif args.command == "all":
        print(f"\n🚀 Running End-to-End Pipeline with sample size {args.size:,}...\n")
        subprocess.run([py_bin, "scripts/inspect_data.py"], check=True)
        subprocess.run([py_bin, "scripts/create_sample.py", "--size", str(args.size)], check=True)
        subprocess.run([py_bin, "scripts/preprocess.py", "--mode", "sample"], check=True)
        subprocess.run([py_bin, "scripts/train.py", "--mode", "sample"], check=True)
        subprocess.run([py_bin, "scripts/evaluate.py", "--mode", "sample"], check=True)
        subprocess.run([py_bin, "scripts/predict.py", "--mode", "sample"], check=True)
        subprocess.run([py_bin, "scripts/validate_submission.py"], check=True)
        print("\n🎉 All Pipeline Steps Completed and Verified Successfully!\n")

if __name__ == "__main__":
    main()
