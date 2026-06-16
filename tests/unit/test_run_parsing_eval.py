"""Tests for the refactored run_parsing_eval grading pipeline."""

import csv
import json
from pathlib import Path

import pytest

from doc_bench.runners.run_parsing_eval import GoldItem, _grade, load_dataset


class TestGoldItem:
    """GoldItem dataclass contract."""

    def test_construction(self):
        g = GoldItem(doc_id="foo", text="hello", html_tables=[])
        assert g.doc_id == "foo"
        assert g.text == "hello"
        assert g.html_tables == []

    def test_immutable(self):
        from dataclasses import FrozenInstanceError

        g = GoldItem(doc_id="x", text="y", html_tables=[])
        with pytest.raises(FrozenInstanceError):
            g.doc_id = "z"  # frozen=True


class TestGrade:
    """_grade() returns (ned_similarity, teds, teds_s) tuples in [0, 1]."""

    def test_perfect_match_ned(self):
        gold = GoldItem(doc_id="d", text="hello world", html_tables=[])
        ned_sim, teds, teds_s = _grade(gold, "hello world")
        assert ned_sim == pytest.approx(1.0)

    def test_empty_pred_returns_zeros(self):
        gold = GoldItem(doc_id="d", text="hello world", html_tables=[])
        ned_sim, teds, teds_s = _grade(gold, "")
        assert ned_sim == pytest.approx(0.0)

    def test_all_values_in_unit_interval(self):
        gold = GoldItem(doc_id="d", text="some text here", html_tables=[])
        for val in _grade(gold, "some partial text"):
            assert 0.0 <= val <= 1.0

    def test_equations_stripped_from_prediction_before_ned(self):
        gold = GoldItem(doc_id="d", text="hello world", html_tables=[])
        # Prediction has extra LaTeX that should be stripped before comparison
        ned_eq, _, _ = _grade(gold, "hello world $x^2 + y^2 = z^2$")
        ned_clean, _, _ = _grade(gold, "hello world")
        # Stripping equations should make scores closer
        assert ned_eq >= ned_clean - 0.1  # not dramatically worse

    def test_html_tables_used_for_teds_when_present(self):
        html_table = "<table><tr><td>A</td><td>B</td></tr></table>"
        gold = GoldItem(doc_id="d", text="", html_tables=[html_table])
        pred_md = "| A | B |\n| --- | --- |\n"
        ned_sim, teds, teds_s = _grade(gold, pred_md)
        assert teds > 0.0


class TestLoadDatasetBundled:
    """load_dataset() works from bundled fixtures when root=None."""

    def test_ato_bench_bundled_yields_gold_items(self):
        items = list(load_dataset("ato_bench", root=None))
        assert len(items) >= 1
        for item in items:
            assert isinstance(item, GoldItem)
            assert item.doc_id
            assert item.text

    def test_dp_bench_bundled_yields_gold_items(self):
        items = list(load_dataset("dp_bench", root=None))
        assert len(items) >= 1
        for item in items:
            assert isinstance(item, GoldItem)
            assert item.doc_id

    def test_omnidocbench_bundled_yields_gold_items(self):
        items = list(load_dataset("omnidocbench", root=None))
        assert len(items) >= 1
        for item in items:
            assert isinstance(item, GoldItem)
            assert item.doc_id

    def test_query_id_is_doc_id_not_positional(self):
        # All datasets should use real doc stems, never "dataset_0" etc.
        for dataset in ("ato_bench", "dp_bench", "omnidocbench"):
            for item in load_dataset(dataset, root=None):
                assert not item.doc_id.startswith(f"{dataset}_"), (
                    f"Positional query_id leaked into {dataset}: {item.doc_id}"
                )


class TestMainCLI:
    """main() integration smoke tests via bundled fixtures."""

    def _make_prediction(self, tmp_path: Path, doc_id: str) -> None:
        pred = {
            "schema_version": "1.0.0",
            "parser_version": "0.0.1",
            "source": {
                "doc_id": doc_id,
                "filename": f"{doc_id}.pdf",
                "mime_type": "application/pdf",
                "sha256": "a" * 64,
            },
            "pages": [{"page_index": 0, "width": 612.0, "height": 792.0}],
            "elements": [
                {
                    "element_id": "e1",
                    "type": "paragraph",
                    "page_index": 0,
                    "char_span": [0, 11],
                    "text": "sample text",
                    "content": {"kind": "text"},
                }
            ],
        }
        (tmp_path / f"{doc_id}.json").write_text(json.dumps(pred))

    def test_grading_without_config_file(self, tmp_path, monkeypatch):
        """main() must succeed without eval_config.yaml when using bundled fixtures."""
        import sys

        from doc_bench.runners.run_parsing_eval import main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        # Provide predictions for all bundled ato_bench docs
        for item in load_dataset("ato_bench", root=None):
            self._make_prediction(preds_dir, item.doc_id)

        monkeypatch.chdir(tmp_path)  # no eval_config.yaml here
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc-bench",
                "--dataset",
                "ato_bench",
                "--predictions",
                str(preds_dir),
                "--output-dir",
                str(results_dir),
            ],
        )

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_csv_uses_ned_similarity_column(self, tmp_path, monkeypatch):
        """CSV output must have ned_similarity column, not ned."""
        import sys

        from doc_bench.runners.run_parsing_eval import main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        for item in load_dataset("ato_bench", root=None):
            self._make_prediction(preds_dir, item.doc_id)

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc-bench",
                "--dataset",
                "ato_bench",
                "--predictions",
                str(preds_dir),
                "--output-dir",
                str(results_dir),
            ],
        )

        with pytest.raises(SystemExit):
            main()

        csv_files = list(results_dir.glob("*_results_*.csv"))
        assert csv_files, "No results CSV output produced"
        with open(csv_files[0]) as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

        assert "ned_similarity" in fieldnames
        assert "ned" not in fieldnames

    def test_csv_query_id_matches_doc_id(self, tmp_path, monkeypatch):
        """CSV query_id must be the doc stem, not a positional index."""
        import sys

        from doc_bench.runners.run_parsing_eval import main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        bundled = list(load_dataset("ato_bench", root=None))
        for item in bundled:
            self._make_prediction(preds_dir, item.doc_id)

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc-bench",
                "--dataset",
                "ato_bench",
                "--predictions",
                str(preds_dir),
                "--output-dir",
                str(results_dir),
            ],
        )

        with pytest.raises(SystemExit):
            main()

        csv_files = list(results_dir.glob("*_results_*.csv"))
        with open(csv_files[0]) as f:
            rows = list(csv.DictReader(f))

        actual_ids = {r["query_id"] for r in rows if r.get("error") == ""}
        expected_ids = {item.doc_id for item in bundled}
        assert actual_ids == expected_ids
