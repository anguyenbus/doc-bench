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
    from docling_core.types.doc import DocItemLabel

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

            for item in doc.texts:
                prov_list = item.prov if hasattr(item, "prov") else []
                if not prov_list:
                    continue

                prov = prov_list[0]
                page_idx = prov.page_no - 1  # Docling uses 1-based

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
                element: dict[str, Any] = {
                    "element_id": f"{doc_id}_{element_type}_{len(elements):03d}",
                    "type": element_type,
                    "page_index": page_idx,
                    "char_span": [char_start, char_end],
                    "text": item_text,
                    "content": {"kind": "text"},
                }

                # Add bbox if available
                if prov and hasattr(prov, "bbox"):
                    page_height = pages[page_idx]["height"] if page_idx < len(pages) else 792
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
