"""
Tests for schema cleanup validation.

Verifies that RAG schemas are deleted and kept/created schemas exist.
"""

from pathlib import Path


def test_deleted_rag_schemas_not_exist() -> None:
    """Test that RAG-related schemas (and the old contracts/ dir) are deleted.

    The legacy contracts/ directory was removed entirely; schemas now live
    under src/doc_bench/fixtures/. These guards fail loudly if any removed RAG
    schema reappears in either location.
    """
    repo_root = Path(__file__).parent.parent.parent
    contracts_dir = repo_root / "contracts"
    fixtures_dir = repo_root / "src" / "doc_bench" / "fixtures"

    assert not contracts_dir.exists(), f"Legacy contracts/ dir should be deleted: {contracts_dir}"

    rag_schema_names = [
        "rag_query_output.schema.json",
        "eval_questions.schema.json",
        "legal_rag_bench_query_output.schema.json",
    ]

    for name in rag_schema_names:
        assert not (contracts_dir / name).exists(), f"Schema should be deleted: {name}"
        assert not (fixtures_dir / name).exists(), f"Schema should be deleted: {name}"


def test_kept_parser_output_schema_exists() -> None:
    """Test that parser_output schema exists at its current fixtures location."""
    repo_root = Path(__file__).parent.parent.parent
    parser_output_schema = (
        repo_root / "src" / "doc_bench" / "fixtures" / "parser_output.schema.json"
    )

    assert parser_output_schema.exists(), "parser_output.schema.json should exist"

    # Verify it's valid JSON
    import json

    with open(parser_output_schema) as f:
        schema = json.load(f)

    assert schema is not None
    assert "$schema" in schema


def test_results_v1_schema_not_exist() -> None:
    """Test that the RAG-era results_v1 schema stays absent.

    results_v1.schema.json was a RAG-era CSV-output schema (query_id/metrics);
    it does not exist in the current parsing-only layout. This guard fails
    loudly if it is reintroduced in either the legacy contracts/ dir or the
    current fixtures dir.
    """
    repo_root = Path(__file__).parent.parent.parent
    legacy_path = repo_root / "contracts" / "results_v1.schema.json"
    fixtures_path = repo_root / "src" / "doc_bench" / "fixtures" / "results_v1.schema.json"

    assert not legacy_path.exists(), f"results_v1 schema should stay absent: {legacy_path}"
    assert not fixtures_path.exists(), f"results_v1 schema should stay absent: {fixtures_path}"
