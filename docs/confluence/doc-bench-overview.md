# doc-bench: Why We Need It and How It Works

> **Audience:** Engineering, ML, and document-processing teams
> **Status:** Living document
> **TL;DR:** doc-bench is our shared, reproducible scoreboard for document-parsing quality. It grades any parser's output against public benchmarks using deterministic metrics — no GPUs, no API keys, no LLM judges — so two people on two machines always get the same number. Install it, run the smoke test, grade your predictions.

---

## Table of Contents

- [The problem we kept hitting](#the-problem-we-kept-hitting)
- [What doc-bench is](#what-doc-bench-is)
- [Why it is required](#why-it-is-required)
- [How it works](#how-it-works)
- [What it measures](#what-it-measures)
- [What ships in the box](#what-ships-in-the-box)
- [Where the baseline numbers come from](#where-the-baseline-numbers-come-from)
- [Getting started in five minutes](#getting-started-in-five-minutes)
- [What doc-bench is not](#what-doc-bench-is-not)
- [FAQ](#faq)
- [Where to go next](#where-to-go-next)

---

## The problem we kept hitting

Document parsing is everywhere in our stack — extracting text, tables, and structure from PDFs and scanned forms. But "is the parser good?" turned into an argument every time, because:

- **Everyone measured differently.** One team eyeballed a few PDFs, another counted table cells, a third quoted a vendor's published number. None of the numbers were comparable.
- **Results were not reproducible.** Evaluations that depended on an LLM-as-judge, a particular GPU, or a hosted API gave a different answer each run and could not be reproduced in CI or on a teammate's laptop.
- **Evaluation was expensive and tightly coupled.** Re-running a heavy parser just to re-test a scoring tweak burned hours, and parser predictions were thrown away, so failures were hard to inspect.
- **Regressions slipped through.** With no shared gate, a model change that quietly degraded table extraction could ship unnoticed.

The cost of this was real: we could not objectively verify parser-quality claims, could not compare options fairly, and could not put a quality check in CI.

## What doc-bench is

doc-bench is a **deterministic, CPU-only, secret-free evaluation framework for document parsers.** You give it your parser's output; it scores that output against public benchmarks and produces the same numbers every time, on every machine.

It is distributed as a small pip wheel with everything needed to run bundled inside — no downloads required to get started.

## Why it is required

| Pain | How doc-bench removes it |
|------|--------------------------|
| Incomparable, ad-hoc metrics | One standard set of six metrics, applied identically to every parser. |
| Non-reproducible scores | Deterministic metrics: same input always yields the same score. No judge variance, no sampling. |
| Needs GPUs / API keys / secrets | Runs on any CPU with no credentials. Safe for CI and local laptops. |
| Expensive re-runs | File-based grading: run the parser once, write predictions to disk, re-grade for free as often as you like. |
| Hard-to-debug failures | Predictions are plain JSON files you can open and inspect; ungradable ones are reported with explicit reason codes, not silently dropped. |
| No quality gate in CI | A seconds-long smoke test with a clear pass/fail exit code drops straight into a pipeline. |

In short: **doc-bench turns "parser quality" from an opinion into a number the whole team trusts.**

## How it works

doc-bench runs **file-based evaluation**. Your parser and the scorer are decoupled: the parser runs separately and writes one prediction file per document; doc-bench only scores those files against ground truth.

```
   ground truth (benchmark)          your predictions (<doc_id>.json)
                  \                   /
                   \                 /
                    v               v
            doc-bench deterministic metrics
                        |
                        v
     per-document CSV   +   summary JSON (averages)   +   rejected CSV
```

The workflow is three steps:

1. **Export** the benchmark documents (`doc-bench-dump-dataset`). This also fixes the naming contract: a prediction for `01030000000001.pdf` must be written as `01030000000001.json`.
2. **Predict** — run your own parser over those documents and write each result as a JSON file conforming to the published `ParserOutput` schema.
3. **Grade** — point doc-bench at the predictions directory (`doc-bench --dataset ... --predictions ...`). It renders both the ground truth and your predictions to a common form, computes the six metrics per document, and writes results.

Predictions that are missing, malformed, or fail schema validation are not crashes — they are recorded as **rejections** with a reason code (`MISSING_PREDICTION`, `INVALID_JSON`, `INVALID_SCHEMA`, `EVALUATION_ERROR`), so a broken run is obvious rather than silently optimistic.

Because the parser step is separate, the same predictions can be graded repeatedly while you iterate on scoring or compare against baselines — without paying the parser's cost again.

## What it measures

Six deterministic metrics, each normalized to `[0.0, 1.0]` where **1.0 is a perfect match**:

| Metric | What it captures |
|--------|------------------|
| **NID** | Text similarity (normalized edit distance) |
| **TEDS** | Table structure (tree-edit distance over table grids) |
| **MHS** | Heading hierarchy (document outline) |
| **ARD** | Reading order |
| **BLEU** | N-gram overlap with the gold text |
| **METEOR** | Stemmed precision/recall |

These cover the dimensions that matter for parsing quality: did we get the *text*, the *tables*, the *structure*, and the *order* right? Each is computed by a small, well-understood algorithm — never by a model — so a score change is always traceable to an input change.

## What ships in the box

The wheel bundles **33 documents** plus their ground truth and a reference scoreboard, so the smoke test and examples run with zero downloads:

| Benchmark | Bundled docs | What it is |
|-----------|-------------:|------------|
| DP-Bench | 16 | Digital-PDF benchmark (paragraphs, captions, charts, headings, indices); includes a few deliberately hard PDFs for robustness testing. |
| OmniDocBench | 16 | Multi-type document pages (academic literature, books, textbooks, exam papers, slide conversions). |
| ATO-Bench | 1 | An Australian Tax Office form (2-page individual income tax return) representing real-world government forms. |

Each benchmark has known characteristics we document honestly (for example, DP-Bench gold is single-page; OmniDocBench annotations are sparse), so nobody misreads a score.

## Where the baseline numbers come from

doc-bench also ships **reference baseline scores** — what a known parser (Docling) achieves on the bundled set — so you have something to compare against out of the box.

Those baseline numbers are produced by a separate, in-repo tool called **docling-baseline**. It is important to understand the split:

- **docling-baseline produces** the baseline-score fixtures. It is heavy (it pulls the full Docling/torch stack), runs only on demand by maintainers, and is **never shipped in the doc-bench wheel** and **never a runtime dependency**.
- **doc-bench consumes and ships** those fixtures and does the day-to-day grading. It is light and has nothing to do with Docling at runtime.

This separation is enforced automatically by two CI guards — one proves the heavy generator can never leak into the shipped wheel, the other proves the metric definitions stay consistent between the two tools. The upshot for the team: **the baseline numbers are reproducible and trustworthy, and installing doc-bench never drags in a multi-gigabyte ML stack.**

## Getting started in five minutes

```bash
# Install (bundled fixtures + schema included)
pip install doc_bench-0.1.0-py3-none-any.whl

# Confirm it works against the 33 bundled documents
doc-bench-smoke-test          # exits 0 on pass; prints a per-type breakdown

# Grade your own parser's predictions
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results
```

If METEOR reports 0 on first use, run `doc-bench-setup` once to fetch the small NLTK corpora it needs.

Working from a source checkout instead of the wheel? Prefix commands with `uv run` (for example `uv run doc-bench-smoke-test`).

## What doc-bench is not

To set expectations clearly:

- **It is not a parser.** It does not extract anything; it grades what your parser extracted.
- **It is not an LLM-judge / "vibes" evaluator.** Every score is a deterministic algorithm.
- **It is not a full-dataset license bundle.** It ships a small bundled sample for instant use; full datasets are downloaded on demand with pinned versions.
- **The bundled sample is a smoke test, not a statistical benchmark.** Use the full datasets for headline quality numbers.

## FAQ

**Do I need a GPU or any API keys?**
No. It runs on any CPU with no credentials. That is the point.

**Can I evaluate a parser that is not Docling?**
Yes. doc-bench grades *any* parser — it only needs prediction files in the `ParserOutput` JSON format. Docling is just the reference baseline.

**Why are some scores (e.g. TEDS) zero on certain documents?**
Some benchmarks' ground truth contains no markdown tables or headings, so the table/heading metrics have nothing to compare against. This is a property of the benchmark's annotations, not a parser failure — we document these cases explicitly.

**Will the same predictions always get the same scores?**
Yes — that is the core guarantee. No variance across runs or machines.

**Can I put this in CI?**
Yes. The smoke test returns a clear pass/fail exit code in seconds, and grading produces machine-readable CSV/JSON.

## Where to go next

The full technical documentation lives in the repository:

- **Start here:** `docs/README.md` (the documentation index)
- **CLI reference:** `docs/doc-bench/cli-reference.md`
- **Metrics in depth:** `docs/doc-bench/metrics.md`
- **The prediction contract:** `docs/doc-bench/parser-output.md`
- **Hands-on:** `examples/` (runnable scripts) and `notebooks/` (Jupyter walkthroughs)
- **For maintainers — the baseline generator:** `docs/docling-baseline/overview.md`
