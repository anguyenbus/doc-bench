"""
Tests for config cleanup validation.

Verifies that config system is simplified to parsing-only keys.
"""

import tempfile
from pathlib import Path


def test_parsing_config_loads_correctly() -> None:
    """Test that parsing-only config loads without errors."""
    from doc_bench.config import load_config

    # Create a minimal parsing-only config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
datasets:
  omnidocbench:
    path: /tmp/omnidocbench
  dp_bench:
    path: /tmp/dp_bench

metrics:
  parsing:
    enabled:
      - nid
      - teds
      - mhs
      - ard
      - bleu
      - meteor

models:
  parser: stub
""")
        config_path = Path(f.name)

    try:
        config = load_config(config_path)

        # Check that datasets section exists
        assert "datasets" in config
        assert "omnidocbench" in config["datasets"]
        assert "dp_bench" in config["datasets"]

        # Check that metrics section exists
        assert "metrics" in config

        # Check that models section exists
        assert "models" in config

    finally:
        config_path.unlink()


def test_removed_config_keys_rejected() -> None:
    """Test that only datasets is required; metrics/models and RAG sections are not."""
    from doc_bench.config import REQUIRED_SECTIONS

    # Only datasets is required — metrics and models are not consumed by the grader.
    assert "datasets" in REQUIRED_SECTIONS

    # None of these should be required
    not_required = {"metrics", "models", "phoenix", "chromadb", "replay", "generator", "ragas"}
    for section in not_required:
        assert (
            section not in REQUIRED_SECTIONS
        ), f"Section {section} should not be required, got {REQUIRED_SECTIONS}"
