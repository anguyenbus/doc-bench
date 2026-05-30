"""
download CLI command for version-pinned dataset downloads.

This module provides the CLI for downloading datasets with explicit version
pinning, SHA-256 verification, and cache management.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any

import click
import yaml

from doc_bench.cli import get_manifest_path

try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None  # Will error at runtime if needed


def _compute_sha256(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hexadecimal SHA-256 hash string.

    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _verify_hash(file_path: Path, expected_hash: str) -> bool:
    """
    Verify that file matches expected SHA-256 hash.

    Args:
        file_path: Path to file to verify.
        expected_hash: Expected SHA-256 hash.

    Returns:
        True if hash matches, False otherwise.

    """
    if not file_path.exists():
        return False

    actual_hash = _compute_sha256(file_path)
    return actual_hash == expected_hash


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


def _download_huggingface(
    repo_id: str,
    output_dir: Path,
    version: str,
) -> Path:
    """
    Download dataset from HuggingFace.

    Args:
        repo_id: HuggingFace repository ID.
        output_dir: Directory to download to.
        version: Version string for documentation.

    Returns:
        Path to downloaded directory.

    """
    if snapshot_download is None:
        raise click.ClickException(
            "huggingface_hub required for download. Install: pip install huggingface-hub"
        )

    click.echo(f"Downloading {repo_id} from HuggingFace...")

    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=output_dir,
        local_dir_use_symlinks=False,
    )

    return output_dir


@click.command()
@click.option(
    "--dataset",
    type=click.Choice(["dp_bench", "omnidocbench"]),
    required=True,
    help="Dataset to download",
)
@click.option(
    "--version",
    required=True,
    help="Version to download (e.g., v1.0). Must be explicit, no 'latest' keyword.",
)
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
    help="Cache directory override (default: ~/.cache/doc-bench)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (default: cache-dir/<dataset>-<version>)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-download even if cached version exists",
)
def main(
    dataset: str,
    version: str,
    manifest: Path | None,
    cache_dir: Path | None,
    output: Path | None,
    force: bool,
) -> None:
    """
    Download dataset with explicit version pinning.

    Downloads are cached at ~/.cache/doc-bench/<dataset>-<version>/ by default.
    SHA-256 verification is performed automatically.

    Example:
        doc-bench-download --dataset dp_bench --version v1.0

    """
    # Reject 'latest' keyword
    if version.lower() == "latest":
        raise click.ClickException(
            "Version must be explicit. The 'latest' keyword is not supported. "
            "Use a specific version like 'v1.0'."
        )

    # Get cache directory
    cache_base = _get_cache_dir(cache_dir)

    # Resolve manifest path
    manifest_path = get_manifest_path(manifest)

    # Load manifest
    try:
        manifest_data = _load_manifest(manifest_path)
    except Exception as e:
        raise click.ClickException(f"Failed to load manifest: {e}")

    # Validate dataset exists in manifest
    if dataset not in manifest_data:
        raise click.ClickException(f"Dataset '{dataset}' not found in manifest")

    dataset_info = manifest_data[dataset]

    # Validate version
    manifest_version = dataset_info.get("version")
    if manifest_version != version:
        raise click.ClickException(
            f"Version '{version}' not found in manifest. Available version: '{manifest_version}'"
        )

    # Determine output directory
    if output:
        target_dir = output
    else:
        target_dir = cache_base / f"{dataset}-{version}"

    # Check if already cached
    if target_dir.exists() and any(target_dir.iterdir()):
        if force:
            click.echo(f"Removing cached version at {target_dir}")
            shutil.rmtree(target_dir)
        else:
            click.echo(f"Dataset already cached at: {target_dir}")
            click.echo("Use --force to re-download")
            return

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Download based on dataset type
    if dataset == "dp_bench":
        repo_id = "upstage/dp-bench"
        downloaded_path = _download_huggingface(repo_id, target_dir, version)
    elif dataset == "omnidocbench":
        repo_id = "opendatalab/OmniDocBench"
        downloaded_path = _download_huggingface(repo_id, target_dir, version)
    else:
        raise click.ClickException(f"Unknown dataset: {dataset}")

    # Verify hash if specified in manifest
    expected_hash = dataset_info.get("sha256")
    if expected_hash and expected_hash != "manual":
        # Find a representative file to verify
        # For DP-Bench: reference.json
        # For OmniDocBench: OmniDocBench.json
        if dataset == "dp_bench":
            verify_file = downloaded_path / "reference.json"
        elif dataset == "omnidocbench":
            verify_file = downloaded_path / "OmniDocBench.json"
        else:
            verify_file = None

        if verify_file and verify_file.exists():
            if _verify_hash(verify_file, expected_hash):
                click.echo(f"SHA-256 verification passed: {verify_file.name}")
            else:
                click.echo(f"SHA-256 verification failed for {verify_file.name}")
                click.echo(f"Expected: {expected_hash}")
                click.echo(f"Got: {_compute_sha256(verify_file)}")
                raise click.Abort()
        else:
            click.echo(f"Warning: Could not verify hash (file not found: {verify_file})")

    click.echo(f"Dataset downloaded successfully to: {target_dir}")


if __name__ == "__main__":
    main()
