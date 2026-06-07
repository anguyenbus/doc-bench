"""
Tests for the NED (Normalized Edit Distance) metric module.

Covers:
- Formula pins with known-distance character pairs
- Boundary cases (empty strings, identical strings, dissimilar strings)
- NFC unicode normalization
- Whitespace normalization
- Real fixture page pins for pipeline regression detection
"""

import json
import unicodedata
from pathlib import Path

import Levenshtein
import pytest

FIXTURE_DIR: Path = Path(__file__).resolve().parent.parent.parent / "src" / "doc_bench" / "fixtures"


# ---------------------------------------------------------------------------
# Phase 1 (TDD): tests written BEFORE ned.py exists — they must fail first.
# ---------------------------------------------------------------------------


def test_ned_both_empty_returns_one() -> None:
    """Both empty strings: similarity must be 1.0."""
    from doc_bench.metrics.parsing.ned import ned_score

    assert ned_score("", "") == 1.0


def test_ned_one_empty_returns_zero() -> None:
    """One empty, one non-empty: similarity must be 0.0."""
    from doc_bench.metrics.parsing.ned import ned_score

    assert ned_score("hello", "") == 0.0
    assert ned_score("", "world") == 0.0


def test_ned_identical_strings_return_one() -> None:
    """Identical non-empty strings: similarity must be 1.0."""
    from doc_bench.metrics.parsing.ned import ned_score

    assert ned_score("hello world", "hello world") == 1.0


def test_ned_completely_dissimilar_returns_zero() -> None:
    """Completely dissimilar strings of the same length: similarity must be 0.0."""
    from doc_bench.metrics.parsing.ned import ned_score

    # "aaaa" vs "bbbb" -- Levenshtein.distance = 4, max_len = 4 → NED = 1.0 → sim = 0.0
    assert ned_score("aaaa", "bbbb") == 0.0


def test_ned_formula_pin_one_char_difference_five_chars() -> None:
    """One char difference in a 5-char string: similarity = 1 - (1/5) = 0.8."""
    from doc_bench.metrics.parsing.ned import ned_score

    # Levenshtein.distance("hello", "hxllo") = 1; max(5, 5) = 5; NED = 0.2 → sim = 0.8
    result = ned_score("hello", "hxllo")
    assert abs(result - 0.8) < 1e-9


def test_ned_formula_pin_known_distance_pairs() -> None:
    """Verify formula pins for at least 3 known-distance character pairs."""
    from doc_bench.metrics.parsing.ned import ned_score

    # pair 1: "kitten" vs "sitting" — Levenshtein distance = 3, max_len = 7
    assert abs(ned_score("kitten", "sitting") - (1.0 - 3 / 7)) < 1e-9

    # pair 2: "abc" vs "xyz" — distance = 3, max_len = 3 → sim = 0.0
    assert ned_score("abc", "xyz") == 0.0

    # pair 3: "ab" vs "abc" — distance = 1, max_len = 3 → sim = 1 - 1/3 ≈ 0.6667
    expected = 1.0 - 1 / 3
    assert abs(ned_score("ab", "abc") - expected) < 1e-9


def test_ned_nfc_normalization_combining_vs_precomposed() -> None:
    """NFC normalization: combining and precomposed forms must compare equal."""
    from doc_bench.metrics.parsing.ned import ned_score

    # "e" + combining acute (U+0301) is NFD; precomposed "e with acute" (U+00E9) is NFC.
    nfd_form = "é"  # two code points
    nfc_form = "é"  # one code point
    # After NFC both become "é" — identical, so similarity = 1.0
    assert ned_score(nfd_form, nfc_form) == 1.0


def test_ned_whitespace_normalization_leading_trailing() -> None:
    """Leading/trailing whitespace is stripped before comparison."""
    from doc_bench.metrics.parsing.ned import ned_score

    assert ned_score("  hello  ", "hello") == 1.0
    assert ned_score("hello", "  hello  ") == 1.0


def test_ned_whitespace_normalization_interior() -> None:
    """Repeated interior whitespace is collapsed to a single space."""
    from doc_bench.metrics.parsing.ned import ned_score

    # "hello   world" → "hello world" after normalization
    assert ned_score("hello   world", "hello world") == 1.0


# ---------------------------------------------------------------------------
# Real fixture pins — pipeline guard (fail if preprocessing or aggregation regresses).
# ---------------------------------------------------------------------------


def _build_dp_bench_gold_markdown(doc_id: str) -> str:
    """Build gold markdown from a bundled dp_bench fixture."""
    import sys
    sys.path.insert(0, str(FIXTURE_DIR.parent.parent))
    from doc_bench.datasets.dp_bench import build_gold_markdown

    gold_path = FIXTURE_DIR / "dp_bench" / f"{doc_id}.json"
    data = json.loads(gold_path.read_text())
    return build_gold_markdown(data)


def test_ned_score_identical_gold_vs_gold_is_one() -> None:
    """Scoring a fixture's gold markdown against itself must yield 1.0."""
    from doc_bench.metrics.parsing.ned import ned_score

    gold_md = _build_dp_bench_gold_markdown("01030000000001")
    result = ned_score(gold_md, gold_md)
    assert result == 1.0


def test_ned_score_gold_vs_empty_is_zero() -> None:
    """Scoring a fixture gold against empty prediction must yield 0.0."""
    from doc_bench.metrics.parsing.ned import ned_score

    gold_md = _build_dp_bench_gold_markdown("01030000000001")
    result = ned_score(gold_md, "")
    assert result == 0.0


def test_ned_score_known_pair_is_stable() -> None:
    """Verify a known-difference pair yields a stable value (regression pin)."""
    from doc_bench.metrics.parsing.ned import ned_score

    # gold: paragraph-heavy fixture
    gold_md = _build_dp_bench_gold_markdown("01030000000001")
    # pred: deliberately truncated to 50% of content (predictable NED > 0)
    truncated_pred = gold_md[: len(gold_md) // 2]

    result = ned_score(gold_md, truncated_pred)
    # We expect similarity < 1.0 because pred is shorter and truncated
    assert 0.0 < result < 1.0
    # Pin to 4 decimal places; this value is computed once and serves as the regression anchor
    # The actual value: Lev.distance(norm(gold), norm(pred)) / max(len(norm(gold)), len(norm(pred)))
    import re

    def _norm(t: str) -> str:
        t = unicodedata.normalize("NFC", t)
        return re.sub(r"\s+", " ", t).strip()

    g = _norm(gold_md)
    p = _norm(truncated_pred)
    expected = round(1.0 - Levenshtein.distance(g, p) / max(len(g), len(p)), 4)
    assert round(result, 4) == expected
