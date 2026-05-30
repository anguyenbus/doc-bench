#!/usr/bin/env python
"""Prune OmniDocBench dataset to representative samples from each document type."""

import json
import pathlib
import shutil
import sys


def main():
    # Sample 2 pages from each document type for representative baseline
    samples_per_type = 2
    # Must match RELEVANT_DOC_TYPES in download_datasets.py
    target_types = {
        "academic_literature",
        "book",
        "PPT2PDF",
        "exam_paper",
        "colorful_textbook",
    }

    src = pathlib.Path("/opt/doc-bench/data/parsing/omnidocbench_english_large")
    dst = pathlib.Path("/opt/doc-bench/data/parsing/omnidocbench_sample")

    if not src.exists():
        print(f"ERROR: Source directory {src} does not exist")
        sys.exit(1)

    # Load full OmniDocBench.json
    json_src = src / "OmniDocBench.json"
    if not json_src.exists():
        print(f"ERROR: OmniDocBench.json not found at {json_src}")
        sys.exit(1)

    with open(json_src) as f:
        all_pages = json.load(f)

    # Group pages by document type
    pages_by_type = {t: [] for t in target_types}
    for page in all_pages:
        attrs = page.get("page_info", {}).get("page_attribute", {})
        dtype = attrs.get("data_source", "")
        if dtype in pages_by_type:
            pages_by_type[dtype].append(page)

    # Sample first N pages from each type
    selected_pages = []
    for dtype, pages in sorted(pages_by_type.items()):
        sample = pages[:samples_per_type]
        selected_pages.extend(sample)
        print(f"{dtype}: {len(sample)} pages (from {len(pages)} available)")

    # Get image filenames from selected pages
    image_names = set()
    for page in selected_pages:
        img_path = page.get("page_info", {}).get("image_path", "")
        if img_path:
            img_name = pathlib.Path(img_path).name
            image_names.add(img_name)

    # Create destination directories
    (dst / "images").mkdir(parents=True, exist_ok=True)

    # Copy selected images
    copied_count = 0
    for img_name in image_names:
        src_img = src / "images" / img_name
        if src_img.exists():
            shutil.copy(src_img, dst / "images" / img_name)
            copied_count += 1
        else:
            print(f"WARNING: Image not found: {img_name}")

    # Write filtered OmniDocBench.json
    with open(dst / "OmniDocBench.json", "w") as f:
        json.dump(selected_pages, f, indent=2)

    # Copy other metadata files if they exist
    for metadata_file in ["page_map.json", "README.md"]:
        src_metadata = src / metadata_file
        if src_metadata.exists():
            shutil.copy(src_metadata, dst / metadata_file)

    # Replace source with pruned version
    shutil.rmtree(src)
    dst.rename(src)

    print(f"\nKept {copied_count} OmniDocBench images across {len(target_types)} document types")
    print(f"Filtered OmniDocBench.json: {len(selected_pages)} pages")

if __name__ == "__main__":
    main()
