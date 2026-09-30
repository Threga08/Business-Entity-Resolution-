# Dataset Report — Business Entity Resolution

## Overview

This project involves resolving business entities across three data sources. Source 1 (S1) is the "anchor" source; the ground truth maps S1 entities to matching entities in Source 2 (S2) and Source 3 (S3).

---

## Files

| File | Size | Rows (excl. header) | Columns |
|------|------|---------------------|---------|
| `train_source1.txt` | 200.34 MB | 2,206,821 | 4 |
| `train_source2.txt` | 466.63 MB | 5,034,616 | 4 |
| `train_source3.txt` | 480.37 MB | 5,285,603 | 4 |
| `train_ground_truth.txt` | 121.13 MB | 2,206,821 | 2 |

---

## Column Schemas

### Source Files (S1, S2, S3 — identical schema)

| Column | Type | Description |
|--------|------|-------------|
| `entity_id` | string | Unique ID per source (prefix: `S1-`, `S2-`, `S3-`) |
| `business_name` | string | Business name (may include website URLs, non-Latin scripts, typos) |
| `business_address` | string | Full address (format varies by source; may be empty) |
| `country` | string | Country: `US` or `India` |

### Ground Truth

| Column | Type | Description |
|--------|------|-------------|
| `source1_entity_id` | string | S1 entity ID |
| `matched_entity_ids` | string | Comma-separated list of matching S2/S3 entity IDs (may be empty for singletons) |

---

## Missing Values

| File | entity_id | business_name | business_address | country |
|------|-----------|---------------|------------------|---------|
| S1 | 0 | 0 | 0 | 0 |
| S2 | 0 | 0 | 168,967 (3.4%) | 0 |
| S3 | 0 | 0 | 175,916 (3.3%) | 0 |

Ground truth `matched_entity_ids`: 123,247 empty (5.58%) — these are **singleton** entities with no matches.

---

## Country Distribution (sampled)

All three sources have approximately 60% US and 40% India entities.

---

## Ground Truth Statistics

| Metric | Value |
|--------|-------|
| Total S1 entities | 2,206,821 |
| Singletons (0 matches) | 123,247 (5.58%) |
| Total true match pairs (S1→S2/S3) | 7,638,365 |
| — S2 matches | 3,693,619 (48.4%) |
| — S3 matches | 3,944,746 (51.6%) |
| Avg matches per S1 entity | 3.46 |
| Avg matches per matched S1 entity | 3.67 |

### Match Count Distribution

| # Matches | Count | % |
|-----------|-------|---|
| 0 | 123,247 | 5.58% |
| 1 | 119,157 | 5.40% |
| 2 | 375,212 | 17.00% |
| 3 | 530,841 | 24.05% |
| 4 | 484,115 | 21.94% |
| 5 | 321,957 | 14.59% |
| 6 | 164,868 | 7.47% |
| 7 | 63,968 | 2.90% |
| 8 | 18,680 | 0.85% |
| 9 | 4,205 | 0.19% |
| 10 | 534 | 0.02% |
| 11 | 37 | 0.00% |

---

## Key Observations

1. **All sources share the same 4-column schema**: `entity_id`, `business_name`, `business_address`, `country`.
2. **Country is always `US` or `India`** — matches never cross countries (verified on sample).
3. **Country is a perfect blocking key** — no cross-country matches.
4. **Data quality challenges**:
   - Business names may contain typos, OCR artifacts, URLs, non-Latin scripts (Hindi/Devanagari), multiple spaces, company suffix variations (Inc/LLC/Pvt/Ltd).
   - Addresses have varying formats: some reversed, some with abbreviations, different state format (state code vs full name).
   - S2 tends to use uppercase; S3 uses mixed case with more variation.
5. **Scale**: ~2.2M S1 entities × ~10.3M S2+S3 entities. Full Cartesian is ~22.7 trillion pairs → blocking is essential.
6. **Ground truth provides directional mapping**: S1 → {S2, S3}. The task is to find, for each S1 entity, all matching S2 and S3 entities.

---

## Example Matched Records

| S1 | Matched | Observation |
|----|---------|-------------|
| `Urology Partners Inc` | `Urology Partners  Inc` (S2) | Extra space |
| `VL Sprott` | `VL SPROTT` (S3) | Case difference |
| `Painters Local Union 634` | `Mirapyra formerly Painters Local Union 634` (S3) | Name superset |
| `Sai Traders Private Limited` | `SAI TRADERS PRIVATE LIMITED` (S2) | Case + Hindi chars in address |
| `Golden One Consultants Private Limited` | `GOLDEN ONE CÓNSULTANTS PRIVATE LTD` (S2) | Accented chars + abbreviation |
| `Siia Investments Inc` | `siiainvestments.com` (S2) | URL form |
| `Lowe Galata LLC` | `Galatalowe.Com` (S3) | URL form + reordered |
| `Wright & Cutrone Environmental Services LLC` | `Wright & Cutrflne Environmental Services LLC` (S3) | OCR-like typo |
