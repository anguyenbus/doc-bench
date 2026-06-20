"""
ATO-Bench loader.

ATO-Bench contains multi-page Australian Tax Office form PDFs with a single
document-level gold JSON in ParserOutput ``elements`` format (``{"pages", "elements"}``).
Each element carries a ``text`` field and a ``page_index`` (0-based); text is
extracted in page order, then top-to-bottom within each page via the ``bbox.y0``
coordinate.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def _extract_gold_text(gold: dict[str, Any]) -> str:
    """
    Extract document-level gold text from a ParserOutput-format gold JSON.

    Elements are sorted by page, then top-to-bottom (``bbox.y0``), then
    left-to-right (``bbox.x0``). Empty-text elements are skipped.

    Args:
        gold: Parsed JSON with ``elements`` and ``pages`` keys.

    Returns:
        All element texts joined by a single space.

    """
    elements = gold.get("elements", [])

    def _sort_key(el: dict[str, Any]) -> tuple[int, float, float]:
        bbox = el.get("bbox") or {}
        return (
            el.get("page_index", 0),
            float(bbox.get("y0", 0)),
            float(bbox.get("x0", 0)),
        )

    texts = [el["text"] for el in sorted(elements, key=_sort_key) if el.get("text", "").strip()]
    return " ".join(texts)


def load_ato_bench(root: Path) -> Iterator[tuple[str, str]]:
    """
    Yield ``(doc_id, gold_text)`` for each ATO-Bench document under ``root``.

    Args:
        root: Directory containing ``manifest.json`` and an ``ato_bench/`` folder
            with the gold JSON files (the bundled fixture layout).

    Yields:
        ``(doc_id, gold_text)`` where ``gold_text`` is extracted from the
        document's ParserOutput-format gold JSON.

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
        gold_rel = entry.get("gold", "")
        if not gold_rel:
            continue
        gold_path = root / gold_rel
        if not gold_path.exists():
            continue
        with open(gold_path) as gf:
            gold = json.load(gf)
        gold_text = _extract_gold_text(gold)
        if gold_text:
            yield doc_id, gold_text
