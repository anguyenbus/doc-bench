"""
Docling parser adapter.

This module provides integration with the Docling document parsing library,
converting Docling output to our standardized parser_output schema.
"""

import hashlib
import os
from pathlib import Path
from typing import Any

# Force CPU usage BEFORE importing docling
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["DOCLING_DEVICE"] = "cpu"

# Try to import docling, provide clear error if not available
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.settings import settings
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DocItemLabel, TableItem

    DOCLING_AVAILABLE = True

    # Create converter once and reuse (weight loading is expensive)
    _DOCLING_CONVERTER: DocumentConverter | None = None

    def _get_converter() -> DocumentConverter:
        """Get cached DocumentConverter instance."""
        global _DOCLING_CONVERTER
        if _DOCLING_CONVERTER is None:
            _DOCLING_CONVERTER = DocumentConverter()
        return _DOCLING_CONVERTER

except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None
    InputFormat = None
    settings = None
    DocItemLabel = None
    TableItem = None

    def _get_converter():
        raise ImportError("docling is not installed")


# Map docling labels to our schema types
DOCLING_LABEL_MAP: dict = {} if not DOCLING_AVAILABLE else {
    DocItemLabel.TITLE: "heading",
    DocItemLabel.DOCUMENT_INDEX: "heading",
    DocItemLabel.SECTION_HEADER: "heading",
    DocItemLabel.PARAGRAPH: "paragraph",
    DocItemLabel.TABLE: "table",
    DocItemLabel.PICTURE: "figure",
    DocItemLabel.FORMULA: "equation",
    DocItemLabel.TEXT: "paragraph",
    DocItemLabel.LIST_ITEM: "list_item",
    DocItemLabel.CODE: "code_block",
    DocItemLabel.CAPTION: "caption",
    DocItemLabel.PAGE_HEADER: "header",
    DocItemLabel.PAGE_FOOTER: "footer",
    DocItemLabel.FOOTNOTE: "footnote",
    DocItemLabel.CHECKBOX_UNSELECTED: "paragraph",
    DocItemLabel.CHECKBOX_SELECTED: "paragraph",
    DocItemLabel.REFERENCE: "paragraph",
}


# Best-effort constant header-row count. _table_to_markdown ignores this value
# (it hardcodes row 0 as the header), so a computed leading-header-row count has
# zero TEDS impact; and "any header cell" would inflate it to num_rows whenever a
# row-header column is present. See spec Task 2 (Q6).
_HEADER_ROWS: int = 1


def _build_table_content(table_data: Any) -> dict[str, Any]:
    """Map a Docling ``TableData`` to a schema ``TableContent`` dict.

    The mapping is a pure function so the ``TableData -> TableContent`` transform
    is unit-testable without running model inference.

    Args:
        table_data: A Docling ``TableData`` instance (``num_rows`` / ``num_cols``
            and a ``table_cells`` collection of ``TableCell``). Field access is
            guarded with ``getattr`` defaults because Docling field names vary by
            version.

    Returns:
        A ``TableContent`` dict: ``kind == "table"``, ``rows``/``cols`` from the
        grid dimensions, a constant best-effort ``header_rows`` of 1, and one
        ``cells`` entry per source cell. Each cell carries ``row``/``col`` (from
        the cell's ``start_*_offset_idx``), ``text``, the REAL ``row_span`` /
        ``col_span`` (preserved truthfully — the markdown render later flattens
        them, so structured content and rendered markdown intentionally disagree
        on shape), and ``is_header`` derived from ``column_header`` ONLY (NOT
        ``row_header``, which would mark every row in a row-header column).

    Note:
        Spanned source cells map to their ``(start_row, start_col)``; covered
        grid positions are simply absent (no text replication). This is the
        documented cause of the TEDS ceiling for tables with spans.

    """
    num_rows = int(getattr(table_data, "num_rows", 0) or 0)
    num_cols = int(getattr(table_data, "num_cols", 0) or 0)
    source_cells = getattr(table_data, "table_cells", []) or []

    cells: list[dict[str, Any]] = []
    for cell in source_cells:
        cells.append(
            {
                "row": int(getattr(cell, "start_row_offset_idx", 0) or 0),
                "col": int(getattr(cell, "start_col_offset_idx", 0) or 0),
                "text": str(getattr(cell, "text", "") or ""),
                "row_span": int(getattr(cell, "row_span", 1) or 1),
                "col_span": int(getattr(cell, "col_span", 1) or 1),
                "is_header": bool(getattr(cell, "column_header", False)),
            }
        )

    return {
        "kind": "table",
        "rows": num_rows,
        "cols": num_cols,
        "header_rows": _HEADER_ROWS,
        "cells": cells,
    }


class DoclingParser:
    """
    Docling document parser adapter.

    This class wraps the Docling library and provides a clean interface
    for parsing documents (PDFs and images) into our standardized schema.
    """

    def __init__(self):
        """Initialize Docling parser."""
        if not DOCLING_AVAILABLE:
            raise ImportError(
                "docling is not installed. Install with: uv add docling"
            )
        self._converter = _get_converter()

    def parse(self, file_path: Path) -> dict[str, Any]:
        """
        Parse a document file.

        Args:
            file_path: Path to PDF or image file.

        Returns:
            Dictionary conforming to parser_output schema.

        Raises:
            RuntimeError: If parsing fails.

        """
        if not DOCLING_AVAILABLE:
            raise ImportError("docling is not installed")

        doc_id = file_path.stem

        try:
            result = self._converter.convert(file_path)
            doc = result.document

            # Get file hash
            sha256 = self._get_sha256(file_path)

            # Build pages array
            pages = []
            doc_pages_dict = doc.pages if isinstance(doc.pages, dict) else {}
            page_count = len(doc_pages_dict)

            for page_no in range(page_count):
                page = doc_pages_dict.get(page_no)
                if page is None:
                    pages.append({
                        "page_index": page_no,
                        "width": 612,
                        "height": 792,
                        "rotation": 0,
                    })
                    continue

                # Handle both Page object and simple size dict
                if hasattr(page, "size"):
                    if hasattr(page.size, "width"):
                        width = page.size.width
                        height = page.size.height
                    else:
                        width = page.size.get("width", 612)
                        height = page.size.get("height", 792)
                else:
                    width = page.get("width", 612) if isinstance(page, dict) else 612
                    height = page.get("height", 792) if isinstance(page, dict) else 792

                pages.append({
                    "page_index": page_no,
                    "width": width,
                    "height": height,
                    "rotation": 0,
                })

            # Build elements array
            elements = []
            char_offset = 0

            # NOTE: iterate_items() yields text AND table items in reading order
            # through one traversal, so tables stay interleaved with body text
            # (instead of being appended after it, which would distort NED order).
            for item, _level in doc.iterate_items():
                prov_list = item.prov if hasattr(item, "prov") else []
                if not prov_list:
                    continue

                prov = prov_list[0]
                page_idx = prov.page_no - 1  # Docling uses 1-based

                # Dispatch: TableItem -> structured table element; else text item.
                if TableItem is not None and isinstance(item, TableItem):
                    table_data = getattr(item, "data", None)
                    if table_data is None:
                        continue

                    content = _build_table_content(table_data)
                    if content["rows"] == 0 or content["cols"] == 0:
                        continue

                    element = {
                        "element_id": f"{doc_id}_table_{len(elements):03d}",
                        "type": "table",
                        "page_index": page_idx,
                        # Table text lives in content.cells; the top-level text is
                        # an empty readable rendering (the converter builds the
                        # pipe table from content).
                        "char_span": [char_offset, char_offset],
                        "text": "",
                        "content": content,
                    }
                    if prov and hasattr(prov, "bbox"):
                        element["bbox"] = {
                            "x0": float(prov.bbox.l),
                            "y0": float(prov.bbox.t),
                            "x1": float(prov.bbox.r),
                            "y1": float(prov.bbox.b),
                        }

                    elements.append(element)
                    continue

                item_text = item.text if hasattr(item, "text") else ""

                if not item_text:
                    continue

                # Calculate character span
                char_start = char_offset
                char_end = char_offset + len(item_text)
                char_offset = char_end

                # Get element type
                element_type = self._get_element_type(item)

                # Build element
                element = {
                    "element_id": f"{doc_id}_{element_type}_{len(elements):03d}",
                    "type": element_type,
                    "page_index": page_idx,
                    "char_span": [char_start, char_end],
                    "text": item_text,
                    "content": {"kind": "text"},
                }

                # Add bbox if available
                if prov and hasattr(prov, "bbox"):
                    element["bbox"] = {
                        "x0": float(prov.bbox.l),
                        "y0": float(prov.bbox.t),
                        "x1": float(prov.bbox.r),
                        "y1": float(prov.bbox.b),
                    }

                # Add heading level if applicable
                if element_type == "heading":
                    level = self._get_heading_level(item)
                    if level is not None:
                        element["level"] = level

                elements.append(element)

            # Build output
            docling_version = result._version if hasattr(result, "_version") else "unknown"
            parsed_at = result._time_started if hasattr(result, "_time_started") else "2025-01-01T00:00:00Z"

            # Detect MIME type
            mime_type = self._detect_mime_type(file_path)

            return {
                "schema_version": "1.0.0",
                "parser_version": f"docling-{docling_version}",
                "parsed_at": parsed_at,
                "source": {
                    "doc_id": doc_id,
                    "filename": file_path.name,
                    "mime_type": mime_type,
                    "sha256": sha256,
                    "page_count": len(pages),
                    "language": "en",
                },
                "pages": pages,
                "elements": elements,
                "warnings": [],
            }

        except Exception as e:
            raise RuntimeError(f"Failed to parse {file_path}: {e}") from e

    def _get_sha256(self, file_path: Path) -> str:
        """Generate SHA-256 hash of file."""
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type from file extension."""
        suffix = file_path.suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".tiff": "image/tiff",
            ".bmp": "image/bmp",
        }
        return mime_map.get(suffix, "application/octet-stream")

    def _get_element_type(self, item: Any) -> str:
        """Map docling item label to our schema element type."""
        if not DOCLING_AVAILABLE:
            return "text"

        label = item.label if hasattr(item, "label") else None

        if label in DOCLING_LABEL_MAP:
            return DOCLING_LABEL_MAP[label]

        return "text"

    def _get_heading_level(self, item: Any) -> int | None:
        """Get heading level from docling item."""
        if not DOCLING_AVAILABLE:
            return None

        if hasattr(item, "label"):
            if item.label == DocItemLabel.TITLE:
                return 1
            elif item.label == DocItemLabel.DOCUMENT_INDEX:
                return 1
            elif item.label == DocItemLabel.SECTION_HEADER:
                if hasattr(item, "props") and hasattr(item.props, "level"):
                    return item.props.level
                return 2

        return None


# Global parser instance for convenience
_parser_instance: DoclingParser | None = None


def parse(file_path: Path | str) -> dict[str, Any]:
    """
    Parse a document file using Docling.

    Convenience function that uses a cached parser instance.

    Args:
        file_path: Path to PDF or image file.

    Returns:
        Dictionary conforming to parser_output schema.

    Raises:
        ImportError: If docling is not installed.
        RuntimeError: If parsing fails.

    """
    global _parser_instance

    if isinstance(file_path, str):
        file_path = Path(file_path)

    if _parser_instance is None:
        _parser_instance = DoclingParser()

    return _parser_instance.parse(file_path)
