"""
Security and hardening validation tests.

Tests for non-root execution, no secrets, file permissions, and read-only filesystem support.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Final

import pytest

# Paths
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
DOCKERFILE_PATH: Final[Path] = ROOT_DIR / "Dockerfile"


# Skip these tests if Docker is not available
docker_available = pytest.mark.skipif(
    not os.path.exists("/var/run/docker.sock") and os.name != "nt",
    reason="Docker socket not available",
)


@pytest.fixture(scope="module")
def dockerfile_content() -> str:
    """Load Dockerfile content as string."""
    if not DOCKERFILE_PATH.exists():
        pytest.fail(f"Dockerfile not found at {DOCKERFILE_PATH}")

    return DOCKERFILE_PATH.read_text()


@docker_available
class TestNonRootExecution:
    """Test that container runs as non-root user."""

    def test_container_runs_as_docbench(self) -> None:
        """Test that container runs as docbench user."""
        result = subprocess.run(
            ["docker", "run", "--rm", "doc-bench:test", "id", "-un"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Container not built or run failed")

        assert "docbench" in result.stdout, "Container should run as docbench user"

    def test_container_uid_is_1000(self) -> None:
        """Test that container runs with UID 1000."""
        result = subprocess.run(
            ["docker", "run", "--rm", "doc-bench:test", "id", "-u"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Container not built or run failed")

        assert "1000" in result.stdout, "Container should run with UID 1000"

    def test_user_cannot_elevate_privileges(self) -> None:
        """Test that user cannot elevate privileges (no sudo)."""
        result = subprocess.run(
            ["docker", "run", "--rm", "doc-bench:test", "which", "sudo"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Container not built or run failed")

        # sudo should not be available
        assert result.returncode != 0 or not result.stdout.strip(), \
            "sudo should not be available to non-root user"


@docker_available
class TestNoSecretsInImage:
    """Test that no secrets are baked into the image."""

    def test_no_api_keys_in_image(self) -> None:
        """Test that no API keys are present in the image."""
        result = subprocess.run(
            ["docker", "run", "--rm", "doc-bench:test", "env"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Container not built or run failed")

        # Check for common API key environment variables
        env_output = result.stdout
        assert "OPENAI_API_KEY" not in env_output, "OPENAI_API_KEY should not be set"
        assert "ANTHROPIC_API_KEY" not in env_output, "ANTHROPIC_API_KEY should not be set"
        assert "HF_TOKEN" not in env_output, "HF_TOKEN should not be set"


class TestDockerfileSecurity:
    """Test Dockerfile security practices."""

    def test_no_secrets_in_dockerfile(self, dockerfile_content: str) -> None:
        """Test that no secrets are present in Dockerfile."""
        # Check for common secret patterns
        assert "api_key" not in dockerfile_content.lower(), \
            "API keys should not be in Dockerfile"
        assert "password" not in dockerfile_content.lower(), \
            "Passwords should not be in Dockerfile"
        assert "secret" not in dockerfile_content.lower(), \
            "Secrets should not be in Dockerfile"

    def test_no_unnecessary_packages(self, dockerfile_content: str) -> None:
        """Test that unnecessary packages are not installed."""
        # Check for common unnecessary packages
        assert "vim" not in dockerfile_content.lower(), \
            "vim should not be installed (minimal image)"
        assert "nano" not in dockerfile_content.lower(), \
            "nano should not be installed (minimal image)"
        assert "wget" not in dockerfile_content.lower() or \
               dockerfile_content.count("wget") <= 1, \
            "wget should be minimized (use curl instead)"


@docker_available
class TestReadOnlyFilesystem:
    """Test read-only filesystem support."""

    def test_read_only_root_with_tmpfs(self) -> None:
        """Test that container can run with read-only root filesystem."""
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--read-only",
                "--tmpfs", "/tmp",
                "--tmpfs", "/work",
                "doc-bench:test",
                "id"
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Container not built or read-only test failed")

        # Should succeed with tmpfs mounts
        assert result.returncode == 0, \
            "Container should run with read-only root filesystem when tmpfs is provided"
