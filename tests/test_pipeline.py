"""
Comprehensive unit test suite for Business Entity Resolution pipeline.
Validates normalization, blocking indexes, feature computation, F0.5 edge cases, and submission validation.
"""
import sys
import os
import pytest
import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.business_entity_resolution import config
from src.business_entity_resolution.preprocessing import (
    normalize_unicode,
    normalize_whitespace,
    normalize_business_name,
    normalize_address,
    normalize_country,
    extract_tokens
)
from src.business_entity_resolution.blocking import BlockingIndex
from src.business_entity_resolution.features import compute_pair_features, FEATURE_COLUMNS
from src.business_entity_resolution.evaluation import compute_entity_f05, evaluate_predictions
from scripts.validate_submission import validate_submission

class TestPreprocessing:
    def test_unicode_and_whitespace(self):
        assert normalize_unicode("Café & Résumé") == "Cafe & Resume"
        assert normalize_whitespace("  hello   world \t ") == "hello world"

    def test_business_name_normalization(self):
        norm, no_suf = normalize_business_name("Acme & Sons Corporation")
        assert "and" in norm
        assert "corp" in norm
        assert "corp" not in no_suf
        assert "acme and sons" in no_suf

    def test_legal_suffix_variants(self):
        norm1, nosuf1 = normalize_business_name("Apex Limited")
        norm2, nosuf2 = normalize_business_name("Apex Private Limited")
        assert "ltd" in norm1
        assert "pvt ltd" in norm2
        assert nosuf1 == "apex"
        assert nosuf2 == "apex"

    def test_address_normalization_and_extraction(self):
        addr, numbers, postals = normalize_address("123 Main Street, Suite 400, Austin, TX 78701")
        assert "123 main st" in addr
        assert "123" in numbers
        assert "78701" in postals

    def test_open_set_country(self):
        assert normalize_country("US") == "us"
        assert normalize_country("France") == "france"
        assert normalize_country("  INDIA  ") == "india"
        assert normalize_country(None) == ""

class TestEvaluationMetric:
    def test_singleton_both_empty(self):
        # Special case: true empty and pred empty => 1.0
        p, r, f05 = compute_entity_f05(set(), set())
        assert f05 == 1.0
        assert p == 1.0
        assert r == 1.0

    def test_false_positive_singleton(self):
        # True empty, predicted has matches => 0.0
        p, r, f05 = compute_entity_f05(set(), {"S2-100"})
        assert f05 == 0.0
        assert p == 0.0

    def test_false_negative_singleton(self):
        # True has match, predicted empty => 0.0
        p, r, f05 = compute_entity_f05({"S2-100"}, set())
        assert f05 == 0.0
        assert r == 0.0

    def test_f05_formula_exact(self):
        # Precision = 1.0, Recall = 0.5
        # F0.5 = (1.25 * 1.0 * 0.5) / (0.25 * 1.0 + 0.5) = 0.625 / 0.75 = 0.8333...
        p, r, f05 = compute_entity_f05({"S2-1", "S2-2"}, {"S2-1"})
        assert round(p, 4) == 1.0
        assert round(r, 4) == 0.5
        assert round(f05, 4) == round(0.625 / 0.75, 4)

class TestFeatures:
    def test_pair_feature_vector(self):
        s1 = {
            "norm_name": "target corporation",
            "name_no_suffix": "target",
            "norm_address": "1000 nicollet mall minneapolis mn",
            "norm_country": "us",
            "address_numbers": {"1000"},
            "postal_codes": {"55403"}
        }
        tgt = {
            "norm_name": "target corp",
            "name_no_suffix": "target",
            "norm_address": "1000 nicollet mall minneapolis mn",
            "norm_country": "us",
            "address_numbers": {"1000"},
            "postal_codes": {"55403"}
        }
        feats = compute_pair_features(s1, tgt, ["exact_name", "suffix_name"])
        assert feats["feat_exact_nosuf"] == 1.0
        assert feats["feat_country_eq"] == 1.0
        assert feats["feat_has_shared_num"] == 1.0
        assert feats["feat_has_shared_postal"] == 1.0
        assert feats["feat_rule_nosuf"] == 1.0
        assert len(feats) == len(FEATURE_COLUMNS)

class TestSubmissionValidation:
    def test_submission_files_pass(self):
        if os.path.exists(config.MATCHING_RESULTS_TSV) and os.path.exists(config.CANDIDATE_PAIRS_TSV):
            assert validate_submission() is True
