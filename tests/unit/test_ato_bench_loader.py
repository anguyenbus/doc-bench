"""Tests for the ATO-Bench loader against the bundled fixtures."""

import json
from pathlib import Path

import doc_bench
from doc_bench.datasets import load_ato_bench

BUNDLED_FIXTURES = Path(doc_bench.__file__).parent / "fixtures"


def test_load_ato_bench_yields_bundled_docs():
    """The loader yields each ATO doc from the bundled manifest with combined gold."""
    items = list(load_ato_bench(BUNDLED_FIXTURES))

    manifest = json.loads((BUNDLED_FIXTURES / "manifest.json").read_text())
    expected_ids = [e["doc_id"] for e in manifest["ato_bench"]]

    assert [doc_id for doc_id, _ in items] == expected_ids
    assert items, "expected at least one bundled ATO document"


def test_load_ato_bench_combines_pages_in_order():
    """Combined gold text contains content from all of a document's pages."""
    items = dict(load_ato_bench(BUNDLED_FIXTURES))
    doc_id, gold = next(iter(items.items()))

    # The bundled doc is the 2-page 1371-6.1997 income tax return.
    assert doc_id == "1371-6.1997"
    assert gold  # non-empty combined gold
    # Page 1 begins the income tax return; page 2 mentions "Page 2".
    assert "Income Tax Return" in gold
    assert "Page 2" in gold


def test_load_ato_bench_missing_manifest(tmp_path):
    """A missing manifest raises FileNotFoundError."""
    try:
        list(load_ato_bench(tmp_path))
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError for missing manifest.json")


def test_load_dataset_routes_ato_bench_to_bundled_fixtures():
    """load_dataset('ato_bench', root=None) yields bundled fixture GoldItems."""
    from doc_bench.runners.run_parsing_eval import GoldItem, load_dataset

    items = list(load_dataset("ato_bench", root=None))
    assert len(items) >= 1
    for item in items:
        assert isinstance(item, GoldItem)
    assert any(item.doc_id == "1371-6.1997" for item in items)
