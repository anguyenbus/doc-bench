#!/usr/bin/env python
"""Analyze DP-Bench to find representative PDFs for each element type."""

import json
import pathlib
from collections import defaultdict

def main():
    # Download reference.json from HuggingFace
    temp_dir = pathlib.Path("/tmp/dp_bench_analysis")
    temp_dir.mkdir(parents=True, exist_ok=True)

    ref_path = temp_dir / "reference.json"

    if not ref_path.exists():
        print("Downloading reference.json...")
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id="upstage/dp-bench",
            repo_type="dataset",
            local_dir=temp_dir,
            allow_patterns=["dataset/reference.json"],
        )
        ref_path = temp_dir / "dataset" / "reference.json"

    print(f"Loading reference from {ref_path}")
    with open(ref_path) as f:
        reference = json.load(f)

    # Target element types
    target_types = {"Table", "Paragraph", "Figure", "Chart", "Header", "Footer"}

    # Analyze each PDF for element types
    pdf_elements = defaultdict(dict)  # pdf_name -> {element_type: count}

    for pdf_name, data in reference.items():
        elements = data.get("elements", [])
        element_counts = defaultdict(int)

        for elem in elements:
            category = elem.get("category", "")
            if category in target_types:
                element_counts[category] += 1

        # Only keep PDFs that have at least one target element
        if element_counts:
            pdf_elements[pdf_name] = dict(element_counts)

    # Find best candidates for each element type
    selected_pdfs = []

    for elem_type in target_types:
        # Find PDFs with this element type
        candidates = []
        for pdf_name, counts in pdf_elements.items():
            if elem_type in counts:
                candidates.append((pdf_name, counts[elem_type]))

        # Sort by count (descending) to get PDFs with most instances of this element
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Select top 2 candidates for this element type
        if candidates:
            for pdf_name, count in candidates[:2]:
                if pdf_name not in [p[0] for p in selected_pdfs]:
                    selected_pdfs.append((pdf_name, elem_type, count))
                    print(f"{elem_type}: {pdf_name} ({count} {elem_type} elements)")

    print(f"\nTotal unique PDFs selected: {len(selected_pdfs)}")

    # Create final selection (prioritize diversity)
    final_pdfs = []
    seen = set()

    # First pass: get one PDF for each element type
    for elem_type in target_types:
        for pdf_name, category, count in selected_pdfs:
            if category == elem_type and pdf_name not in seen:
                final_pdfs.append(pdf_name)
                seen.add(pdf_name)
                break

    # Second pass: get second PDF for each element type
    for elem_type in target_types:
        for pdf_name, category, count in selected_pdfs:
            if category == elem_type and pdf_name not in seen:
                final_pdfs.append(pdf_name)
                seen.add(pdf_name)
                break

    print(f"\nFinal selection ({len(final_pdfs)} PDFs):")
    for pdf in sorted(final_pdfs):
        elem_types = [k for k, v in pdf_elements[pdf].items() if v > 0]
        print(f"  {pdf}: {', '.join(elem_types)}")

    # Save selection to file
    output_path = pathlib.Path("/home/an/atoprojects/doc-bench/baseline/dp_bench/selected_pdfs.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for pdf in sorted(final_pdfs):
            f.write(f"{pdf}\n")

    print(f"\nSaved selection to: {output_path}")

if __name__ == "__main__":
    main()
