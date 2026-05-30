"""
list-datasets CLI command for listing available datasets.

This module provides the CLI for listing datasets with version information
and cache status.
"""

import os
from pathlib import Path
from typing import Any

import click
import yaml

from doc_bench.cli import get_manifest_path


def _get_cache_dir(explicit_cache: Path | None) -> Path:
    """
    Get cache directory for datasets.

    Args:
        explicit_cache: Explicit cache directory path override.

    Returns:
        Path to cache directory.

    """
    if explicit_cache:
        return explicit_cache

    # Check for environment variable override
    env_cache = os.environ.get("DOC_BENCH_CACHE")
    if env_cache:
        return Path(env_cache)

    # Default to ~/.cache/doc-bench
    return Path.home() / ".cache" / "doc-bench"


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    """
    Load dataset manifest.

    Args:
        manifest_path: Path to MANIFEST.yaml.

    Returns:
        Manifest dictionary.

    """
    if not manifest_path.exists():
        raise click.ClickException(f"Manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        return yaml.safe_load(f) or {}


def _check_cached(dataset_name: str, version: str, cache_dir: Path) -> bool:
    """
    Check if dataset version is cached.

    Args:
        dataset_name: Name of dataset.
        version: Version string.
        cache_dir: Cache directory path.

    Returns:
        True if cached, False otherwise.

    """
    cache_path = cache_dir / f"{dataset_name}-{version}"
    return cache_path.exists() and any(cache_path.iterdir())


@click.command()
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to MANIFEST.yaml (auto-detected if not specified)",
)
@click.option(
    "--cache-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Cache directory (default: ~/.cache/doc-bench)",
)
def main(manifest: Path | None, cache_dir: Path | None) -> None:
    """
    List available datasets with version and cache status.

    Shows dataset name, available version, and whether the dataset
    is currently cached locally.

    Example:
        doc-bench-list-datasets

    """
    # Get cache directory
    cache_base = _get_cache_dir(cache_dir)

    # Resolve manifest path
    manifest_path = get_manifest_path(manifest)

    # Load manifest
    try:
        manifest_data = _load_manifest(manifest_path)
    except Exception as e:
        raise click.ClickException(f"Failed to load manifest: {e}")

    if not manifest_data:
        click.echo("No datasets found in manifest")
        return

    # Prepare table data
    table_data = []
    for dataset_name, dataset_info in manifest_data.items():
        version = dataset_info.get("version", "unknown")
        is_cached = _check_cached(dataset_name, version, cache_base)
        cache_status = "cached" if is_cached else "not cached"

        table_data.append(
            {
                "dataset": dataset_name,
                "version": version,
                "cached": cache_status,
            }
        )

    # Sort by dataset name
    table_data.sort(key=lambda x: x["dataset"])

    # Print table header
    click.echo(f"{'Dataset':<25} {'Version':<10} {'Status':<15}")
    click.echo("-" * 50)

    # Print table rows
    for row in table_data:
        click.echo(f"{row['dataset']:<25} {row['version']:<10} {row['cached']:<15}")

    click.echo("-" * 50)
    click.echo(f"Total: {len(table_data)} datasets")


if __name__ == "__main__":
    main()
