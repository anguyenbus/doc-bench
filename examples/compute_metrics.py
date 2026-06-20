"""
Compute each of the six doc-bench metrics directly on toy markdown inputs.

This shows what every metric rewards, without needing a dataset. Metrics operate
on rendered markdown strings (NID/TEDS/MHS/BLEU/METEOR); ARD operates on two
ordered sequences.

Run:
    uv run python examples/compute_metrics.py
"""

from __future__ import annotations

from doc_bench.metrics.parsing.mhs import mhs_s_score, mhs_score
from doc_bench.metrics.parsing.nid import nid_s_score, nid_score
from doc_bench.metrics.parsing.reading_order import ard_score
from doc_bench.metrics.parsing.text_similarity import bleu_score, meteor_score

from doc_bench.metrics.parsing.table_teds import teds_s_score, teds_score

GOLD = """# Quarterly Report

## Revenue

Revenue grew across all regions this quarter.

| Region | Revenue |
| --- | --- |
| North | 100 |
| South | 80 |
"""

# A "good" prediction: same structure, one cell value off.
PRED_GOOD = """# Quarterly Report

## Revenue

Revenue grew across all regions this quarter.

| Region | Revenue |
| --- | --- |
| North | 100 |
| South | 85 |
"""

# A "poor" prediction: flattened, no headings or table.
PRED_POOR = "Quarterly Report Revenue Revenue grew across regions. North 100 South 80"


def show(label: str, gold: str, pred: str) -> None:
    """Print all six metrics comparing one prediction against gold."""
    print(f"--- {label} ---")
    print(f"  NID    {nid_score(gold, pred):.4f}   NID-S  {nid_s_score(gold, pred):.4f}")
    print(f"  TEDS   {teds_score(gold, pred):.4f}   TEDS-S {teds_s_score(gold, pred):.4f}")
    print(f"  MHS    {mhs_score(gold, pred):.4f}   MHS-S  {mhs_s_score(gold, pred):.4f}")
    print(f"  BLEU   {bleu_score(gold, pred):.4f}")
    print(f"  METEOR {meteor_score(gold, pred):.4f}")
    # ARD compares ordered sequences; here we use whitespace tokens.
    print(f"  ARD    {ard_score(pred.split(), gold.split()):.4f}")
    print()


def main() -> None:
    """Score a good and a poor prediction against the same gold."""
    show("good prediction (structure preserved)", GOLD, PRED_GOOD)
    show("poor prediction (flattened text)", GOLD, PRED_POOR)
    print("Notes:")
    print("  - METEOR needs NLTK data; run `doc-bench-setup` if it reads 0.")
    print("  - TEDS reads 0 here because its table parser is stricter than a plain")
    print("    pipe-table; see docs/doc-bench/metrics.md for when TEDS is meaningful.")


if __name__ == "__main__":
    main()
