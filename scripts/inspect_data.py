"""
Fast, memory-safe inspection script for huge multi-gigabyte raw files.
Streams files in chunks, sniffs delimiters, counts rows, detects missing fields and country distribution.
"""
import os
import sys
from collections import Counter
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Reconfigure stdout for safe Windows UTF-8 terminal printing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.business_entity_resolution import config
from src.business_entity_resolution.data_loader import get_file_info, read_tsv_chunks

def inspect_dataset():
    files = [
        ("Source 1", config.RAW_SOURCE1),
        ("Source 2", config.RAW_SOURCE2),
        ("Source 3", config.RAW_SOURCE3),
        ("Ground Truth", config.RAW_GROUND_TRUTH),
    ]
    
    print("\n" + "=" * 50)
    print("DATASET INSPECTION REPORT")
    print("=" * 50)
    
    for name, path in files:
        print(f"\n--- {name} ---")
        if not os.path.exists(path):
            print(f"Status: File not found at {path}")
            continue
            
        info = get_file_info(path)
        print(f"File Path:                {info['path']}")
        print(f"File Size:                {info['size_mb']} MB ({info['size_bytes']:,} bytes)")
        print(f"Detected Delimiter:       {info['delimiter']}")
        print(f"Columns:                  {info['columns']}")
        print(f"Estimated Rows:           {info['estimated_rows']:,}")
        
        # Analyze missing values & countries via chunked streaming
        missing_name = 0
        missing_addr = 0
        country_counter = Counter()
        rows_scanned = 0
        sample_limit = 500000  # Scan up to 500k rows quickly for stats to keep inspection fast
        
        try:
            for chunk in read_tsv_chunks(path, chunksize=100000):
                rows_scanned += len(chunk)
                if config.BUSINESS_NAME in chunk.columns:
                    missing_name += int((chunk[config.BUSINESS_NAME] == "").sum())
                if config.BUSINESS_ADDRESS in chunk.columns:
                    missing_addr += int((chunk[config.BUSINESS_ADDRESS] == "").sum())
                if config.COUNTRY in chunk.columns:
                    country_counter.update(chunk[config.COUNTRY].tolist())
                    
                if rows_scanned >= sample_limit:
                    break
                    
            if config.BUSINESS_NAME in info['columns']:
                print(f"Missing business_name:    {missing_name:,} in first {rows_scanned:,} rows")
            if config.BUSINESS_ADDRESS in info['columns']:
                print(f"Missing business_address: {missing_addr:,} in first {rows_scanned:,} rows")
            if country_counter:
                top_countries = country_counter.most_common(5)
                ctry_str = ", ".join([f"{c}: {n:,}" for c, n in top_countries if c])
                print(f"Top Countries:            {ctry_str}")
        except Exception as e:
            print(f"Inspection error during chunk reading: {e}")
            
        print("\nSample Preview (first 2 records):")
        for idx, sample in enumerate(info.get("sample_preview", [])[:2]):
            print(f"  Record {idx+1}: {sample}")
            
    print("\n" + "=" * 50)
    print("INSPECTION COMPLETE")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    inspect_dataset()
