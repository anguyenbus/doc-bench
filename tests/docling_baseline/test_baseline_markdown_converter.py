"""Tests for the docling_baseline markdown converter.

These tests pin the behaviour required by Task 1 of the
``2026-06-20-docling-table-extraction-fix`` spec: structured ``table`` and
``figure`` elements that carry an empty top-level ``text`` field must survive
the early pre-skip guard in :func:`elements_to_markdown` and reach type
dispatch so they render.
"""

from doc_bench.metrics.parsing.table_teds import _SEP_RE
from docling_baseline.converters.markdown import elements_to_markdown


class TestDoclingBaselineConverter:
    """Converter rendering of structured table/figure elements."""

    def test_table_with_empty_text_renders_pipe_table(self) -> None:
        """A ``content.kind=='table'`` element with empty text renders a GFM table.

        The second line of the rendered table must match the GFM separator
        regex (``_SEP_RE``) imported from the scoring module, proving the output
        is a real pipe table the TEDS extractor will recognise.
        """
        elements = [
            {
                "type": "table",
                "text": "",
                "content": {
                    "kind": "table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        {"row": 0, "col": 0, "text": "H1"},
                        {"row": 0, "col": 1, "text": "H2"},
                        {"row": 1, "col": 0, "text": "C1"},
                        {"row": 1, "col": 1, "text": "C2"},
                    ],
                },
            },
        ]

        result = elements_to_markdown(elements)
        lines = result.splitlines()

        assert len(lines) >= 2
        assert _SEP_RE.match(lines[1]), f"second line not a GFM separator: {lines[1]!r}"
        assert "H1" in result
        assert "C2" in result

    def test_figure_with_only_alt_text_renders(self) -> None:
        """A ``figure`` element with only ``alt_text`` (empty text) still renders."""
        elements = [
            {
                "type": "figure",
                "text": "",
                "content": {"kind": "figure", "alt_text": "A diagram"},
            },
        ]

        result = elements_to_markdown(elements)
        assert "![A diagram]" in result
