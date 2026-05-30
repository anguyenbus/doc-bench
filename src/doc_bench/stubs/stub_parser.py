"""
Stub parser for testing parsing evaluation.

Returns a minimal parser_output that passes schema validation.
"""

from pathlib import Path
from typing import Any


def parse(pdf_path: Path) -> dict[str, Any]:
    """
    Stub parser that returns minimal valid output.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        Minimal parser output that conforms to parser_output schema.

    """
    return {
        "schema_version": "1.0.0",
        "parser_version": "0.0.1-stub",
        "parsed_at": "2024-01-01T00:00:00Z",
        "source": {
            "doc_id": "stub-doc-1",
            "filename": pdf_path.name,
            "mime_type": "application/pdf",
            "sha256": "a" * 64,  # Dummy SHA-256
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
                "char_span": [0, 19],
                "text": "Stub text content",
                "content": {"kind": "text"},
            }
        ],
        "warnings": [{"code": "STUB_OUTPUT", "message": "This is stub parser output"}],
    }
