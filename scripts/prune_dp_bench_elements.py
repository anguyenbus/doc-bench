#!/usr/bin/env python
"""Prune DP-Bench dataset to representative samples for each element type."""

import json
import pathlib
import shutil
import sys


def main():
    """Prune DP-Bench to representative PDFs covering each element type."""
    # Representative PDFs for each element type (2 each)
    selected_pdfs = [
        "01030000000001.pdf",  # Header
        "01030000000002.pdf",  # Header
        "01030000000017.pdf",  # Footer
        "01030000000027.pdf",  # Chart
        "01030000000040.pdf",  # Footer
        "01030000000076.pdf",  # Chart
        "01030000000083.pdf",  # Table
        "01030000000118.pdf",  # Figure
        "01030000000120.pdf",  # Figure
        "01030000000127.pdf",  # Table
        "01030000000192.pdf",  # Paragraph
        "01030000000193.pdf",  # Paragraph
    ]

    src = pathlib.Path("/opt/doc-bench/data/parsing/dp_bench/dataset")
    dst = pathlib.Path("/opt/doc-bench/data/parsing/dp_bench_temp")

    if not src.exists():
        print(f"ERROR: Source directory {src} does not exist")
        sys.exit(1)

    # Find reference.json
    reference_json = src / "reference.json"
    if not reference_json.exists():
        print(f"ERROR: reference.json not found at {reference_json}")
        sys.exit(1)

    # Load reference.json
    with open(reference_json) as f:
        reference = json.load(f)

    # Create filtered reference with selected PDFs
    filtered_reference = {}
    for pdf_name in selected_pdfs:
        if pdf_name in reference:
            filtered_reference[pdf_name] = reference[pdf_name]
            print(f"Included: {pdf_name}")
        else:
            print(f"WARNING: {pdf_name} not found in reference.json")

    # Create destination directory
    dst.mkdir(parents=True, exist_ok=True)

    # Copy PDFs for selected documents
    pdfs_dir = dst / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)

    copied_count = 0
    for pdf_name in selected_pdfs:
        src_pdf = src / "pdfs" / pdf_name
        if src_pdf.exists():
            shutil.copy(src_pdf, pdfs_dir / pdf_name)
            copied_count += 1
            print(f"Copied: {pdf_name}")
        else:
            print(f"WARNING: PDF not found: {pdf_name}")

    # Create filtered reference.json
    with open(dst / "reference.json", "w") as f:
        json.dump(filtered_reference, f, indent=2)

    # Copy sample_results directory (optional, for reference)
    sample_src = src / "sample_results"
    if sample_src.exists():
        shutil.copytree(sample_src, dst / "sample_results")

    # Replace original dataset directory with pruned version
    shutil.rmtree(src)
    dst.rename(src)

    print(f"\nKept {copied_count} DP-Bench files (element type representatives)")
    print(f"Filtered reference.json: {len(filtered_reference)} entries")

    # Show element type distribution
    element_types = {}
    for pdf_name, data in filtered_reference.items():
        for elem in data.get("elements", []):
            category = elem.get("category", "")
            element_types[category] = element_types.get(category, 0) + 1

    print("Element type distribution:")
    for elem_type, count in sorted(element_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {elem_type}: {count} occurrences")


if __name__ == "__main__":
    main()
