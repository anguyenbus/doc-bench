#!/usr/bin/env python3
"""
Generate bundled fixture sets for smoke testing.

This maintainer-only script creates stratified fixture samples from
DP-Bench and OmniDocBench datasets for fast smoke testing.

Usage:
    uv run python scripts/generate_fixtures.py --data-dir /path/to/data

Fixtures are written to src/doc_bench/fixtures/ and bundled with the package.
"""

import argparse
import json
import shutil
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

# Element categories for DP-Bench stratification
DP_BENCH_CATEGORIES = ["Header", "Paragraph", "Table", "List", "Figure", "Caption"]

# Document types for OmniDocBench stratification
OMNIDOC_TYPES = [
    "academic_literature",
    "research_report",
    "exam_paper",
    "colorful_textbook",
    "book",
    "PPT2PDF",
]

FIXTURE_COUNT_PER_TYPE = 2  # 2 fixtures per type


def load_dp_bench(root: Path) -> Iterator[tuple[str, Path, dict]]:
    """Load DP-Bench dataset."""
    from doc_bench.datasets.dp_bench import load_dp_bench as dp_bench_loader
    yield from dp_bench_loader(root)


def load_omnidocbench(root: Path) -> Iterator[tuple[str, dict]]:
    """Load OmniDocBench dataset."""
    from doc_bench.datasets import load_omnidocbench
    yield from load_omnidocbench(root)


def categorize_dp_bench_element(elements: dict) -> str | None:
    """
    Get primary category from DP-Bench elements.

    Returns the most common category in the document, or None if empty.

    Args:
        elements: DP-Bench gold elements dict.

    Returns:
        Category name or None.

    """
    element_list = elements.get("elements", [])
    if not element_list:
        return None

    category_counts = defaultdict(int)
    for elem in element_list:
        category = elem.get("category", "")
        if category:
            category_counts[category] += 1

    if not category_counts:
        return None

    # Return most common category
    return max(category_counts.items(), key=lambda x: x[1])[0]


def categorize_omnidocbench_doc(page: dict) -> str | None:
    """
    Get document type from OmniDocBench page metadata.

    Args:
        page: OmniDocBench page dict.

    Returns:
        Document type or None.

    """
    page_info = page.get("page_info", {})
    page_attr = page_info.get("page_attribute", {})

    # Try data_source first (baseline format)
    doc_type = page_attr.get("data_source")
    if doc_type:
        return doc_type

    # Fall back to doc_type (full dataset format)
    return page_info.get("doc_type")


def select_dp_bench_fixtures(root: Path) -> list[tuple[str, Path, dict, str]]:
    """
    Select stratified DP-Bench fixtures.

    Selects 2 documents per element category.

    Args:
        root: Path to DP-Bench dataset.

    Returns:
        List of (doc_id, pdf_path, gold_elements, category) tuples.

    """
    fixtures_by_category: dict[str, list] = {cat: [] for cat in DP_BENCH_CATEGORIES}

    for doc_id, pdf_path, gold_elements in load_dp_bench(root):
        category = categorize_dp_bench_element(gold_elements)
        if category and category in fixtures_by_category:
            if len(fixtures_by_category[category]) < FIXTURE_COUNT_PER_TYPE:
                fixtures_by_category[category].append((doc_id, pdf_path, gold_elements, category))

    # Flatten selected fixtures
    selected = []
    for category, fixtures in fixtures_by_category.items():
        selected.extend(fixtures)

    return selected


def select_omnidocbench_fixtures(root: Path) -> list[tuple[str, dict, str]]:
    """
    Select stratified OmniDocBench fixtures.

    Selects 2 documents per document type.

    Args:
        root: Path to OmniDocBench dataset.

    Returns:
        List of (doc_id, page, doc_type) tuples.

    """
    fixtures_by_type: dict[str, list] = {doc_type: [] for doc_type in OMNIDOC_TYPES}

    for doc_id, page in load_omnidocbench(root):
        doc_type = categorize_omnidocbench_doc(page)
        if doc_type and doc_type in fixtures_by_type:
            if len(fixtures_by_type[doc_type]) < FIXTURE_COUNT_PER_TYPE:
                fixtures_by_type[doc_type].append((doc_id, page, doc_type))

    # Flatten selected fixtures
    selected = []
    for doc_type, fixtures in fixtures_by_type.items():
        selected.extend(fixtures)

    return selected


def select_baseline_dp_bench_fixtures(root: Path) -> list[tuple[str, Path, dict, str]]:
    """
    Select stratified DP-Bench fixtures from baseline directory.

    Selects 2 documents per element category from baseline/ structure.

    Args:
        root: Path to baseline/dp_bench/ directory.

    Returns:
        List of (doc_id, pdf_path, gold_elements, category) tuples.
    """
    import json

    reference_path = root / "reference.json"
    pdfs_dir = root / "pdfs"

    if not reference_path.exists() or not pdfs_dir.exists():
        return []

    with open(reference_path) as f:
        reference = json.load(f)

    fixtures_by_category: dict[str, list] = {cat: [] for cat in DP_BENCH_CATEGORIES}

    for pdf_filename, gold_elements in reference.items():
        category = categorize_dp_bench_element(gold_elements)
        if category and category in fixtures_by_category:
            if len(fixtures_by_category[category]) < FIXTURE_COUNT_PER_TYPE:
                pdf_path = pdfs_dir / pdf_filename
                if pdf_path.exists():
                    doc_id = pdf_filename.replace(".pdf", "")
                    fixtures_by_category[category].append((doc_id, pdf_path, gold_elements, category))

    # Flatten selected fixtures
    selected = []
    for category, fixtures in fixtures_by_category.items():
        selected.extend(fixtures)

    return selected


def select_baseline_omnidocbench_fixtures(root: Path) -> list[tuple[str, dict, str, str]]:
    """
    Select stratified OmniDocBench fixtures from baseline directory.

    Selects 2 documents per document type from baseline/ structure.

    Args:
        root: Path to baseline/omnidocbench/ directory.

    Returns:
        List of (doc_id, page, doc_type, image_name) tuples.
    """
    import json

    json_path = root / "OmniDocBench.json"

    if not json_path.exists():
        return []

    with open(json_path) as f:
        pages = json.load(f)

    fixtures_by_type: dict[str, list] = {doc_type: [] for doc_type in OMNIDOC_TYPES}

    for page in pages:
        page_info = page.get("page_info", {})
        image_name = page_info.get("image_path", "")
        doc_type = categorize_omnidocbench_doc(page)

        # Generate doc_id from image_name
        doc_id = image_name.replace(".png", "").replace(".jpg", "") if image_name else ""

        if doc_id and doc_type and doc_type in fixtures_by_type:
            if len(fixtures_by_type[doc_type]) < FIXTURE_COUNT_PER_TYPE:
                fixtures_by_type[doc_type].append((doc_id, page, doc_type, image_name))

    # Flatten selected fixtures
    selected = []
    for doc_type, fixtures in fixtures_by_type.items():
        selected.extend(fixtures)

    return selected


def generate_fixtures(data_dir: Path, output_dir: Path) -> dict:
    """
    Generate bundled fixture sets.

    Args:
        data_dir: Root data directory containing datasets.
        output_dir: Output directory for fixtures.

    Returns:
        Manifest dictionary with fixture metadata.

    """
    manifest = {
        "name": "bundled-smoke-stratified",
        "description": "Stratified fixture set for smoke testing",
        "dp_bench": [],
        "omnidocbench": [],
        "total": 0,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    # Try baseline structure first
    dp_bench_baseline = data_dir / "dp_bench"
    if dp_bench_baseline.exists():
        dp_fixtures = select_baseline_dp_bench_fixtures(dp_bench_baseline)
        for doc_id, pdf_path, gold_elements, category in dp_fixtures:
            # Copy PDF to fixtures
            fixture_pdf = output_dir / "dp_bench" / f"{doc_id}.pdf"
            fixture_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, fixture_pdf)

            # Save gold elements
            fixture_gold = output_dir / "dp_bench" / f"{doc_id}.json"
            with open(fixture_gold, "w") as f:
                json.dump(gold_elements, f)

            manifest["dp_bench"].append({
                "doc_id": doc_id,
                "category": category,
                "pdf": f"dp_bench/{doc_id}.pdf",
                "gold": f"dp_bench/{doc_id}.json",
            })

    # Select DP-Bench fixtures from full data
    dp_bench_path = data_dir / "parsing" / "dp_bench"
    if dp_bench_path.exists() and not manifest["dp_bench"]:
        dp_fixtures = select_dp_bench_fixtures(dp_bench_path)
        for doc_id, pdf_path, gold_elements, category in dp_fixtures:
            # Copy PDF to fixtures
            fixture_pdf = output_dir / "dp_bench" / f"{doc_id}.pdf"
            fixture_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, fixture_pdf)

            # Save gold elements
            fixture_gold = output_dir / "dp_bench" / f"{doc_id}.json"
            with open(fixture_gold, "w") as f:
                json.dump(gold_elements, f)

            manifest["dp_bench"].append({
                "doc_id": doc_id,
                "category": category,
                "pdf": f"dp_bench/{doc_id}.pdf",
                "gold": f"dp_bench/{doc_id}.json",
            })

    # Try baseline OmniDocBench structure
    omnidoc_baseline = data_dir / "omnidocbench"
    if omnidoc_baseline.exists():
        od_fixtures = select_baseline_omnidocbench_fixtures(omnidoc_baseline)
        for doc_id, page, doc_type, image_name in od_fixtures:
            # Save page metadata
            fixture_page = output_dir / "omnidocbench" / f"{doc_id}.json"
            fixture_page.parent.mkdir(parents=True, exist_ok=True)
            with open(fixture_page, "w") as f:
                json.dump(page, f)

            # Copy image if exists
            if image_name:
                source_image = omnidoc_baseline / image_name
                if source_image.exists():
                    fixture_image = output_dir / "omnidocbench" / image_name
                    shutil.copy2(source_image, fixture_image)

            manifest["omnidocbench"].append({
                "doc_id": doc_id,
                "doc_type": doc_type,
                "page": f"omnidocbench/{doc_id}.json",
                "image": f"omnidocbench/{image_name}" if image_name else None,
            })

    # Select OmniDocBench fixtures from full data
    omnidoc_path = data_dir / "parsing" / "omnidocbench_english_large"
    if omnidoc_path.exists() and not manifest["omnidocbench"]:
        od_fixtures = select_omnidocbench_fixtures(omnidoc_path)
        for doc_id, page, doc_type in od_fixtures:
            # Save page metadata
            fixture_page = output_dir / "omnidocbench" / f"{doc_id}.json"
            fixture_page.parent.mkdir(parents=True, exist_ok=True)
            with open(fixture_page, "w") as f:
                json.dump(page, f)

            # Copy image if exists
            page_info = page.get("page_info", {})
            image_name = page_info.get("image_path", "")
            if image_name:
                source_image = omnidoc_path / "images" / image_name
                if source_image.exists():
                    fixture_image = output_dir / "omnidocbench" / image_name
                    shutil.copy2(source_image, fixture_image)

            manifest["omnidocbench"].append({
                "doc_id": doc_id,
                "doc_type": doc_type,
                "page": f"omnidocbench/{doc_id}.json",
            })

    manifest["total"] = len(manifest["dp_bench"]) + len(manifest["omnidocbench"])

    # Write manifest
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    """Generate bundled fixtures."""
    parser = argparse.ArgumentParser(
        description="Generate bundled fixture sets for smoke testing"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Root data directory containing datasets",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/doc_bench/fixtures"),
        help="Output directory for fixtures",
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"ERROR: Data directory not found: {args.data_dir}")
        return 1

    print("Generating bundled fixtures...")
    manifest = generate_fixtures(args.data_dir, args.output_dir)

    print(f"Generated {manifest['total']} fixtures:")
    print(f"  - DP-Bench: {len(manifest['dp_bench'])} documents")
    print(f"  - OmniDocBench: {len(manifest['omnidocbench'])} documents")
    print(f"\nFixtures written to: {args.output_dir}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")

    return 0


if __name__ == "__main__":
    exit(main())
