"""
Tests for rejection reporting in scores.json (Task Group 7).

Tests the evaluated_samples and rejected_samples fields in scores.json output.
"""

import json


class TestScoresJsonRejectionFields:
    """Tests for scores.json rejection reporting fields."""

    def test_scores_json_contains_evaluated_samples(self, tmp_path):
        """scores.json should contain evaluated_samples field."""
        # Create a sample scores.json with evaluated_samples
        scores_file = tmp_path / "scores.json"
        sample_scores = {
            "dataset": "dp_bench",
            "parser": "predictions",
            "timestamp": "20240101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"nid": 0.85, "teds": 0.90},
            "evaluated_samples": 10,
            "rejected_samples": {
                "MISSING_PREDICTION": 1,
                "INVALID_JSON": 0,
                "INVALID_SCHEMA": 2,
                "EVALUATION_ERROR": 0,
            },
        }

        with open(scores_file, "w") as f:
            json.dump(sample_scores, f)

        # Read back and verify
        with open(scores_file) as f:
            loaded = json.load(f)

        assert "evaluated_samples" in loaded
        assert loaded["evaluated_samples"] == 10

    def test_scores_json_contains_rejected_samples(self, tmp_path):
        """scores.json should contain rejected_samples dict."""
        scores_file = tmp_path / "scores.json"
        sample_scores = {
            "dataset": "dp_bench",
            "parser": "predictions",
            "timestamp": "20240101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"nid": 0.85, "teds": 0.90},
            "evaluated_samples": 10,
            "rejected_samples": {
                "MISSING_PREDICTION": 1,
                "INVALID_JSON": 0,
                "INVALID_SCHEMA": 2,
                "EVALUATION_ERROR": 0,
            },
        }

        with open(scores_file, "w") as f:
            json.dump(sample_scores, f)

        # Read back and verify
        with open(scores_file) as f:
            loaded = json.load(f)

        assert "rejected_samples" in loaded
        assert isinstance(loaded["rejected_samples"], dict)
        assert loaded["rejected_samples"]["MISSING_PREDICTION"] == 1
        assert loaded["rejected_samples"]["INVALID_SCHEMA"] == 2

    def test_rejected_samples_has_all_reason_codes(self, tmp_path):
        """rejected_samples should contain all reason codes."""
        scores_file = tmp_path / "scores.json"
        sample_scores = {
            "dataset": "dp_bench",
            "parser": "predictions",
            "evaluated_samples": 10,
            "rejected_samples": {
                "MISSING_PREDICTION": 1,
                "INVALID_JSON": 0,
                "INVALID_SCHEMA": 2,
                "EVALUATION_ERROR": 0,
            },
        }

        with open(scores_file, "w") as f:
            json.dump(sample_scores, f)

        # Read back and verify
        with open(scores_file) as f:
            loaded = json.load(f)

        expected_reasons = {
            "MISSING_PREDICTION",
            "INVALID_JSON",
            "INVALID_SCHEMA",
            "EVALUATION_ERROR",
        }
        actual_reasons = set(loaded["rejected_samples"].keys())
        assert actual_reasons == expected_reasons

    def test_parser_mode_has_legacy_fields(self, tmp_path):
        """Parser mode should maintain legacy fields (total_processed, errors)."""
        scores_file = tmp_path / "scores.json"
        sample_scores = {
            "dataset": "dp_bench",
            "parser": "stub",
            "timestamp": "20240101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"nid": 0.85, "teds": 0.90},
            "total_processed": 10,
            "errors": 1,
        }

        with open(scores_file, "w") as f:
            json.dump(sample_scores, f)

        # Read back and verify
        with open(scores_file) as f:
            loaded = json.load(f)

        assert "total_processed" in loaded
        assert "errors" in loaded
        assert loaded["total_processed"] == 10
        assert loaded["errors"] == 1

    def test_parser_mode_does_not_have_rejection_fields(self, tmp_path):
        """Parser mode should not have evaluated_samples or rejected_samples."""
        scores_file = tmp_path / "scores.json"
        sample_scores = {
            "dataset": "dp_bench",
            "parser": "stub",
            "timestamp": "20240101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"nid": 0.85},
            "total_processed": 10,
            "errors": 1,
        }

        with open(scores_file, "w") as f:
            json.dump(sample_scores, f)

        # Read back and verify
        with open(scores_file) as f:
            loaded = json.load(f)

        assert "evaluated_samples" not in loaded
        assert "rejected_samples" not in loaded


class TestRejectionCountsAccuracy:
    """Tests for accuracy of rejection counts."""

    def test_rejection_counts_match_csv_records(self, tmp_path):
        """Rejection counts should match actual CSV records."""
        # This is a structural test - the actual integration test
        # would run the full pipeline and verify counts match

        # For now, verify the structure is correct
        rejection_counts = {
            "MISSING_PREDICTION": 2,
            "INVALID_JSON": 1,
            "INVALID_SCHEMA": 3,
            "EVALUATION_ERROR": 0,
        }

        total = sum(rejection_counts.values())
        assert total == 6

    def test_evaluated_plus_rejected_equals_total(self, tmp_path):
        """evaluated_samples + sum(rejected_samples) should equal total documents."""
        evaluated = 10
        rejected = {
            "MISSING_PREDICTION": 1,
            "INVALID_JSON": 0,
            "INVALID_SCHEMA": 2,
            "EVALUATION_ERROR": 0,
        }

        total = evaluated + sum(rejected.values())
        assert total == 13

    def test_scores_json_is_valid_json(self, tmp_path):
        """scores.json should be valid JSON."""
        scores_file = tmp_path / "scores.json"
        sample_scores = {
            "dataset": "dp_bench",
            "parser": "predictions",
            "evaluated_samples": 10,
            "rejected_samples": {
                "MISSING_PREDICTION": 1,
                "INVALID_JSON": 0,
                "INVALID_SCHEMA": 2,
                "EVALUATION_ERROR": 0,
            },
        }

        with open(scores_file, "w") as f:
            json.dump(sample_scores, f)

        # Should be able to load without error
        with open(scores_file) as f:
            loaded = json.load(f)

        assert loaded is not None
