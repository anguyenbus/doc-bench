"""
Tests for Dockerfile core structure.

Validates multi-stage build, base image, non-root user, WORKDIR, and entry point.
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


class TestMultiStageBuild:
    """Test that Dockerfile has proper multi-stage build structure."""

    def test_has_builder_stage(self, dockerfile_content: str) -> None:
        """Test that Dockerfile has a builder stage."""
        assert re.search(
            r"FROM\s+python:3\.12-slim\s+AS\s+builder",
            dockerfile_content,
            re.IGNORECASE,
        ), "Dockerfile must have 'FROM python:3.12-slim AS builder' stage"

    def test_has_runtime_stage(self, dockerfile_content: str) -> None:
        """Test that Dockerfile has a runtime stage."""
        assert re.search(
            r"FROM\s+python:3\.12-slim\s+AS\s+runtime",
            dockerfile_content,
            re.IGNORECASE,
        ), "Dockerfile must have 'FROM python:3.12-slim AS runtime' stage"

    def test_stages_are_separate(self, dockerfile_content: str) -> None:
        """Test that builder and runtime stages are separate FROM instructions."""
        from_count = len(re.findall(r"^FROM\s+", dockerfile_content, re.MULTILINE))
        assert from_count >= 2, (
            "Dockerfile must have at least 2 FROM instructions for multi-stage build"
        )


class TestBaseImage:
    """Test that base image is correct."""

    def test_base_image_is_python_312_slim(self, dockerfile_content: str) -> None:
        """Test that base image is python:3.12-slim."""
        assert re.search(
            r"FROM\s+python:3\.12-slim",
            dockerfile_content,
        ), "Base image must be python:3.12-slim (not 3.13)"

    def test_no_python_313(self, dockerfile_content: str) -> None:
        """Test that python:3.13 is NOT used."""
        assert not re.search(
            r"FROM\s+python:3\.13",
            dockerfile_content,
        ), "Python 3.13 should not be used (use 3.12-slim for stability)"


class TestNonRootUser:
    """Test that non-root user is created and used."""

    def test_non_root_user_created(self, dockerfile_content: str) -> None:
        """Test that docbench user with UID 1000 is created."""
        # Match useradd with -u 1000 (allow other flags like -r)
        assert re.search(
            r"useradd.*-u\s+1000",
            dockerfile_content,
            re.IGNORECASE,
        ), "Dockerfile must create user 'docbench' with UID 1000"

    def test_user_switched_to_docbench(self, dockerfile_content: str) -> None:
        """Test that container switches to docbench user."""
        assert re.search(
            r"USER\s+docbench",
            dockerfile_content,
            re.IGNORECASE,
        ), "Dockerfile must switch to docbench user"


class TestWorkdir:
    """Test that WORKDIR is set correctly."""

    def test_workdir_set(self, dockerfile_content: str) -> None:
        """Test that WORKDIR is set to /opt/doc-bench."""
        assert re.search(
            r"WORKDIR\s+/opt/doc-bench",
            dockerfile_content,
        ), "WORKDIR must be set to /opt/doc-bench"


class TestEntryPoint:
    """Test that entry point is configured."""

    def test_entrypoint_configured(self, dockerfile_content: str) -> None:
        """Test that ENTRYPOINT is set."""
        assert re.search(
            r"ENTRYPOINT\s+\[",
            dockerfile_content,
        ), "Dockerfile must have ENTRYPOINT configured with exec form"


class TestBuildEnvironment:
    """Test build-time environment variables."""

    def test_compile_bytecode_set(self, dockerfile_content: str) -> None:
        """Test that UV_COMPILE_BYTECODE=1 is set."""
        assert re.search(
            r"UV_COMPILE_BYTECODE\s*=\s*1",
            dockerfile_content,
            re.IGNORECASE,
        ), "UV_COMPILE_BYTECODE=1 should be set for optimization"

    def test_python_optimize_set(self, dockerfile_content: str) -> None:
        """Test that PYTHONOPTIMIZE=2 is set."""
        assert re.search(
            r"PYTHONOPTIMIZE\s*=\s*2",
            dockerfile_content,
            re.IGNORECASE,
        ), "PYTHONOPTIMIZE=2 should be set for optimization"

    def test_python_unbuffered_set(self, dockerfile_content: str) -> None:
        """Test that PYTHONUNBUFFERED=1 is set."""
        assert re.search(
            r"PYTHONUNBUFFERED\s*=\s*1",
            dockerfile_content,
            re.IGNORECASE,
        ), "PYTHONUNBUFFERED=1 should be set"
