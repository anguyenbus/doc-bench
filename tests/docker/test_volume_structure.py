"""
Tests for volume structure configuration.

Validates volume mount directories, internal data directory, and WORKDIR.
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


class TestVolumeMountDirectories:
    """Test that volume mount directories are created."""

    def test_work_parsers_created(self, dockerfile_content: str) -> None:
        """Test that /work/parsers directory is created."""
        assert re.search(
            r"mkdir.*?/work/parsers",
            dockerfile_content,
        ), "/work/parsers directory should be created"

    def test_work_results_created(self, dockerfile_content: str) -> None:
        """Test that /work/results directory is created."""
        assert re.search(
            r"mkdir.*?/work/results",
            dockerfile_content,
        ), "/work/results directory should be created"


class TestInternalDataDirectory:
    """Test that internal data directory is created."""

    def test_opt_docbench_data_created_or_copied(self, dockerfile_content: str) -> None:
        """Test that /opt/doc-bench/data directory is created or copied."""
        # Data directory is created by download script in datasets stage
        # and then copied to runtime stage
        data_copied = re.search(
            r"COPY.*?/opt/doc-bench/data",
            dockerfile_content,
        )
        assert data_copied, "/opt/doc-bench/data directory should be copied from datasets stage"


class TestWorkdir:
    """Test that WORKDIR is set correctly."""

    def test_workdir_set_to_opt_docbench(self, dockerfile_content: str) -> None:
        """Test that WORKDIR is set to /opt/doc-bench."""
        assert re.search(
            r"WORKDIR\s+/opt/doc-bench",
            dockerfile_content,
        ), "WORKDIR should be set to /opt/doc-bench"


class TestApplicationDirectories:
    """Test that application directories are created."""

    def test_src_directory_created(self, dockerfile_content: str) -> None:
        """Test that /opt/doc-bench/src directory is created."""
        assert re.search(
            r"mkdir.*?/opt/doc-bench/src",
            dockerfile_content,
        ), "/opt/doc-bench/src directory should be created"

    def test_scripts_directory_created(self, dockerfile_content: str) -> None:
        """Test that /opt/doc-bench/scripts directory is created."""
        assert re.search(
            r"mkdir.*?/opt/doc-bench/scripts",
            dockerfile_content,
        ), "/opt/doc-bench/scripts directory should be created"

    def test_configs_directory_created(self, dockerfile_content: str) -> None:
        """Test that /opt/doc-bench/configs directory is created."""
        assert re.search(
            r"mkdir.*?/opt/doc-bench/configs",
            dockerfile_content,
        ), "/opt/doc-bench/configs directory should be created"
