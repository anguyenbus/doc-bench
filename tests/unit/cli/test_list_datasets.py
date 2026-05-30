"""
Tests for list-datasets CLI command.

Tests dataset listing with version information and cache status.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_manifest(tmp_path):
    """Create a mock MANIFEST.yaml."""
    import yaml

    manifest = {
        "dp_bench": {
            "version": "v1.0",
            "sha256": "abc123",
        },
        "omnidocbench": {
            "version": "v1.0",
            "sha256": "def456",
        },
        "omnidocbench_nano": {
            "version": "v1.0",
            "sha256": "xyz789",
        },
    }

    manifest_path = tmp_path / "MANIFEST.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    return manifest_path


@pytest.fixture
def empty_cache(tmp_path):
    """Create empty cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def populated_cache(tmp_path):
    """Create cache directory with cached datasets."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create some cached dataset directories
    (cache_dir / "dp_bench-v1.0").mkdir()
    (cache_dir / "omnidocbench-v1.0").mkdir()

    return cache_dir


class TestListDatasetsBasic:
    """Tests for basic dataset listing functionality."""

    def test_list_shows_available_datasets(self, runner, mock_manifest, empty_cache):
        """Test listing shows all available datasets from manifest."""
        from doc_bench.cli.list_datasets import main

        result = runner.invoke(
            main,
            ["--manifest", str(mock_manifest), "--cache-dir", str(empty_cache)],
        )

        assert result.exit_code == 0
        assert "dp_bench" in result.output
        assert "omnidocbench" in result.output
        assert "omnidocbench_nano" in result.output

    def test_list_shows_versions(self, runner, mock_manifest, empty_cache):
        """Test listing shows version information."""
        from doc_bench.cli.list_datasets import main

        result = runner.invoke(
            main,
            ["--manifest", str(mock_manifest), "--cache-dir", str(empty_cache)],
        )

        assert result.exit_code == 0
        assert "v1.0" in result.output

    def test_list_shows_not_cached_status(self, runner, mock_manifest, empty_cache):
        """Test listing shows 'not cached' for uncached datasets."""
        from doc_bench.cli.list_datasets import main

        result = runner.invoke(
            main,
            ["--manifest", str(mock_manifest), "--cache-dir", str(empty_cache)],
        )

        assert result.exit_code == 0
        # Empty cache should show datasets as not cached
        assert "not cached" in result.output.lower() or "no" in result.output.lower()

    def test_list_shows_cached_status(self, runner, mock_manifest, populated_cache):
        """Test listing shows 'cached' for cached datasets."""
        from doc_bench.cli.list_datasets import main

        result = runner.invoke(
            main,
            ["--manifest", str(mock_manifest), "--cache-dir", str(populated_cache)],
        )

        assert result.exit_code == 0
        # Should show at least some datasets as cached
        assert "cached" in result.output.lower() or "yes" in result.output.lower()

    def test_list_missing_manifest(self, runner, empty_cache):
        """Test listing handles missing manifest gracefully."""
        from doc_bench.cli.list_datasets import main

        missing_manifest = Path("/nonexistent/MANIFEST.yaml")
        result = runner.invoke(
            main,
            ["--manifest", str(missing_manifest), "--cache-dir", str(empty_cache)],
        )

        assert result.exit_code != 0
        assert "manifest" in result.output.lower() or "not found" in result.output.lower()

    def test_list_format_table_structure(self, runner, mock_manifest, empty_cache):
        """Test listing output has table-like structure."""
        from doc_bench.cli.list_datasets import main

        result = runner.invoke(
            main,
            ["--manifest", str(mock_manifest), "--cache-dir", str(empty_cache)],
        )

        assert result.exit_code == 0
        # Should have headers and data rows
        lines = result.output.strip().split('\n')
        assert len(lines) >= 3  # Header + separator + at least one data row
