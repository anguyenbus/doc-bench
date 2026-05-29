"""
Tests for image size optimization.

Validates .dockerignore, cleanup steps, and layer optimization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

# Paths
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
DOCKERFILE_PATH: Final[Path] = ROOT_DIR / "Dockerfile"
DOCKERIGNORE_PATH: Final[Path] = ROOT_DIR / ".dockerignore"


@pytest.fixture(scope="module")
def dockerfile_content() -> str:
    """Load Dockerfile content as string."""
    if not DOCKERFILE_PATH.exists():
        pytest.fail(f"Dockerfile not found at {DOCKERFILE_PATH}")

    return DOCKERFILE_PATH.read_text()


@pytest.fixture(scope="module")
def dockerignore_content() -> str | None:
    """Load .dockerignore content as string."""
    if not DOCKERIGNORE_PATH.exists():
        return None
    return DOCKERIGNORE_PATH.read_text()


class TestDockerignore:
    """Test that .dockerignore file exists and excludes unnecessary files."""

    def test_dockerignore_exists(self, dockerignore_content: str | None) -> None:
        """Test that .dockerignore file exists."""
        assert dockerignore_content is not None, ".dockerignore file should exist"

    def test_git_excluded(self, dockerignore_content: str | None) -> None:
        """Test that .git is excluded."""
        if dockerignore_content is None:
            pytest.fail(".dockerignore does not exist")
        assert ".git" in dockerignore_content, ".git should be excluded"

    def test_pycache_excluded(self, dockerignore_content: str | None) -> None:
        """Test that __pycache__ is excluded."""
        if dockerignore_content is None:
            pytest.fail(".dockerignore does not exist")
        assert "__pycache__" in dockerignore_content, "__pycache__ should be excluded"

    def test_tests_excluded(self, dockerignore_content: str | None) -> None:
        """Test that tests/ directory is excluded."""
        if dockerignore_content is None:
            pytest.fail(".dockerignore does not exist")
        assert "tests" in dockerignore_content, "tests directory should be excluded"


class TestCleanupSteps:
    """Test that cleanup steps are implemented."""

    def test_apt_cache_cleaned(self, dockerfile_content: str) -> None:
        """Test that apt cache is cleaned."""
        assert re.search(
            r"rm\s+-rf\s+/var/lib/apt/lists",
            dockerfile_content,
        ), "apt cache should be cleaned"

    def test_uv_cache_cleaned(self, dockerfile_content: str) -> None:
        """Test that uv cache is cleaned."""
        assert re.search(
            r"uv\s+cache\s+clean",
            dockerfile_content,
            re.IGNORECASE,
        ), "uv cache should be cleaned"

    def test_apt_get_clean_used(self, dockerfile_content: str) -> None:
        """Test that apt-get clean is used."""
        assert re.search(
            r"apt-get\s+clean",
            dockerfile_content,
        ), "apt-get clean should be used"


class TestLayerOptimization:
    """Test that layers are optimized."""

    def test_multi_stage_build_used(self, dockerfile_content: str) -> None:
        """Test that multi-stage build is used."""
        from_count = len(re.findall(r"^FROM\s+", dockerfile_content, re.MULTILINE))
        assert from_count >= 3, "Multi-stage build should have at least 3 stages"

    def test_copy_from_builder_used(self, dockerfile_content: str) -> None:
        """Test that COPY --from=builder is used."""
        assert re.search(
            r"COPY.*?--from=builder",
            dockerfile_content,
        ), "COPY --from=builder should be used for multi-stage build"

    def test_copy_from_datasets_used(self, dockerfile_content: str) -> None:
        """Test that COPY --from=datasets is used."""
        assert re.search(
            r"COPY.*?--from=datasets",
            dockerfile_content,
        ), "COPY --from=datasets should be used"
