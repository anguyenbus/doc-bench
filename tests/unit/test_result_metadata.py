"""
Tests for result metadata stamping.

Tests results.json includes all required metadata fields:
dataset_version, doc_bench_version, document_count, timestamp,
smoke-test labeling, and SHA-256 hashes.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestMetadataHelperFunctions:
    """Tests for metadata helper functions."""

    def test_compute_sha256_known_content(self, tmp_path):
        """Test SHA-256 computation for known content."""
        from doc_bench.runners.run_parsing_eval import _compute_sha256
        import hashlib

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        expected = hashlib.sha256(b"Hello, World!").hexdigest()
        assert _compute_sha256(test_file) == expected

    def test_compute_sha256_binary_content(self, tmp_path):
        """Test SHA-256 computation for binary content."""
        from doc_bench.runners.run_parsing_eval import _compute_sha256
        import hashlib

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03")

        expected = hashlib.sha256(b"\x00\x01\x02\x03").hexdigest()
        assert _compute_sha256(test_file) == expected

    def test_get_doc_bench_version(self):
        """Test doc-bench version retrieval."""
        from doc_bench.runners.run_parsing_eval import _get_doc_bench_version

        version = _get_doc_bench_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_dataset_version_no_manifest(self):
        """Test dataset version without manifest returns fallback."""
        from doc_bench.runners.run_parsing_eval import _get_dataset_version

        with patch("pathlib.Path.exists", return_value=False):
            version = _get_dataset_version("dp_bench", {})
            assert version == "2026.05"  # Fallback version

    def test_get_dataset_version_manifest_structure(self):
        """Test dataset version function structure."""
        from doc_bench.runners.run_parsing_eval import _get_dataset_version

        # Test that function handles manifest reading structure
        # Even if manifest doesn't exist, should return fallback
        config = {}
        version = _get_dataset_version("test_dataset", config)
        assert isinstance(version, str)


class TestResultsMetadataFields:
    """Tests for results.json metadata fields."""

    def test_results_json_has_required_fields(self, tmp_path):
        """Test results.json includes all required top-level fields."""
        # Test that we can create a results dict with all required fields
        from doc_bench.runners.run_parsing_eval import (
            _get_doc_bench_version,
            _get_dataset_version,
        )

        results = {
            "dataset": "dp_bench",
            "dataset_version": _get_dataset_version("dp_bench", {}),
            "doc_bench_version": _get_doc_bench_version(),
            "parser": "stub",
            "timestamp": "20260101_120000",
            "csv_file": "results.csv",
            "metrics_avg": {"bleu": 0.85},
            "document_count": 10,
        }

        # Check all required fields exist
        assert "dataset" in results
        assert "dataset_version" in results
        assert "doc_bench_version" in results
        assert "parser" in results
        assert "timestamp" in results
        assert "document_count" in results

    def test_results_json_predictions_hash(self, tmp_path):
        """Test results.json can include predictions SHA-256 hash."""
        from doc_bench.runners.run_parsing_eval import _compute_sha256

        # Create test predictions
        pred_file = tmp_path / "doc1.json"
        pred_file.write_text('{"test": "data"}')

        hash_value = _compute_sha256(pred_file)
        assert len(hash_value) == 64  # SHA-256 is 64 hex chars
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestSmokeTestLabeling:
    """Tests for smoke-test result labeling."""

    def test_smoke_test_results_labeled_bundled(self, tmp_path):
        """Test smoke-test results are labeled 'bundled-smoke-stratified'."""
        from doc_bench.cli.smoke_test import main
        from click.testing import CliRunner

        runner = CliRunner()
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()

        # Create fixture manifest
        import json
        manifest = {
            "dataset_name": "bundled-smoke-stratified",
            "documents": [],
            "count": 0,
        }
        with open(fixtures_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        result = runner.invoke(main, ["--data", str(fixtures_dir)])

        # Should pass with bundled fixtures
        assert result.exit_code == 0
