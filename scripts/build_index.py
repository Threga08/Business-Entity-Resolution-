"""
Script to build the SQLite Full-Text Search index for Source 1 entities.
Usage:
    python scripts/build_index.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.indexing import init_search_db

def main():
    print(f"Building Full-Text Search index for Source 1 from {config.SAMPLE_SOURCE1}...")
    db_path = init_search_db(config.SAMPLE_SOURCE1)
    print(f"Search index built successfully at: {db_path}")

if __name__ == "__main__":
    main()
