"""
Tests for result metadata in results.json.

_compute_sha256, _get_doc_bench_version, _get_dataset_version were private
helpers in the old monolith runner and have been removed. Tests for the
current results.json structure live in test_run_parsing_eval.py.
"""

import json


class TestResultsJsonStructure:
    """results.json summary structure produced by main()."""

    def _run_main(self, tmp_path, monkeypatch):
        import sys

        from doc_bench.runners.run_parsing_eval import load_dataset, main

        preds_dir = tmp_path / "predictions"
        preds_dir.mkdir()
        results_dir = tmp_path / "results"

        for item in load_dataset("ato_bench", root=None):
            pred = {
                "schema_version": "1.0.0",
                "parser_version": "0.0.1",
                "source": {
                    "doc_id": item.doc_id,
                    "filename": f"{item.doc_id}.pdf",
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
            (preds_dir / f"{item.doc_id}.json").write_text(json.dumps(pred))

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
        import pytest

        with pytest.raises(SystemExit):
            main()
        return results_dir

    def test_results_json_has_required_fields(self, tmp_path, monkeypatch):
        results_dir = self._run_main(tmp_path, monkeypatch)
        json_files = list(results_dir.glob("*_results_*.json"))
        assert json_files
        summary = json.loads(json_files[0].read_text())

        assert "dataset" in summary
        assert "parser" in summary
        assert "timestamp" in summary
        assert "csv_file" in summary
        assert "metrics_avg" in summary
        assert "evaluated_samples" in summary
        assert "rejected_samples" in summary

    def test_metrics_avg_uses_ned_similarity(self, tmp_path, monkeypatch):
        results_dir = self._run_main(tmp_path, monkeypatch)
        json_files = list(results_dir.glob("*_results_*.json"))
        summary = json.loads(json_files[0].read_text())

        avg = summary.get("metrics_avg", {})
        assert "ned_similarity" in avg
        assert "ned" not in avg


class TestSmokeTestLabeling:
    """Tests for smoke-test result labeling."""

    def test_smoke_test_results_labeled_bundled(self, tmp_path):
        """Smoke-test results are labeled 'bundled-smoke-stratified'."""
        from click.testing import CliRunner

        from doc_bench.cli.smoke_test import main

        runner = CliRunner()
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()

        import json

        manifest = {
            "dataset_name": "bundled-smoke-stratified",
            "documents": [],
            "count": 0,
        }
        with open(fixtures_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        result = runner.invoke(main, ["--data", str(fixtures_dir)])
        assert result.exit_code == 0
