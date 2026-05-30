"""
Shared utilities for CLI modules.
"""

import os
from pathlib import Path

from doc_bench import get_bundled_schema_path

__all__ = ["get_bundled_schema_path", "get_manifest_path"]


def get_manifest_path(manifest_arg: Path | None = None) -> Path:
    """
    Resolve manifest path from argument, package data, or default.

    Args:
        manifest_arg: Explicit manifest path from CLI argument.

    Returns:
        Path to MANIFEST.yaml.

    """
    if manifest_arg:
        return manifest_arg

    # Try package data location (installed)
    try:
        import importlib.resources as resources

        pkg = "doc_bench"
        # Try to find manifest in package
        if resources.files(pkg) is not None:
            manifest_path = resources.files(pkg) / "MANIFEST.yaml"
            if manifest_path.is_file():
                return Path(manifest_path)
    except (ImportError, AttributeError):
        pass

    # Try site-packages location (older Python)
    try:
        import doc_bench

        pkg_dir = Path(doc_bench.__file__).parent
        manifest_path = pkg_dir / "MANIFEST.yaml"
        if manifest_path.exists():
            return manifest_path
    except (ImportError, AttributeError):
        pass

    # Fall back to local development path
    manifest_path = Path("src/doc_bench/MANIFEST.yaml")
    if manifest_path.exists():
        return manifest_path

    # Last resort: try current directory
    cwd_manifest = Path.cwd() / "src" / "doc_bench" / "MANIFEST.yaml"
    if cwd_manifest.exists():
        return cwd_manifest

    # Return default (will error if not found)
    return Path("src/doc_bench/MANIFEST.yaml")
