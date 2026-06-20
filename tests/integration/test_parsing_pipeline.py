"""End-to-end integration tests for parsing eval pipeline."""

import csv
import json
import sys
import time

import pytest


def _valid_prediction(doc_id: str) -> dict:
    return {
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
                "char_span": [0, 4],
                "text": "text",
                "content": {"kind": "text"},
            }
        ],
    }


class TestParsingPipeline:
    """Integration tests for complete parsing evaluation workflow."""

    def _populate_predictions(self, preds_dir, dataset_name):
        from doc_bench.runners.run_parsing_eval import load_dataset

        for item in load_dataset(dataset_name, root=None):
            (preds_dir / f"{item.doc_id}.json").write_text(
                json.dumps(_valid_prediction(item.doc_id))
            )

    def test_full_parsing_eval_with_stub_parser(self, tmp_path, monkeypatch):
        """Test complete parsing eval workflow using bundled fixtures."""
        from doc_bench.runners.run_parsing_eval import main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        self._populate_predictions(preds_dir, "omnidocbench")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc-bench",
                "--dataset",
                "omnidocbench",
                "--predictions",
                str(preds_dir),
                "--output-dir",
                str(results_dir),
            ],
        )

        start_time = time.time()
        with pytest.raises(SystemExit) as exc_info:
            main()
        elapsed = time.time() - start_time

        assert exc_info.value.code == 0
        assert elapsed < 30

    def test_csv_output_generation(self, tmp_path, monkeypatch):
        """CSV output is generated with ned_similarity, teds, teds_s columns."""
        from doc_bench.runners.run_parsing_eval import main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        self._populate_predictions(preds_dir, "dp_bench")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc-bench",
                "--dataset",
                "dp_bench",
                "--predictions",
                str(preds_dir),
                "--output-dir",
                str(results_dir),
            ],
        )

        with pytest.raises(SystemExit):
            main()

        csv_files = list(results_dir.glob("*_results_*.csv"))
        assert csv_files, "No results CSV produced"

        with open(csv_files[0]) as f:
            rows = list(csv.DictReader(f))

        assert rows
        assert "ned_similarity" in rows[0]
        assert "teds" in rows[0]
        assert "query_id" in rows[0]

    def test_html_report_generation(self, tmp_path):
        """HTML report is generated correctly."""
        import pandas as pd

        from doc_bench.reporting.html_summary import generate_summary

        csv_path = tmp_path / "results.csv"
        df = pd.DataFrame(
            {
                "query_id": ["q001", "q002"],
                "question_id": ["text_fidelity", "structure_recall"],
                "score": [0.95, 0.80],
                "label": ["pass", "fail"],
                "error": ["", ""],
            }
        )
        df.to_csv(csv_path, index=False)

        html_path = tmp_path / "summary.html"
        generate_summary(csv_path, html_path)

        assert html_path.exists()
        html = html_path.read_text()
        assert "<html>" in html or "<HTML" in html

    def test_regression_check_with_mock_baseline(self, tmp_path):
        """Regression check works with mock baseline."""
        from doc_bench.reporting.regression_check import check_regression

        baseline_path = tmp_path / "baseline.json"
        baseline_data = {
            "metrics": {
                "text_fidelity": {"score": 0.95, "severity": "major"},
                "structure_recall": {"score": 0.90, "severity": "blocker"},
            }
        }
        baseline_path.write_text(json.dumps(baseline_data))

        current_path = tmp_path / "current.json"
        current_data = {
            "metrics": {
                "text_fidelity": {"score": 0.96, "severity": "major"},
                "structure_recall": {"score": 0.90, "severity": "blocker"},
            }
        }
        current_path.write_text(json.dumps(current_data))
        check_regression(current_path, baseline_path)

        current_path.write_text(
            json.dumps(
                {
                    "metrics": {
                        "text_fidelity": {"score": 0.95, "severity": "major"},
                        "structure_recall": {"score": 0.80, "severity": "blocker"},
                    }
                }
            )
        )
        with pytest.raises(RuntimeError, match="Regression detected"):
            check_regression(current_path, baseline_path)

    @pytest.mark.slow
    def test_pipeline_runtime_under_2_minutes(self, tmp_path, monkeypatch):
        """Complete pipeline runs in under 2 minutes on bundled fixtures."""
        from doc_bench.runners.run_parsing_eval import main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        self._populate_predictions(preds_dir, "omnidocbench")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc-bench",
                "--dataset",
                "omnidocbench",
                "--predictions",
                str(preds_dir),
                "--output-dir",
                str(results_dir),
            ],
        )

        start_time = time.time()
        with pytest.raises(SystemExit) as exc_info:
            main()
        elapsed = time.time() - start_time

        assert exc_info.value.code == 0
        assert elapsed < 120, f"Pipeline took {elapsed:.1f}s, should be under 2 minutes"
