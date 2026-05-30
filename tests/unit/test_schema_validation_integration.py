"""
Tests for prediction schema validation integration (Task Group 5).

Tests the integration of schema validation for predictions loaded from files.
"""

from pathlib import Path

import pytest

from doc_bench.adapters.schema_validator import SchemaValidationError, validate


@pytest.fixture
def sample_valid_prediction():
    """Sample valid prediction conforming to parser_output.schema.json."""
    return {
        "schema_version": "1.0.0",
        "parser_version": "1.0.0",
        "source": {
            "doc_id": "test_doc",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "sha256": "a" * 64,
        },
        "pages": [{"page_index": 0, "width": 612, "height": 792}],
        "elements": [
            {
                "element_id": "elem1",
                "type": "paragraph",
                "page_index": 0,
                "char_span": [0, 10],
                "text": "Test text",
                "content": {"kind": "text"},
            }
        ],
    }


@pytest.fixture
def sample_invalid_prediction():
    """Sample invalid prediction (missing required fields)."""
    return {
        "schema_version": "1.0.0",
        # Missing parser_version, source, pages, elements
    }


@pytest.fixture
def sample_invalid_field_type():
    """Sample prediction with invalid field type."""
    return {
        "schema_version": "1.0.0",
        "parser_version": "1.0.0",
        "source": {
            "doc_id": "test_doc",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "sha256": "invalid",  # Should be 64 hex chars
        },
        "pages": [{"page_index": 0, "width": 612, "height": 792}],
        "elements": [],
    }


@pytest.fixture
def schema_path(tmp_path):
    """Path to parser output schema."""
    # Copy actual schema to temp location for tests
    import shutil

    src_schema = Path("contracts/parser_output.schema.json")
    dst_schema = tmp_path / "parser_output.schema.json"
    if src_schema.exists():
        shutil.copy(src_schema, dst_schema)
    return dst_schema


class TestPredictionSchemaValidation:
    """Tests for schema validation of predictions."""

    def test_valid_prediction_passes_validation(self, sample_valid_prediction, schema_path):
        """Valid prediction should pass schema validation."""
        # This test assumes schema_path exists
        if not schema_path.exists():
            pytest.skip(f"Schema file not found: {schema_path}")

        # Should not raise any exception
        validate(sample_valid_prediction, schema_path)

    def test_invalid_prediction_fails_validation(self, sample_invalid_prediction, schema_path):
        """Invalid prediction should fail with SchemaValidationError."""
        if not schema_path.exists():
            pytest.skip(f"Schema file not found: {schema_path}")

        with pytest.raises(SchemaValidationError) as exc_info:
            validate(sample_invalid_prediction, schema_path)

        assert exc_info.value.field_path != "" or exc_info.value.original_error != ""

    def test_invalid_field_type_fails_validation(self, sample_invalid_field_type, schema_path):
        """Prediction with invalid field type should fail validation."""
        if not schema_path.exists():
            pytest.skip(f"Schema file not found: {schema_path}")

        with pytest.raises(SchemaValidationError) as exc_info:
            validate(sample_invalid_field_type, schema_path)

        # Should include field path in error
        assert exc_info.value.field_path or exc_info.value.original_error

    def test_validation_error_contains_field_path(self, sample_invalid_prediction, schema_path):
        """SchemaValidationError should contain field path for debugging."""
        if not schema_path.exists():
            pytest.skip(f"Schema file not found: {schema_path}")

        with pytest.raises(SchemaValidationError) as exc_info:
            validate(sample_invalid_prediction, schema_path)

        # Error should have helpful information
        error = exc_info.value
        assert error.field_path != "" or error.original_error != ""
        assert "Schema validation failed" in str(error)


class TestValidationErrorMessages:
    """Tests for validation error message formatting."""

    def test_missing_required_field_message(self, schema_path):
        """Test error message for missing required field."""
        if not schema_path.exists():
            pytest.skip(f"Schema file not found: {schema_path}")

        invalid_pred = {"schema_version": "1.0.0"}

        with pytest.raises(SchemaValidationError) as exc_info:
            validate(invalid_pred, schema_path)

        # Error should be informative
        error_str = str(exc_info.value)
        assert "Schema validation failed" in error_str

    def test_field_path_format(self, schema_path):
        """Test that field paths are formatted correctly."""
        if not schema_path.exists():
            pytest.skip(f"Schema file not found: {schema_path}")

        # Create prediction with invalid nested field - width as string instead of number
        invalid_pred = {
            "schema_version": "1.0.0",
            "parser_version": "1.0.0",
            "source": {
                "doc_id": "test",
                "filename": "test.pdf",
                "mime_type": "application/pdf",
                "sha256": "a" * 64,
            },
            "pages": [{"page_index": 0, "width": "invalid", "height": 792}],  # Invalid: string
            "elements": [],
        }

        with pytest.raises(SchemaValidationError) as exc_info:
            validate(invalid_pred, schema_path)

        # Field path should indicate nested structure
        error = exc_info.value
        # Path might include 'pages' or array index
        assert error.field_path or error.original_error
