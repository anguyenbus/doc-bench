"""
Tests for application code integration.

Validates source code copying, package installation, CLI entry points, and module imports.
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


class TestSourceCodeCopy:
    """Test that source code is copied correctly."""

    def test_src_directory_copied(self, dockerfile_content: str) -> None:
        """Test that src/ directory is copied to image."""
        assert re.search(
            r"COPY.*?references/eval-harness/src\s+/opt/doc-bench/src",
            dockerfile_content,
        ), "src/ directory should be copied to /opt/doc-bench/src"

    def test_scripts_directory_copied(self, dockerfile_content: str) -> None:
        """Test that scripts/ directory is copied to image."""
        assert re.search(
            r"COPY.*?references/eval-harness/scripts",
            dockerfile_content,
        ), "scripts/ directory should be copied"

    def test_configs_directory_copied(self, dockerfile_content: str) -> None:
        """Test that configs/ directory is copied to image."""
        assert re.search(
            r"COPY.*?references/eval-harness/configs",
            dockerfile_content,
        ), "configs/ directory should be copied"


class TestPythonpath:
    """Test that PYTHONPATH is configured correctly."""

    def test_pythonpath_includes_src(self, dockerfile_content: str) -> None:
        """Test that PYTHONPATH includes src directory."""
        assert re.search(
            r"PYTHONPATH=.*?/opt/doc-bench/src",
            dockerfile_content,
        ), "PYTHONPATH should include /opt/doc-bench/src"

    def test_pythonpath_includes_scripts(self, dockerfile_content: str) -> None:
        """Test that PYTHONPATH includes scripts directory."""
        assert re.search(
            r"PYTHONPATH=.*?/opt/doc-bench/scripts",
            dockerfile_content,
        ), "PYTHONPATH should include /opt/doc-bench/scripts"


class TestCliEntryPoints:
    """Test that CLI entry points are available."""

    def test_entrypoint_uses_uv_run(self, dockerfile_content: str) -> None:
        """Test that ENTRYPOINT uses uv run for executing CLI commands."""
        assert re.search(
            r'ENTRYPOINT\s+\["uv",\s*"run"\]',
            dockerfile_content,
        ), "ENTRYPOINT should use uv run pattern"

    def test_default_cmd_is_help(self, dockerfile_content: str) -> None:
        """Test that default CMD is --help."""
        assert re.search(
            r'CMD\s+\["--help"\]',
            dockerfile_content,
        ), "Default CMD should be --help"


class TestFileOwnership:
    """Test that application files have correct ownership."""

    def test_src_ownership_set(self, dockerfile_content: str) -> None:
        """Test that src directory ownership is set to docbench."""
        assert re.search(
            r"--chown=docbench.*?/opt/doc-bench/src",
            dockerfile_content,
        ), "src ownership should be set to docbench"

    def test_scripts_ownership_set(self, dockerfile_content: str) -> None:
        """Test that scripts directory ownership is set to docbench."""
        assert re.search(
            r"--chown=docbench.*?/opt/doc-bench/scripts",
            dockerfile_content,
        ), "scripts ownership should be set to docbench"

    def test_configs_ownership_set(self, dockerfile_content: str) -> None:
        """Test that configs directory ownership is set to docbench."""
        assert re.search(
            r"--chown=docbench.*?/opt/doc-bench/configs",
            dockerfile_content,
        ), "configs ownership should be set to docbench"
