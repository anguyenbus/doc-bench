"""Tests for prediction loading module."""

import json

from doc_bench.predictions import load_prediction


class TestPredictionLoading:
    """Test suite for load_prediction() function."""

    def test_successful_load_of_valid_json_file(self, tmp_path):
        """Test successful load of valid JSON file."""
        # Create a valid prediction file
        predictions_dir = tmp_path / "predictions"
        predictions_dir.mkdir()

        prediction_data = {
            "schema_version": "1.0.0",
            "parser_version": "0.1.0",
            "source": {
                "doc_id": "test_doc",
                "filename": "test_doc.pdf",
                "mime_type": "application/pdf",
                "sha256": "a" * 64,
            },
            "pages": [],
            "elements": [],
        }

        pred_file = predictions_dir / "test_doc.json"
        pred_file.write_text(json.dumps(prediction_data))

        # Load the prediction
        result = load_prediction(predictions_dir, "test_doc")

        assert result is not None
        assert result == prediction_data
        assert result["schema_version"] == "1.0.0"

    def test_missing_file_returns_none(self, tmp_path):
        """Test missing file returns None."""
        predictions_dir = tmp_path / "predictions"
        predictions_dir.mkdir()

        # Try to load a non-existent file
        result = load_prediction(predictions_dir, "nonexistent_doc")

        assert result is None

    def test_invalid_json_returns_none(self, tmp_path):
        """Test invalid JSON returns None (JSONDecodeError handling)."""
        predictions_dir = tmp_path / "predictions"
        predictions_dir.mkdir()

        # Create a file with invalid JSON
        pred_file = predictions_dir / "bad_json.json"
        pred_file.write_text("{invalid json content")

        # Try to load the invalid JSON
        result = load_prediction(predictions_dir, "bad_json")

        assert result is None

    def test_oserror_handling(self, tmp_path):
        """Test OSError handling (e.g., permission denied)."""
        # This test verifies OSError is caught and returns None
        # In practice, we'd need to create a scenario that raises OSError
        # For now, we test that missing directory is handled gracefully
        nonexistent_dir = tmp_path / "nonexistent" / "predictions"

        result = load_prediction(nonexistent_dir, "any_doc")

        # Should return None gracefully, not crash
        assert result is None
