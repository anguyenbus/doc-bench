#!/usr/bin/env python
"""Prune OmniDocBench dataset to N files for minimal Docker image."""

import json
import pathlib
import shutil
import sys

def main():
    keep_count = 10  # Keep only 10 files for minimal image

    src = pathlib.Path("/opt/doc-bench/data/parsing/omnidocbench_english_large")
    dst = pathlib.Path("/opt/doc-bench/data/parsing/omnidocbench_sample")

    if not src.exists():
        print(f"ERROR: Source directory {src} does not exist")
        sys.exit(1)

    # Get first N images
    images = sorted(src.glob("images/*.png"))[:keep_count]
    image_names = {img.name for img in images}

    # Create destination directories
    (dst / "images").mkdir(parents=True, exist_ok=True)

    # Copy images
    for img in images:
        shutil.copy(img, dst / "images" / img.name)

    # Load and filter OmniDocBench.json
    json_src = src / "OmniDocBench.json"
    if json_src.exists():
        with open(json_src) as f:
            all_pages = json.load(f)

        # Filter to only pages whose images exist
        filtered_pages = []
        for page in all_pages:
            img_path = page.get("page_info", {}).get("image_path", "")
            if img_path:
                img_name = pathlib.Path(img_path).name
                if img_name in image_names:
                    filtered_pages.append(page)

        # Write filtered JSON
        with open(dst / "OmniDocBench.json", "w") as f:
            json.dump(filtered_pages, f, indent=2)

        print(f"Filtered OmniDocBench.json: {len(filtered_pages)} pages (from {len(all_pages)})")
    else:
        print(f"WARNING: OmniDocBench.json not found at {json_src}")

    # Copy other metadata files if they exist
    for metadata_file in ["page_map.json", "README.md"]:
        src_metadata = src / metadata_file
        if src_metadata.exists():
            shutil.copy(src_metadata, dst / metadata_file)
            print(f"Copied {metadata_file}")

    # Replace source with pruned version
    shutil.rmtree(src)
    dst.rename(src)

    print(f"Kept {len(images)} OmniDocBench files")

if __name__ == "__main__":
    main()
