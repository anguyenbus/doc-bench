"""
Tests for user documentation.

Validates that all required documentation files exist and contain required content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest


# Paths
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
README_PATH: Final[Path] = ROOT_DIR / "README.md"
DOCKER_README_PATH: Final[Path] = ROOT_DIR / "docs/docker/README.md"
ENV_EXAMPLE_PATH: Final[Path] = ROOT_DIR / ".env.example"


class TestRootReadme:
    """Test that root README.md exists and has required content."""

    def test_readme_exists(self) -> None:
        """Test that README.md exists in project root."""
        assert README_PATH.exists(), "README.md should exist in project root"

    def test_readme_has_docker_section(self) -> None:
        """Test that README.md has Docker section."""
        content = README_PATH.read_text()
        assert "docker" in content.lower(), "README.md should mention Docker"

    def test_readme_has_quick_start(self) -> None:
        """Test that README.md has quick start section."""
        content = README_PATH.read_text()
        assert "quick start" in content.lower() or "getting started" in content.lower(), \
            "README.md should have quick start section"

    def test_readme_has_volume_mount_docs(self) -> None:
        """Test that README.md documents volume mounts."""
        content = README_PATH.read_text()
        assert "volume" in content.lower() or "mount" in content.lower(), \
            "README.md should document volume mounts"

    def test_readme_has_env_var_docs(self) -> None:
        """Test that README.md documents environment variables."""
        content = README_PATH.read_text()
        assert "environment" in content.lower() or "DOC_BENCH_LOG_LEVEL" in content, \
            "README.md should document environment variables"


class TestDockerReadme:
    """Test that Docker-specific README exists and has required content."""

    def test_docker_readme_exists(self) -> None:
        """Test that docs/docker/README.md exists."""
        assert DOCKER_README_PATH.exists(), "docs/docker/README.md should exist"

    def test_docker_readme_has_build_instructions(self) -> None:
        """Test that Docker README has build instructions."""
        content = DOCKER_README_PATH.read_text()
        assert "docker build" in content.lower(), \
            "Docker README should have build instructions"

    def test_docker_readme_has_run_examples(self) -> None:
        """Test that Docker README has run examples."""
        content = DOCKER_README_PATH.read_text()
        assert "docker run" in content.lower(), \
            "Docker README should have run examples"

    def test_docker_readme_has_volume_mount_docs(self) -> None:
        """Test that Docker README documents volume mounts."""
        content = DOCKER_README_PATH.read_text()
        assert "/work/parsers" in content or "/work/results" in content, \
            "Docker README should document /work volume mounts"

    def test_docker_readme_has_env_var_reference(self) -> None:
        """Test that Docker README has environment variable reference."""
        content = DOCKER_README_PATH.read_text()
        assert "DOC_BENCH_LOG_LEVEL" in content or "environment variable" in content, \
            "Docker README should document environment variables"

    def test_docker_readme_has_troubleshooting(self) -> None:
        """Test that Docker README has troubleshooting section."""
        content = DOCKER_README_PATH.read_text()
        assert "troubleshoot" in content.lower() or "trouble" in content.lower(), \
            "Docker README should have troubleshooting section"


class TestEnvExample:
    """Test that .env.example exists and documents variables."""

    def test_env_example_exists(self) -> None:
        """Test that .env.example exists."""
        assert ENV_EXAMPLE_PATH.exists(), ".env.example should exist"

    def test_env_example_has_log_level(self) -> None:
        """Test that .env.example documents DOC_BENCH_LOG_LEVEL."""
        content = ENV_EXAMPLE_PATH.read_text()
        assert "DOC_BENCH_LOG_LEVEL" in content, \
            ".env.example should document DOC_BENCH_LOG_LEVEL"

    def test_env_example_has_output_format(self) -> None:
        """Test that .env.example documents DOC_BENCH_OUTPUT_FORMAT."""
        content = ENV_EXAMPLE_PATH.read_text()
        assert "DOC_BENCH_OUTPUT_FORMAT" in content, \
            ".env.example should document DOC_BENCH_OUTPUT_FORMAT"

    def test_env_example_has_defaults(self) -> None:
        """Test that .env.example shows default values."""
        content = ENV_EXAMPLE_PATH.read_text()
        assert "INFO" in content or "DEBUG" in content, \
            ".env.example should show default log level values"
        assert "csv" in content or "json" in content, \
            ".env.example should show output format values"


class TestDocumentationStructure:
    """Test that documentation structure is complete."""

    def test_docs_directory_exists(self) -> None:
        """Test that docs/ directory exists."""
        docs_dir = ROOT_DIR / "docs"
        assert docs_dir.exists(), "docs/ directory should exist"

    def test_docker_docs_directory_exists(self) -> None:
        """Test that docs/docker/ directory exists."""
        docker_docs_dir = ROOT_DIR / "docs/docker"
        assert docker_docs_dir.exists(), "docs/docker/ directory should exist"
