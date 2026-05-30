"""
Tests for schema cleanup validation.

Verifies that RAG schemas are deleted and kept/created schemas exist.
"""

from pathlib import Path


def test_deleted_rag_schemas_not_exist() -> None:
    """Test that RAG-related schemas are deleted."""
    contracts_dir = Path(__file__).parent.parent.parent / "contracts"

    deleted_schemas = [
        contracts_dir / "rag_query_output.schema.json",
        contracts_dir / "eval_questions.schema.json",
        contracts_dir / "legal_rag_bench_query_output.schema.json",
    ]

    for schema_path in deleted_schemas:
        assert not schema_path.exists(), f"Schema should be deleted: {schema_path}"


def test_kept_parser_output_schema_exists() -> None:
    """Test that parser_output schema still exists."""
    contracts_dir = Path(__file__).parent.parent.parent / "contracts"
    parser_output_schema = contracts_dir / "parser_output.schema.json"

    assert parser_output_schema.exists(), "parser_output.schema.json should exist"

    # Verify it's valid JSON
    import json

    with open(parser_output_schema) as f:
        schema = json.load(f)

    assert schema is not None
    assert "$schema" in schema


def test_results_v1_schema_exists() -> None:
    """Test that results_v1 schema was created."""
    contracts_dir = Path(__file__).parent.parent.parent / "contracts"
    results_schema = contracts_dir / "results_v1.schema.json"

    assert results_schema.exists(), "results_v1.schema.json should exist"

    # Verify it's valid JSON
    import json

    with open(results_schema) as f:
        schema = json.load(f)

    assert schema is not None
    assert "$schema" in schema

    # Check for expected fields for CSV output
    if "properties" in schema:
        properties = schema["properties"]
        # Should have query_id and metrics fields
        assert "query_id" in properties or "query_id" in str(properties)
