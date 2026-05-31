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


def _html_table_to_markdown(html: str) -> str:
    """
    Convert HTML table to Markdown pipe-table format.

    Args:
        html: HTML string containing <tr><td>...</td></tr> structure.

    Returns:
        Markdown table string with header separator.

    """
    # Simple HTML table parser - handles <tr><td>...</td></tr>
    # Each <tr> becomes a row, each <td> becomes a cell
    rows = []
    current_row = []

    # Parse rows by splitting on <tr> tags
    i = 0
    while i < len(html):
        if html[i:i+4].lower() == "<tr>":
            i += 4
        elif html[i:i+5].lower() == "</tr>":
            if current_row:
                rows.append(current_row)
                current_row = []
            i += 5
        elif html[i:i+4].lower() == "<td>":
            i += 4
            # Find cell content until </td>
            end_idx = html.find("</td>", i)
            if end_idx != -1:
                cell_text = html[i:end_idx].strip()
                current_row.append(cell_text)
                i = end_idx + 5
            else:
                break
        else:
            i += 1

    if not rows:
        return ""

    cols = len(rows[0])
    lines = []

    for row_idx, row in enumerate(rows):
        # Pad row to consistent column count
        while len(row) < cols:
            row.append("")
        lines.append("| " + " | ".join(row) + " |")

        # Add header separator after first row
        if row_idx == 0:
            lines.append("| " + " | ".join(["---"] * cols) + " |")

    return "\n".join(lines)


def build_gold_markdown(gold_elements: dict) -> str:
    """
    Build gold markdown text from DP-Bench elements.

    This constructs the ground truth text in a format compatible with the
    grader. Elements are processed in JSON order (no coordinate sorting).

    Category markup:
    - Header: "# {text}"
    - Table: rendered from content.html to Markdown pipe-table
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

        # Tables: render from html, fallback to text
        if category == "Table":
            html = content.get("html", "") if isinstance(content, dict) else ""
            markdown = content.get("markdown", "") if isinstance(content, dict) else ""

            if html:
                table_md = _html_table_to_markdown(html)
                if table_md:
                    gt_lines.append(table_md)
            elif markdown:
                gt_lines.append(markdown)
            elif text:
                gt_lines.append(text)
            # If all empty, table is skipped
        elif not text:
            # Non-table elements with empty text are skipped
            continue
        elif category == "Header":
            gt_lines.append(f"# {text}")
        elif category == "Paragraph":
            gt_lines.append(text)
        elif category == "List":
            gt_lines.append(f"- {text}")
        else:
            gt_lines.append(text)

        gt_lines.append("")  # Blank line between elements

    return "\n".join(gt_lines)
