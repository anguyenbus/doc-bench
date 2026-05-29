"""
Tests for non-root user configuration.

Validates non-root user creation, UID, file permissions, and privilege restriction.
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


class TestNonRootUserCreation:
    """Test that non-root user is created correctly."""

    def test_docbench_user_created(self, dockerfile_content: str) -> None:
        """Test that docbench user is created."""
        assert re.search(
            r"useradd.*?docbench",
            dockerfile_content,
            re.IGNORECASE,
        ), "docbench user should be created"

    def test_docbench_uid_1000(self, dockerfile_content: str) -> None:
        """Test that docbench user has UID 1000."""
        assert re.search(
            r"useradd.*?-u\s+1000",
            dockerfile_content,
            re.IGNORECASE,
        ), "docbench user should have UID 1000"

    def test_home_directory_created(self, dockerfile_content: str) -> None:
        """Test that home directory is created."""
        assert re.search(
            r"-d\s+/home/docbench",
            dockerfile_content,
        ), "docbench home directory should be created"


class TestDirectoryOwnership:
    """Test that directories have correct ownership."""

    def test_opt_docbench_ownership(self, dockerfile_content: str) -> None:
        """Test that /opt/doc-bench ownership is set."""
        assert re.search(
            r"chown.*?docbench.*?/opt/doc-bench",
            dockerfile_content,
        ), "/opt/doc-bench ownership should be set to docbench"

    def test_work_ownership(self, dockerfile_content: str) -> None:
        """Test that /work ownership is set."""
        assert re.search(
            r"chown.*?docbench.*?/work",
            dockerfile_content,
        ), "/work ownership should be set to docbench"


class TestUserSwitch:
    """Test that container switches to non-root user."""

    def test_user_docbench_directive(self, dockerfile_content: str) -> None:
        """Test that USER docbench directive is present."""
        assert re.search(
            r"USER\s+docbench",
            dockerfile_content,
            re.IGNORECASE,
        ), "Container should switch to docbench user"

    def test_user_switch_after_privileged_ops(self, dockerfile_content: str) -> None:
        """Test that USER switch comes after privileged operations."""
        # Find USER docbench line
        user_match = re.search(r"USER\s+docbench", dockerfile_content, re.IGNORECASE)
        assert user_match, "USER docbench directive should be present"

        # Check that COPY with chown comes before USER
        user_line_pos = dockerfile_content[:user_match.start()].count('\n')
        chown_pos = dockerfile_content.find("--chown=docbench")
        assert chown_pos != -1 and chown_pos < user_match.start(), \
            "USER switch should come after chown operations"
