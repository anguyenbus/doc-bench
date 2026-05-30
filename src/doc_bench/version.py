"""
Version alignment module.

Provides functions for version management and alignment checks
between package version and dataset versions.
"""

from pathlib import Path


def get_version() -> str:
    """
    Get doc-bench package version.

    Returns:
        Version string from package __version__.

    """
    try:
        from doc_bench import __version__

        return __version__
    except Exception:
        # Fallback to importlib.metadata
        try:
            from importlib.metadata import version

            return version("doc-bench")
        except Exception:
            return "0.1.0"


def check_dataset_version_alignment(manifest_path: str) -> list[str]:
    """
    Check dataset versions align with package version.

    Args:
        manifest_path: Path to MANIFEST.yaml file.

    Returns:
        List of error messages (empty if all aligned).

    """
    errors = []

    # Get package version
    package_version = get_version()

    # Load manifest
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return [f"Manifest not found: {manifest_path}"]

    try:
        import yaml

        with open(manifest_file) as f:
            manifest = yaml.safe_load(f) or {}
    except Exception as e:
        return [f"Failed to load manifest: {e}"]

    # Check each dataset version
    for dataset_name, dataset_info in manifest.items():
        if isinstance(dataset_info, dict):
            dataset_version = dataset_info.get("version")
            if dataset_version and dataset_version != package_version:
                errors.append(
                    f"Dataset '{dataset_name}' version '{dataset_version}' "
                    f"does not match package version '{package_version}'"
                )

    return errors
