"""
Tests for smoke-test CLI command.

Tests smoke test mode with bundled fixtures, per-type breakdown reporting,
and pass/fail criteria based on rejections.
"""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_fixtures(tmp_path):
    """Create mock fixture files."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Create mock manifest.json
    manifest = {
        "dataset_name": "bundled-smoke-stratified",
        "documents": [
            {"doc_id": "doc1", "file": "doc1.pdf", "doc_type": "academic_literature"},
            {"doc_id": "doc2", "file": "doc2.pdf", "doc_type": "research_report"},
            {"doc_id": "doc3", "file": "doc3.pdf", "doc_type": "exam_paper"},
            {"doc_id": "doc4", "file": "doc4.pdf", "doc_type": "colorful_textbook"},
            {"doc_id": "doc5", "file": "doc5.pdf", "doc_type": "book"},
            {"doc_id": "doc6", "file": "doc6.pdf", "doc_type": "PPT2PDF"},
        ],
        "count": 6,
    }

    with open(fixtures_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    # Create empty PDF files
    for doc in manifest["documents"]:
        (fixtures_dir / doc["file"]).write_bytes(b"%PDF-1.4 mock pdf")

    return fixtures_dir


@pytest.fixture
def mock_predictions(tmp_path):
    """Create mock prediction files."""
    pred_dir = tmp_path / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)

    # Create mock prediction files for each document
    for i in range(1, 7):
        pred_file = pred_dir / f"doc{i}.json"
        pred_data = {
            "doc_id": f"doc{i}",
            "elements": [
                {"type": "header", "text": "Test Header"},
                {"type": "paragraph", "text": "Test paragraph"},
            ],
        }
        with open(pred_file, "w") as f:
            json.dump(pred_data, f)

    return pred_dir


class TestSmokeTestBasic:
    """Tests for basic smoke test functionality."""

    @patch("doc_bench.cli.smoke_test._run_evaluation")
    def test_smoke_test_runs_against_fixtures(self, mock_run, runner, mock_fixtures):
        """Test smoke test runs against bundled fixtures."""
        from doc_bench.cli.smoke_test import main

        # Mock successful evaluation
        mock_run.return_value = {
            "total_docs": 6,
            "rejected_docs": 0,
            "by_doc_type": {
                "academic_literature": {"total": 1, "rejected": 0},
                "research_report": {"total": 1, "rejected": 0},
            },
            "by_element_category": {
                "header": {"total": 6, "rejected": 0},
                "paragraph": {"total": 6, "rejected": 0},
            },
        }

        result = runner.invoke(main, ["--data", str(mock_fixtures)])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_smoke_test_passes_with_low_rejections(self, runner, mock_fixtures, mock_predictions):
        """Test smoke test passes when <10% rejections."""
        from doc_bench.cli.smoke_test import main

        with patch("doc_bench.cli.smoke_test._run_evaluation") as mock_run:
            # Mock evaluation with 5% rejections (1/20 docs)
            mock_run.return_value = {
                "total_docs": 20,
                "rejected_docs": 1,
                "by_doc_type": {
                    "academic_literature": {"total": 10, "rejected": 0},
                    "research_report": {"total": 10, "rejected": 1},
                },
                "by_element_category": {
                    "header": {"total": 20, "rejected": 0},
                    "paragraph": {"total": 20, "rejected": 0},
                },
            }

            result = runner.invoke(
                main, ["--data", str(mock_fixtures), "--predictions", str(mock_predictions)]
            )

            # Should pass with exit code 0 (5% < 10% threshold)
            assert result.exit_code == 0
            assert "PASS" in result.output or "passed" in result.output.lower()

    def test_smoke_test_fails_with_high_rejections(self, runner, mock_fixtures, mock_predictions):
        """Test smoke test fails when >=10% rejections."""
        from doc_bench.cli.smoke_test import main

        with patch("doc_bench.cli.smoke_test._run_evaluation") as mock_run:
            # Mock evaluation with 15% rejections (3/20 docs)
            mock_run.return_value = {
                "total_docs": 20,
                "rejected_docs": 3,
                "by_doc_type": {
                    "academic_literature": {"total": 10, "rejected": 2},
                    "research_report": {"total": 10, "rejected": 1},
                },
                "by_element_category": {
                    "header": {"total": 20, "rejected": 1},
                    "paragraph": {"total": 20, "rejected": 2},
                },
            }

            result = runner.invoke(
                main, ["--data", str(mock_fixtures), "--predictions", str(mock_predictions)]
            )

            # Should fail with non-zero exit code (15% >= 10% threshold)
            assert result.exit_code != 0
            assert "FAIL" in result.output or "failed" in result.output.lower()

    @patch("doc_bench.cli.smoke_test._run_evaluation")
    def test_smoke_test_reports_per_type_breakdown(self, mock_run, runner, mock_fixtures):
        """Test smoke test reports per-type breakdown."""
        from doc_bench.cli.smoke_test import main

        # Use low rejection rate to pass the test
        mock_run.return_value = {
            "total_docs": 6,
            "rejected_docs": 0,  # 0% to pass threshold
            "by_doc_type": {
                "academic_literature": {"total": 3, "rejected": 0},
                "research_report": {"total": 3, "rejected": 0},
            },
            "by_element_category": {
                "header": {"total": 6, "rejected": 0},
                "paragraph": {"total": 6, "rejected": 0},
            },
        }

        result = runner.invoke(main, ["--data", str(mock_fixtures)])

        assert result.exit_code == 0
        # Should show document type breakdown
        assert "academic_literature" in result.output
        assert "research_report" in result.output
        # Should show element category breakdown
        assert "header" in result.output or "paragraph" in result.output

    @patch("doc_bench.cli.smoke_test._run_evaluation")
    def test_smoke_test_respects_data_override(self, mock_run, runner, tmp_path):
        """Test smoke test respects --data override for custom fixtures."""
        from doc_bench.cli.smoke_test import main

        custom_fixtures = tmp_path / "custom_fixtures"
        custom_fixtures.mkdir()

        mock_run.return_value = {
            "total_docs": 0,
            "rejected_docs": 0,
            "by_doc_type": {},
            "by_element_category": {},
        }

        result = runner.invoke(main, ["--data", str(custom_fixtures)])

        assert result.exit_code == 0
        # Verify custom path was used
        call_args = mock_run.call_args
        assert custom_fixtures in call_args[1].values() or str(custom_fixtures) in str(call_args)

    @patch("doc_bench.cli.smoke_test._run_evaluation")
    def test_smoke_test_global_guard(self, mock_run, runner, mock_fixtures):
        """Test smoke test global guard: fail if both doc type AND element category >10%."""
        from doc_bench.cli.smoke_test import main

        # Mock evaluation where both doc type and element category exceed 10%
        mock_run.return_value = {
            "total_docs": 20,
            "rejected_docs": 3,
            "by_doc_type": {
                "academic_literature": {"total": 10, "rejected": 2},  # 20%
                "research_report": {"total": 10, "rejected": 1},
            },
            "by_element_category": {
                "header": {"total": 20, "rejected": 3},  # 15%
                "paragraph": {"total": 20, "rejected": 0},
            },
        }

        result = runner.invoke(main, ["--data", str(mock_fixtures)])

        # Should fail because both doc type AND element category have >10% rejections
        assert result.exit_code != 0
        assert "FAIL" in result.output or "failed" in result.output.lower()
