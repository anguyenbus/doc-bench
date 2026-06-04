# doc-bench Metrics

doc-bench scores parser output with six deterministic metrics. "Deterministic" means same input → same score, every run, every machine: there is no LLM judge, no sampling, and no network call. Every metric is normalized to `[0.0, 1.0]` where **1.0 is a perfect match** with the ground truth.

## Table of Contents

- [Why deterministic metrics](#why-deterministic-metrics)
- [The six metrics](#the-six-metrics)
  - [NID / NID-S — text similarity](#nid--nid-s--text-similarity)
  - [TEDS / TEDS-S — table structure](#teds--teds-s--table-structure)
  - [MHS / MHS-S — heading hierarchy](#mhs--mhs-s--heading-hierarchy)
  - [ARD — reading order](#ard--reading-order)
  - [BLEU — n-gram overlap](#bleu--n-gram-overlap)
  - [METEOR — stemmed similarity](#meteor--stemmed-similarity)
- [How scores are computed and reported](#how-scores-are-computed-and-reported)
- [Known metric caveats](#known-metric-caveats)

## Why deterministic metrics

LLM-as-judge evaluation introduces variance, cost, and a dependency on API keys and GPUs. doc-bench deliberately uses only deterministic string/tree/sequence metrics so that:

- results are reproducible across runs and environments,
- evaluation has zero incremental cost and needs no secrets, and
- a regression in a metric is always attributable to the input, never to judge drift.

The metric implementations live in [`src/doc_bench/metrics/parsing/`](../../src/doc_bench/metrics/parsing/). The vendored generator keeps a byte-identical copy of these files, protected by the [drift guard](../docling-baseline/guards.md).

## The six metrics

Each metric compares the **gold markdown** (rendered from ground-truth annotations) against the **prediction markdown** (rendered from the parser's `parser_output` JSON).

### NID / NID-S — text similarity

**Normalized Indel Distance.** Measures how close the predicted text is to the gold text as a normalized insertion/deletion edit distance, reported as a similarity (1.0 = identical text).

- **NID** scores the full rendered markdown.
- **NID-S** scores a "structure-stripped" variant, isolating text fidelity from table markup.

Backed by `rapidfuzz`. NID is the headline text-quality number for most documents.

### TEDS / TEDS-S — table structure

**Tree Edit Distance Similarity.** Parses tables out of both gold and prediction markdown, builds tree representations, and computes a normalized tree-edit-distance similarity.

- **TEDS** accounts for both table structure and cell content.
- **TEDS-S** accounts for structure only.

Backed by `apted`. TEDS only produces a meaningful score when **both** gold and prediction contain markdown tables (`| ... |`). If the gold has no markdown tables, TEDS is 0 — see [caveats](#known-metric-caveats).

### MHS / MHS-S — heading hierarchy

**Markdown Hierarchical Similarity.** Compares the heading outline (`#`, `##`, ...) of gold and prediction to measure how well the parser recovered document structure.

- **MHS** considers heading text and level.
- **MHS-S** considers the structural outline.

Like TEDS, MHS depends on the gold actually containing markdown headings.

### ARD — reading order

**Average Rank Distance.** Measures how well the predicted reading order of content matches the gold order, as a normalized rank distance over the aligned token/element sequence.

### BLEU — n-gram overlap

Token-level n-gram precision with brevity penalty, via `sacrebleu`. Sensitive to exact wording and ordering; complements NID's edit-distance view.

### METEOR — stemmed similarity

Harmonic mean of unigram precision and recall with stemming and synonym matching, via `nltk`. More forgiving than BLEU because of stemming. **Requires NLTK corpora** — run [`doc-bench-setup`](cli-reference.md#doc-bench-setup--provision-nltk-data) if METEOR returns 0.

## How scores are computed and reported

1. Ground-truth annotations are rendered to gold markdown; the prediction JSON is rendered to prediction markdown.
2. Each metric is computed per document.
3. Per-document scores are written to the results CSV; their averages go to the results JSON summary.

Example per-document CSV row:

```csv
query_id,error,nid,nid_s,teds,teds_s,mhs,mhs_s,ard,bleu,meteor
omnidocbench_0,,0.85,0.87,0.92,0.94,0.88,0.90,0.12,0.75,0.68
```

Bundled reference baselines are stored alongside the fixtures (`doc_bench/fixtures/*_results.json`) and documented in [datasets.md](datasets.md#bundled-baseline-scores).

## Known metric caveats

These are properties of the **gold builder**, not parser failures. Document them when reporting numbers so readers do not misinterpret zeros.

- **TEDS / MHS can be 0 on sparse or text-only gold.** If the gold markdown contains no `|` tables or no `#` headings, the table/heading metrics have nothing to compare against and return 0. This is common on OmniDocBench-format gold.
- **OmniDocBench-format gold ignores table cells.** The gold-text builder reads each detection's `text` field and does not expand table `cells`, so table-heavy documents contribute no table text to the gold and score 0 on TEDS/MHS/ARD. See the worked discussion in [adding-a-dataset.md](../docling-baseline/adding-a-dataset.md#gotchas).
- **Page-count alignment matters.** If a prediction covers more pages than the gold (for example a 6-page PDF graded against 2-page gold), the extra predicted text deflates text metrics. Align the source document to the gold's page coverage.
- **METEOR needs NLTK data.** A METEOR of exactly 0 across all documents usually means the corpora are missing — run `doc-bench-setup`.
