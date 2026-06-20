"""
Tests for Docker feature deletion validation.

The Docker workflow (Dockerfile, docker-compose.yml, and the dedicated
``tests/docker/`` suite) was removed; ``docs/doc-bench/overview.md`` states
"no Docker support". These guards fail loudly if any of those artifacts return,
modeled on ``tests/unit/test_test_deletion.py`` and
``tests/unit/test_module_deletion.py``.
"""

from pathlib import Path


def test_docker_tests_directory_not_exists() -> None:
    """Test that the stale tests/docker/ directory is deleted."""
    docker_tests_path = Path(__file__).parent.parent / "docker"
    assert (
        not docker_tests_path.exists()
    ), f"Docker test directory should be deleted: {docker_tests_path}"


def test_dockerfile_not_exists() -> None:
    """Test that the repo-root Dockerfile stays absent."""
    repo_root = Path(__file__).parent.parent.parent
    dockerfile_path = repo_root / "Dockerfile"
    assert not dockerfile_path.exists(), f"Dockerfile should not exist: {dockerfile_path}"


def test_docker_compose_not_exists() -> None:
    """Test that the repo-root docker-compose.yml stays absent."""
    repo_root = Path(__file__).parent.parent.parent
    compose_path = repo_root / "docker-compose.yml"
    assert not compose_path.exists(), f"docker-compose.yml should not exist: {compose_path}"
