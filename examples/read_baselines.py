"""
Load the bundled baseline-score fixtures that ship inside the doc-bench wheel.

These reference scores let you compare a parser's results against the documented
Docling baseline without re-running anything.

Run:
    uv run python examples/read_baselines.py
"""

from __future__ import annotations

import json
from importlib.resources import files

# Baseline files bundled at doc_bench/fixtures/<name>_results.json.
BASELINES = {
    "DP-Bench": "dpbench_results.json",
    "OmniDocBench": "omnidocbench_results.json",
    "ATO-Bench": "ato_bench_results.json",
}

METRICS = ["nid", "teds", "mhs", "ard", "bleu", "meteor"]


def main() -> None:
    """Print the bundled baseline averages as a small table."""
    fixtures = files("doc_bench") / "fixtures"

    header = f"{'dataset':14} " + " ".join(f"{m:>8}" for m in METRICS) + f" {'docs':>5}"
    print(header)
    print("-" * len(header))

    for label, filename in BASELINES.items():
        data = json.loads((fixtures / filename).read_text())
        avg = data.get("averages", {})
        row = f"{label:14} " + " ".join(f"{avg.get(m, 0.0):>8.4f}" for m in METRICS)
        row += f" {data.get('total', 0):>5}"
        print(row)


if __name__ == "__main__":
    main()
