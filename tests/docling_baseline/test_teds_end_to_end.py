"""Deterministic, Docling-free end-to-end TEDS proof (Task 3).

This test proves the full scoring path produces a pinned, non-zero TEDS without
running any ML model:

    reconstructed TableData
        -> _build_table_content        (the real adapter mapping)
        -> parser_output_to_markdown   (the real converter -> pipe table)
        -> _evaluate_teds(gold, pred)  (the real scoring chain)

Non-circularity is a HARD requirement: the predicted table is REBUILT from the
gold cell *texts and spans* as a Docling ``TableData`` and pushed through the
real mapping path -- it is never the gold HTML echoed back. Because markdown
cannot express colspan/rowspan, the rendered prediction flattens the spanned
header cells, so TEDS is strictly ``< 1.0`` (the documented, shared ceiling).

The path contains no ML model and APTED is deterministic, so the exact TEDS /
TEDS-S values are PINNED with a float epsilon only. A shift on an ``apted`` /
``lxml`` / ``rapidfuzz`` upgrade must surface as a loud, intentional failure.

Reads ONLY the bundled varistor fixture; no external path, no ``docling`` import.
"""

import json
import re
from pathlib import Path
from typing import Any

from docling_baseline.adapters.docling import _build_table_content
from docling_baseline.converters.markdown import parser_output_to_markdown
from docling_baseline.runners.omnidocbench import _evaluate_teds

_FIXTURE: Path = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "doc_bench"
    / "fixtures"
    / "omnidocbench"
    / "page-458ab820-615f-42fe-af33-3a8fb15ad691.json"
)

# Pinned from the first green run. Reproducible because the scoring path is
# ML-free and APTED is deterministic; a dependency upgrade that shifts these is
# meant to fail loudly here.
_EXPECTED_TEDS: float = 0.9755519488328181
_EXPECTED_TEDS_S: float = 0.9801192842942346
_EPS: float = 1e-9


class _Cell:
    """Minimal stand-in for a Docling ``TableCell`` (duck-typed for the helper).

    The mapping helper reads fields via ``getattr``; this object exposes exactly
    the field names Docling uses, so it exercises the real mapping without
    importing ``docling``.
    """

    __slots__ = (
        "text",
        "row_span",
        "col_span",
        "start_row_offset_idx",
        "start_col_offset_idx",
        "column_header",
        "row_header",
    )

    def __init__(
        self,
        *,
        text: str,
        row: int,
        col: int,
        row_span: int,
        col_span: int,
        column_header: bool,
    ) -> None:
        self.text = text
        self.start_row_offset_idx = row
        self.start_col_offset_idx = col
        self.row_span = row_span
        self.col_span = col_span
        self.column_header = column_header
        self.row_header = False


class _TableData:
    """Minimal stand-in for a Docling ``TableData`` (duck-typed for the helper)."""

    __slots__ = ("num_rows", "num_cols", "table_cells")

    def __init__(self, *, num_rows: int, num_cols: int, table_cells: list[_Cell]) -> None:
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.table_cells = table_cells


def _load_gold_page() -> dict[str, Any]:
    """Load the bundled varistor gold page (read-only)."""
    return json.loads(_FIXTURE.read_text())


def _reconstruct_table_data_from_gold() -> _TableData:
    """Rebuild the gold table as a Docling-shaped ``TableData``.

    Parses the gold HTML into ``(row, col, text, col_span, is_header)`` cells and
    builds duck-typed cell objects. This is NOT a gold-HTML echo: the prediction
    is reconstructed cell-by-cell and re-rendered through the real mapping +
    converter, which flattens spans.
    """
    page = _load_gold_page()
    tables = [
        det["html"]
        for det in page.get("layout_dets", [])
        if det.get("category_type") == "table" and det.get("html")
    ]
    html = tables[0]
    rows_html = re.findall(r"<tr>(.*?)</tr>", html, re.S)

    cells: list[_Cell] = []
    max_cols = 0
    for row_idx, row_html in enumerate(rows_html):
        tds = re.findall(r"<td(.*?)>(.*?)</td>", row_html, re.S)
        col_cursor = 0
        for attr, raw_text in tds:
            colspan_match = re.search(r'colspan="(\d+)"', attr)
            col_span = int(colspan_match.group(1)) if colspan_match else 1
            # Normalise inline <br/> to spaces; this is text reconstruction,
            # not an HTML echo.
            text = re.sub(r"<br\s*/?>", " ", raw_text).strip()
            cells.append(
                _Cell(
                    text=text,
                    row=row_idx,
                    col=col_cursor,
                    row_span=1,
                    col_span=col_span,
                    column_header=row_idx <= 1,
                )
            )
            col_cursor += col_span
        max_cols = max(max_cols, col_cursor)

    return _TableData(num_rows=len(rows_html), num_cols=max_cols, table_cells=cells)


def _build_pred_markdown() -> str:
    """Build predicted markdown through the real mapping + converter path."""
    table_data = _reconstruct_table_data_from_gold()
    content = _build_table_content(table_data)
    parser_output = {
        "elements": [
            {
                "type": "table",
                "text": "",
                "content": content,
            }
        ]
    }
    return parser_output_to_markdown(parser_output)


class TestTedsEndToEnd:
    """End-to-end TEDS proof on the bundled varistor fixture."""

    def test_pinned_teds_values(self) -> None:
        """The reconstructed table scores the exact pinned TEDS / TEDS-S."""
        gold_page = _load_gold_page()
        pred_markdown = _build_pred_markdown()

        # Sanity: prediction is a real pipe table, not a gold-HTML echo.
        assert "| " in pred_markdown
        assert "<table>" not in pred_markdown

        teds, teds_s = _evaluate_teds(gold_page, pred_markdown)

        # Non-circularity guard: a faithful flattening cannot be a perfect echo.
        assert teds < 1.0
        assert abs(teds - _EXPECTED_TEDS) < _EPS
        assert abs(teds_s - _EXPECTED_TEDS_S) < _EPS

    def test_tableless_prediction_scores_zero(self) -> None:
        """A tableless prediction still scores ``(0.0, 0.0)`` (guard intact)."""
        gold_page = _load_gold_page()
        pred_markdown = parser_output_to_markdown(
            {"elements": [{"type": "paragraph", "text": "no table here"}]}
        )

        teds, teds_s = _evaluate_teds(gold_page, pred_markdown)
        assert teds == 0.0
        assert teds_s == 0.0
