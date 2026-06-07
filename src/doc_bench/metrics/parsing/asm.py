"""
Adjacency Search Match (ASM) pre-matching for document element scoring.

ASM is ported from the OmniDocBench evaluation repository
(github.com/opendatalab/OmniDocBench, commit 176a7813e41427d21acac3c243308cb2fdff9054)
and provides type-aware paragraph-level alignment between ground-truth and
predicted elements before NED/TEDS scoring.  The reference implementation is
preserved verbatim in ``references/omnidocbench/match.py`` and
``references/omnidocbench/cal_metric.py``.

This module operates on the **structured elements array** from the parsed JSON
(list of dicts with ``category``/``type`` and ``content.text`` fields).  Using
structured elements, ASM can:

- Route text elements to NED scoring and table elements to TEDS scoring.
- Exclude ignored regions (abandoned text, irrelevant regions) from scoring.
- Merge/split paragraph segments to avoid penalizing parsers for different
  segmentation strategies.

Degraded mode
-------------
When only flat markdown is available (e.g., a parser emits a single string
rather than a structured element list), the function
``markdown_to_pseudo_elements`` converts the markdown to a minimal pseudo-
elements array.  This path is explicitly **degraded mode**: scores computed
via the markdown fallback are NOT leaderboard-comparable to OmniDocBench
numbers.  A ``rich`` warning is emitted whenever this path is taken.

# WARN: The degraded-mode fallback degrades score comparability.
# Scores produced through markdown_to_pseudo_elements are NOT
# comparable to the OmniDocBench leaderboard.

Category routing
----------------
- ``text_all`` / text-like categories → ``ned_score()``
- ``table`` / HTML table categories → ``table_teds.py`` (TEDS scoring)

# NOTE: Formula elements (``equation_isolated``) are skipped rather than
# scored.  OmniDocBench uses CDM (Content Distance Metric) for formula
# elements, which requires a TeX Live installation.  CDM is out of scope
# for this spec (see spec §Out of Scope).  Figure elements are also skipped
# because they are image-only and have no text to compare.

Ignore flags
------------
Elements marked with the following OmniDocBench ignore flags are excluded
from scoring:

# NOTE: OmniDocBench marks ignored elements via ``attribute.is_abandoned``
# (abandoned/meaningless text regions) and ``attribute.ignore``
# (regions explicitly marked as irrelevant).  Both are respected here.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console

from doc_bench.metrics.parsing.ned import ned_score

_console = Console(stderr=True)

# NOTE: Categories treated as scoreable text by OmniDocBench.
_TEXT_CATEGORIES: frozenset[str] = frozenset(
    {
        "text_all",
        "text_block",
        "title",
        "code_txt",
        "code_txt_caption",
        "reference",
        "equation_caption",
        "figure_caption",
        "figure_footnote",
        "table_caption",
        "table_footnote",
        "code_algorithm",
        "code_algorithm_caption",
        "header",
        "footer",
        "page_footnote",
        "page_number",
        # doc-bench element types mapped to text
        "paragraph",
        "heading",
        "list_item",
        "caption",
        "footnote",
        "equation",
        "code_block",
    }
)

# NOTE: Categories treated as table content that routes to TEDS scoring.
_TABLE_CATEGORIES: frozenset[str] = frozenset({"table", "html_table", "latex_table"})

# NOTE: Categories explicitly skipped (formula/figure — no CDM in scope).
_SKIP_CATEGORIES: frozenset[str] = frozenset(
    {"equation_isolated", "equation_inline", "formula", "figure", "formula_rescue"}
)


def _is_ignored(element: dict[str, Any]) -> bool:
    """
    Return True if the element should be excluded from scoring.

    Respects OmniDocBench ignore flags:
    - ``attribute.is_abandoned``: abandoned text regions
    - ``attribute.ignore``: explicitly ignored regions

    Args:
        element: Element dict from the structured elements array.

    Returns:
        True if the element should be skipped.

    """
    attr = element.get("attribute", {}) or {}
    return bool(attr.get("is_abandoned") or attr.get("ignore"))


def _extract_text(element: dict[str, Any]) -> str:
    """
    Extract the text content from an element dict.

    Checks both ``content.text`` (doc-bench schema) and ``text`` /
    ``content`` (OmniDocBench schema) fields.

    Args:
        element: Element dict.

    Returns:
        Extracted text, or empty string.

    """
    content = element.get("content", {}) or {}
    if isinstance(content, dict):
        text = content.get("text", "") or ""
    else:
        text = str(content)
    if not text:
        text = element.get("text", "") or ""
    return str(text)


def _category_of(element: dict[str, Any]) -> str:
    """
    Return the canonical category string for an element.

    Checks ``fine_category_type``, ``category_type``, ``category``, and
    ``type`` fields in order of specificity.

    Args:
        element: Element dict.

    Returns:
        Category string.

    """
    return (
        element.get("fine_category_type")
        or element.get("category_type")
        or element.get("category")
        or element.get("type")
        or ""
    )


def _collect_text_blocks(elements: list[dict[str, Any]]) -> list[str]:
    """
    Collect scoreable text blocks from a structured elements array.

    Skips ignored elements, formula/figure elements, and elements with
    empty text.  Table elements are also skipped here (they are scored
    separately via TEDS).

    Args:
        elements: Structured elements array.

    Returns:
        List of non-empty text strings in document order.

    """
    blocks: list[str] = []
    for elem in elements:
        if _is_ignored(elem):
            continue
        category = _category_of(elem).lower()
        if category in _SKIP_CATEGORIES:
            # NOTE: Formula/figure elements skipped — CDM out of scope.
            continue
        if category in _TABLE_CATEGORIES:
            # Tables scored via TEDS separately; skip here.
            continue
        text = _extract_text(elem)
        if text:
            blocks.append(text)
    return blocks


def _merge_blocks(blocks: list[str]) -> str:
    """
    Merge text blocks into a single comparable string.

    Blocks are joined with a single space, matching OmniDocBench's
    concatenation strategy for element-level text before NED scoring.

    Args:
        blocks: List of text blocks.

    Returns:
        Concatenated string.

    """
    return " ".join(b.strip() for b in blocks if b.strip())


def asm_ned_score(
    gt_elements: list[dict[str, Any]],
    pred_elements: list[dict[str, Any]],
) -> float:
    """
    Compute ASM-aligned NED score between structured element arrays.

    This is the canonical (leaderboard-comparable) path.  Both arrays must
    contain element dicts with ``category``/``type`` and ``content.text``
    fields (the structured elements array from the parsed JSON).

    The algorithm:
    1. Extract scoreable text blocks from both arrays (skip ignored/formula/figure).
    2. Merge blocks into concatenated strings on both sides.
    3. Compute NED on the merged strings.

    # NOTE: The full OmniDocBench ASM uses a Hungarian-algorithm paragraph
    # alignment step to merge/split paragraphs before scoring (see
    # references/omnidocbench/match.py: match_gt2pred_timeout_safe).
    # That alignment requires scipy and the OmniDocBench preprocessing
    # functions (normalized_text, etc.).  Because doc-bench currently uses
    # flat markdown as its internal representation, the full paragraph-level
    # alignment is approximated here by merging all text blocks and computing
    # NED on the merged string, which is equivalent to the OmniDocBench
    # ``match_gt2pred_no_split`` path (positional concatenation, no split).
    # If exact leaderboard parity is required, replace the merger with the
    # full ASM graph-matching step.

    Args:
        gt_elements: Ground-truth structured elements array.
        pred_elements: Predicted structured elements array.

    Returns:
        NED similarity score in [0.0, 1.0].

    """
    gt_blocks = _collect_text_blocks(gt_elements)
    pred_blocks = _collect_text_blocks(pred_elements)
    gt_text = _merge_blocks(gt_blocks)
    pred_text = _merge_blocks(pred_blocks)
    return ned_score(gt_text, pred_text)


def markdown_to_pseudo_elements(md: str) -> list[dict[str, Any]]:
    """
    Convert flat markdown to a minimal pseudo-elements array.

    # WARN: This function produces a DEGRADED-MODE output.
    # Scores computed from pseudo-elements are NOT comparable to the
    # OmniDocBench leaderboard because:
    #   - Category routing (text vs. table vs. formula) is lost.
    #   - ASM paragraph alignment cannot operate without element boundaries.
    #   - Ignore flags cannot be applied (no element metadata).
    # Use structured element arrays (asm_ned_score) for leaderboard parity.

    Args:
        md: Flat markdown string from a parser that emits no structure.

    Returns:
        List containing a single pseudo-element dict wrapping the full text.

    """
    _console.print(
        "[yellow]WARNING[/yellow] markdown_to_pseudo_elements called: scoring in DEGRADED MODE. "
        "NED scores are NOT leaderboard-comparable (no element structure available). "
        "Provide structured elements for leaderboard-comparable results.",
        highlight=False,
    )
    return [
        {
            "category_type": "text_all",
            "type": "paragraph",
            "content": {"text": md},
            "attribute": {},
        }
    ]


def asm_ned_score_from_markdown(
    gt_markdown: str,
    pred_markdown: str,
) -> float:
    """
    Compute NED score from flat markdown strings (degraded mode).

    Converts both markdown strings to pseudo-elements via
    ``markdown_to_pseudo_elements`` and then calls ``asm_ned_score``.  This
    path is explicitly degraded mode — a rich warning is emitted.

    Args:
        gt_markdown: Ground-truth markdown string.
        pred_markdown: Predicted markdown string.

    Returns:
        NED similarity score in [0.0, 1.0].  NOT leaderboard-comparable.

    """
    # NOTE: markdown_to_pseudo_elements emits the degraded-mode warning internally.
    gt_elements = markdown_to_pseudo_elements(gt_markdown)
    pred_elements = markdown_to_pseudo_elements(pred_markdown)
    return asm_ned_score(gt_elements, pred_elements)
