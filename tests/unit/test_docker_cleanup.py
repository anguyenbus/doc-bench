"""
Tests for Docker cleanup validation.

Verifies that Docker configuration is cleaned up for parsing-only scope.
"""

from pathlib import Path


def test_dockerfile_no_phoenix_references() -> None:
    """Test that Dockerfile doesn't contain Phoenix/RAG references."""
    dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"

    if not dockerfile_path.exists():
        return  # Skip if Dockerfile doesn't exist

    content = dockerfile_path.read_text().lower()

    # Should not have Phoenix/RAG terms
    rag_terms = ["phoenix", "deepeval", "chromadb", "rag evaluation"]

    for term in rag_terms:
        assert term not in content, f"Dockerfile should not contain {term}"


def test_docker_compose_no_legacy_paths() -> None:
    """Test that docker-compose.yml doesn't have legacy eval-harness paths."""
    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"

    if not compose_path.exists():
        return  # Skip if docker-compose.yml doesn't exist

    content = compose_path.read_text()

    # Should not have legacy eval-harness paths
    assert (
        "./references/eval-harness" not in content
    ), "docker-compose.yml should not contain legacy eval-harness paths"

    # Should have doc-bench service name
    assert (
        "doc-bench" in content or "doc_bench" in content
    ), "docker-compose.yml should reference doc-bench"


def test_docker_compose_correct_volumes() -> None:
    """Test that docker-compose.yml has correct volume mounts."""
    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"

    if not compose_path.exists():
        return  # Skip if docker-compose.yml doesn't exist

    content = compose_path.read_text()

    # Should have parsers and results volumes
    assert (
        "./parsers" in content or "/work/parsers" in content
    ), "docker-compose.yml should mount parsers directory"
    assert (
        "./results" in content or "/work/results" in content
    ), "docker-compose.yml should mount results directory"
