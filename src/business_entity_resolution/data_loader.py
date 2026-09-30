"""
Data Loader module for chunked, memory-efficient loading and streaming of huge TSV/CSV datasets.
"""
import os
import csv
import logging
from typing import Generator, List, Dict, Tuple, Optional, Any
import pandas as pd

from . import config

logger = config.logger

def detect_delimiter(file_path: str, num_lines: int = 5) -> str:
    """Sniffs the delimiter of a text file from the first few lines."""
    if not os.path.exists(file_path):
        return "\t"
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        sample = "".join([f.readline() for _ in range(num_lines)])
        
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=["\t", ",", "|", ";"])
        return dialect.delimiter
    except Exception:
        # Fallback heuristic
        tab_count = sample.count("\t")
        comma_count = sample.count(",")
        return "\t" if tab_count >= comma_count else ","

def count_lines_fast(file_path: str) -> int:
    """Efficiently counts total lines in a large file using binary buffer chunks."""
    if not os.path.exists(file_path):
        return 0
    lines = 0
    buf_size = 1024 * 1024  # 1MB buffer
    with open(file_path, "rb") as f:
        while True:
            buf = f.read(buf_size)
            if not buf:
                break
            lines += buf.count(b"\n")
    return lines

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Retrieves file size, delimiter, header columns, and line count."""
    if not os.path.exists(file_path):
        return {"exists": False, "path": file_path}
    
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    sep = detect_delimiter(file_path)
    
    # Read first line for columns
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        header_line = f.readline().strip()
        columns = header_line.split(sep)
        sample_rows = [f.readline().strip().split(sep) for _ in range(3)]
        
    total_lines = count_lines_fast(file_path)
    # Header line doesn't count as data row
    data_rows = max(0, total_lines - 1)
    
    return {
        "exists": True,
        "path": file_path,
        "filename": os.path.basename(file_path),
        "size_bytes": size_bytes,
        "size_mb": round(size_mb, 2),
        "delimiter": repr(sep),
        "sep": sep,
        "columns": columns,
        "estimated_rows": data_rows,
        "sample_preview": sample_rows
    }

def read_tsv_chunks(
    file_path: str,
    chunksize: int = config.DEFAULT_CHUNK_SIZE,
    usecols: Optional[List[str]] = None,
    sep: Optional[str] = None
) -> Generator[pd.DataFrame, None, None]:
    """
    Streams a large TSV/CSV file in chunks with pure string types and zero type inference.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    if sep is None:
        sep = detect_delimiter(file_path)
        
    for chunk in pd.read_csv(
        file_path,
        sep=sep,
        chunksize=chunksize,
        dtype=str,
        keep_default_na=False,
        usecols=usecols,
        quoting=csv.QUOTE_NONE,
        on_bad_lines="skip",
        encoding="utf-8"
    ):
        yield chunk

def load_source_df(file_path: str, usecols: Optional[List[str]] = None) -> pd.DataFrame:
    """Loads a full dataframe for small/sampled datasets with proper string types."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")
    sep = detect_delimiter(file_path)
    return pd.read_csv(
        file_path,
        sep=sep,
        dtype=str,
        keep_default_na=False,
        usecols=usecols,
        quoting=csv.QUOTE_NONE,
        on_bad_lines="skip",
        encoding="utf-8"
    )

def load_ground_truth_map(file_path: str) -> Dict[str, List[str]]:
    """
    Loads ground truth TSV into a dictionary mapping source1_id -> list of matched_ids.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Ground truth not found: {file_path}")
        
    sep = detect_delimiter(file_path)
    gt_map: Dict[str, List[str]] = {}
    
    for chunk in pd.read_csv(
        file_path,
        sep=sep,
        chunksize=config.DEFAULT_CHUNK_SIZE,
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
        encoding="utf-8"
    ):
        s1_col = config.GT_SOURCE1_ID if config.GT_SOURCE1_ID in chunk.columns else chunk.columns[0]
        match_col = config.GT_MATCHED_IDS if config.GT_MATCHED_IDS in chunk.columns else chunk.columns[1]
        
        for _, row in chunk.iterrows():
            s1_id = str(row[s1_col]).strip()
            raw_matches = str(row[match_col]).strip()
            if raw_matches:
                matches = [m.strip() for m in raw_matches.split(",") if m.strip()]
            else:
                matches = []
            gt_map[s1_id] = matches
            
    return gt_map
