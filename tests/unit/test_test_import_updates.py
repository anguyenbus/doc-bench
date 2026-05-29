"""
Tests for test import updates validation.

Verifies that kept tests use new package name imports.
"""

from pathlib import Path


def test_parsing_integration_tests_updated() -> None:
    """Test that parsing integration tests use doc_bench imports."""
    tests_dir = Path(__file__).parent.parent

    # Check test_parsing_pipeline.py
    parsing_pipeline = tests_dir / "integration" / "test_parsing_pipeline.py"
    if parsing_pipeline.exists():
        content = parsing_pipeline.read_text()
        # Should contain doc_bench imports, not eval_harness
        assert "from doc_bench" in content or "import doc_bench" in content, \
            "test_parsing_pipeline.py should use doc_bench imports"
        assert "eval_harness" not in content, \
            "test_parsing_pipeline.py should not contain eval_harness imports"

    # Check test_docling_eval_integration.py
    docling_integration = tests_dir / "integration" / "test_docling_eval_integration.py"
    if docling_integration.exists():
        content = docling_integration.read_text()
        # Should contain doc_bench imports, not eval_harness
        assert "from doc_bench" in content or "import doc_bench" in content, \
            "test_docling_eval_integration.py should use doc_bench imports"
        assert "eval_harness" not in content, \
            "test_docling_eval_integration.py should not contain eval_harness imports"


def test_parsing_unit_tests_updated() -> None:
    """Test that parsing unit tests use doc_bench imports."""
    tests_dir = Path(__file__).parent.parent

    parsing_test_files = [
        "unit/test_nid.py",
        "unit/test_table_teds.py",
        "unit/test_text_similarity.py",
        "unit/test_reading_order.py",
        "unit/test_structure_recall.py",
        "unit/test_dp_bench_loader.py",
        "unit/test_config.py",
        "unit/test_parser_adapter.py",
    ]

    for test_file in parsing_test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            content = test_path.read_text()
            # Should not contain eval_harness imports
            assert "eval_harness" not in content or "test eval_harness" in content.lower(), \
                f"{test_file} should not contain eval_harness imports"
