"""
Tests for test file deletion validation.

Verifies that deleted RAG/replay/observability test files are gone,
that deleted parsing metric test files are gone, and that kept parsing
tests still exist.
"""

from pathlib import Path


def test_deleted_replay_tests_directory_not_exists() -> None:
    """Test that replay test directory is deleted."""
    replay_path = Path(__file__).parent.parent / "replay"
    assert not replay_path.exists(), f"Replay directory should be deleted: {replay_path}"


def test_deleted_observability_tests_directory_not_exists() -> None:
    """Test that observability test directory is deleted."""
    obs_path = Path(__file__).parent.parent / "observability"
    assert not obs_path.exists(), f"Observability directory should be deleted: {obs_path}"


def test_deleted_experiments_tests_directory_not_exists() -> None:
    """Test that experiments test directory is deleted."""
    exp_path = Path(__file__).parent.parent / "experiments"
    assert not exp_path.exists(), f"Experiments directory should be deleted: {exp_path}"


def test_deleted_phoenix_test_files_not_exist() -> None:
    """Test that Phoenix-specific test files are deleted."""
    tests_dir = Path(__file__).parent.parent

    phoenix_files = [
        tests_dir / "integration" / "test_phoenix_native_phase1.py",
        tests_dir / "integration" / "test_phoenix_native_phase3.py",
        tests_dir / "integration" / "test_phoenix_native_phase5.py",
        tests_dir / "integration" / "test_phoenix_native_phase6.py",
        tests_dir / "integration" / "test_phoenix_experiments_api.py",
        tests_dir / "integration" / "test_phoenix_native_integration.py",
        tests_dir / "unit" / "test_phoenix_eval_formatting.py",
        tests_dir / "unit" / "test_phoenix_dataset_extraction.py",
        tests_dir / "unit" / "test_phoenix_client_datasets.py",
        tests_dir / "unit" / "test_phoenix_auto_instrumentation.py",
        tests_dir / "unit" / "test_phoenix_native_feature_flag.py",
        tests_dir / "adapters" / "test_phoenix_eval_adapter.py",
    ]

    for file_path in phoenix_files:
        assert not file_path.exists(), f"Phoenix test file should be deleted: {file_path}"


def test_deleted_rag_test_files_not_exist() -> None:
    """Test that RAG-specific test files are deleted."""
    tests_dir = Path(__file__).parent.parent

    rag_files = [
        tests_dir / "integration" / "test_rag_pipeline.py",
        tests_dir / "integration" / "test_deepeval_integration.py",
        tests_dir / "unit" / "test_rag_adapter.py",
        tests_dir / "unit" / "test_deepeval_adapter.py",
        tests_dir / "unit" / "test_stub_rag.py",
        tests_dir / "unit" / "test_deepeval_trace_suppression.py",
        tests_dir / "unit" / "test_deepeval_config.py",
        tests_dir / "unit" / "test_deepeval_async.py",
        tests_dir / "unit" / "test_run_rag_eval.py",
        tests_dir / "unit" / "test_legal_rag_bench_loader.py",
        tests_dir / "unit" / "test_legal_rag_bench_config.py",
        tests_dir / "unit" / "test_legal_rag_bench_schema.py",
        tests_dir / "unit" / "test_eval_questions.py",
    ]

    for file_path in rag_files:
        assert not file_path.exists(), f"RAG test file should be deleted: {file_path}"


def test_deleted_parsing_metric_test_files_not_exist() -> None:
    """Test that deleted parsing metric test files are gone.

    NOTE: test_docling_eval_integration.py was also deleted because it tested
    only the removed metrics (ard_score, layout_map_score, bleu_score, meteor_score).
    """
    tests_dir = Path(__file__).parent.parent

    deleted_test_files = [
        tests_dir / "unit" / "test_nid.py",
        tests_dir / "unit" / "test_text_similarity.py",
        tests_dir / "unit" / "test_text_fidelity.py",
        tests_dir / "unit" / "test_ard.py",
        tests_dir / "unit" / "test_reading_order.py",
        tests_dir / "unit" / "test_structure_recall.py",
        tests_dir / "unit" / "test_layout_map.py",
        # Integration test that tested only deleted metrics:
        tests_dir / "integration" / "test_docling_eval_integration.py",
    ]

    for file_path in deleted_test_files:
        assert not file_path.exists(), f"Deleted metric test file should be gone: {file_path}"


def test_kept_parsing_tests_exist() -> None:
    """Test that parsing-specific test files still exist.

    NOTE: test_ned.py is the canonical NED metric test (replaces the deleted
    metric tests). test_docling_eval_integration.py was removed because it
    tested only deleted metrics.
    """
    tests_dir = Path(__file__).parent.parent

    parsing_files = [
        tests_dir / "integration" / "test_parsing_pipeline.py",
        tests_dir / "unit" / "test_ned.py",
        tests_dir / "unit" / "test_table_teds.py",
        tests_dir / "unit" / "test_dp_bench_loader.py",
        tests_dir / "unit" / "test_config.py",
        tests_dir / "unit" / "test_schema_validation.py",
    ]

    for file_path in parsing_files:
        assert file_path.exists(), f"Parsing test file should exist: {file_path}"
