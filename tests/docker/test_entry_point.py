"""
Tests for container entry point configuration.

Validates ENTRYPOINT pattern, CMD default, and command routing.
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


class TestEntryPoint:
    """Test that ENTRYPOINT is configured correctly."""

    def test_entrypoint_uses_uv_run(self, dockerfile_content: str) -> None:
        """Test that ENTRYPOINT uses uv run pattern."""
        assert re.search(
            r'ENTRYPOINT\s+\["uv",\s*"run"\]',
            dockerfile_content,
        ), "ENTRYPOINT should use uv run for CLI execution"

    def test_entrypoint_exec_form(self, dockerfile_content: str) -> None:
        """Test that ENTRYPOINT uses JSON array exec form."""
        assert re.search(
            r'ENTRYPOINT\s+\[',
            dockerfile_content,
        ), "ENTRYPOINT should use exec form (JSON array)"


class TestDefaultCommand:
    """Test that default CMD is configured."""

    def test_cmd_is_help(self, dockerfile_content: str) -> None:
        """Test that default CMD is --help."""
        assert re.search(
            r'CMD\s+\["--help"\]',
            dockerfile_content,
        ), "Default CMD should be --help"

    def test_cmd_exec_form(self, dockerfile_content: str) -> None:
        """Test that CMD uses JSON array exec form."""
        assert re.search(
            r'CMD\s+\[',
            dockerfile_content,
        ), "CMD should use exec form (JSON array)"


class TestCommandOverride:
    """Test that command override pattern is supported."""

    def test_entrypoint_after_all_copy(self, dockerfile_content: str) -> None:
        """Test that ENTRYPOINT comes after all COPY commands (allows command override)."""
        # Find all COPY lines
        copy_matches = list(re.finditer(r'^\s*COPY', dockerfile_content, re.MULTILINE))
        # Find ENTRYPOINT
        entrypoint_match = re.search(r'ENTRYPOINT', dockerfile_content)

        assert entrypoint_match, "ENTRYPOINT should be defined"

        # ENTRYPOINT should come after the last COPY
        if copy_matches:
            last_copy_pos = copy_matches[-1].end()
            assert entrypoint_match.start() > last_copy_pos, \
                "ENTRYPOINT should come after COPY operations to allow command override"


class TestCliCommandsAvailable:
    """Test that CLI commands will be available in container."""

    def test_path_includes_venv(self, dockerfile_content: str) -> None:
        """Test that PATH includes venv for CLI entry points."""
        assert re.search(
            r"PATH=.*?/\.venv/bin",
            dockerfile_content,
        ), "PATH should include /.venv/bin for CLI commands"

    def test_pythonpath_includes_src(self, dockerfile_content: str) -> None:
        """Test that PYTHONPATH includes src for CLI modules."""
        assert re.search(
            r"PYTHONPATH=.*?/opt/doc-bench/src",
            dockerfile_content,
        ), "PYTHONPATH should include src for CLI modules"
