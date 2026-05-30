"""
Tests for download CLI command.

Tests version-pinned dataset download system with SHA-256 verification
and cache management.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

# Import will be added after implementation
# from doc_bench.cli.download import main, _compute_sha256, _verify_hash, _get_cache_dir


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
            "url": "https://example.com/dp_bench.zip",
        },
        "omnidocbench": {
            "version": "v1.0",
            "sha256": "def456",
            "url": "https://example.com/omnidocbench.zip",
        },
    }

    manifest_path = tmp_path / "MANIFEST.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    return manifest_path


class TestSha256Computation:
    """Tests for SHA-256 computation."""

    def test_compute_sha256_known_content(self, tmp_path):
        """Test SHA-256 computation for known content."""
        from doc_bench.cli.download import _compute_sha256

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        expected = hashlib.sha256(b"Hello, World!").hexdigest()
        assert _compute_sha256(test_file) == expected

    def test_compute_sha256_binary_content(self, tmp_path):
        """Test SHA-256 computation for binary content."""
        from doc_bench.cli.download import _compute_sha256

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03")

        expected = hashlib.sha256(b"\x00\x01\x02\x03").hexdigest()
        assert _compute_sha256(test_file) == expected


class TestHashVerification:
    """Tests for hash verification."""

    def test_verify_hash_success(self, tmp_path):
        """Test successful hash verification."""
        from doc_bench.cli.download import _verify_hash

        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        sha256 = hashlib.sha256(b"test").hexdigest()
        assert _verify_hash(test_file, sha256) is True

    def test_verify_hash_failure(self, tmp_path):
        """Test failed hash verification."""
        from doc_bench.cli.download import _verify_hash

        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        assert _verify_hash(test_file, "wronghash") is False

    def test_verify_hash_missing_file(self, tmp_path):
        """Test verification with missing file."""
        from doc_bench.cli.download import _verify_hash

        missing_file = tmp_path / "missing.txt"
        assert _verify_hash(missing_file, "anyhash") is False


class TestCacheManagement:
    """Tests for cache management."""

    def test_get_cache_dir_default(self):
        """Test default cache directory path."""
        from doc_bench.cli.download import _get_cache_dir

        with patch("pathlib.Path.home", return_value=Path("/mock/home")):
            cache_dir = _get_cache_dir(None)
            expected = Path("/mock/home/.cache/doc-bench")
            assert cache_dir == expected

    def test_get_cache_dir_custom_env(self, monkeypatch):
        """Test custom cache directory via environment variable."""
        from doc_bench.cli.download import _get_cache_dir

        monkeypatch.setenv("DOC_BENCH_CACHE", "/custom/cache/path")
        cache_dir = _get_cache_dir(None)
        assert cache_dir == Path("/custom/cache/path")

    def test_get_cache_dir_explicit(self):
        """Test explicitly provided cache directory."""
        from doc_bench.cli.download import _get_cache_dir

        explicit_path = Path("/explicit/cache")
        cache_dir = _get_cache_dir(explicit_path)
        assert cache_dir == explicit_path


class TestDownloadValidation:
    """Tests for download validation."""

    def test_download_requires_version(self, runner, mock_manifest):
        """Test download command requires explicit version."""
        from doc_bench.cli.download import main

        result = runner.invoke(main, ["--dataset", "dp_bench", "--manifest", str(mock_manifest)])

        assert result.exit_code != 0
        assert "version" in result.output.lower() or "required" in result.output.lower()

    def test_download_validates_version_exists(self, runner, mock_manifest):
        """Test download validates version exists in manifest."""
        from doc_bench.cli.download import main

        result = runner.invoke(
            main,
            [
                "--dataset",
                "dp_bench",
                "--version",
                "v2.0",  # Non-existent version
                "--manifest",
                str(mock_manifest),
            ],
        )

        assert result.exit_code != 0
        assert "version" in result.output.lower() or "not found" in result.output.lower()

    def test_download_rejects_latest_keyword(self, runner, mock_manifest):
        """Test download rejects 'latest' as version."""
        from doc_bench.cli.download import main

        result = runner.invoke(
            main,
            [
                "--dataset",
                "dp_bench",
                "--version",
                "latest",
                "--manifest",
                str(mock_manifest),
            ],
        )

        assert result.exit_code != 0
        assert "latest" in result.output.lower() or "explicit" in result.output.lower()
