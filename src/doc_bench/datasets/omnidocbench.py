"""
OmniDocBench loader with English-only filter.

This module loads OmniDocBench dataset and filters to English-only documents
with RFI-relevant document types. Each yielded page includes _eval_tags
metadata for stratified analysis.

Bundled fixture set (src/doc_bench/fixtures/omnidocbench/):
  - 11 pages, English only, all clean (no fuzzy_scan / watermark)
  - Distribution: academic_literature×3, book×2, PPT2PDF×2,
    exam_paper×1, colorful_textbook×2, research_report×1
  - Selected 2026-06-06 from opendatalab/OmniDocBench English-filtered snapshot
  - See fixtures/omnidocbench/README.md for full selection criteria
"""

import json
from collections.abc import Iterator
from pathlib import Path

# Document types relevant to RFI workflows
RELEVANT_DOC_TYPES = {
    "academic_literature",
    "research_report",
    "exam_paper",
    "colorful_textbook",
    "book",
    "PPT2PDF",
}

# Languages we keep (English only for MVP)
RELEVANT_LANGUAGES = {"english"}


def _is_clean_scan(page: dict) -> bool:
    """
    Check if a page is a clean scan (no fuzzy scan or watermark).

    Args:
        page: Page dictionary from OmniDocBench.

    Returns:
        True if page is clean, False if noisy.

    """
    page_info = page.get("page_info", {})
    attrs = page_info.get("page_attribute", {})
    return not (attrs.get("fuzzy_scan", False) or attrs.get("watermark", False))


def _load_omnidocbench_bundled(fixtures_root: Path) -> Iterator[dict]:
    """
    Load the bundled OmniDocBench fixture subset from the package fixtures directory.

    Iterates the manifest.json["omnidocbench"] list (the authoritative curated
    selection), loads each per-page JSON, and yields the page dict with _eval_tags
    added — no OmniDocBench.json required.

    Args:
        fixtures_root: Path to the doc_bench fixtures directory.

    Yields:
        dict: Annotated page dict matching the full loader's output shape.

    Raises:
        FileNotFoundError: If manifest.json is missing under fixtures_root.

    """
    import json as _json

    manifest_path = fixtures_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found at {manifest_path}")

    with open(manifest_path) as f:
        manifest = _json.load(f)

    for entry in manifest.get("omnidocbench", []):
        page_path = fixtures_root / entry["page"]
        if not page_path.exists():
            continue

        with open(page_path) as f:
            page = _json.load(f)

        attrs = page.get("page_info", {}).get("page_attribute", {})
        page["_eval_tags"] = {
            "is_clean": not (attrs.get("fuzzy_scan", False) or attrs.get("watermark", False)),
            "has_watermark": attrs.get("watermark", False),
            "has_fuzzy_scan": attrs.get("fuzzy_scan", False),
            "has_colorful_bg": attrs.get("colorful_backgroud", False),
            "layout": attrs.get("layout"),
        }
        yield page


def load_omnidocbench(
    root: Path | None = None,
    include_hard_subset: bool = True,
) -> Iterator[dict]:
    """
    Yield filtered OmniDocBench pages with evaluation metadata.

    Filtering policy:
      - English only
      - Document types relevant to RFI workflows
      - Noisy pages (fuzzy_scan, watermark) tagged but not excluded

    Args:
        root: Path to OmniDocBench directory containing OmniDocBench.json. Pass
            None to use the bundled 11-page fixture subset (no external data required).
        include_hard_subset: If True, includes hard subset (difficult formulas,
            tables, layouts). Hard pages are tagged in _eval_tags.

    Yields:
        dict: Annotated page with added _eval_tags metadata.
            Each page includes the original OmniDocBench fields plus:
            - _eval_tags: Dict with is_clean, has_watermark, has_fuzzy_scan,
              has_colorful_bg, and layout keys.

    """
    if root is None:
        import doc_bench

        fixtures_root = Path(doc_bench.__file__).parent / "fixtures"
        yield from _load_omnidocbench_bundled(fixtures_root)
        return

    json_path = root / "OmniDocBench.json"

    if not json_path.exists():
        raise FileNotFoundError(f"OmniDocBench.json not found at {json_path}")

    with open(json_path) as f:
        all_pages = json.load(f)

    for page in all_pages:
        attrs = page.get("page_info", {}).get("page_attribute", {})

        # Skip non-English
        if attrs.get("language") not in RELEVANT_LANGUAGES:
            continue

        # Skip non-relevant document types
        if attrs.get("data_source") not in RELEVANT_DOC_TYPES:
            continue

        # Tag noisy pages so we can stratify in reports without dropping them
        page["_eval_tags"] = {
            "is_clean": _is_clean_scan(page),
            "has_watermark": attrs.get("watermark", False),
            "has_fuzzy_scan": attrs.get("fuzzy_scan", False),
            "has_colorful_bg": attrs.get("colorful_backgroud", False),
            "layout": attrs.get("layout"),
        }

        yield page
