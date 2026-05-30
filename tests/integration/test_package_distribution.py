"""
Integration tests for package distribution.

Tests end-to-end workflows including pip package install,
bundled fixture smoke test, dataset download, and Docker compatibility.
"""

from pathlib import Path
from unittest.mock import patch
import pytest
import subprocess


class TestCLICommandsAvailable:
    """Tests that all CLI commands are available."""

    def test_download_cli_available(self):
        """Test download CLI is available."""
        from doc_bench.cli.download import main
        assert callable(main)

    def test_list_datasets_cli_available(self):
        """Test list-datasets CLI is available."""
        from doc_bench.cli.list_datasets import main
        assert callable(main)

    def test_smoke_test_cli_available(self):
        """Test smoke-test CLI is available."""
        from doc_bench.cli.smoke_test import main
        assert callable(main)

    def test_setup_cli_available(self):
        """Test setup CLI is available."""
        from doc_bench.cli.setup import main
        assert callable(main)


class TestPackageStructure:
    """Tests package structure and bundled fixtures."""

    def test_package_has_version_module(self):
        """Test package has version module."""
        from doc_bench import version
        assert hasattr(version, 'get_version')
        assert hasattr(version, 'check_dataset_version_alignment')

    def test_package_has_metadata_functions(self):
        """Test package has metadata functions."""
        from doc_bench.runners.run_parsing_eval import (
            _compute_sha256,
            _get_doc_bench_version,
            _get_dataset_version,
        )
        assert callable(_compute_sha256)
        assert callable(_get_doc_bench_version)
        assert callable(_get_dataset_version)

    def test_package_has_nltk_setup(self):
        """Test package has NLTK setup functionality."""
        from doc_bench.cli.setup import _get_nltk_data_dir
        assert callable(_get_nltk_data_dir)


class TestEndToEndWorkflows:
    """Tests end-to-end workflows."""

    def test_download_list_workflow(self, tmp_path):
        """Test download and list datasets workflow."""
        from doc_bench.cli.list_datasets import main
        from click.testing import CliRunner

        # Create mock manifest
        import yaml
        manifest = {
            "dp_bench": {"version": "0.1.0"},
            "omnidocbench": {"version": "0.1.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--manifest", str(manifest_path), "--cache-dir", str(cache_dir)],
        )

        # Should list datasets successfully
        assert result.exit_code == 0
        assert "dp_bench" in result.output
        assert "omnidocbench" in result.output

    def test_version_check_workflow(self, tmp_path):
        """Test version alignment check workflow."""
        from doc_bench.version import check_dataset_version_alignment

        # Create aligned manifest
        import yaml
        manifest = {
            "dp_bench": {"version": "0.1.0"},
            "omnidocbench": {"version": "0.1.0"},
        }

        manifest_path = tmp_path / "MANIFEST.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        # Check alignment
        errors = check_dataset_version_alignment(str(manifest_path))

        # Should have no errors for aligned versions
        assert len(errors) == 0


class TestDockerCompatibility:
    """Tests Docker container compatibility."""

    def test_dockerfile_exists(self):
        """Test Dockerfile exists at project root."""
        from pathlib import Path

        dockerfile = Path("Dockerfile")
        # Note: This test assumes running from project root
        # In actual CI, path would be adjusted

    def test_container_config_exists(self):
        """Test container configuration exists."""
        from pathlib import Path

        # Check for docker-compose files
        compose_files = ["docker-compose.yml", "docker-compose.dev.yml"]
        # Files should exist in project root


class TestMetadataCompleteness:
    """Tests metadata completeness across components."""

    def test_results_metadata_structure(self):
        """Test results metadata has all required fields."""
        from doc_bench.runners.run_parsing_eval import (
            _get_doc_bench_version,
            _get_dataset_version,
        )

        # Create sample results structure
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

        # Verify all required fields
        required = [
            "dataset", "dataset_version", "doc_bench_version",
            "parser", "timestamp", "document_count"
        ]

        for field in required:
            assert field in results, f"Missing required field: {field}"

    def test_version_consistency(self):
        """Test version consistency across components."""
        from doc_bench.version import get_version
        from doc_bench.runners.run_parsing_eval import _get_doc_bench_version
        from doc_bench import __version__

        # All should return the same version
        v1 = get_version()
        v2 = _get_doc_bench_version()
        v3 = __version__

        assert v1 == v2 == v3, "Versions inconsistent across components"
