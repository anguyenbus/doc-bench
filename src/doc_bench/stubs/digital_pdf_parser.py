"""Fast stub parser for digital PDFs (pypdf-based).

Returns a minimal parser_output that passes schema validation.
"""

from pathlib import Path
from typing import Any


def parse(pdf_path: Path) -> dict[str, Any]:
    """
    Fast stub parser for digital PDFs.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        Minimal parser output that conforms to parser_output schema.

    """
    return {
        "schema_version": "1.0.0",
        "parser_version": "digital-1.0.0",
        "parsed_at": "2024-01-01T00:00:00Z",
        "source": {
            "doc_id": "digital-doc-1",
            "filename": pdf_path.name,
            "mime_type": "application/pdf",
            "sha256": "b" * 64,  # Dummy SHA-256
            "page_count": 1,
        },
        "pages": [
            {
                "page_index": 0,
                "width": 612.0,
                "height": 792.0,
            }
        ],
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "page_index": 0,
                "char_span": [0, 31],
                "text": "Fast digital PDF parser content",
                "content": {"kind": "text"},
            }
        ],
    }
