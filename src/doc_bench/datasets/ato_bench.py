"""
ATO-Bench loader.

ATO-Bench contains multi-page Australian Tax Office form PDFs with page-level
ground-truth annotations in OmniDocBench ``layout_dets`` format. Unlike the full
public benchmarks, ATO-Bench ground truth is consumed from the bundled fixture
layout: a ``manifest.json`` lists each document and its per-page annotation files.

For grading we combine a document's per-page gold text into one document-level
gold string, mirroring how the docling-baseline ATO runner scores ATO documents.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def _extract_page_gold_text(page: dict[str, Any]) -> str:
    """
    Concatenate a page's ``layout_dets`` text in reading order.

    Args:
        page: A single OmniDocBench-format page dict with a ``layout_dets`` array.

    Returns:
        The page's detections' text joined in ``order`` order.

    """

    def sort_key(det: dict[str, Any]) -> float:
        order = det.get("order")
        return float("inf") if order is None else order

    texts = [
        det.get("text", "")
        for det in sorted(page.get("layout_dets", []), key=sort_key)
        if det.get("text", "")
    ]
    return " ".join(texts)


def load_ato_bench(root: Path) -> Iterator[tuple[str, str]]:
    """
    Yield ``(doc_id, gold_text)`` for each ATO-Bench document under ``root``.

    Args:
        root: Directory containing ``manifest.json`` and an ``ato_bench/`` folder
            of per-page annotation files (the bundled fixture layout).

    Yields:
        ``(doc_id, gold_text)`` where ``gold_text`` is the document's per-page
        gold text combined in page order.

    Raises:
        FileNotFoundError: If ``manifest.json`` is missing under ``root``.

    """
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found at {manifest_path}")

    with open(manifest_path) as f:
        manifest = json.load(f)

    for entry in manifest.get("ato_bench", []):
        doc_id = entry["doc_id"]
        parts: list[str] = []
        for page_rel in entry.get("pages", []):
            page_path = root / page_rel
            if not page_path.exists():
                continue
            with open(page_path) as pf:
                page = json.load(pf)
            page_text = _extract_page_gold_text(page)
            if page_text:
                parts.append(page_text)
        yield doc_id, " ".join(parts)
