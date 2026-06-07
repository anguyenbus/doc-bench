# doc-bench Metrics

doc-bench scores parser output with deterministic metrics. "Deterministic" means same input
produces the same score every run, every machine: there is no LLM judge, no sampling, and no
network call. Every metric is normalized to `[0.0, 1.0]` where **1.0 is a perfect match** with
the ground truth.

## Table of Contents

- [Why deterministic metrics](#why-deterministic-metrics)
- [The metrics](#the-metrics)
  - [NED -- Normalized Edit Distance (text)](#ned----normalized-edit-distance-text)
  - [TEDS / TEDS-S -- table structure](#teds--teds-s----table-structure)
- [ASM pre-matching](#asm-pre-matching)
- [How scores are computed and reported](#how-scores-are-computed-and-reported)
- [OmniDocBench leaderboard comparability](#omnidocbench-leaderboard-comparability)
- [Migration note: removed metrics](#migration-note-removed-metrics)
- [Known metric caveats](#known-metric-caveats)

## Why deterministic metrics

LLM-as-judge evaluation introduces variance, cost, and a dependency on API keys and GPUs.
doc-bench deliberately uses only deterministic string/tree/sequence metrics so that:

- results are reproducible across runs and environments,
- evaluation has zero incremental cost and needs no secrets, and
- a regression in a metric is always attributable to the input, never to judge drift.

The metric implementations live in [`src/doc_bench/metrics/parsing/`](../../src/doc_bench/metrics/parsing/).
The vendored generator keeps a copy of `table_teds.py`, protected by the
[drift guard](../docling-baseline/guards.md).

## The metrics

Each metric compares the **gold content** (from ground-truth annotations) against the
**predicted content** (from the parser's `parser_output` JSON).

### NED -- Normalized Edit Distance (text)

**NED** measures how close the predicted text is to the gold text using a character-level
Levenshtein edit distance, normalized by the maximum string length, and reported as a
similarity (1.0 = identical text).

**Formula:**

```
NED(gt, pred) = Levenshtein.distance(gt, pred) / max(len(gt), len(pred))
NED_score(gt, pred) = 1 - NED(gt, pred)
```

**Normalization steps applied before comparison:**

1. NFC unicode normalization: combining character sequences (e.g., "e" + U+0301) are
   collapsed to their precomposed equivalents (e.g., U+00E9 "e with acute").
2. Whitespace collapse: any run of whitespace (spaces, tabs, newlines) is replaced by a
   single ASCII space, and leading/trailing whitespace is stripped.

**Empty string handling:**
- Both empty: similarity = 1.0 (no content to disagree on)
- One empty: similarity = 0.0 (all content is missing or spurious)

**Implementation:** `src/doc_bench/metrics/parsing/ned.py` using the `Levenshtein` package
(`python-Levenshtein`), NOT `rapidfuzz`. This matches the canonical OmniDocBench implementation
exactly. See the audit trail at `references/omnidocbench/cal_metric.py`.

**Important distinction:** This is a **character-level** NED, not a word-token NED. It differs
from:

- `docling-eval` NED, which operates on word tokens
- DP-Bench NID (Normalized Indel Distance), which uses a rapidfuzz-based normalized edit distance

Scores from doc-bench NED are **directly comparable** to the OmniDocBench leaderboard because
they use the same formula, the same normalization, and the same library. Historical NID scores
are **not comparable** to new NED scores -- see
[Migration note: removed metrics](#migration-note-removed-metrics).

### TEDS / TEDS-S -- table structure

**Tree Edit Distance Similarity.** Parses tables out of both gold and prediction markdown,
builds tree representations, and computes a normalized tree-edit-distance similarity.

- **TEDS** accounts for both table structure and cell content.
- **TEDS-S** accounts for structure only.

Backed by `apted`. TEDS only produces a meaningful score when **both** gold and prediction
contain markdown tables (`| ... |`). If the gold has no markdown tables, TEDS is 0 -- see
[caveats](#known-metric-caveats).

**Implementation:** `src/doc_bench/metrics/parsing/table_teds.py`. This file is protected by the
[drift guard](../docling-baseline/guards.md); the vendored docling_baseline copy is
token-identical to the doc-bench copy (minus a legacy alias stub).

## ASM pre-matching

When structured element arrays are available (list of dicts with `category`/`type` and
`content.text` fields from the parsed JSON), doc-bench uses **Adjacency Search Match (ASM)**
pre-matching before scoring.

ASM (ported from OmniDocBench) provides type-aware paragraph-level alignment:

- **Text elements** (paragraphs, headings, captions, etc.) are routed to NED scoring.
- **Table elements** are routed to TEDS scoring.
- **Formula and figure elements** are skipped (CDM/image scoring is out of scope).
- **Ignored elements** (abandoned text, explicitly ignored regions) are excluded.

The full ASM algorithm uses a Hungarian-algorithm paragraph alignment step to merge/split
paragraphs before scoring. doc-bench approximates this with a merge-and-compare approach
equivalent to `match_gt2pred_no_split` in the OmniDocBench reference.

**Degraded mode:** When only flat markdown is available (the parser emits a single string
rather than a structured element list), `markdown_to_pseudo_elements()` converts the markdown
to a minimal pseudo-element array. A `rich` warning is emitted in this case:

```
WARNING markdown_to_pseudo_elements called: scoring in DEGRADED MODE.
NED scores are NOT leaderboard-comparable (no element structure available).
```

Scores computed via degraded mode are **not comparable to the OmniDocBench leaderboard**.

**Reference:** `references/omnidocbench/match.py` (audit trail copy, commit
`176a7813e41427d21acac3c243308cb2fdff9054`).

## How scores are computed and reported

1. Ground-truth annotations are rendered to gold markdown; the prediction JSON is rendered
   to prediction markdown.
2. Each metric is computed per document.
3. Per-document scores are written to the results CSV; their averages go to the results JSON
   summary.

Example per-document CSV row:

```csv
query_id,error,ned,teds,teds_s
omnidocbench_0,,0.85,0.92,0.94
```

Example `scores.json` summary:

```json
{
  "metrics_avg": {
    "ned": 0.85,
    "teds": 0.92,
    "teds_s": 0.94
  }
}
```

Bundled reference baselines are stored alongside the fixtures
(`doc_bench/fixtures/*_results.json`) and documented in
[datasets.md](datasets.md#bundled-baseline-scores).

## OmniDocBench leaderboard comparability

doc-bench NED scores are directly comparable to the
[OmniDocBench leaderboard](https://arxiv.org/abs/2412.07626) because:

- The formula is identical: `Levenshtein.distance(gt, pred) / max(len(gt), len(pred))`.
- The normalization is identical: NFC + whitespace collapse, both applied before comparison.
- The library is identical: `python-Levenshtein`, not `rapidfuzz`.

The OmniDocBench evaluation pipeline source is audited in
`references/omnidocbench/` (commit `176a7813e41427d21acac3c243308cb2fdff9054`, Apache-2.0).
These files are never imported at runtime; they serve as a read-only audit trail.

For the academic justification for using NED+TEDS, see
[docs/whynedteds.md](../whynedteds.md) if available.

## Migration note: removed metrics

The following metrics were removed as part of the 2026-06-07 NED/metrics simplification:

| Removed metric | Replaced by | Reason for removal |
|---|---|---|
| NID / NID-S (Normalized Indel Distance) | NED | NID used rapidfuzz word-token distance; NED uses Levenshtein character-level distance matching OmniDocBench |
| MHS / MHS-S (Markdown Hierarchical Similarity) | -- | Heading-only similarity not tracked by OmniDocBench leaderboard |
| ARD (Average Rank Distance) | -- | Reading-order metric not in OmniDocBench leaderboard scope |
| BLEU | -- | N-gram precision redundant with NED for leaderboard comparison |
| METEOR | -- | Stemmed recall redundant with NED; required NLTK data download |
| text_f1 | -- | Word-level F1 redundant with NED |
| structure_recall | -- | Structure metric not in OmniDocBench leaderboard scope |
| layout_map | -- | Layout mAP not in OmniDocBench leaderboard scope |

**Non-comparability warning:** Historical NID scores are not comparable to new NED scores and
must not be trended on the same chart. NID used `rapidfuzz.distance.Levenshtein` with word-level
tokenization; NED uses `python-Levenshtein` with character-level comparison. The same parser
will produce different numbers on NID vs NED.

Scores reported before the 2026-06-07 spec migration use the old metric set and should be
labeled with the metric name (NID, MHS, etc.) to avoid confusion with post-migration NED scores.

## Known metric caveats

These are properties of the gold builder or scoring approach, not parser failures. Document them
when reporting numbers so readers do not misinterpret zeros.

- **TEDS / TEDS-S can be 0 on text-only documents.** If the gold markdown contains no `|` tables,
  the table metrics have nothing to compare against and return 0. This is common on
  OmniDocBench-format gold.
- **OmniDocBench-format gold ignores table cells.** The gold-text builder reads each detection's
  `text` field and does not expand table `cells`, so table-heavy documents contribute no table
  text to the gold and score 0 on TEDS. See the worked discussion in
  [adding-a-dataset.md](../docling-baseline/adding-a-dataset.md#gotchas).
- **Page-count alignment matters.** If a prediction covers more pages than the gold (for example
  a 6-page PDF graded against 2-page gold), the extra predicted text deflates NED. Align the
  source document to the gold's page coverage.
- **Degraded mode degrades comparability.** When only flat markdown is available, NED scores
  are computed without element-type routing or paragraph alignment. These scores are NOT
  comparable to the OmniDocBench leaderboard.
