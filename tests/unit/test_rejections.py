"""
Tests for rejection tracking and reporting (Task Group 6).

Tests the rejected.csv writing with 4 columns: doc_id, reason, source_file, detail.
"""

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from doc_bench.rejections import RejectionReason, format_rejection_detail


class TestRejectionDetailFormatting:
    """Tests for rejection detail message formatting."""

    def test_missing_prediction_detail_empty(self):
        """MISSING_PREDICTION should have empty detail."""
        detail = format_rejection_detail(RejectionReason.MISSING_PREDICTION)
        assert detail == ""

    def test_missing_prediction_detail_with_message_ignored(self):
        """MISSING_PREDICTION should ignore error message."""
        detail = format_rejection_detail(
            RejectionReason.MISSING_PREDICTION, "ignored message"
        )
        assert detail == ""

    def test_invalid_json_detail_includes_message(self):
        """INVALID_JSON should include JSON parse error."""
        detail = format_rejection_detail(
            RejectionReason.INVALID_JSON, "Expecting property name enclosed in double quotes"
        )
        assert "JSON parse error" in detail
        assert "Expecting property name" in detail

    def test_invalid_json_empty_message(self):
        """INVALID_JSON should have default message when none provided."""
        detail = format_rejection_detail(RejectionReason.INVALID_JSON, "")
        assert detail == "Invalid JSON"

    def test_invalid_schema_detail_includes_path(self):
        """INVALID_SCHEMA should include field path and message."""
        detail = format_rejection_detail(
            RejectionReason.INVALID_SCHEMA, "elements[0].bbox: Missing required property 'x0'"
        )
        assert detail == "elements[0].bbox: Missing required property 'x0'"

    def test_evaluation_error_detail_includes_message(self):
        """EVALUATION_ERROR should include exception message."""
        detail = format_rejection_detail(
            RejectionReason.EVALUATION_ERROR, "ZeroDivisionError: division by zero"
        )
        assert detail == "ZeroDivisionError: division by zero"


class TestRejectedCsvWriting:
    """Tests for writing rejected.csv with 4 columns."""

    @pytest.fixture
    def rejection_csv_path(self, tmp_path):
        """Path to rejected.csv in temp directory."""
        return tmp_path / "rejected.csv"

    def test_rejected_csv_has_four_columns(self, rejection_csv_path):
        """rejected.csv should have exactly 4 columns."""
        # Write a sample rejection
        with open(rejection_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["doc_id", "reason", "source_file", "detail"])
            writer.writeheader()
            writer.writerow({
                "doc_id": "test_doc",
                "reason": "MISSING_PREDICTION",
                "source_file": "test_doc.pdf",
                "detail": ""
            })

        # Read back and verify columns
        with open(rejection_csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        assert row["doc_id"] == "test_doc"
        assert row["reason"] == "MISSING_PREDICTION"
        assert row["source_file"] == "test_doc.pdf"
        assert row["detail"] == ""

    def test_rejected_csv_incremental_writing(self, rejection_csv_path):
        """rejected.csv should support incremental writing."""
        fieldnames = ["doc_id", "reason", "source_file", "detail"]

        # Write first rejection
        with open(rejection_csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "doc_id": "doc1",
                "reason": "MISSING_PREDICTION",
                "source_file": "doc1.pdf",
                "detail": ""
            })
            f.flush()

        # Append second rejection
        with open(rejection_csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow({
                "doc_id": "doc2",
                "reason": "INVALID_SCHEMA",
                "source_file": "doc2.pdf",
                "detail": "elements[0]: Missing required field"
            })
            f.flush()

        # Read back and verify
        with open(rejection_csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["doc_id"] == "doc1"
        assert rows[1]["doc_id"] == "doc2"

    def test_rejected_csv_all_reason_types(self, rejection_csv_path):
        """rejected.csv should handle all rejection reason types."""
        fieldnames = ["doc_id", "reason", "source_file", "detail"]

        test_cases = [
            ("doc1", "MISSING_PREDICTION", "doc1.pdf", ""),
            ("doc2", "INVALID_JSON", "doc2.json", "JSON parse error: Unexpected token"),
            ("doc3", "INVALID_SCHEMA", "doc3.pdf", "elements[0].bbox: Missing x0"),
            ("doc4", "EVALUATION_ERROR", "doc4.pdf", "AttributeError: 'NoneType' object has no attribute 'x'"),
        ]

        with open(rejection_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for doc_id, reason, source, detail in test_cases:
                writer.writerow({
                    "doc_id": doc_id,
                    "reason": reason,
                    "source_file": source,
                    "detail": detail
                })

        # Verify all written
        with open(rejection_csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 4
        for i, (doc_id, reason, source, detail) in enumerate(test_cases):
            assert rows[i]["doc_id"] == doc_id
            assert rows[i]["reason"] == reason
            assert rows[i]["source_file"] == source
            assert rows[i]["detail"] == detail

    def test_rejected_csv_handles_special_characters(self, rejection_csv_path):
        """rejected.csv should handle special characters in detail field."""
        fieldnames = ["doc_id", "reason", "source_file", "detail"]

        # Detail with special characters (quotes, commas, newlines)
        special_detail = 'elements[0].text: Error "with, commas" and\n newlines'

        with open(rejection_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "doc_id": "doc_special",
                "reason": "INVALID_SCHEMA",
                "source_file": "doc.pdf",
                "detail": special_detail
            })

        # Read back and verify
        with open(rejection_csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["detail"] == special_detail


class TestRejectionIntegration:
    """Integration tests for rejection tracking with predictions module."""

    def test_missing_prediction_creates_rejection_record(self, tmp_path):
        """Missing prediction should create a rejection record."""
        from doc_bench.predictions import load_prediction

        predictions_dir = tmp_path / "predictions"
        predictions_dir.mkdir()

        rejected_csv = tmp_path / "rejected.csv"

        # Try to load non-existent prediction
        doc_id = "missing_doc"
        prediction = load_prediction(predictions_dir, doc_id)

        assert prediction is None

        # Should create rejection record
        with open(rejected_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["doc_id", "reason", "source_file", "detail"])
            writer.writeheader()
            if prediction is None:
                writer.writerow({
                    "doc_id": doc_id,
                    "reason": RejectionReason.MISSING_PREDICTION.value,
                    "source_file": f"{doc_id}.json",
                    "detail": format_rejection_detail(RejectionReason.MISSING_PREDICTION)
                })

        # Verify
        with open(rejected_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["reason"] == "MISSING_PREDICTION"

    def test_invalid_json_creates_rejection_record(self, tmp_path):
        """Invalid JSON prediction should create a rejection record."""
        from doc_bench.predictions import load_prediction

        predictions_dir = tmp_path / "predictions"
        predictions_dir.mkdir()

        # Create invalid JSON file
        invalid_file = predictions_dir / "invalid_doc.json"
        invalid_file.write_text("{ invalid json }")

        rejected_csv = tmp_path / "rejected.csv"

        # Try to load invalid prediction
        doc_id = "invalid_doc"
        prediction = load_prediction(predictions_dir, doc_id)

        assert prediction is None

        # Should create rejection record
        with open(rejected_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["doc_id", "reason", "source_file", "detail"])
            writer.writeheader()
            if prediction is None:
                # Distinguish between missing and invalid by checking file existence
                source_file = f"{doc_id}.json"
                if not (predictions_dir / source_file).exists():
                    reason = RejectionReason.MISSING_PREDICTION
                else:
                    reason = RejectionReason.INVALID_JSON
                writer.writerow({
                    "doc_id": doc_id,
                    "reason": reason.value,
                    "source_file": source_file,
                    "detail": format_rejection_detail(reason, "JSON decode error")
                })

        # Verify
        with open(rejected_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["reason"] == "INVALID_JSON"
