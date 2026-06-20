"""
Tests for the run_parsing_eval.py schema contract.

Verifies that the runner emits ned_similarity (not ned) and does not
emit old metric columns (nid, nid_s, mhs, mhs_s, ard, bleu, meteor).
"""

from pathlib import Path


def test_csv_fieldnames_contain_ned_similarity_teds() -> None:
    """CSV fieldnames must contain ned_similarity, teds, teds_s."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert '"ned_similarity"' in source
    assert '"teds"' in source
    assert '"teds_s"' in source


def test_csv_fieldnames_do_not_contain_plain_ned() -> None:
    """CSV fieldnames must NOT contain a bare 'ned' column (it's ned_similarity now)."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    # ned_similarity is fine; a bare "ned" fieldname is not
    assert '"ned"' not in source, "Bare 'ned' column still present — should be ned_similarity"


def test_csv_fieldnames_do_not_contain_old_metrics() -> None:
    """CSV fieldnames must NOT contain nid, nid_s, mhs, mhs_s, ard, bleu, meteor."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    for old in ['"nid"', '"nid_s"', '"mhs"', '"mhs_s"', '"ard"', '"bleu"', '"meteor"']:
        assert old not in source, f"Old metric {old} still present in runner"


def test_metrics_avg_uses_ned_similarity() -> None:
    """metrics list in main() must reference ned_similarity, not ned."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert '"ned_similarity"' in source
    assert 'metrics = ["ned",' not in source


def test_runner_imports_ned_score() -> None:
    """run_parsing_eval must import ned_score."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert "from doc_bench.metrics.parsing.ned import ned_score" in source


def test_runner_does_not_import_old_metrics() -> None:
    """run_parsing_eval must not import deleted metric modules."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert "from doc_bench.metrics.parsing.mhs import" not in source
    assert "from doc_bench.metrics.parsing.nid import" not in source
    assert "from doc_bench.metrics.parsing.reading_order import" not in source
    assert "from doc_bench.metrics.parsing.text_similarity import" not in source


def test_zero_row_uses_ned_similarity_key() -> None:
    """Rejection zero-rows must use ned_similarity key."""
    import doc_bench.runners.run_parsing_eval as module

    source = Path(module.__file__).read_text()
    assert '"ned_similarity": 0.0' in source
    assert '"teds": 0.0' in source
    assert '"teds_s": 0.0' in source
