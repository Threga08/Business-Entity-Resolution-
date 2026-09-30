"""
Configuration module for Business Entity Resolution.
Defines paths, hyperparameters, constants, and logging setup.
"""
import os
import sys
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Directories
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SAMPLE_DIR = os.path.join(DATA_DIR, "sample")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

for d in [DATA_DIR, RAW_DIR, SAMPLE_DIR, PROCESSED_DIR, MODELS_DIR, OUTPUT_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# Log file
LOG_FILE = os.path.join(LOGS_DIR, "pipeline.log")

def setup_logger(name: str = "business_entity_resolution", level=logging.INFO) -> logging.Logger:
    """Configures and returns a thread-safe logger writing to console and file."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # File handler
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Stream handler (console)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
    return logger

logger = setup_logger()

# Raw Data Paths (with fallback to Downloads or dataset/train)
DOWNLOADS_DIR = r"C:\Users\THREGA\Downloads"
DATASET_TRAIN_DIR = os.path.join(PROJECT_ROOT, "dataset", "train")

def resolve_raw_path(filename: str) -> str:
    """Finds the raw file across standard locations."""
    candidates = [
        os.path.join(RAW_DIR, filename),
        os.path.join(DOWNLOADS_DIR, filename),
        os.path.join(DATASET_TRAIN_DIR, filename),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return os.path.join(RAW_DIR, filename)

RAW_SOURCE1 = resolve_raw_path("train_source1.txt")
RAW_SOURCE2 = resolve_raw_path("train_source2.txt")
RAW_SOURCE3 = resolve_raw_path("train_source3.txt")
RAW_GROUND_TRUTH = resolve_raw_path("train_ground_truth.txt")

# Sample Data Paths
SAMPLE_SOURCE1 = os.path.join(SAMPLE_DIR, "source1.tsv")
SAMPLE_SOURCE2 = os.path.join(SAMPLE_DIR, "source2.tsv")
SAMPLE_SOURCE3 = os.path.join(SAMPLE_DIR, "source3.tsv")
SAMPLE_GROUND_TRUTH = os.path.join(SAMPLE_DIR, "ground_truth.tsv")

# Processed Data Paths
PROCESSED_SOURCE1 = os.path.join(PROCESSED_DIR, "source1_processed.parquet")
PROCESSED_SOURCE2 = os.path.join(PROCESSED_DIR, "source2_processed.parquet")
PROCESSED_SOURCE3 = os.path.join(PROCESSED_DIR, "source3_processed.parquet")

# Model & Artifacts
MODEL_PATH = os.path.join(MODELS_DIR, "entity_matcher.joblib")
THRESHOLD_PATH = os.path.join(MODELS_DIR, "threshold.json")
METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")
BLOCKING_REPORT_PATH = os.path.join(MODELS_DIR, "blocking_report.json")

# Output files
MATCHING_RESULTS_TSV = os.path.join(OUTPUT_DIR, "matching_results.tsv")
CANDIDATE_PAIRS_TSV = os.path.join(OUTPUT_DIR, "candidate_pairs.tsv")

# Schema Column Names
ENTITY_ID = "entity_id"
BUSINESS_NAME = "business_name"
BUSINESS_ADDRESS = "business_address"
COUNTRY = "country"

GT_SOURCE1_ID = "source1_entity_id"
GT_MATCHED_IDS = "matched_entity_ids"

SOURCE_COLS = [ENTITY_ID, BUSINESS_NAME, BUSINESS_ADDRESS, COUNTRY]
GT_COLS = [GT_SOURCE1_ID, GT_MATCHED_IDS]

# Normalization & Blocking Constants
RANDOM_SEED = 42
DEFAULT_SAMPLE_SIZE = 100000
MIN_SAMPLE_SIZE = 10000
DEFAULT_CHUNK_SIZE = 100000

# Candidate Generation Parameters
NAME_PREFIX_LEN = 4
MAX_CANDIDATES_PER_S1 = 200

# Evaluation & Threshold Tuning
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
DEFAULT_THRESHOLD = 0.70
