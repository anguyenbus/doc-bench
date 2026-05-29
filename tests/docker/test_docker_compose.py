"""
Tests for Docker Compose configuration.

Validates docker-compose.yml structure, volume mounts, and environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest
import yaml

# Paths
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
DOCKER_COMPOSE_PATH: Final[Path] = ROOT_DIR / "docker-compose.yml"
DOCKER_COMPOSE_DEV_PATH: Final[Path] = ROOT_DIR / "docker-compose.dev.yml"


@pytest.fixture(scope="module")
def compose_content() -> dict:
    """Load docker-compose.yml content as dict."""
    if not DOCKER_COMPOSE_PATH.exists():
        pytest.fail(f"docker-compose.yml not found at {DOCKER_COMPOSE_PATH}")

    with open(DOCKER_COMPOSE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def compose_dev_content() -> dict | None:
    """Load docker-compose.dev.yml content as dict."""
    if not DOCKER_COMPOSE_DEV_PATH.exists():
        return None

    with open(DOCKER_COMPOSE_DEV_PATH) as f:
        return yaml.safe_load(f)


class TestServiceDefinition:
    """Test that service is defined correctly."""

    def test_doc_bench_service_exists(self, compose_content: dict) -> None:
        """Test that doc-bench service is defined."""
        assert "services" in compose_content, "services section should exist"
        assert "doc-bench" in compose_content["services"], "doc-bench service should be defined"

    def test_build_context_configured(self, compose_content: dict) -> None:
        """Test that build context is configured."""
        service = compose_content["services"]["doc-bench"]
        assert "build" in service, "build should be configured"
        assert service["build"].get("context") == ".", "build context should be current directory"

    def test_target_stage_is_runtime(self, compose_content: dict) -> None:
        """Test that target stage is runtime."""
        service = compose_content["services"]["doc-bench"]
        assert service["build"].get("target") == "runtime", "target stage should be runtime"


class TestVolumeMounts:
    """Test that volume mounts are configured."""

    def test_parsers_volume_mount(self, compose_content: dict) -> None:
        """Test that /work/parsers volume is mounted."""
        service = compose_content["services"]["doc-bench"]
        volumes = service.get("volumes", [])
        parser_mounts = [v for v in volumes if "/work/parsers" in str(v)]
        assert len(parser_mounts) > 0, "/work/parsers should be mounted"

    def test_results_volume_mount(self, compose_content: dict) -> None:
        """Test that /work/results volume is mounted."""
        service = compose_content["services"]["doc-bench"]
        volumes = service.get("volumes", [])
        result_mounts = [v for v in volumes if "/work/results" in str(v)]
        assert len(result_mounts) > 0, "/work/results should be mounted"

    def test_parsers_is_read_only(self, compose_content: dict) -> None:
        """Test that /work/parsers is mounted read-only."""
        service = compose_content["services"]["doc-bench"]
        volumes = service.get("volumes", [])
        for volume in volumes:
            if "/work/parsers" in str(volume) and ":ro" in str(volume):
                return
        pytest.fail("/work/parsers should be mounted read-only (:ro)")

    def test_results_is_read_write(self, compose_content: dict) -> None:
        """Test that /work/results is mounted read-write."""
        service = compose_content["services"]["doc-bench"]
        volumes = service.get("volumes", [])
        for volume in volumes:
            if "/work/results" in str(volume):
                # Check if it's explicitly rw or not ro (default is rw)
                if ":rw" in str(volume) or ":ro" not in str(volume):
                    return
        pytest.fail("/work/results should be mounted read-write")


class TestEnvironmentVariables:
    """Test that environment variables are passed."""

    def test_log_level_env_passed(self, compose_content: dict) -> None:
        """Test that DOC_BENCH_LOG_LEVEL is passed."""
        service = compose_content["services"]["doc-bench"]
        env = service.get("environment", [])
        if isinstance(env, dict):
            assert "DOC_BENCH_LOG_LEVEL" in env, "DOC_BENCH_LOG_LEVEL should be in environment"
        else:
            assert any("DOC_BENCH_LOG_LEVEL" in str(e) for e in env), \
                "DOC_BENCH_LOG_LEVEL should be in environment"

    def test_output_format_env_passed(self, compose_content: dict) -> None:
        """Test that DOC_BENCH_OUTPUT_FORMAT is passed."""
        service = compose_content["services"]["doc-bench"]
        env = service.get("environment", [])
        if isinstance(env, dict):
            assert "DOC_BENCH_OUTPUT_FORMAT" in env, "DOC_BENCH_OUTPUT_FORMAT should be in environment"
        else:
            assert any("DOC_BENCH_OUTPUT_FORMAT" in str(e) for e in env), \
                "DOC_BENCH_OUTPUT_FORMAT should be in environment"


class TestRestartPolicy:
    """Test that restart policy is configured."""

    def test_restart_policy_is_no(self, compose_content: dict) -> None:
        """Test that restart policy is set to 'no' for development."""
        service = compose_content["services"]["doc-bench"]
        restart = service.get("restart")
        assert restart == "no" or restart is False, \
            "restart policy should be 'no' or False for development"


class TestDevCompose:
    """Test that docker-compose.dev.yml exists."""

    def test_dev_compose_exists(self, compose_dev_content: dict | None) -> None:
        """Test that docker-compose.dev.yml exists."""
        assert compose_dev_content is not None, "docker-compose.dev.yml should exist"
