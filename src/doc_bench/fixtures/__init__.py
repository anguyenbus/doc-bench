"""
Fixtures module for bundled smoke test data.

This module provides access to bundled fixture sets for fast smoke testing.
Fixtures are stratified samples from DP-Bench and OmniDocBench datasets.
"""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"


def get_fixture_path() -> Path:
    """
    Get path to fixtures directory.

    Returns:
        Path to bundled fixtures directory.

    """
    return FIXTURES_DIR


def load_manifest() -> dict:
    """
    Load fixtures manifest.

    Returns:
        Manifest dictionary with fixture metadata.

    """
    if not MANIFEST_PATH.exists():
        return {}

    import json

    with open(MANIFEST_PATH) as f:
        return json.load(f)
