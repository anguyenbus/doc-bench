"""
Tests for environment variable support.

Validates DOC_BENCH_LOG_LEVEL and DOC_BENCH_OUTPUT_FORMAT environment variables.
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


class TestEnvironmentVariables:
    """Test that environment variables are configured."""

    def test_doc_bench_log_level_env(self, dockerfile_content: str) -> None:
        """Test that DOC_BENCH_LOG_LEVEL environment variable is set."""
        assert re.search(
            r"DOC_BENCH_LOG_LEVEL",
            dockerfile_content,
        ), "DOC_BENCH_LOG_LEVEL environment variable should be set"

    def test_doc_bench_output_format_env(self, dockerfile_content: str) -> None:
        """Test that DOC_BENCH_OUTPUT_FORMAT environment variable is set."""
        assert re.search(
            r"DOC_BENCH_OUTPUT_FORMAT",
            dockerfile_content,
        ), "DOC_BENCH_OUTPUT_FORMAT environment variable should be set"


class TestDefaultValues:
    """Test that default values are set correctly."""

    def test_log_level_default_info(self, dockerfile_content: str) -> None:
        """Test that default log level is INFO."""
        match = re.search(
            r"DOC_BENCH_LOG_LEVEL\s*=.*?INFO",
            dockerfile_content,
            re.IGNORECASE,
        )
        assert match, "DOC_BENCH_LOG_LEVEL default should be INFO"

    def test_output_format_default_csv(self, dockerfile_content: str) -> None:
        """Test that default output format is csv."""
        match = re.search(
            r"DOC_BENCH_OUTPUT_FORMAT\s*=.*?csv",
            dockerfile_content,
            re.IGNORECASE,
        )
        assert match, "DOC_BENCH_OUTPUT_FORMAT default should be csv"


class TestEnvExample:
    """Test that .env.example file exists and is documented."""

    def test_env_example_exists(self) -> None:
        """Test that .env.example file exists in eval-harness."""
        env_example = ROOT_DIR / "references/eval-harness/.env.example"
        assert env_example.exists(), ".env.example should exist"
