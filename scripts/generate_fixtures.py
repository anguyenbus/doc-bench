#!/usr/bin/env python3
"""
Generate bundled fixture sets for smoke testing.

This maintainer-only script copies stratified fixtures from the baseline
directory (which already has representative samples with pre-computed scores).

Usage:
    uv run python scripts/generate_fixtures.py

Fixtures are written to src/doc_bench/fixtures/ and bundled with the package.
"""

import json
import shutil
from pathlib import Path


def generate_dp_bench_fixtures(
    baseline_root: Path,
    output_dir: Path,
) -> list[dict]:
    """
    Copy DP-Bench fixtures from baseline directory.

    Args:
        baseline_root: Path to baseline/dp_bench/.
        output_dir: Output fixtures directory.

    Returns:
        List of fixture entries for manifest.

    """
    reference_path = baseline_root / "reference.json"
    pdfs_dir = baseline_root / "pdfs"

    if not reference_path.exists() or not pdfs_dir.exists():
        print(f"  ERROR: Missing reference.json or pdfs/ in {baseline_root}")
        return []

    with open(reference_path) as f:
        reference = json.load(f)

    fixtures = []
    output_dp_dir = output_dir / "dp_bench"
    output_dp_dir.mkdir(parents=True, exist_ok=True)

    for pdf_name, gold_elements in reference.items():
        pdf_path = pdfs_dir / pdf_name
        if not pdf_path.exists():
            continue

        doc_id = pdf_name.replace(".pdf", "")

        # Copy PDF
        dest_pdf = output_dp_dir / pdf_name
        shutil.copy2(pdf_path, dest_pdf)

        # Save gold elements
        gold_path = output_dp_dir / f"{doc_id}.json"
        with open(gold_path, "w") as f:
            json.dump(gold_elements, f)

        # Get primary category (most common element type)
        element_list = gold_elements.get("elements", [])
        if element_list:
            from collections import Counter

            categories = [e.get("category", "") for e in element_list if e.get("category")]
            if categories:
                category = Counter(categories).most_common(1)[0][0]
            else:
                category = "unknown"
        else:
            category = "unknown"

        fixtures.append(
            {
                "doc_id": doc_id,
                "category": category,
                "pdf": f"dp_bench/{pdf_name}",
                "gold": f"dp_bench/{doc_id}.json",
            }
        )

    return fixtures


def generate_omnidocbench_fixtures(
    baseline_root: Path,
    output_dir: Path,
) -> list[dict]:
    """
    Copy OmniDocBench fixtures from baseline directory.

    Args:
        baseline_root: Path to baseline/omnidocbench/.
        output_dir: Output fixtures directory.

    Returns:
        List of fixture entries for manifest.

    """
    json_path = baseline_root / "OmniDocBench.json"

    if not json_path.exists():
        print(f"  ERROR: Missing OmniDocBench.json in {baseline_root}")
        return []

    with open(json_path) as f:
        pages = json.load(f)

    fixtures = []
    output_omni_dir = output_dir / "omnidocbench"
    output_omni_dir.mkdir(parents=True, exist_ok=True)

    for page in pages:
        page_info = page.get("page_info", {})
        page_attr = page_info.get("page_attribute", {})

        image_name = page_info.get("image_path", "")
        if not image_name:
            continue

        doc_id = image_name.replace(".png", "").replace(".jpg", "")

        # Copy image if exists in baseline
        source_image = baseline_root / image_name
        if source_image.exists():
            dest_image = output_omni_dir / image_name
            shutil.copy2(source_image, dest_image)

        # Save page metadata
        page_path = output_omni_dir / f"{doc_id}.json"
        with open(page_path, "w") as f:
            json.dump(page, f)

        # Get doc_type
        doc_type = page_attr.get("data_source") or page_info.get("doc_type", "unknown")

        fixtures.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "page": f"omnidocbench/{doc_id}.json",
                "image": (
                    f"omnidocbench/{image_name}" if (baseline_root / image_name).exists() else None
                ),
            }
        )

    return fixtures


def add_problematic_dp_bench_fixtures(
    reference_path: Path,
    pdfs_dir: Path,
    output_dir: Path,
    pdf_names: list[str],
) -> list[dict]:
    """
    Add specific DP-Bench PDFs known to cause parser issues.

    Args:
        reference_path: Path to reference.json.
        pdfs_dir: Path to PDFs directory.
        output_dir: Output fixtures directory.
        pdf_names: List of PDF filenames to add.

    Returns:
        List of fixture entries for manifest.

    """
    if not reference_path.exists() or not pdfs_dir.exists():
        print("  ERROR: Missing reference.json or pdfs/")
        return []

    with open(reference_path) as f:
        reference = json.load(f)

    fixtures = []
    output_dp_dir = output_dir / "dp_bench"
    output_dp_dir.mkdir(parents=True, exist_ok=True)

    for pdf_name in pdf_names:
        if pdf_name not in reference:
            print(f"  WARNING: {pdf_name} not in reference.json")
            continue

        pdf_path = pdfs_dir / pdf_name
        if not pdf_path.exists():
            print(f"  WARNING: PDF not found: {pdf_path}")
            continue

        gold_elements = reference[pdf_name]
        doc_id = pdf_name.replace(".pdf", "")

        # Copy PDF
        dest_pdf = output_dp_dir / pdf_name
        shutil.copy2(pdf_path, dest_pdf)

        # Save gold elements
        gold_path = output_dp_dir / f"{doc_id}.json"
        with open(gold_path, "w") as f:
            json.dump(gold_elements, f)

        # Get primary category
        element_list = gold_elements.get("elements", [])
        if element_list:
            from collections import Counter

            categories = [e.get("category", "") for e in element_list if e.get("category")]
            if categories:
                category = Counter(categories).most_common(1)[0][0]
            else:
                category = "unknown"
        else:
            category = "unknown"

        fixtures.append(
            {
                "doc_id": doc_id,
                "category": category,
                "pdf": f"dp_bench/{pdf_name}",
                "gold": f"dp_bench/{doc_id}.json",
            }
        )
        print(f"  Added {pdf_name} ({category}, {len(element_list)} elements)")

    return fixtures


def generate_fixtures(
    data_dir: Path,
    output_dir: Path,
) -> dict:
    """
    Generate bundled fixture sets from baseline directory.

    Args:
        data_dir: Root data directory (baseline/).
        output_dir: Output directory for fixtures.

    Returns:
        Manifest dictionary with fixture metadata.

    """
    manifest = {
        "name": "bundled-baseline-stratified",
        "description": "Stratified fixture set from baseline evaluations",
        "dp_bench": [],
        "omnidocbench": [],
        "total": 0,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy DP-Bench fixtures
    dp_bench_baseline = data_dir / "dp_bench"
    if dp_bench_baseline.exists():
        print("  Processing DP-Bench fixtures...")
        manifest["dp_bench"] = generate_dp_bench_fixtures(dp_bench_baseline, output_dir)
        print(f"  Copied {len(manifest['dp_bench'])} DP-Bench documents")

    # Copy OmniDocBench fixtures
    omnidoc_baseline = data_dir / "omnidocbench"
    if omnidoc_baseline.exists():
        print("  Processing OmniDocBench fixtures...")
        manifest["omnidocbench"] = generate_omnidocbench_fixtures(omnidoc_baseline, output_dir)
        print(f"  Copied {len(manifest['omnidocbench'])} OmniDocBench documents")

    manifest["total"] = len(manifest["dp_bench"]) + len(manifest["omnidocbench"])

    # Write manifest
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    """Generate bundled fixtures from baseline directory."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate bundled fixtures from baseline directory"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("baseline"),
        help="Baseline data directory (default: baseline/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/doc_bench/fixtures"),
        help="Output directory for fixtures",
    )
    parser.add_argument(
        "--add-problematic",
        type=Path,
        default=None,
        help="Path to opendataloader-bench reference directory for problematic PDFs",
    )
    parser.add_argument(
        "--problematic-pdfs",
        type=str,
        default="01030000000172.pdf,01030000000018.pdf,01030000000141.pdf,01030000000121.pdf",
        help="Comma-separated list of problematic PDF names to add",
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"ERROR: Data directory not found: {args.data_dir}")
        return 1

    print("Generating bundled fixtures from baseline...")
    manifest = generate_fixtures(args.data_dir, args.output_dir)

    print(f"\nGenerated {manifest['total']} fixtures:")
    print(f"  - DP-Bench: {len(manifest['dp_bench'])} documents")
    print(f"  - OmniDocBench: {len(manifest['omnidocbench'])} documents")

    # Add problematic PDFs if specified
    if args.add_problematic:
        print(f"\nAdding problematic PDFs from {args.add_problematic}...")
        problematic_pdfs = [p.strip() for p in args.problematic_pdfs.split(",")]
        reference_path = args.add_problematic / "ground-truth" / "reference.json"
        pdfs_dir = args.add_problematic / "pdfs"

        new_fixtures = add_problematic_dp_bench_fixtures(
            reference_path, pdfs_dir, args.output_dir, problematic_pdfs
        )

        # Add to manifest if not duplicate
        existing_doc_ids = {f["doc_id"] for f in manifest["dp_bench"]}
        for fixture in new_fixtures:
            if fixture["doc_id"] not in existing_doc_ids:
                manifest["dp_bench"].append(fixture)
                existing_doc_ids.add(fixture["doc_id"])

        manifest["total"] = len(manifest["dp_bench"]) + len(manifest["omnidocbench"])

        # Rewrite manifest with additions
        with open(args.output_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"  Total DP-Bench after additions: {len(manifest['dp_bench'])} documents")
        print(f"  Total fixtures: {manifest['total']} documents")

    print(f"\nFixtures written to: {args.output_dir}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")

    return 0


if __name__ == "__main__":
    exit(main())
