# Notebooks

Interactive Jupyter walkthroughs for doc-bench. Like the [examples](../examples/README.md), every notebook runs against the **bundled fixtures** — no downloads. All code cells are verified to execute against an installed `doc_bench`.

## Notebooks

| Notebook | What you learn |
|----------|----------------|
| [01_explore_fixtures.ipynb](01_explore_fixtures.ipynb) | Read the packaged `manifest.json`, see the 33-document composition, and peek at a ground-truth annotation. |
| [02_understand_metrics.ipynb](02_understand_metrics.ipynb) | Compute the six metrics on toy inputs to build intuition for what each rewards. |
| [03_grade_and_compare.ipynb](03_grade_and_compare.ipynb) | Build a schema-valid prediction, validate it, and compare against the bundled baseline scores. |

## Running them

Install Jupyter and launch from the repo root:

```bash
uv run --with jupyter jupyter lab
# or
uv run --with jupyter jupyter notebook
```

Then open a notebook and run all cells. The kernel must have `doc_bench` importable — running from a source checkout via `uv` satisfies this. If METEOR shows 0, run `doc-bench-setup` once to provision the NLTK corpora.

## See also

- [docs/doc-bench/metrics.md](../docs/doc-bench/metrics.md) — the metrics in depth.
- [docs/doc-bench/parser-output.md](../docs/doc-bench/parser-output.md) — the prediction contract.
- [examples/](../examples/README.md) — the same ideas as standalone scripts.
