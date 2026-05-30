#!/usr/bin/env python
"""Prune DP-Bench dataset to N files for minimal Docker image."""

import json
import pathlib
import shutil
import sys

def main():
    keep_count = 50  # Keep only 50 files for minimal image

    # DP-Bench has data under dataset/ subdirectory
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

    # Get first N document IDs
    doc_ids = list(reference.keys())[:keep_count]

    # Create destination directory
    dst.mkdir(parents=True, exist_ok=True)

    # Copy PDFs for first N documents
    pdfs_dir = dst / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)

    copied_count = 0
    for doc_id in doc_ids:
        src_pdf = src / "pdfs" / f"{doc_id}.pdf"
        if src_pdf.exists():
            shutil.copy(src_pdf, pdfs_dir / f"{doc_id}.pdf")
            copied_count += 1
        else:
            print(f"WARNING: PDF not found for {doc_id}")

    # Create filtered reference.json
    filtered_reference = {k: reference[k] for k in doc_ids if k in reference}
    with open(dst / "reference.json", "w") as f:
        json.dump(filtered_reference, f, indent=2)

    # Copy sample_results directory (optional, for reference)
    sample_src = src / "sample_results"
    if sample_src.exists():
        shutil.copytree(sample_src, dst / "sample_results")

    # Replace original dataset directory with pruned version
    parent = src.parent
    shutil.rmtree(src)
    dst.rename(src)

    print(f"Kept {copied_count} DP-Bench files (from {len(reference)} total)")
    print(f"Filtered reference.json: {len(filtered_reference)} entries")

if __name__ == "__main__":
    main()
