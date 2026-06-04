# CI Guards for the Vendored Generator

The vendored generator keeps a **second copy** of the metric code and the
`parser_output` schema, and it lives as a sibling of the production package. Two
CI guards protect against the two ways that arrangement can go wrong: silent
metric drift, and the generator leaking into the shipped wheel. This document
explains both guards in detail. For context, see
[overview.md](./overview.md) and [architecture.md](./architecture.md).

## Table of contents

- [Running the guards](#running-the-guards)
- [Drift guard](#drift-guard)
  - [What it prevents](#what-it-prevents)
  - [What it checks](#what-it-checks)
  - [The pinned allow-list](#the-pinned-allow-list)
  - [When it fires: remediation](#when-it-fires-remediation)
- [Wheel-leak guard](#wheel-leak-guard)
  - [What it proves](#what-it-proves)
  - [Structural enforcement](#structural-enforcement)
  - [When it fires: remediation](#when-it-fires-remediation-1)
- [How CI runs both](#how-ci-runs-both)

## Running the guards

| Guard | Test file | How to run |
| --- | --- | --- |
| Drift guard | [`tests/test_metric_drift_guard.py`](../../tests/test_metric_drift_guard.py) | Runs in the fast loop: `make test` (`uv run pytest -q`). |
| Wheel-leak guard | [`tests/test_wheel_no_generator_leak.py`](../../tests/test_wheel_no_generator_leak.py) | Marked `build`, deselected from the default run. Run explicitly: `uv run pytest -m build` or `make test-build`. |

`make ci` runs both guards.

## Drift guard

The drift guard
([`tests/test_metric_drift_guard.py`](../../tests/test_metric_drift_guard.py))
runs in the fast `make test` loop.

### What it prevents

The generator's metric files and schema are a second copy of the same logic
`doc-bench` ships under
[`src/doc_bench/metrics/parsing/`](../../src/doc_bench/metrics/parsing/) and
[`src/doc_bench/fixtures/parser_output.schema.json`](../../src/doc_bench/fixtures/parser_output.schema.json).
Without a guard, the two copies can **silently diverge**: someone edits one
copy, the other is left behind, and now the baseline fixtures are scored by
different code than `doc-bench` uses at runtime. The fixtures would no longer be
a valid reference. The drift guard makes any **unreviewed** divergence fail CI.

### What it checks

It compares each vendored metric file and the schema against its `doc-bench`
counterpart in two classes:

1. **Byte-identical, no allowed delta.** `mhs.py`, `reading_order.py`,
   `text_similarity.py`, and `parser_output.schema.json` must be byte-for-byte
   identical between the vendored copy
   ([`src/docling_baseline/metrics/`](../../src/docling_baseline/metrics/),
   [`src/docling_baseline/schemas/parser_output.schema.json`](../../src/docling_baseline/schemas/parser_output.schema.json))
   and the `doc-bench` copy. A single changed byte fails the test.
2. **Identical core plus an appended legacy alias.** `nid.py` and
   `table_teds.py` are **not** byte-identical, because `doc-bench` appends a
   deprecated legacy-alias function to the end of each file for backward
   compatibility. The guard strips the pinned alias suffix and asserts the
   remaining core matches the vendored file.

### The pinned allow-list

The allow-list is **exactly** the legacy-alias deltas, and nothing else:

| File | Allowed delta |
| --- | --- |
| `nid.py` | Appended legacy alias `normalized_indel_distance`. |
| `table_teds.py` | Appended legacy alias `table_teds`. |
| `mhs.py` | None (must be byte-identical). |
| `reading_order.py` | None (must be byte-identical). |
| `text_similarity.py` | None (must be byte-identical). |
| `parser_output.schema.json` | None (must be byte-identical). |

The alias suffixes are **pinned to exact bytes**: editing the alias text, or
adding any new unlisted trailing content, fails the guard.

### When it fires: remediation

A failure means a vendored metric/schema file diverged from its `doc-bench`
counterpart in a way the allow-list does not permit. To remediate:

1. **Review the divergence.** Identify which file changed and whether the change
   was intentional.
2. **If a `doc-bench` metric was changed intentionally,** mirror the same change
   into the vendored copy under
   [`src/docling_baseline/metrics/`](../../src/docling_baseline/metrics/) (or
   the schema), so the two copies match again.
3. **If the change is to the alias suffix itself** (or is a deliberate new
   allowed delta), update the pinned allow-list in the guard **after review**.

Never silence the guard without doing one of the above; that is precisely the
silent-corruption case it exists to catch.

## Wheel-leak guard

The wheel-leak guard
([`tests/test_wheel_no_generator_leak.py`](../../tests/test_wheel_no_generator_leak.py))
is marked `build` and is deselected from the default `pytest -q` run because
building the wheel is slow.

### What it proves

It builds the actual `doc-bench` wheel with `uv build --wheel` and inspects the
archive members, asserting:

- **Zero** archive paths contain `docling_baseline` (the vendored generator
  never ships).
- **At least one** archive path contains `doc_bench`, so the test fails loudly
  on an empty or garbage build instead of passing vacuously.

### Structural enforcement

The guarantee is enforced by **hatch scoping**, not by the test:

- `[tool.hatch.build.targets.wheel]` sets `packages = ["src/doc_bench"]`.
- `[tool.hatch.build]` `include` globs are scoped to `src/doc_bench/**`.
- `src/docling_baseline/` is a sibling that no glob matches.

The guard proves that scoping holds end-to-end against a real build.

### When it fires: remediation

A failure means `docling_baseline` paths appeared in the wheel (or no
`doc_bench` paths did). Restore the structural scoping in
[`pyproject.toml`](../../pyproject.toml): keep `packages` and the `include`
globs scoped to `src/doc_bench/**`, and ensure nothing was added that pulls the
sibling generator into the build.

## How CI runs both

```bash
make ci
```

`make ci` runs the fast suite (which includes the drift guard) and then
`make test-build` (the wheel-leak guard), so both guards must pass before merge.
