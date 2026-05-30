"""
Tests for equivalence verification script (Task Group 10).

Tests the verify_equivalence.py script that compares metrics from
parser mode and predictions mode.
"""

import json
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import verify_equivalence

load_scores = verify_equivalence.load_scores
compare_metrics = verify_equivalence.compare_metrics
verify_equivalence = verify_equivalence.verify_equivalence


@pytest.fixture
def sample_parser_scores(tmp_path):
    """Sample parser mode scores.json."""
    scores_file = tmp_path / "parser_scores.json"
    scores = {
        "dataset": "dp_bench",
        "parser": "stub",
        "timestamp": "20240101_120000",
        "csv_file": "results.csv",
        "metrics_avg": {
            "nid": 0.85,
            "nid_s": 0.80,
            "teds": 0.90,
            "teds_s": 0.88,
            "mhs": 0.75,
            "mhs_s": 0.70,
            "ard": 0.60,
            "bleu": 0.65,
            "meteor": 0.68,
        },
        "total_processed": 10,
        "errors": 0,
    }
    with open(scores_file, "w") as f:
        json.dump(scores, f)
    return scores_file


@pytest.fixture
def sample_predictions_scores(tmp_path):
    """Sample predictions mode scores.json."""
    scores_file = tmp_path / "predictions_scores.json"
    scores = {
        "dataset": "dp_bench",
        "parser": "predictions",
        "timestamp": "20240101_120001",  # Different timestamp
        "csv_file": "results.csv",
        "metrics_avg": {
            "nid": 0.85,
            "nid_s": 0.80,
            "teds": 0.90,
            "teds_s": 0.88,
            "mhs": 0.75,
            "mhs_s": 0.70,
            "ard": 0.60,
            "bleu": 0.65,
            "meteor": 0.68,
        },
        "evaluated_samples": 10,
        "rejected_samples": {
            "MISSING_PREDICTION": 0,
            "INVALID_JSON": 0,
            "INVALID_SCHEMA": 0,
            "EVALUATION_ERROR": 0,
        },
    }
    with open(scores_file, "w") as f:
        json.dump(scores, f)
    return scores_file


@pytest.fixture
def divergent_scores(tmp_path):
    """Sample predictions mode scores with divergent metrics."""
    scores_file = tmp_path / "divergent_scores.json"
    scores = {
        "dataset": "dp_bench",
        "parser": "predictions",
        "timestamp": "20240101_120001",
        "csv_file": "results.csv",
        "metrics_avg": {
            "nid": 0.84,  # Different from parser
            "nid_s": 0.80,
            "teds": 0.90,
            "teds_s": 0.88,
            "mhs": 0.75,
            "mhs_s": 0.70,
            "ard": 0.60,
            "bleu": 0.65,
            "meteor": 0.68,
        },
        "evaluated_samples": 10,
        "rejected_samples": {
            "MISSING_PREDICTION": 0,
            "INVALID_JSON": 0,
            "INVALID_SCHEMA": 0,
            "EVALUATION_ERROR": 0,
        },
    }
    with open(scores_file, "w") as f:
        json.dump(scores, f)
    return scores_file


class TestLoadScores:
    """Tests for load_scores function."""

    def test_load_valid_scores(self, sample_parser_scores):
        """Should load valid scores.json."""
        scores = load_scores(sample_parser_scores)
        assert scores is not None
        assert "dataset" in scores
        assert "metrics_avg" in scores

    def test_load_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_scores(tmp_path / "nonexistent.json")

    def test_load_invalid_json(self, tmp_path):
        """Should raise ValueError for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(ValueError):
            load_scores(invalid_file)


class TestCompareMetrics:
    """Tests for compare_metrics function."""

    def test_identical_metrics(self):
        """Identical metrics should produce no errors."""
        parser_metrics = {"nid": 0.85, "teds": 0.90}
        predictions_metrics = {"nid": 0.85, "teds": 0.90}

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 0

    def test_divergent_metrics(self):
        """Divergent metrics should produce errors."""
        parser_metrics = {"nid": 0.85, "teds": 0.90}
        predictions_metrics = {"nid": 0.84, "teds": 0.90}

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 1
        assert "nid" in errors[0]

    def test_floating_point_tolerance(self):
        """Metrics within tolerance should be considered equivalent."""
        parser_metrics = {"nid": 0.8500}
        predictions_metrics = {"nid": 0.8501}  # Within tolerance

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 0

    def test_beyond_tolerance(self):
        """Metrics beyond tolerance should be flagged."""
        parser_metrics = {"nid": 0.85}
        predictions_metrics = {"nid": 0.84}  # 0.01 difference

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 1

    def test_none_values(self):
        """Should handle None values correctly."""
        parser_metrics = {"nid": None, "teds": 0.90}
        predictions_metrics = {"nid": None, "teds": 0.90}

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 0

    def test_mismatched_none_values(self):
        """Should flag mismatched None values."""
        parser_metrics = {"nid": 0.85}
        predictions_metrics = {"nid": None}

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 1

    def test_partial_metric_overlap(self):
        """Should only compare metrics present in both."""
        parser_metrics = {"nid": 0.85, "teds": 0.90}
        predictions_metrics = {"nid": 0.85, "bleu": 0.65}

        errors = compare_metrics(parser_metrics, predictions_metrics)
        assert len(errors) == 0  # Only nid is compared


class TestVerifyEquivalence:
    """Tests for verify_equivalence function."""

    def test_equivalent_scores(self, sample_parser_scores, sample_predictions_scores):
        """Equivalent scores should return 0."""
        exit_code = verify_equivalence(sample_parser_scores, sample_predictions_scores)
        assert exit_code == 0

    def test_divergent_scores(self, sample_parser_scores, divergent_scores):
        """Divergent scores should return 1."""
        exit_code = verify_equivalence(sample_parser_scores, divergent_scores)
        assert exit_code == 1

    def test_missing_parser_scores(self, sample_predictions_scores):
        """Missing parser scores should return 2."""
        exit_code = verify_equivalence(Path("nonexistent_parser.json"), sample_predictions_scores)
        assert exit_code == 2

    def test_missing_predictions_scores(self, sample_parser_scores):
        """Missing predictions scores should return 2."""
        exit_code = verify_equivalence(sample_parser_scores, Path("nonexistent_predictions.json"))
        assert exit_code == 2


class TestEquivalenceIntegration:
    """Integration tests for equivalence verification."""

    def test_timestamp_field_ignored(self, tmp_path):
        """Timestamp field differences should not affect comparison."""
        parser_file = tmp_path / "parser.json"
        pred_file = tmp_path / "pred.json"

        parser_scores = {"timestamp": "20240101_120000", "metrics_avg": {"nid": 0.85}}
        pred_scores = {
            "timestamp": "20240101_120001",  # Different
            "metrics_avg": {"nid": 0.85},
        }

        with open(parser_file, "w") as f:
            json.dump(parser_scores, f)
        with open(pred_file, "w") as f:
            json.dump(pred_scores, f)

        exit_code = verify_equivalence(parser_file, pred_file)
        assert exit_code == 0

    def test_evaluated_vs_total_processed_ignored(self, tmp_path):
        """Different metadata fields should not affect comparison."""
        parser_file = tmp_path / "parser.json"
        pred_file = tmp_path / "pred.json"

        parser_scores = {"total_processed": 10, "metrics_avg": {"nid": 0.85}}
        pred_scores = {"evaluated_samples": 10, "metrics_avg": {"nid": 0.85}}

        with open(parser_file, "w") as f:
            json.dump(parser_scores, f)
        with open(pred_file, "w") as f:
            json.dump(pred_scores, f)

        exit_code = verify_equivalence(parser_file, pred_file)
        assert exit_code == 0

    def test_all_metrics_compared(self, tmp_path):
        """All standard metrics should be compared."""
        parser_file = tmp_path / "parser.json"
        pred_file = tmp_path / "pred.json"

        all_metrics = {
            "nid": 0.85,
            "nid_s": 0.80,
            "teds": 0.90,
            "teds_s": 0.88,
            "mhs": 0.75,
            "mhs_s": 0.70,
            "ard": 0.60,
            "bleu": 0.65,
            "meteor": 0.68,
        }

        parser_scores = {"metrics_avg": all_metrics.copy()}
        pred_scores = {"metrics_avg": all_metrics.copy()}

        with open(parser_file, "w") as f:
            json.dump(parser_scores, f)
        with open(pred_file, "w") as f:
            json.dump(pred_scores, f)

        exit_code = verify_equivalence(parser_file, pred_file)
        assert exit_code == 0
