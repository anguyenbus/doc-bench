"""Tests for Table TEDS metric."""

import json
from pathlib import Path

import pytest

from doc_bench.metrics.parsing.table_teds import (
    _extract_tables_from_markdown,
    _markdown_table_to_html,
    table_teds,
)

# Path to bundled OmniDocBench fixtures used in acceptance tests
_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "src" / "doc_bench" / "fixtures" / "omnidocbench"
_VARISTOR_FIXTURE = _FIXTURES_DIR / "page-458ab820-615f-42fe-af33-3a8fb15ad691.json"


class TestSeparatorDetection:
    """Acceptance criterion 1 — separator variant recognition (Bug 1 fix)."""

    SIMPLE_TABLE_COMPACT = "| A | B |\n|---|---|\n| 1 | 2 |"
    SIMPLE_TABLE_SPACED = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    SIMPLE_TABLE_ALIGNED = "| A | B |\n|:---|:---:|\n| 1 | 2 |"

    @pytest.mark.parametrize(
        "separator_style,markdown",
        [
            ("compact |---|---|", SIMPLE_TABLE_COMPACT),
            ("standard | --- | --- |", SIMPLE_TABLE_SPACED),
            ("aligned |:---|:---:|", SIMPLE_TABLE_ALIGNED),
        ],
    )
    def test_extract_tables_recognises_separator(self, separator_style, markdown):
        """_extract_tables_from_markdown must return non-empty list for all GFM separator styles."""
        tables = _extract_tables_from_markdown(markdown)
        assert len(tables) > 0, f"Expected a table extracted for separator style: {separator_style}"

    def test_extract_tables_spaced_mineru_separator(self):
        """Reproduces the exact MinerU separator format that triggered Bug 1."""
        mineru_sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        header = "| " + " | ".join([f"Col{i}" for i in range(13)]) + " |"
        row = "| " + " | ".join([f"val{i}" for i in range(13)]) + " |"
        markdown = f"{header}\n{mineru_sep}\n{row}"
        tables = _extract_tables_from_markdown(markdown)
        assert len(tables) == 1

    def test_separator_line_excluded_from_html(self):
        """Separator row must not appear as a data row in the HTML output."""
        markdown = "| A | B |\n| --- | --- |\n| 1 | 2 |"
        html = _markdown_table_to_html(markdown)
        # Separator row should never produce a table row whose cells contain only dashes/spaces
        assert "---" not in html


class TestEvaluateTEDSOmniDocBench:
    """Acceptance criterion 2 — TEDS non-zero on the varistor fixture (Bug 2 fix)."""

    @pytest.mark.skipif(
        not _VARISTOR_FIXTURE.exists(),
        reason="varistor fixture not bundled in this environment",
    )
    def test_teds_nonzero_for_table_page(self):
        """_evaluate_teds_for_omnidocbench must return TEDS > 0 when pred contains a table."""
        from doc_bench.runners.run_parsing_eval import _evaluate_teds_for_omnidocbench

        page = json.loads(_VARISTOR_FIXTURE.read_text())
        # Minimal 2-row markdown table — enough to prove the path is not blocked
        pred_markdown = "| A | B |\n| --- | --- |\n| 1 | 2 |"
        teds, teds_s = _evaluate_teds_for_omnidocbench(page, pred_markdown)
        assert teds > 0.0, "TEDS must be non-zero when pred contains a markdown table"
        assert teds_s > 0.0, "TEDS-S must be non-zero when pred contains a markdown table"

    @pytest.mark.skipif(
        not _VARISTOR_FIXTURE.exists(),
        reason="varistor fixture not bundled in this environment",
    )
    def test_teds_zero_when_no_pred_table(self):
        """_evaluate_teds_for_omnidocbench returns (0, 0) when pred has no markdown table."""
        from doc_bench.runners.run_parsing_eval import _evaluate_teds_for_omnidocbench

        page = json.loads(_VARISTOR_FIXTURE.read_text())
        teds, teds_s = _evaluate_teds_for_omnidocbench(page, "no table here at all")
        assert teds == 0.0
        assert teds_s == 0.0

    def test_teds_zero_when_no_gold_table(self):
        """_evaluate_teds_for_omnidocbench returns (0, 0) when page has no table layout_det."""
        from doc_bench.runners.run_parsing_eval import _evaluate_teds_for_omnidocbench

        page = {"layout_dets": [{"category_type": "text", "text": "hello", "html": ""}]}
        pred = "| A |\n| --- |\n| 1 |"
        teds, teds_s = _evaluate_teds_for_omnidocbench(page, pred)
        assert teds == 0.0
        assert teds_s == 0.0


class TestTableTEDS:
    """Test suite for Tree Edit Distance Similarity for tables."""

    def test_identical_tables(self):
        """Test TEDS of 1.0 for identical tables."""
        table1 = {
            "rows": 2,
            "cols": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "A1"},
                {"row": 0, "col": 1, "text": "B1"},
                {"row": 1, "col": 0, "text": "A2"},
                {"row": 1, "col": 1, "text": "B2"},
            ],
        }

        score = table_teds(table1, table1)
        assert score == 1.0

    def test_different_structure(self):
        """Test TEDS for tables with different structure."""
        predicted = {
            "rows": 2,
            "cols": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "A1"},
                {"row": 0, "col": 1, "text": "B1"},
                {"row": 1, "col": 0, "text": "A2"},
                {"row": 1, "col": 1, "text": "B2"},
            ],
        }

        gold = {
            "rows": 3,  # Different row count
            "cols": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "A1"},
                {"row": 0, "col": 1, "text": "B1"},
                {"row": 1, "col": 0, "text": "A2"},
                {"row": 1, "col": 1, "text": "B2"},
                {"row": 2, "col": 0, "text": "A3"},
                {"row": 2, "col": 1, "text": "B3"},
            ],
        }

        score = table_teds(predicted, gold)
        # Should be less than 1.0 due to missing row
        assert 0 <= score < 1.0

    def test_same_structure_different_content(self):
        """Test TEDS for tables with same structure but different content."""
        predicted = {
            "rows": 2,
            "cols": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "A1"},
                {"row": 0, "col": 1, "text": "B1"},
                {"row": 1, "col": 0, "text": "A2"},
                {"row": 1, "col": 1, "text": "B2"},
            ],
        }

        gold = {
            "rows": 2,
            "cols": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "X1"},  # Different content
                {"row": 0, "col": 1, "text": "B1"},
                {"row": 1, "col": 0, "text": "A2"},
                {"row": 1, "col": 1, "text": "Y2"},  # Different content
            ],
        }

        score = table_teds(predicted, gold)
        # Should be between 0 and 1
        assert 0 < score < 1.0

    def test_empty_tables(self):
        """Test TEDS for empty tables."""
        table = {"rows": 0, "cols": 0, "cells": []}
        score = table_teds(table, table)
        assert score == 1.0

    def test_deterministic_behavior(self):
        """Test that same inputs produce same output."""
        table1 = {
            "rows": 2,
            "cols": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "B"},
                {"row": 1, "col": 0, "text": "C"},
                {"row": 1, "col": 1, "text": "D"},
            ],
        }

        score1 = table_teds(table1, table1)
        score2 = table_teds(table1, table1)
        assert score1 == score2

    def test_completely_different_tables(self):
        """Test TEDS near 0 for completely different tables."""
        predicted = {
            "rows": 1,
            "cols": 1,
            "cells": [{"row": 0, "col": 0, "text": "A"}],
        }

        gold = {
            "rows": 3,
            "cols": 3,
            "cells": [{"row": i, "col": j, "text": f"{i}{j}"} for i in range(3) for j in range(3)],
        }

        score = table_teds(predicted, gold)
        # Should be low due to very different structure
        assert 0 <= score <= 0.5
