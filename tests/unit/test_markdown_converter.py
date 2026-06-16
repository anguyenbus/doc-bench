"""
Tests for markdown_converter module.

Tests conversion of parser_output elements to markdown strings,
especially the handling of tables with empty text but populated cells.
"""

from doc_bench.metrics.parsing.markdown_converter import (
    elements_to_markdown,
    parser_output_to_markdown,
)


class TestMarkdownConverter:
    """Tests for markdown conversion of parser_output elements."""

    def test_table_with_empty_text_renders_from_cells(self):
        """
        Test that tables with empty top-level text render from content.cells.

        Regression test for bug where tables with empty text were skipped
        before reaching table rendering code. Tables carry data in content.cells
        with empty text field; they should still render as markdown tables.
        """
        elements = [
            {
                "type": "paragraph",
                "text": "Before table",
                "content": {"kind": "text"},
            },
            {
                "type": "table",
                "text": "",  # Empty text, but cells populated
                "content": {
                    "kind": "table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        {"row": 0, "col": 0, "text": "Header 1"},
                        {"row": 0, "col": 1, "text": "Header 2"},
                        {"row": 1, "col": 0, "text": "Cell 1"},
                        {"row": 1, "col": 1, "text": "Cell 2"},
                    ],
                },
            },
            {
                "type": "paragraph",
                "text": "After table",
                "content": {"kind": "text"},
            },
        ]

        result = elements_to_markdown(elements)

        # Should include the table
        assert "Header 1" in result
        assert "Header 2" in result
        assert "Cell 1" in result
        assert "Cell 2" in result
        # Should have markdown table format
        assert "| " in result
        assert "---" in result
        # Should include before/after paragraphs
        assert "Before table" in result
        assert "After table" in result

    def test_table_with_text_uses_text_as_fallback(self):
        """Test that tables with text but no cells use the text field."""
        elements = [
            {
                "type": "table",
                "text": "Simple table text",
                "content": {"kind": "text"},  # Not a table content
            },
        ]

        result = elements_to_markdown(elements)
        assert "Simple table text" in result

    def test_empty_text_only_elements_skipped(self):
        """Test that text-only elements with empty text are skipped."""
        elements = [
            {"type": "paragraph", "text": "", "content": {"kind": "text"}},
            {"type": "heading", "text": "", "level": 1, "content": {"kind": "text"}},
            {"type": "paragraph", "text": "Keep me", "content": {"kind": "text"}},
        ]

        result = elements_to_markdown(elements)
        assert "Keep me" in result
        # Empty elements should not produce blank lines
        lines = [line for line in result.split("\n") if line]
        assert len(lines) == 1

    def test_figure_with_alt_text_renders(self):
        """Test that figures with alt_text render even with empty text."""
        elements = [
            {
                "type": "figure",
                "text": "",  # Empty text
                "content": {"kind": "figure", "alt_text": "Figure caption"},
            },
        ]

        result = elements_to_markdown(elements)
        assert "![Figure caption]" in result

    def test_full_parser_output_to_markdown(self):
        """Test conversion of full parser_output dict to markdown."""
        parser_output = {
            "schema_version": "1.0.0",
            "parser_version": "1.0.0",
            "source": {
                "doc_id": "test-doc",
                "filename": "test.pdf",
                "mime_type": "application/pdf",
                "sha256": "a" * 64,
            },
            "pages": [{"page_index": 0, "width": 100, "height": 100}],
            "elements": [
                {
                    "type": "table",
                    "text": "",
                    "page_index": 0,
                    "char_span": [0, 0],
                    "content": {
                        "kind": "table",
                        "rows": 1,
                        "cols": 1,
                        "cells": [{"row": 0, "col": 0, "text": "Data"}],
                    },
                },
            ],
        }

        result = parser_output_to_markdown(parser_output)
        assert "Data" in result
        assert "| " in result
