"""
CLI script to create reproducible, relation-preserving development samples.
Usage:
    python scripts/create_sample.py --size 100000
    python scripts/create_sample.py --size 10000
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.data_sampler import create_sample

def main():
    parser = argparse.ArgumentParser(description="Generate relation-preserving sample dataset.")
    parser.add_argument(
        "--size",
        type=int,
        default=config.DEFAULT_SAMPLE_SIZE,
        help="Number of Source 1 entities to sample (e.g. 10000, 50000, 100000, 250000)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=config.RANDOM_SEED,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=config.SAMPLE_DIR,
        help="Target output directory for sample TSV files"
    )
    args = parser.parse_args()
    
    print(f"Generating sample of size {args.size:,} with seed {args.seed}...")
    stats = create_sample(sample_size=args.size, random_seed=args.seed, output_dir=args.outdir)
    print("\nSample Created Successfully!")
    for k, v in stats.items():
        print(f"  {k}: {v:,}")

if __name__ == "__main__":
    main()
