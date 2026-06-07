"""
Tests for the updated run_parsing_eval.py schema contract.

Verifies that the runner emits only the new metric columns (ned, teds, teds_s)
and not the old metric columns (nid, nid_s, mhs, mhs_s, ard, bleu, meteor).
"""

import csv
import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_minimal_prediction() -> dict:
    """Build a minimal valid parser output prediction."""
    return {
        "schema_version": "1.0",
        "elements": [
            {
                "type": "paragraph",
                "text": "Sample prediction text.",
                "content": {},
            }
        ],
    }


def test_csv_fieldnames_contain_ned_teds_teds_s() -> None:
    """CSV fieldnames must contain ned, teds, teds_s."""
    import importlib

    import doc_bench.runners.run_parsing_eval as module

    importlib.reload(module)

    # The fieldnames are defined as a local variable inside main().
    # We verify by grepping the source for the expected structure.
    source = Path(module.__file__).read_text()
    assert '"ned"' in source
    assert '"teds"' in source
    assert '"teds_s"' in source


def test_csv_fieldnames_do_not_contain_old_metrics() -> None:
    """CSV fieldnames must NOT contain nid, nid_s, mhs, mhs_s, ard, bleu, meteor."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()

    # These should NOT appear in the fieldnames list
    old_metrics = ['"nid"', '"nid_s"', '"mhs"', '"mhs_s"', '"ard"', '"bleu"', '"meteor"']
    for metric in old_metrics:
        assert metric not in source, f"Old metric {metric} still present in runner"


def test_zero_row_uses_ned_keys() -> None:
    """Zero-row rejection dicts must use ned, teds, teds_s keys."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert '"ned": 0.0' in source
    assert '"teds": 0.0' in source
    assert '"teds_s": 0.0' in source


def test_metrics_avg_uses_ned_teds_teds_s() -> None:
    """metrics_avg list must contain exactly ned, teds, teds_s."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    # The metrics list should appear in the source
    assert 'metrics = ["ned", "teds", "teds_s"]' in source


def test_runner_imports_ned_score() -> None:
    """run_parsing_eval must import ned_score (not evaluate_nid or similar)."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert "from doc_bench.metrics.parsing.ned import ned_score" in source


def test_runner_does_not_import_old_metrics() -> None:
    """run_parsing_eval must not import deleted metric modules."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert "from doc_bench.metrics.parsing.mhs import" not in source
    assert "from doc_bench.metrics.parsing.nid import" not in source
    assert "from doc_bench.metrics.parsing.reading_order import" not in source
    assert "from doc_bench.metrics.parsing.text_similarity import" not in source


def test_grade_text_item_zero_row_has_correct_keys(tmp_path) -> None:
    """_grade_text_item zero-row on rejection must have ned, teds, teds_s keys."""
    from doc_bench.runners.run_parsing_eval import _grade_text_item

    output_csv = tmp_path / "out.csv"
    fieldnames = ["query_id", "error", "ned", "teds", "teds_s"]

    with open(output_csv, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        rejection_tracker = MagicMock()
        rejection_tracker.record_rejection = MagicMock()

        outcome = _grade_text_item(
            doc_id="nonexistent_doc",
            query_id="test_query",
            gold_markdown="some gold text",
            predictions_dir=tmp_path,  # Empty dir — prediction missing
            schema_path=tmp_path / "schema.json",
            writer=writer,
            csv_file=csv_file,
            rejection_tracker=rejection_tracker,
        )

    assert outcome == "error"

    # Read back the CSV and verify column names
    with open(output_csv) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert "ned" in row
    assert "teds" in row
    assert "teds_s" in row
    assert "nid" not in row
    assert "mhs" not in row
    assert "bleu" not in row
