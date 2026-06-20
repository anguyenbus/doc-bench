# Examples

Runnable, self-contained examples for doc-bench. Every script here works against the **bundled fixtures and schema** — no dataset downloads required. From a source checkout, run them with `uv run`.

## Scripts

| Script | What it does | Run |
|--------|--------------|-----|
| [read_baselines.py](read_baselines.py) | Load the bundled baseline-score fixtures and print them as a table. | `uv run python examples/read_baselines.py` |
| [explore_fixtures.py](explore_fixtures.py) | Summarize the 33 bundled documents from the packaged manifest. | `uv run python examples/explore_fixtures.py` |
| [compute_metrics.py](compute_metrics.py) | Compute all six metrics on toy markdown to see what each rewards. | `uv run python examples/compute_metrics.py` |
| [make_prediction.py](make_prediction.py) | Build a schema-valid `ParserOutput` prediction and validate it. | `uv run python examples/make_prediction.py --out predictions/01030000000001.json` |
| [run_smoke_test.sh](run_smoke_test.sh) | Validate the install against the bundled fixtures. | `./examples/run_smoke_test.sh` |

## End-to-end grading

The examples above cover everything except a full grading run, which needs a benchmark's ground truth. The grading workflow is three commands (see [docs/file-based-evaluation.md](../docs/file-based-evaluation.md)):

```bash
# 1. Export documents (defines the <doc_id> filenames)
doc-bench-dump-dataset --dataset dp_bench --output ./pdfs --limit 5

# 2. Produce predictions/<doc_id>.json with your parser.
#    examples/make_prediction.py shows the required JSON shape.

# 3. Grade them
doc-bench --dataset dp_bench --predictions ./predictions --output-dir ./results
```

Results land in `./results/` as a per-document CSV, a summary JSON with averages, and a rejected CSV. See [docs/doc-bench/cli-reference.md](../docs/doc-bench/cli-reference.md) for all flags.

## Next steps

- Walk through the same ideas interactively in the [notebooks](../notebooks/README.md).
- Understand the metrics in depth: [docs/doc-bench/metrics.md](../docs/doc-bench/metrics.md).
- Understand the prediction contract: [docs/doc-bench/parser-output.md](../docs/doc-bench/parser-output.md).
