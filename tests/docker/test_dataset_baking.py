"""
Tests for build-time dataset download.

Validates OmniDocBench and DP-Bench dataset baking during Docker build.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

# Paths
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
DOCKERFILE_PATH: Final[Path] = ROOT_DIR / "Dockerfile"


@pytest.fixture(scope="module")
def dockerfile_content() -> str:
    """Load Dockerfile content as string."""
    if not DOCKERFILE_PATH.exists():
        pytest.fail(f"Dockerfile not found at {DOCKERFILE_PATH}")

    return DOCKERFILE_PATH.read_text()


class TestDatasetDownloadScript:
    """Test that dataset download script is integrated."""

    def test_download_script_copied(self, dockerfile_content: str) -> None:
        """Test that download_datasets.py script is available."""
        # The script should be copied via the scripts directory copy
        assert re.search(
            r"COPY.*?scripts",
            dockerfile_content,
        ), "scripts directory (containing download_datasets.py) should be copied"

    def test_download_invoked_during_build(self, dockerfile_content: str) -> None:
        """Test that dataset download is invoked during Docker build."""
        # Look for uv run with download_datasets.py
        assert re.search(
            r"uv\s+run.*?(download|dataset)",
            dockerfile_content,
            re.IGNORECASE,
        ), "Dataset download should be invoked with uv run during build"


class TestDownloadTarget:
    """Test that datasets are downloaded to correct location."""

    def test_download_to_opt_docbench_data(self, dockerfile_content: str) -> None:
        """Test that datasets are downloaded to /opt/doc-bench/data."""
        # This could be via --output-dir flag or working directory
        assert "/opt/doc-bench/data" in dockerfile_content or \
               "/opt/doc-bench" in dockerfile_content, \
               "Datasets should be downloaded to /opt/doc-bench/data"

    def test_omnidocbench_dataset_specified(self, dockerfile_content: str) -> None:
        """Test that OmniDocBench dataset is specified for download."""
        # Check for omnidocbench in download arguments
        assert re.search(
            r"omnidocbench",
            dockerfile_content,
            re.IGNORECASE,
        ), "OmniDocBench dataset should be specified for download"

    def test_dp_bench_dataset_specified(self, dockerfile_content: str) -> None:
        """Test that DP-Bench dataset is specified for download."""
        # Check for dp_bench in download arguments
        assert re.search(
            r"dp_bench",
            dockerfile_content,
            re.IGNORECASE,
        ), "DP-Bench dataset should be specified for download"


class TestDatasetVerification:
    """Test that datasets are verified after download."""

    def test_dataset_integrity_checked(self, dockerfile_content: str) -> None:
        """Test that dataset integrity is verified after download."""
        # Look for test commands that verify directories exist
        assert re.search(
            r"test\s+-d",
            dockerfile_content,
        ), "Dataset directories should be verified"

    def test_manifest_checked(self, dockerfile_content: str) -> None:
        """Test that MANIFEST.yaml is checked after download."""
        assert re.search(
            r"MANIFEST\.yaml",
            dockerfile_content,
        ), "MANIFEST.yaml should be checked after download"


class TestDatasetCleanup:
    """Test that build artifacts are cleaned after download."""

    def test_cleanup_after_download(self, dockerfile_content: str) -> None:
        """Test that cleanup is performed after dataset download."""
        # Look for cleanup commands (rm, apt-get clean, uv cache clean, etc.)
        assert re.search(
            r"(rm\s+-rf|apt-get\s+clean|cache\s+clean)",
            dockerfile_content,
        ), "Cleanup should be performed after operations"


class TestDatasetCopyToRuntime:
    """Test that datasets are copied to runtime stage."""

    def test_datasets_copied_from_datasets_stage(self, dockerfile_content: str) -> None:
        """Test that data directory is copied from datasets stage to runtime."""
        assert re.search(
            r"COPY.*?--from=datasets.*?/opt/doc-bench/data",
            dockerfile_content,
        ), "Datasets should be copied from datasets stage to runtime"

    def test_dataset_ownership_set(self, dockerfile_content: str) -> None:
        """Test that dataset ownership is set to docbench user."""
        assert re.search(
            r"--chown=docbench.*?/opt/doc-bench/data",
            dockerfile_content,
        ), "Dataset ownership should be set to docbench user"
