# Business Entity Resolution Machine Learning System

An enterprise-grade, high-performance Entity Resolution (Record Linkage) system designed to identify matching business records across disparate, noisy registry sources at multi-million row scale.

---

## 📑 Table of Contents
1. [What is Business Entity Resolution?](#what-is-business-entity-resolution)
2. [Data Sources Architecture (S1, S2, S3)](#data-sources-architecture)
3. [Why Blocking is Critical (O(N²) Avoidance)](#why-blocking-is-critical)
4. [Machine Learning Pipeline & Features](#machine-learning-pipeline--features)
5. [Competition Metric: Macro F0.5](#competition-metric-macro-f05)
6. [Quickstart Guide (Exact PowerShell Commands)](#quickstart-guide)
7. [Using the Web Dashboard](#using-the-web-dashboard)
8. [Scaling Up (from 10K to 500K to Full Dataset)](#scaling-up)
9. [Memory Footprint & Optimization](#memory-footprint--optimization)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## 1. What is Business Entity Resolution?
**Entity Resolution (ER)**, also called **Record Linkage** or **Deduplication**, is the process of identifying records across different databases that refer to the same real-world entity (in this case, commercial businesses), despite variations, spelling errors, abbreviations, missing data, and differing formats.

In real-world data:
* Legal names differ: `"Acme Corp"`, `"Acme Corporation"`, `"Acme Incorporated"`, `"Acme Inc"`.
* Addresses are noisy: `"100 N Main St, Ste 400"`, `"100 North Main Street #400"`.
* Country labels can vary: `"US"`, `"USA"`, `"United States"`, or open-set international values.

---

## 2. Data Sources Architecture
* **Source 1 (`train_source1.txt`)**: The **reference source**. Every single Source 1 record must be resolved.
* **Source 2 (`train_source2.txt`)**: Target registry source 1 (over 5 million records).
* **Source 3 (`train_source3.txt`)**: Target registry source 2 (over 5.2 million records).
* **Ground Truth (`train_ground_truth.txt`)**: Mapping of `source1_entity_id -> matched_entity_ids` (comma-separated list of S2 and S3 IDs).

### Entity Matching Cardinality: One-to-Many
A Source 1 entity can have:
* **Zero matches** (Singleton: entity only exists in Source 1).
* **One match** (e.g., matched to one S2 or S3 entity).
* **Multiple matches** (e.g., matched to both an S2 entity and two S3 entities).

---

## 3. Why Blocking is Critical (O(N²) Avoidance)
If you attempted brute-force Cartesian comparison:
$$\text{Comparisons} = |S_1| \times (|S_2| + |S_3|) = 2,206,821 \times 10,320,219 \approx 2.27 \times 10^{13} \text{ pairs}$$
Comparing 22 trillion pairs would take **months** and hundreds of gigabytes of RAM.

### Multi-Key Union Inverted Indexing
Instead, we index target entities into lightweight hash lookups and retrieve high-probability candidates in $O(1)$ amortized time:
1. **Exact Normalized Name**: Exact match on clean, lowercase business name.
2. **Suffix-Free Name**: Match on name after stripping legal extensions (`corp`, `inc`, `pvt ltd`, `llc`).
3. **4-Character Name Prefix**: Catches typos occurring after the name root.
4. **Combined Address Number + Name Prefix**: High-precision key combining street number and name prefix (e.g., `123#acm`).
5. **Country + Postal/PIN Code**: Aligns businesses sharing regional postal codes.
6. **Inverted Token Index**: Filtered meaningful name words (excluding common noise tokens).

### Blocking Performance Achieved on Sample:
* **Candidate Recall:** `88.92%` (26,016 out of 29,258 true matches captured).
* **Search Space Reduction Ratio:** `99.71%` (99.7% of all non-matching combinations pruned immediately).
* **Average Candidates per S1:** ~88 candidates.

---

## 4. Machine Learning Pipeline & Features

### Feature Engineering (29 Pairwise Features)
For each candidate pair $(S_1, \text{Target})$, we compute:
* **Name Similarities**:
  * Exact name match & suffix-stripped exact match indicators.
  * Levenshtein ratio, token-set ratio, token-sort ratio, partial character similarity.
  * Name token Jaccard overlap & relative length difference.
* **Address Similarities**:
  * Normalized address ratio and token set similarity.
  * Extracted street number overlap & shared postal code indicator.
  * Shared address token count & relative length difference.
* **Open-Set Country Features**:
  * Open-set string comparison: `country_eq` (1.0 if identical), `country_diff` (1.0 if different), `country_missing`.
  * **Zero hardcoding** — generalizes effortlessly to US, India, France, Germany, etc.
* **Blocking Rule Provenance Indicators**:
  * Tracks which blocking rules generated this candidate pair (`feat_rule_exact`, `feat_rule_comb`, etc.).

### Leakage-Proof Splitting
Candidate pairs are **never** randomly split. Instead, splitting is grouped strictly by **Source 1 Entity ID** (80% train / 20% validation). This guarantees no entity seen during training leaks into validation evaluation!

---

## 5. Competition Metric: Macro F0.5
Because false positive matches are heavily penalized in entity resolution, the evaluation uses the **$F_{0.5}$ metric**, weighting precision higher than recall:

$$F_{0.5} = \frac{1.25 \times \text{Precision} \times \text{Recall}}{0.25 \times \text{Precision} + \text{Recall}}$$

### Singleton Edge Cases:
* **True set = $\emptyset$ and Predicted set = $\emptyset$**: Score = `1.0` (Correctly identified singleton).
* **True set = $\emptyset$ and Predicted set $\neq \emptyset$**: Score = `0.0` (False positive link).
* **True set $\neq \emptyset$ and Predicted set = $\emptyset$**: Score = `0.0` (Missed true links).

The score is calculated per Source 1 entity and macro-averaged across all entities.

---

## 6. Quickstart Guide (PowerShell)

### Step 1: Environment Setup
```powershell
# Open terminal in project root:
cd C:\Users\THREGA\.gemini\antigravity-ide\scratch\business_entity_resolution

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### Step 2: Run End-to-End Pipeline
You can run individual CLI scripts or the unified `run.py` command:

```powershell
# 1. Inspect raw files safely via streaming chunk reader
python scripts/inspect_data.py

# 2. Create reproducible 10,000-record development sample (Fast Dev)
python scripts/create_sample.py --size 10000

# 3. Preprocess and normalize sample data
python scripts/preprocess.py --mode sample

# 4. Train supervised model & search optimal threshold on validation set
python scripts/train.py --mode sample

# 5. Evaluate candidate recall and Macro F0.5
python scripts/evaluate.py --mode sample

# 6. Generate submission TSV predictions
python scripts/predict.py --mode sample

# 7. Validate submission format, columns, subset, and ID integrity
python scripts/validate_submission.py
```

Or run everything with a single command:
```powershell
python run.py all --size 10000
```

---

## 7. Using the Web Dashboard
Launch the Flask interactive studio:
```powershell
python frontend/app.py
```
Open in Google Chrome:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### Dashboard Features:
* **Live KPI Cards:** Dataset size, records count for S1, S2, S3, Candidate Recall, Validation Macro F0.5, and Current Threshold.
* **Interactive Control Buttons:**
  * `[ Inspect Dataset ]`: Streams and reports raw file parameters.
  * `[ Create Sample ]`: Generates fresh relation-preserving sample (10K, 50K, 100K, 250K).
  * `[ Preprocess Data ]`: Normalizes business names, addresses, numbers, and open-set countries.
  * `[ Train Model & Tune ]`: Runs blocking, builds feature matrices, trains classifier, and optimizes threshold.
  * `[ Evaluate Model ]`: Evaluates precision, recall, and Macro F0.5.
  * `[ Run Prediction ]`: Scores candidate pairs and writes TSVs.
  * `[ Validate Submission ]`: Runs integrity checks and prints PASS.
* **Sample Entity Matching View:** Displays cards comparing Source 1 entities alongside their resolved Source 2 and Source 3 matches.
* **Live Console Output:** Streams logs from `logs/pipeline.log`.

---

## 8. Scaling Up (from 10K to Full Dataset)

1. **Step 1 (10,000 Dev Sample - Done):**
   ```powershell
   python scripts/create_sample.py --size 10000
   python scripts/train.py --mode sample
   ```
2. **Step 2 (100,000 Standard Sample):**
   ```powershell
   python scripts/create_sample.py --size 100000
   python scripts/train.py --mode sample
   ```
3. **Step 3 (250,000 Scaled Sample):**
   ```powershell
   python scripts/create_sample.py --size 250000
   python scripts/train.py --mode sample
   ```
4. **Step 4 (Full 2.2M / 10.3M Dataset):**
   ```powershell
   python scripts/predict.py --mode full
   ```
   *Note: In full mode, processing runs in chunked batches through the inverted index to maintain minimal RAM usage.*

---

## 9. Memory Footprint & Optimization
* **Chunked TSV Streaming:** Raw files are read using 1MB binary buffers or chunked streams (`chunksize=100000`). Never loads full 10M rows into a single dataframe.
* **Compact String Types:** All entity IDs are kept as clean native Python strings (`dtype=str`) without unnecessary pandas object wrapper overhead.
* **Candidate Cap:** Per-entity candidate count is capped (default: 200) prioritizing high-specificity rules to prevent combinatorial blowup.
* **Peak Memory Usage:** ~1.2 GB RAM during 100K entity training; well within normal laptop capacity (8 GB - 16 GB).

---

## 10. Troubleshooting Guide

* **Issue: `UnicodeEncodeError` when printing on Windows PowerShell**
  * *Solution:* Handled automatically via `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` in all modules.
* **Issue: "Model file not found"**
  * *Solution:* Run `python scripts/train.py --mode sample` first to train and serialize `models/entity_matcher.joblib`.
* **Issue: Submission validation fails**
  * *Solution:* Run `python scripts/validate_submission.py`. It checks:
    1. Exactly 2 TSV columns (`source1_entity_id`, `matched_entity_ids`).
    2. Every Source 1 entity appears exactly once.
    3. No S1 IDs appear in the match column (only S2 and S3 IDs).
    4. No duplicate target IDs.
    5. Every final match is a strict subset of the candidate pairs list.
