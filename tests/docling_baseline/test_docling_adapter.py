"""Tests for the docling_baseline Docling adapter table mapping (Task 2).

These tests pin the pure ``TableData -> TableContent`` mapping helper
(:func:`docling_baseline.adapters.docling._build_table_content`) and verify that
a produced table element validates against ``parser_output.schema.json``. They
build a Docling ``TableData`` by hand so the mapping is unit-testable without
running model inference.
"""

import pytest

from doc_bench import get_bundled_schema_path
from doc_bench.adapters.schema_validator import validate

# NOTE: docling_core ships the TableData / TableCell datamodel; the adapter
# module itself imports docling lazily. The helper under test is a pure
# dict-mapping function, but it consumes a real TableData instance, so the
# datamodel is a genuine test dependency.
table_data_mod = pytest.importorskip("docling_core.types.doc")
TableCell = table_data_mod.TableCell
TableData = table_data_mod.TableData

from docling_baseline.adapters.docling import _build_table_content  # noqa: E402


def _make_2x2_one_header_row() -> "TableData":
    """Build a hand-made 2x2 TableData with the first row marked column-header."""
    cells = [
        TableCell(
            text="H1",
            row_span=1,
            col_span=1,
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
            column_header=True,
            row_header=False,
        ),
        TableCell(
            text="H2",
            row_span=1,
            col_span=1,
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=1,
            end_col_offset_idx=2,
            column_header=True,
            row_header=False,
        ),
        TableCell(
            text="C1",
            row_span=1,
            col_span=1,
            start_row_offset_idx=1,
            end_row_offset_idx=2,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
            column_header=False,
            row_header=False,
        ),
        TableCell(
            text="C2",
            row_span=1,
            col_span=1,
            start_row_offset_idx=1,
            end_row_offset_idx=2,
            start_col_offset_idx=1,
            end_col_offset_idx=2,
            column_header=False,
            row_header=False,
        ),
    ]
    return TableData(num_rows=2, num_cols=2, table_cells=cells)


class TestBuildTableContent:
    """Pure ``TableData -> TableContent`` mapping."""

    def test_maps_2x2_one_header_row(self) -> None:
        """A 2x2 (one header row) TableData maps to a valid TableContent dict."""
        content = _build_table_content(_make_2x2_one_header_row())

        assert content["kind"] == "table"
        assert content["rows"] == 2
        assert content["cols"] == 2
        # header_rows is a CONSTANT best-effort value, not a computed count.
        assert content["header_rows"] == 1

        # One cell per (row, col).
        positions = {(c["row"], c["col"]) for c in content["cells"]}
        assert positions == {(0, 0), (0, 1), (1, 0), (1, 1)}
        assert len(content["cells"]) == 4

        by_pos = {(c["row"], c["col"]): c for c in content["cells"]}
        # Cells carry the full per-cell shape.
        for cell in content["cells"]:
            assert set(cell) >= {
                "row",
                "col",
                "text",
                "row_span",
                "col_span",
                "is_header",
            }
        # is_header derives from column_header ONLY.
        assert by_pos[(0, 0)]["is_header"] is True
        assert by_pos[(0, 1)]["is_header"] is True
        assert by_pos[(1, 0)]["is_header"] is False
        assert by_pos[(1, 1)]["is_header"] is False
        # Real spans preserved.
        assert by_pos[(0, 0)]["row_span"] == 1
        assert by_pos[(0, 0)]["col_span"] == 1
        assert by_pos[(0, 0)]["text"] == "H1"


class TestProducedTableElementValidates:
    """A produced table element validates against parser_output.schema.json."""

    def test_table_element_passes_schema_validation(self) -> None:
        """Wrap the produced table element in a minimal parser_output and validate."""
        content = _build_table_content(_make_2x2_one_header_row())

        parser_output = {
            "schema_version": "1.0.0",
            "parser_version": "docling-test",
            "parsed_at": "2025-01-01T00:00:00Z",
            "source": {
                "doc_id": "t",
                "filename": "t.pdf",
                "mime_type": "application/pdf",
                "sha256": "a" * 64,
                "page_count": 1,
            },
            "pages": [{"page_index": 0, "width": 612.0, "height": 792.0}],
            "elements": [
                {
                    "element_id": "t_table_000",
                    "type": "table",
                    "page_index": 0,
                    "char_span": [0, 0],
                    "text": "",
                    "content": content,
                }
            ],
            "warnings": [],
        }

        # validate() raises SchemaValidationError on failure; passing == no raise.
        validate(parser_output, get_bundled_schema_path())
