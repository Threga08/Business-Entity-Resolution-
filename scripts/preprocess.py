"""
Preprocessing CLI script.
Usage:
    python scripts/preprocess.py --mode sample
    python scripts/preprocess.py --mode full
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.data_loader import load_source_df
from src.business_entity_resolution.preprocessing import preprocess_dataframe

def main():
    parser = argparse.ArgumentParser(description="Preprocess and normalize entity registries.")
    parser.add_argument("--mode", type=str, choices=["sample", "full"], default="sample")
    args = parser.parse_args()
    
    s1_path = config.SAMPLE_SOURCE1 if args.mode == "sample" else config.RAW_SOURCE1
    s2_path = config.SAMPLE_SOURCE2 if args.mode == "sample" else config.RAW_SOURCE2
    s3_path = config.SAMPLE_SOURCE3 if args.mode == "sample" else config.RAW_SOURCE3
    
    print(f"Running preprocessing in mode: {args.mode}")
    print(f"Loading Source 1 from {s1_path}...")
    s1_df = load_source_df(s1_path)
    s1_proc = preprocess_dataframe(s1_df)
    print(f"Source 1 normalized: {len(s1_proc):,} records")
    
    print(f"Loading Source 2 from {s2_path}...")
    s2_df = load_source_df(s2_path)
    s2_proc = preprocess_dataframe(s2_df)
    print(f"Source 2 normalized: {len(s2_proc):,} records")
    
    print(f"Loading Source 3 from {s3_path}...")
    s3_df = load_source_df(s3_path)
    s3_proc = preprocess_dataframe(s3_df)
    print(f"Source 3 normalized: {len(s3_proc):,} records")
    
    print("\nNormalization Sample (Source 1 Record 0):")
    sample_r = s1_proc.iloc[0]
    print(f"  Raw Name:        {sample_r['business_name']}")
    print(f"  Norm Name:       {sample_r['norm_name']}")
    print(f"  No Suffix Name:  {sample_r['name_no_suffix']}")
    print(f"  Raw Address:     {sample_r['business_address']}")
    print(f"  Norm Address:    {sample_r['norm_address']}")
    print(f"  Numbers:         {sample_r['address_numbers']}")
    print(f"  Postal Codes:    {sample_r['postal_codes']}")
    print(f"  Country:         {sample_r['norm_country']}")
    print("\nPreprocessing complete.")

if __name__ == "__main__":
    main()
