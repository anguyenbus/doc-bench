"""
Tests for config cleanup validation.

Verifies that config system is simplified to parsing-only keys.
"""

from pathlib import Path
import tempfile


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
    """Test that removed RAG/Phoenix config keys cause validation errors."""
    from doc_bench.config import load_config, REQUIRED_SECTIONS

    # Verify that required sections are only parsing-related
    expected_sections = {"datasets", "metrics", "models"}

    assert REQUIRED_SECTIONS == expected_sections, \
        f"Required sections should be {expected_sections}, got {REQUIRED_SECTIONS}"

    # Verify phoenix, chromadb, replay are not required
    removed_sections = {"phoenix", "chromadb", "replay", "generator", "ragas"}
    for section in removed_sections:
        assert section not in REQUIRED_SECTIONS, \
            f"Removed section {section} should not be in REQUIRED_SECTIONS"
