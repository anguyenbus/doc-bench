# doc-bench Overview

## Table of Contents

- [What doc-bench Is](#what-doc-bench-is)
- [What doc-bench Is Not](#what-doc-bench-is-not)
- [Core Concept: Deterministic File-Based Grading](#core-concept-deterministic-file-based-grading)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Consumer vs. Generator Split](#consumer-vs-generator-split)
- [Evaluation Workflow](#evaluation-workflow)
- [Grading Data Flow](#grading-data-flow)
- [Rejection Handling](#rejection-handling)
- [Where Outputs Go](#where-outputs-go)
- [Related Documentation](#related-documentation)

## What doc-bench Is

`doc-bench` is a deterministic, CPU-only, secret-free document-parser evaluation
framework. It grades pre-computed parser predictions against ground-truth
benchmarks and reports six deterministic metrics, each normalised to the `[0, 1]`
interval where `1.0` is a perfect score:

- `NID` (normalised edit distance similarity)
- `TEDS` (tree-edit distance similarity for tables)
- `MHS` (markup/heading similarity)
- `ARD` (average relative distance)
- `BLEU`
- `METEOR`

It is distributed as a pip wheel with bundled fixtures, so a clean install can
run the smoke test and reproduce baseline scores without any network access,
GPU, or credentials. See [metrics.md](metrics.md) for the precise definition of
each metric.

## What doc-bench Is Not

- It is **not** a parser. `doc-bench` does not extract content from PDFs; it
  grades JSON predictions that some other parser produced.
- It does **not** require GPUs, network access, or secrets for core use.
- It does **not** depend on Docling at runtime for core grading. Docling is an
  optional extra (`[docling]`) used only by an optional runtime parser, and is
  the engine behind the *separate* baseline generator (see below).
- There is **no Docker support.** Any older references to a Docker workflow are
  stale and have been removed.

## Core Concept: Deterministic File-Based Grading

`doc-bench` separates the expensive, non-deterministic step (running a parser
over PDFs) from the cheap, deterministic step (scoring). You run your parser
**once**, write one JSON prediction file per document, and then grade those
predictions as many times as you like. Identical inputs always produce identical
scores.

A prediction file must conform to the bundled JSON Schema
`src/doc_bench/fixtures/parser_output.schema.json` (title `ParserOutput`;
required keys `schema_version`, `parser_version`, `source`, `pages`,
`elements`). See [parser-output.md](parser-output.md) for the full schema
walkthrough.

## Architecture at a Glance

The package is organised by responsibility:

- `datasets/` — loaders that read ground-truth fixtures and expose documents by
  `doc_id`.
- `adapters/` — translate parser predictions into the internal representation and
  run JSON Schema validation against `parser_output.schema.json`.
- `metrics/` — the six deterministic scorers (`NID`, `TEDS`, `MHS`, `ARD`,
  `BLEU`, `METEOR`).
- `runners/` and `cli/` — orchestrate loading, validation, scoring, and output
  writing, and expose the command-line entry points.
- `fixtures/` — bundled ground truth, prediction schema, dataset manifest, and
  baseline reference scores, all shipped inside the wheel.

## Consumer vs. Generator Split

`doc-bench` is the **consumer** of baseline fixtures. A separate, vendored
generator named `docling-baseline` is the **producer** that creates the
baseline-score fixtures `doc-bench` ships with. Keeping the two apart is what
lets `doc-bench` stay Docling-free at runtime: the heavy parsing work happens in
the generator, and `doc-bench` only reads the resulting JSON.

For the producer side, see [../docling-baseline/overview.md](../docling-baseline/overview.md).

## Evaluation Workflow

The workflow is three steps: **dump, predict, grade.**

1. **Dump** the dataset to obtain the PDFs and canonical `doc_id`s using
   `doc-bench-dump-dataset`. The PDF stem is the `doc_id` your prediction files
   must be named after; see [../document-identity.md](../document-identity.md).
2. **Predict.** Run your own parser over those PDFs and write one
   `<doc_id>.json` prediction per document into a predictions directory. Each
   file must satisfy `parser_output.schema.json`.
3. **Grade.** Run the main `doc-bench` command against your predictions:

   ```bash
   doc-bench --dataset omnidocbench --predictions ./predictions
   ```

   `--dataset` (one of `omnidocbench`, `dp_bench`, or `ato_bench`) and
   `--predictions` are required. For `ato_bench` the ground truth defaults to the
   bundled fixtures, so no `--data-dir` is needed. Common optional flags include
   `--output-dir` (default
   `results/`), `--data-dir` (override the ground-truth location), `--limit`,
   and `--max-rejection-rate`. The complete flag reference for every entry point
   lives in [cli-reference.md](cli-reference.md).

The other entry points (`doc-bench-smoke-test`, `doc-bench-dump-dataset`,
`doc-bench-download`, `doc-bench-list-datasets`, `doc-bench-setup`) are also
documented in [cli-reference.md](cli-reference.md).

## Grading Data Flow

```
   ground truth (fixtures)        predictions (<doc_id>.json)
            |                              |
            |                       schema validation
            |                              |
            +-------------+----------------+
                          |
                   metrics engine
            (NID, TEDS, MHS, ARD, BLEU, METEOR)
                          |
            +-------------+----------------+
            |                              |
     per-doc CSV                  summary JSON (averages)
                          |
                   rejected CSV (skipped docs)
```

## Rejection Handling

A prediction that cannot be scored is **rejected** rather than silently scored
as zero. Each rejection carries a reason code:

- `MISSING_PREDICTION` — no prediction file for an expected `doc_id`.
- `INVALID_JSON` — the prediction file does not parse as JSON.
- `INVALID_SCHEMA` — the JSON does not satisfy `parser_output.schema.json`.
- `EVALUATION_ERROR` — scoring raised an error for that document.

Rejections are written to a dedicated rejected CSV. The `--max-rejection-rate`
flag lets a run fail fast when too large a share of documents is rejected.

## Where Outputs Go

By default, outputs are written to `results/` (override with `--output-dir`),
timestamped so successive runs do not overwrite each other:

- `{dataset}_{...}_results_{ts}.csv` — per-document metrics.
- `{dataset}_{...}_results_{ts}.json` — run summary including metric averages.
- `{dataset}_{...}_rejected_{ts}.csv` — rejected documents with reason codes.

## Related Documentation

- [cli-reference.md](cli-reference.md) — full flag reference for every entry point.
- [metrics.md](metrics.md) — definitions of the six deterministic metrics.
- [datasets.md](datasets.md) — datasets, bundled fixtures, baselines, and limitations.
- [parser-output.md](parser-output.md) — the `ParserOutput` prediction schema.
- [../document-identity.md](../document-identity.md) — how `doc_id`s are derived.
- [../docling-baseline/overview.md](../docling-baseline/overview.md) — the baseline generator.
