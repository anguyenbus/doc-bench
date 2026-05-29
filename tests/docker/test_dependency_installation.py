"""
Tests for dependency installation with uv.

Validates uv installation, dependency installation, venv copying, and Python imports.
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


class TestUvInstallation:
    """Test that uv is installed correctly in builder stage."""

    def test_uv_installed_from_official_image(self, dockerfile_content: str) -> None:
        """Test that uv is installed from official uv image."""
        assert re.search(
            r"--from=ghcr\.io/astral-sh/uv",
            dockerfile_content,
        ), "uv should be installed from official ghcr.io/astral-sh/uv image"

    def test_uv_copied_to_path(self, dockerfile_content: str) -> None:
        """Test that uv binary is copied to /usr/local/bin/uv."""
        assert re.search(
            r"COPY.*?/uv\s+/usr/local/bin/uv",
            dockerfile_content,
        ), "uv binary should be copied to /usr/local/bin/uv"


class TestDependencyInstallation:
    """Test that dependencies are installed correctly."""

    def test_uv_sync_with_frozen_flag(self, dockerfile_content: str) -> None:
        """Test that uv sync is run with --frozen flag."""
        assert re.search(
            r"uv\s+sync.*?--frozen",
            dockerfile_content,
        ), "uv sync should use --frozen flag for reproducibility"

    def test_uv_system_python_set(self, dockerfile_content: str) -> None:
        """Test that UV_SYSTEM_PYTHON=1 is set."""
        assert re.search(
            r"UV_SYSTEM_PYTHON\s*=\s*1",
            dockerfile_content,
            re.IGNORECASE,
        ), "UV_SYSTEM_PYTHON=1 should be set"


class TestVenvCopy:
    """Test that virtual environment is copied to runtime stage."""

    def test_venv_copied_from_builder(self, dockerfile_content: str) -> None:
        """Test that .venv is copied from builder stage."""
        assert re.search(
            r"COPY.*?--from=builder.*?/\.venv",
            dockerfile_content,
        ), ".venv should be copied from builder to runtime"

    def test_venv_ownership_set(self, dockerfile_content: str) -> None:
        """Test that venv ownership is set to docbench user."""
        assert re.search(
            r"--chown=docbench.*?/\.venv",
            dockerfile_content,
        ), ".venv ownership should be set to docbench user"


class TestRuntimeDependencies:
    """Test that runtime dependencies are installed."""

    def test_path_includes_venv(self, dockerfile_content: str) -> None:
        """Test that PATH includes /.venv/bin."""
        assert re.search(
            r"PATH=.*?/\.venv/bin",
            dockerfile_content,
        ), "PATH should include /.venv/bin"

    def test_curl_installed(self, dockerfile_content: str) -> None:
        """Test that curl is installed for health checks."""
        # Check for curl in any apt-get install line
        assert "curl" in dockerfile_content.lower(), "curl should be installed for health checks"

    def test_apt_caches_cleaned(self, dockerfile_content: str) -> None:
        """Test that apt caches are cleaned."""
        assert re.search(
            r"rm\s+-rf\s+/var/lib/apt/lists",
            dockerfile_content,
        ), "apt caches should be cleaned"
