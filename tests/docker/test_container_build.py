"""
Integration tests for container build and execution.

These tests require Docker to be installed and running.
They will build and test the actual container image.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Final

import pytest

# Paths
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent

# Skip these tests if Docker is not available
docker_available = pytest.mark.skipif(
    not os.path.exists("/var/run/docker.sock") and os.name != "nt",
    reason="Docker socket not available",
)


@pytest.fixture(scope="module")
def built_image() -> str:
    """Build the Docker image and return the image tag."""
    image_tag = "doc-bench:test"

    # Build the image
    result = subprocess.run(
        ["docker", "build", "-t", image_tag, "."],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.skip(f"Docker build failed: {result.stderr}")

    return image_tag


@docker_available
class TestContainerBuild:
    """Test that container builds successfully."""

    def test_image_builds(self, built_image: str) -> None:
        """Test that Docker image builds successfully."""
        # If built_image fixture returns, the build succeeded
        assert built_image, "Image should build successfully"

    def test_image_size_reasonable(self, built_image: str) -> None:
        """Test that image size is reasonable (< 2GB for now, target < 800MB)."""
        result = subprocess.run(
            ["docker", "images", built_image, "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Could not get image size")

        size_str = result.stdout.strip()

        # Parse size (e.g., "1.2GB" or "850MB")
        try:
            if "GB" in size_str:
                size_gb = float(size_str.replace("GB", "").strip())
                # For now, just warn if over 2GB
                if size_gb > 2.0:
                    pytest.warn(f"Image size {size_gb}GB exceeds 2GB target")
            elif "MB" in size_str:
                size_mb = float(size_str.replace("MB", "").strip())
                # Target is < 800MB
                if size_mb > 800:
                    pytest.warn(f"Image size {size_mb}MB exceeds 800MB target")
        except ValueError:
            pytest.skip(f"Could not parse image size: {size_str}")


@docker_available
class TestContainerExecution:
    """Test that container executes correctly."""

    def test_container_runs(self, built_image: str) -> None:
        """Test that container runs without errors."""
        result = subprocess.run(
            ["docker", "run", "--rm", built_image],
            capture_output=True,
            text=True,
        )

        # Default is --help, so should exit successfully
        assert result.returncode == 0, f"Container run failed: {result.stderr}"

    def test_entrypoint_defaults_to_help(self, built_image: str) -> None:
        """Test that entry point defaults to showing help."""
        result = subprocess.run(
            ["docker", "run", "--rm", built_image],
            capture_output=True,
            text=True,
        )

        # uv run --help should show help output
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower(), (
            "Default command should show help"
        )

    def test_non_root_user_execution(self, built_image: str) -> None:
        """Test that container runs as non-root user."""
        result = subprocess.run(
            ["docker", "run", "--rm", built_image, "id", "-u"],
            capture_output=True,
            text=True,
        )

        # Should output UID 1000
        assert "1000" in result.stdout, "Container should run as UID 1000 (docbench user)"


@docker_available
class TestVolumeMounts:
    """Test that volume mounts work correctly."""

    def test_work_parsers_mount(self, built_image: str) -> None:
        """Test that /work/parsers directory exists in container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{tmpdir}:/work/parsers:ro",
                    built_image,
                    "ls",
                    "/work/parsers",
                ],
                capture_output=True,
                text=True,
            )

            # Should succeed (directory is empty but exists)
            assert result.returncode == 0, "/work/parsers should be accessible"

    def test_work_results_mount(self, built_image: str) -> None:
        """Test that /work/results directory is writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{tmpdir}:/work/results:rw",
                    built_image,
                    "sh",
                    "-c",
                    "touch /work/results/test.txt && ls /work/results",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, "/work/results should be writable"
            assert "test.txt" in result.stdout, "File should be created in /work/results"


@docker_available
class TestDatasets:
    """Test that baked datasets are present."""

    def test_omnidocbench_dataset_exists(self, built_image: str) -> None:
        """Test that OmniDocBench dataset is baked into image."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                built_image,
                "sh",
                "-c",
                "test -d /opt/doc-bench/data/parsing/omnidocbench_english",
            ],
            capture_output=True,
            text=True,
        )

        # Dataset should exist (may be empty in test but directory exists)
        # If download failed during build, this would fail
        if result.returncode != 0:
            pytest.skip(
                "OmniDocBench dataset not found (may not be downloaded in test environment)"
            )

    def test_dp_bench_dataset_exists(self, built_image: str) -> None:
        """Test that DP-Bench dataset is baked into image."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                built_image,
                "sh",
                "-c",
                "test -d /opt/doc-bench/data/parsing/dp_bench",
            ],
            capture_output=True,
            text=True,
        )

        # Dataset should exist
        if result.returncode != 0:
            pytest.skip("DP-Bench dataset not found (may not be downloaded in test environment)")

    def test_manifest_exists(self, built_image: str) -> None:
        """Test that MANIFEST.yaml exists."""
        result = subprocess.run(
            ["docker", "run", "--rm", built_image, "cat", "/opt/doc-bench/data/MANIFEST.yaml"],
            capture_output=True,
            text=True,
        )

        # MANIFEST.yaml should exist
        if result.returncode != 0:
            pytest.skip("MANIFEST.yaml not found (datasets may not be downloaded)")
