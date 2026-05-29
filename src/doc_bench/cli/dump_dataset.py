"""
dump-dataset CLI command for exporting dataset documents.

This module provides the CLI for exporting dataset documents with
canonical identifiers for file-based evaluation.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from doc_bench.config import load_config
from doc_bench.identity import doc_id_for


def _compute_sha256(file_path: Path) -> str:
    """
    Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hexadecimal SHA256 hash string.

    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _dump_dp_bench(root: Path, output_dir: Path, limit: int | None) -> dict:
    """
    Dump DP-Bench dataset documents.

    Args:
        root: Path to DP-Bench root directory.
        output_dir: Path to output directory.
        limit: Maximum number of documents to export.

    Returns:
        Manifest dictionary with metadata.

    """
    from doc_bench.datasets import load_dp_bench

    documents = []
    count = 0

    for idx, (doc_id, pdf_path, _gold_elements) in enumerate(load_dp_bench(root)):
        if limit and idx >= limit:
            break

        # Export as <doc_id>.pdf
        output_file = output_dir / f"{doc_id}.pdf"

        # Copy file
        import shutil

        shutil.copy2(pdf_path, output_file)

        # Compute hash
        sha256 = _compute_sha256(output_file)

        documents.append({
            "doc_id": doc_id,
            "file": f"{doc_id}.pdf",
            "sha256": sha256,
        })

        count += 1

    return {
        "dataset_name": "dp_bench",
        "documents": documents,
        "count": count,
    }


def _dump_omnidocbench(root: Path, output_dir: Path, limit: int | None) -> dict:
    """
    Dump OmniDocBench dataset documents.

    Args:
        root: Path to OmniDocBench root directory.
        output_dir: Path to output directory.
        limit: Maximum number of documents to export.

    Returns:
        Manifest dictionary with metadata.

    """
    from doc_bench.datasets import load_omnidocbench

    documents = []
    count = 0
    images_dir = root / "images"

    for idx, page in enumerate(load_omnidocbench(root)):
        if limit and idx >= limit:
            break

        # Get doc_id
        doc_id = doc_id_for("omnidocbench", page)

        # Get original image path
        page_info = page.get("page_info", {})
        image_path = page_info.get("image_path", "")
        source_file = images_dir / image_path

        if not source_file.exists():
            click.echo(f"WARNING: Image file not found: {source_file}")
            continue

        # Determine extension from original file
        ext = Path(image_path).suffix or ".png"

        # Export as <doc_id>.<ext>
        output_file = output_dir / f"{doc_id}{ext}"

        # Copy file
        import shutil

        shutil.copy2(source_file, output_file)

        # Compute hash
        sha256 = _compute_sha256(output_file)

        documents.append({
            "doc_id": doc_id,
            "file": f"{doc_id}{ext}",
            "sha256": sha256,
        })

        count += 1

    return {
        "dataset_name": "omnidocbench",
        "documents": documents,
        "count": count,
    }


def _write_manifest(
    output_dir: Path,
    dataset_name: str,
    documents: list[dict[str, Any]],
    count: int,
    limit: int | None,
) -> None:
    """
    Write manifest.json with reproducibility metadata.

    Args:
        output_dir: Path to output directory.
        dataset_name: Name of the dataset.
        documents: List of document entries.
        count: Number of exported documents.
        limit: Limit applied (if any).

    """
    # Get version info
    from importlib.metadata import version

    try:
        doc_bench_version = version("doc-bench")
    except Exception:
        doc_bench_version = "0.1.0"

    manifest = {
        "dataset_name": dataset_name,
        "dataset_version": "2026.05",  # TODO: Extract from dataset if available
        "doc_bench_version": doc_bench_version,
        "dumped_at": datetime.now().isoformat(),
        "limit": limit,
        "count": count,
        "documents": documents,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


@click.command()
@click.option(
    "--dataset",
    type=click.Choice(["dp_bench", "omnidocbench"]),
    required=True,
    help="Dataset to export",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output directory for exported documents",
)
@click.option(
    "--config",
    type=click.Path(path_type=Path),
    default=Path("eval_config.yaml"),
    help="Path to eval_config.yaml",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of documents to export (for testing)",
)
def main(dataset: str, output: Path, config: Path, limit: int | None) -> None:
    """
    Export dataset documents with canonical identifiers.

    Exports each document as <doc_id>.<ext> and creates manifest.json
    with reproducibility metadata.

    Example:
        doc-bench dump-dataset --dataset dp_bench --output ./dumped --limit 10
    """
    # Load configuration to get dataset paths
    try:
        config_dict = load_config(config)
    except FileNotFoundError as e:
        click.echo(f"ERROR: {e}")
        raise click.Abort()
    except ValueError as e:
        click.echo(f"ERROR: {e}")
        raise click.Abort()

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)

    # Get dataset root
    dataset_root = Path(config_dict["datasets"][dataset]["path"])

    if not dataset_root.exists():
        click.echo(f"ERROR: Dataset directory not found: {dataset_root}")
        raise click.Abort()

    # Export based on dataset type
    if dataset == "dp_bench":
        result = _dump_dp_bench(dataset_root, output, limit)
    elif dataset == "omnidocbench":
        result = _dump_omnidocbench(dataset_root, output, limit)
    else:
        click.echo(f"ERROR: Unknown dataset: {dataset}")
        raise click.Abort()

    # Write manifest
    _write_manifest(
        output,
        result["dataset_name"],
        result["documents"],
        result["count"],
        limit,
    )

    # Print summary
    click.echo(f"Exported {result['count']} documents to: {output}")
    click.echo(f"Manifest written to: {output / 'manifest.json'}")


if __name__ == "__main__":
    main()
