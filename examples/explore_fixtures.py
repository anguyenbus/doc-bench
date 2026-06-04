"""Inspect the bundled fixture set: list datasets, doc counts, and one sample each.

Reads the bundled manifest.json (no downloads) and prints the composition of the
33 bundled documents.

Run:
    uv run python examples/explore_fixtures.py
"""

from __future__ import annotations

import json
from collections import Counter
from importlib.resources import files


def main() -> None:
    """Summarize the bundled fixtures from the packaged manifest."""
    fixtures = files("doc_bench") / "fixtures"
    manifest = json.loads((fixtures / "manifest.json").read_text())

    print(f"manifest: {manifest.get('name')} -- total docs: {manifest.get('total')}\n")

    for dataset in ("dp_bench", "omnidocbench", "ato_bench"):
        entries = manifest.get(dataset, [])
        print(f"=== {dataset} ({len(entries)} docs) ===")

        # DP-Bench groups by 'category'; the others by 'doc_type'.
        key = "category" if dataset == "dp_bench" else "doc_type"
        counts = Counter(e.get(key, "unknown") for e in entries)
        for label, n in sorted(counts.items()):
            print(f"  {label:32} {n}")

        if entries:
            print(f"  sample entry: {json.dumps(entries[0])}")
        print()


if __name__ == "__main__":
    main()
