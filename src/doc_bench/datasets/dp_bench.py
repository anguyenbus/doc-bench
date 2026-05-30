"""
DP-Bench dataset loader.

This module loads the DP-Bench (Document Parsing Benchmark) dataset,
which provides ground truth layout annotations for document parsing evaluation.
"""

import json
from collections.abc import Iterator
from pathlib import Path

from doc_bench.identity import doc_id_for


def load_dp_bench(root: Path) -> Iterator[tuple[str, Path, dict]]:
    """
    Load DP-Bench dataset and yield (doc_id, pdf_path, gold_elements) tuples.

    Supports two layouts:
    1. Flat layout (baseline/):
       root/
         reference.json
         pdfs/
           01030000000001.pdf
           ...

    2. HuggingFace layout:
       root/
         dataset/
           reference.json
           pdfs/
             01030000000001.pdf
             ...

    Args:
        root: Path to DP-Bench root or dataset directory.

    Yields:
        tuple: (doc_id, pdf_path, gold_elements) where:
            - doc_id: Document identifier derived via doc_id_for()
            - pdf_path: Path to the PDF file
            - gold_elements: Ground truth from reference.json

    Raises:
        FileNotFoundError: If required files/directories don't exist.

    """
    # Try flat layout first (baseline/)
    reference_path = root / "reference.json"
    pdfs_dir = root / "pdfs"

    if not reference_path.exists():
        # Try HuggingFace layout
        dataset_dir = root / "dataset"
        reference_path = dataset_dir / "reference.json"
        pdfs_dir = dataset_dir / "pdfs"

        if not dataset_dir.exists():
            raise FileNotFoundError(
                f"DP-Bench not found at {root} (tried flat and dataset/ layouts)"
            )

    if not reference_path.exists():
        raise FileNotFoundError(f"DP-Bench reference.json not found at {root}")

    if not pdfs_dir.exists():
        raise FileNotFoundError(f"DP-Bench pdfs directory not found at {root}")

    # Load reference annotations
    with open(reference_path) as f:
        reference = json.load(f)

    # Iterate over each document in reference
    for pdf_filename, gold_elements in reference.items():
        # Use doc_id_for() to derive canonical identifier
        doc_id = doc_id_for("dp_bench", (pdf_filename, gold_elements))
        pdf_path = pdfs_dir / pdf_filename

        if not pdf_path.exists():
            # Skip if PDF file missing
            continue

        yield doc_id, pdf_path, gold_elements


def _get_sort_key(element: dict) -> tuple:
    """
    Get sort key for element in reading order.

    Elements are sorted by (page, y, x) coordinates to match
    natural reading order (top-to-bottom, left-to-right).

    Args:
        element: DP-Bench element dict with page and coordinates.

    Returns:
        Sort key tuple (page, y, x). Missing values sort last.

    """
    page = element.get("page", float("inf"))

    # Get y coordinate from first point in coordinates
    coordinates = element.get("coordinates", [])
    if coordinates and isinstance(coordinates, list) and len(coordinates) > 0:
        y = coordinates[0].get("y", float("inf"))
        x = coordinates[0].get("x", float("inf"))
    else:
        y = float("inf")
        x = float("inf")

    return (page, y, x)


def build_gold_markdown(gold_elements: dict) -> str:
    """
    Build gold markdown text from DP-Bench elements.

    This constructs the ground truth text in a format compatible with the
    grader. Elements are processed in JSON order (no coordinate sorting).

    Category markup:
    - Header: "# {text}"
    - Table: "[TABLE: {text}]"
    - List: "- {text}"
    - Paragraph/other: plain text

    Elements are separated by blank lines.

    Args:
        gold_elements: Dictionary from reference.json with "elements" array.

    Returns:
        Gold markdown text string.

    """
    # Process elements in JSON order (no sorting)
    elements = gold_elements.get("elements", [])

    gt_lines = []
    for elem in elements:
        category = elem.get("category", "")
        content = elem.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""

        if not text:
            continue

        if category == "Header":
            gt_lines.append(f"# {text}")
        elif category == "Paragraph":
            gt_lines.append(text)
        elif category == "Table":
            gt_lines.append(f"[TABLE: {text}]")
        elif category == "List":
            gt_lines.append(f"- {text}")
        else:
            gt_lines.append(text)
        gt_lines.append("")  # Blank line between elements

    return "\n".join(gt_lines)
