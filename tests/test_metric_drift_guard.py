"""Byte-equality drift guard for the vendored docling-baseline generator.

This test enforces FR5/AC5 of the docling-baseline generator integration spec
(``@agent-os/specs/2026-06-03-docling-baseline-generator-integration``). The
generator was vendored VERBATIM into ``src/docling_baseline/``, which keeps a
*second, independent copy* of the metric implementations and the parser-output
schema that ``doc-bench`` itself ships under ``src/doc_bench/``. Without a guard
those two copies can silently diverge: a maintainer fixes a NID/TEDS/MHS bug in
one copy, forgets the other, and ``make regen-fixtures`` then bakes baseline
scores that no version of ``doc-bench`` can reproduce. The adversarial review
(``planning/adversarial-review.md``) names this silent metric-drift as the one
outcome the spec exists to prevent.

This guard converts that silent drift into a loud, reviewable CI failure: any
*unreviewed* divergence between a vendored metric/schema file and its
``doc-bench`` counterpart fails the test.

Comparison strategy
-------------------
The files split into two classes:

1. **Byte-identical today** -- ``mhs.py``, ``reading_order.py``,
   ``text_similarity.py`` and ``parser_output.schema.json`` are byte-for-byte
   equal to their ``doc-bench`` counterparts RIGHT NOW. These are asserted with
   a raw ``bytes`` comparison and carry **no allow-listed delta**. A single
   changed byte fails the test.

2. **Identical core logic + an appended legacy alias** -- ``nid.py`` and
   ``table_teds.py`` are NOT byte-identical. ``doc-bench`` appends a deprecated
   legacy-alias function to the end of each file for backward compatibility, and
   (``table_teds.py`` only) reflows three multi-line statements in the shared
   core onto single lines. The core *scoring logic* is equivalent today.

   For these two files the known deltas are captured by the explicit
   :data:`ALLOW_LIST` below as load-bearing data. Each entry pins the **exact
   bytes** of the appended alias suffix (so editing the alias, or any *new*
   trailing addition, fails) and names the precise reason. After the pinned
   alias suffix is stripped from the ``doc-bench`` file, the remaining *core* is
   compared to the vendored file at the level of Python **tokens** -- the
   ``tokenize`` stream with whitespace/indent/newline tokens removed. This makes
   the guard bite exactly where it should:

   * a whitespace-only reflow on shared lines (today's ``table_teds.py`` delta)
     PASSES, because tokens are unchanged;
   * ANY change to an operator, identifier, literal, or call in the core
     scoring logic FAILS, because the token streams differ;
   * ANY edit to the pinned alias bytes, or any unlisted trailing addition,
     FAILS, because the suffix no longer matches the pinned text.

The allow-list lists EXACTLY the legacy-alias deltas on ``nid.py`` and
``table_teds.py`` and nothing else. ``mhs.py``, ``reading_order.py``,
``text_similarity.py`` and the schema deliberately have NO allow-list entry.

This guard is deterministic, requires NO Docling install, and runs in the fast
``pytest -q`` suite (and therefore in CI).
"""

from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
VENDORED_METRICS: Final[Path] = REPO_ROOT / "src" / "docling_baseline" / "metrics"
VENDORED_SCHEMA: Final[Path] = (
    REPO_ROOT / "src" / "docling_baseline" / "schemas" / "parser_output.schema.json"
)
DOCBENCH_METRICS: Final[Path] = REPO_ROOT / "src" / "doc_bench" / "metrics" / "parsing"
DOCBENCH_SCHEMA: Final[Path] = (
    REPO_ROOT / "src" / "doc_bench" / "fixtures" / "parser_output.schema.json"
)


# ---------------------------------------------------------------------------
# Class 1: byte-identical files (NO allow-listed delta).
# ---------------------------------------------------------------------------
# Each tuple is (vendored_path, docbench_path). These MUST be byte-for-byte
# equal today; a single differing byte is a divergence that fails the guard.
BYTE_IDENTICAL: Final[tuple[tuple[Path, Path], ...]] = (
    (VENDORED_METRICS / "mhs.py", DOCBENCH_METRICS / "mhs.py"),
    (VENDORED_METRICS / "reading_order.py", DOCBENCH_METRICS / "reading_order.py"),
    (VENDORED_METRICS / "text_similarity.py", DOCBENCH_METRICS / "text_similarity.py"),
    (VENDORED_SCHEMA, DOCBENCH_SCHEMA),
)


# ---------------------------------------------------------------------------
# Class 2: identical core + an appended legacy alias (the documented allow-list).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AllowedDelta:
    """One documented, reviewed divergence between a vendored file and doc-bench.

    Attributes:
        name: A short label for the file pair (used in test ids / messages).
        vendored: Path to the vendored ``src/docling_baseline`` copy.
        docbench: Path to the ``doc-bench`` counterpart.
        alias_marker: The exact substring in the ``doc-bench`` file at which the
            appended legacy-alias block begins. Everything from this marker to
            the end of file is the allow-listed addition; everything before it
            is the shared core that must match the vendored file token-for-token.
        alias_suffix: The EXACT expected bytes (decoded text) of the appended
            alias block, from ``alias_marker`` to EOF. Pinned so that any edit
            to the alias text -- or any new, unlisted trailing addition -- fails.
        reason: Human-readable justification for why this delta is permitted.
        core_byte_identical: ``True`` if the shared core (file minus the pinned
            alias suffix) is ALSO byte-identical to the vendored file (no
            whitespace reflow); ``False`` if the core differs only by reviewed
            whitespace/line-reflow and must be compared at the token level.
    """

    name: str
    vendored: Path
    docbench: Path
    alias_marker: str
    alias_suffix: str
    reason: str
    core_byte_identical: bool


# NOTE: The ``alias_suffix`` values below are the verbatim current bytes of the
# appended blocks. They are intentionally pinned in full so the guard fails if
# the alias logic is edited or a brand-new function is appended unreviewed.
_NID_ALIAS_SUFFIX: Final[str] = (
    "\n\n# Legacy aliases for compatibility\n"
    "def normalized_indel_distance(predicted: list, gold: list) -> float:\n"
    '    """\n'
    "    Legacy: Calculate edit distance between sequences.\n\n"
    "    DEPRECATED: Use nid_score() with markdown strings instead.\n"
    "    This is kept for backward compatibility.\n"
    '    """\n'
    "    if not predicted and not gold:\n"
    "        return 0.0\n"
    "    if not predicted or not gold:\n"
    "        return 1.0\n\n"
    "    from rapidfuzz.distance import Levenshtein\n\n"
    "    distance = Levenshtein.distance(predicted, gold)\n"
    "    max_len = max(len(predicted), len(gold))\n"
    "    return distance / max_len if max_len > 0 else 0.0\n"
)

_TABLE_TEDS_ALIAS_SUFFIX: Final[str] = (
    "# Legacy alias for backward compatibility\n"
    "def table_teds(predicted_table: dict, gold_table: dict) -> float:\n"
    '    """\n'
    "    Legacy: Calculate simplified table similarity.\n\n"
    "    DEPRECATED: Use teds_score() with markdown strings instead.\n"
    "    This is kept for backward compatibility with existing tests.\n"
    '    """\n'
    '    pred_cells = predicted_table.get("cells", [])\n'
    '    gold_cells = gold_table.get("cells", [])\n\n'
    "    if not pred_cells and not gold_cells:\n"
    "        return 1.0\n"
    "    if not pred_cells or not gold_cells:\n"
    "        return 0.0\n\n"
    "    pred_cells_dict = {}\n"
    "    for cell in pred_cells:\n"
    '        key = (cell.get("row"), cell.get("col"))\n'
    '        pred_cells_dict[key] = cell.get("text", "")\n\n'
    "    gold_cells_dict = {}\n"
    "    for cell in gold_cells:\n"
    '        key = (cell.get("row"), cell.get("col"))\n'
    '        gold_cells_dict[key] = cell.get("text", "")\n\n'
    "    all_positions = set(pred_cells_dict.keys()) | set(gold_cells_dict.keys())\n\n"
    "    if not all_positions:\n"
    "        return 1.0\n\n"
    "    matches = 0\n"
    "    for pos in all_positions:\n"
    '        pred_text = pred_cells_dict.get(pos, "")\n'
    '        gold_text = gold_cells_dict.get(pos, "")\n'
    "        if pred_text == gold_text:\n"
    "            matches += 1\n\n"
    "    return matches / len(all_positions)\n"
)


# The complete allow-list. EXACTLY two entries -- the legacy-alias deltas on
# nid.py and table_teds.py -- and nothing else. mhs.py / reading_order.py /
# text_similarity.py / the schema are absent here on purpose (they are
# byte-identical and live in BYTE_IDENTICAL above).
ALLOW_LIST: Final[tuple[AllowedDelta, ...]] = (
    AllowedDelta(
        name="nid.py",
        vendored=VENDORED_METRICS / "nid.py",
        docbench=DOCBENCH_METRICS / "nid.py",
        alias_marker="\n\n# Legacy aliases for compatibility\n",
        alias_suffix=_NID_ALIAS_SUFFIX,
        reason=(
            "doc-bench appends the legacy alias function "
            "`normalized_indel_distance` (deprecated, kept for backward "
            "compatibility); the vendored core scoring logic is byte-identical."
        ),
        core_byte_identical=True,
    ),
    AllowedDelta(
        name="table_teds.py",
        vendored=VENDORED_METRICS / "table_teds.py",
        docbench=DOCBENCH_METRICS / "table_teds.py",
        alias_marker="# Legacy alias for backward compatibility\n",
        alias_suffix=_TABLE_TEDS_ALIAS_SUFFIX,
        reason=(
            "doc-bench appends the legacy alias function `table_teds` "
            "(deprecated, kept for backward compatibility with existing tests) "
            "and reflows three multi-line statements in the shared core onto "
            "single lines (whitespace-only); the vendored core scoring logic is "
            "token-identical."
        ),
        core_byte_identical=False,
    ),
)


def _core_tokens(source: str) -> list[tuple[int, str]]:
    """Return the meaningful Python token stream of ``source``.

    Whitespace, indentation, newline, comment, encoding, and end-marker tokens
    are dropped so that a whitespace-only reflow compares equal, while every
    operator / identifier / literal / keyword that constitutes the actual
    scoring logic is preserved. A divergence in any such token means the two
    files no longer encode the same logic.

    Args:
        source: Python source text.

    Returns:
        A list of ``(token_type, token_string)`` pairs for the meaningful
        tokens, in order.
    """
    ignored = {
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.COMMENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
    readline = io.StringIO(source).readline
    return [
        (tok.type, tok.string)
        for tok in tokenize.generate_tokens(readline)
        if tok.type not in ignored
    ]


@pytest.mark.parametrize(
    ("vendored", "docbench"),
    BYTE_IDENTICAL,
    ids=[v.name for v, _ in BYTE_IDENTICAL],
)
def test_byte_identical_files_have_no_delta(vendored: Path, docbench: Path) -> None:
    """mhs/reading_order/text_similarity/schema are byte-for-byte equal today.

    These carry NO allow-listed delta. A single differing byte is an
    unreviewed divergence and fails the guard.
    """
    assert vendored.exists(), f"missing vendored file: {vendored}"
    assert docbench.exists(), f"missing doc-bench counterpart: {docbench}"
    vendored_bytes = vendored.read_bytes()
    docbench_bytes = docbench.read_bytes()
    assert vendored_bytes == docbench_bytes, (
        f"BYTE-EQUALITY DRIFT: {vendored} and {docbench} are no longer "
        f"byte-identical. These files have NO allow-listed delta. Either the "
        f"divergence is an unintended drift (fix it / re-sync the copies) or it "
        f"is an intended, reviewed change that must be added to ALLOW_LIST in "
        f"{Path(__file__).name} with an explicit reason."
    )


@pytest.mark.parametrize(
    "delta",
    ALLOW_LIST,
    ids=[d.name for d in ALLOW_LIST],
)
def test_allowed_delta_alias_suffix_is_pinned_exactly(delta: AllowedDelta) -> None:
    """The doc-bench file is its shared core + the EXACT pinned alias suffix.

    Pinning the full alias bytes means: editing the alias, or appending any new
    unlisted function, changes the trailing bytes and fails here.
    """
    assert delta.vendored.exists(), f"missing vendored file: {delta.vendored}"
    assert delta.docbench.exists(), f"missing doc-bench file: {delta.docbench}"
    docbench_text = delta.docbench.read_text(encoding="utf-8")

    assert delta.alias_marker in docbench_text, (
        f"DRIFT in {delta.name}: the allow-listed legacy-alias marker "
        f"{delta.alias_marker!r} is no longer present in {delta.docbench}. The "
        f"documented delta ({delta.reason}) has changed; review and update "
        f"ALLOW_LIST."
    )

    suffix = docbench_text[docbench_text.index(delta.alias_marker) :]
    assert suffix == delta.alias_suffix, (
        f"DRIFT in {delta.name}: the appended legacy-alias block does not match "
        f"the pinned, reviewed text. Either the alias was edited or a new, "
        f"unlisted trailing addition appeared. Update the pinned `alias_suffix` "
        f"in ALLOW_LIST only after explicit review.\n"
        f"Reason on record: {delta.reason}"
    )


@pytest.mark.parametrize(
    "delta",
    ALLOW_LIST,
    ids=[d.name for d in ALLOW_LIST],
)
def test_allowed_delta_core_matches_vendored(delta: AllowedDelta) -> None:
    """The shared core (file minus the pinned alias) matches the vendored copy.

    For ``nid.py`` the core is byte-identical. For ``table_teds.py`` the core
    differs only by reviewed whitespace reflow, so it is compared at the token
    level: any change to a meaningful token (operator/identifier/literal) in the
    core scoring logic fails the guard, while a pure reflow passes.
    """
    vendored_text = delta.vendored.read_text(encoding="utf-8")
    docbench_text = delta.docbench.read_text(encoding="utf-8")
    core = docbench_text[: docbench_text.index(delta.alias_marker)]

    if delta.core_byte_identical:
        assert core == vendored_text, (
            f"CORE DRIFT in {delta.name}: the shared core (doc-bench file minus "
            f"the pinned legacy alias) is no longer byte-identical to the "
            f"vendored copy {delta.vendored}. This is an unreviewed divergence "
            f"in core scoring logic. Re-sync the copies or, if intended, update "
            f"ALLOW_LIST after review."
        )
    else:
        vendored_tokens = _core_tokens(vendored_text)
        core_tokens = _core_tokens(core)
        assert core_tokens == vendored_tokens, (
            f"CORE DRIFT in {delta.name}: the shared core (doc-bench file minus "
            f"the pinned legacy alias) no longer has the same Python token "
            f"stream as the vendored copy {delta.vendored}. The only permitted "
            f"core delta is whitespace reflow; a token-level difference means "
            f"the scoring logic itself diverged. Re-sync the copies or, if "
            f"intended, update ALLOW_LIST after review."
        )


def test_allow_list_contains_exactly_the_known_alias_deltas() -> None:
    """The allow-list lists EXACTLY nid.py and table_teds.py and nothing else.

    Guards against the allow-list silently growing to mask new divergences, and
    against the byte-identical files ever acquiring an (unjustified) entry.
    """
    allowed_names = {delta.name for delta in ALLOW_LIST}
    assert allowed_names == {"nid.py", "table_teds.py"}, (
        f"ALLOW_LIST must contain exactly the two documented legacy-alias "
        f"deltas (nid.py, table_teds.py); found: {sorted(allowed_names)}"
    )
    byte_identical_names = {v.name for v, _ in BYTE_IDENTICAL}
    # The byte-identical files must never appear in the allow-list.
    assert not (allowed_names & byte_identical_names), (
        f"byte-identical files must NOT have an allow-listed delta: "
        f"{sorted(allowed_names & byte_identical_names)}"
    )
