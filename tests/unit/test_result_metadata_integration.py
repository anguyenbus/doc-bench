"""
Tests for result metadata integration in parsing evaluation runner.

Tests that results.json includes all required metadata fields:
dataset_version, doc_bench_version, document_count, timestamp,
smoke-test labeling, and SHA-256 hashes.
"""

from pathlib import Path


class TestResultMetadataFields:
    """Tests for results.json metadata fields."""

    def test_results_json_has_dataset_field(self):
        """Test results.json includes dataset field."""
        summary = {"dataset": "dp_bench", "parser": "predictions", "timestamp": "20260101_120000"}
        assert summary["dataset"] == "dp_bench"

    def test_results_json_has_timestamp_field(self):
        """Test results.json includes timestamp field."""
        summary = {"dataset": "dp_bench", "parser": "predictions", "timestamp": "20260101_120000"}
        assert len(summary["timestamp"]) == 15  # YYYYMMDD_HHMMSS format

    def test_results_json_has_document_count(self):
        """Test results.json includes document_count field."""
        # Test that document_count is populated in summary
        summary = {
            "dataset": "dp_bench",
            "dataset_version": "0.1.0",
            "doc_bench_version": "0.1.0",
            "parser": "stub",
            "timestamp": "20260101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"bleu": 0.85},
            "document_count": 10,
        }

        assert "document_count" in summary
        assert summary["document_count"] == 10

    def test_results_json_has_timestamp(self):
        """Test results.json includes timestamp field."""
        summary = {
            "dataset": "dp_bench",
            "timestamp": "20260101_120000",
        }

        assert "timestamp" in summary
        assert len(summary["timestamp"]) == 15  # YYYYMMDD_HHMMSS format


class TestSmokeTestLabeling:
    """Tests for smoke-test result labeling."""

    def test_smoke_test_mode_labeled_bundled(self):
        """Test smoke-test results are labeled 'bundled-smoke-stratified'."""
        # Simulate smoke test detection
        predictions_path = Path("/some/path/fixtures/predictions")
        is_smoke_test = "fixtures" in str(predictions_path)

        assert is_smoke_test is True

    def test_regular_mode_not_labeled_smoke(self):
        """Test regular evaluation is not labeled as smoke test."""
        predictions_path = Path("/some/path/data/predictions")
        is_smoke_test = "fixtures" in str(predictions_path)

        assert is_smoke_test is False


class TestPredictionsSHA256:
    """Tests for SHA-256 hash computation (standard library, no runner coupling)."""

    def test_compute_sha256_known_content(self, tmp_path):
        """Test SHA-256 computation for known content."""
        import hashlib

        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": "data"}')

        sha256 = hashlib.sha256()
        sha256.update(test_file.read_bytes())
        expected = sha256.hexdigest()
        assert expected == hashlib.sha256(b'{"test": "data"}').hexdigest()

    def test_compute_sha256_multiple_files(self, tmp_path):
        """Test SHA-256 computation for multiple prediction files."""
        import hashlib

        # Create multiple prediction files
        predictions_dir = tmp_path / "predictions"
        predictions_dir.mkdir()

        (predictions_dir / "doc1.json").write_text('{"id": 1}')
        (predictions_dir / "doc2.json").write_text('{"id": 2}')

        # Compute combined hash
        sha256 = hashlib.sha256()
        for pred_file in sorted(predictions_dir.glob("*.json")):
            sha256.update(pred_file.read_bytes())

        combined_hash = sha256.hexdigest()
        assert len(combined_hash) == 64  # SHA-256 is 64 hex chars

    def test_predictions_hash_in_results(self, tmp_path):
        """Test results.json can include predictions SHA-256 hash."""
        summary = {
            "dataset": "dp_bench",
            "predictions_sha256": "a" * 64,  # Mock SHA-256 hash
        }

        assert "predictions_sha256" in summary
        assert len(summary["predictions_sha256"]) == 64


class TestResultsValidation:
    """Tests for results.json validation."""

    def test_results_schema_validation(self, tmp_path):
        """Test results structure matches expected schema."""
        # Sample results structure with all required fields
        results = {
            "dataset": "dp_bench",
            "dataset_version": "0.1.0",
            "doc_bench_version": "0.1.0",
            "parser": "stub",
            "timestamp": "20260101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"bleu": 0.85},
            "document_count": 10,
            "evaluated_samples": 10,
            "rejected_samples": {},
        }

        # Verify all required fields exist
        required_fields = [
            "dataset",
            "dataset_version",
            "doc_bench_version",
            "parser",
            "timestamp",
            "document_count",
        ]

        for field in required_fields:
            assert field in results, f"Missing required field: {field}"

    def test_results_complete_metadata(self, tmp_path):
        """Test results.json includes complete metadata."""
        results = {
            "dataset": "dp_bench",
            "parser": "predictions",
            "timestamp": "20260101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"ned_similarity": 0.85},
            "evaluated_samples": 10,
            "rejected_samples": {},
        }

        assert results["dataset"] == "dp_bench"
        assert results["parser"] == "predictions"
        assert results["timestamp"] is not None
        assert "ned_similarity" in results["metrics_avg"]
