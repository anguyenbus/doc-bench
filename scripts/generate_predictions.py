"""
Generate parser_output.schema.json prediction files for the bundled fixtures.

Uses the Docling adapter to parse each fixture document, then saves the output
as ``<doc_id>.json`` ready for ``doc-bench --predictions DIR``.

Usage:
    uv run --group generator python scripts/generate_predictions.py [--predictions-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "src" / "doc_bench" / "fixtures"


# Maps dataset name -> list of (doc_id, source_path)
def _fixture_docs() -> dict[str, list[tuple[str, Path]]]:
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    docs: dict[str, list[tuple[str, Path]]] = {}

    # dp_bench: PDFs
    dp = []
    for entry in manifest.get("dp_bench", []):
        doc_id = entry["doc_id"]
        pdf = FIXTURES_DIR / entry["pdf"]
        if pdf.exists():
            dp.append((doc_id, pdf))
    docs["dp_bench"] = dp

    # omnidocbench: images (jpg/png)
    omni = []
    for entry in manifest.get("omnidocbench", []):
        doc_id = entry["doc_id"]
        img = FIXTURES_DIR / entry["image"]
        if img.exists():
            omni.append((doc_id, img))
    docs["omnidocbench"] = omni

    # ato_bench: PDFs
    ato = []
    for entry in manifest.get("ato_bench", []):
        doc_id = entry["doc_id"]
        pdf = FIXTURES_DIR / entry["pdf"]
        if pdf.exists():
            ato.append((doc_id, pdf))
    docs["ato_bench"] = ato

    return docs


def generate(predictions_dir: Path) -> None:
    """
    Parse all bundled fixture documents and write prediction JSON files.

    Args:
        predictions_dir: Output directory for ``<doc_id>.json`` prediction files.

    """
    from docling_baseline.adapters.docling import parse

    predictions_dir.mkdir(parents=True, exist_ok=True)
    fixture_docs = _fixture_docs()

    for dataset, items in fixture_docs.items():
        print(f"\n--- {dataset} ({len(items)} docs) ---")
        for doc_id, source_path in items:
            out_path = predictions_dir / f"{doc_id}.json"
            if out_path.exists():
                print(f"  [skip] {doc_id} (already exists)")
                continue
            print(f"  Parsing {doc_id} from {source_path.name}...", end=" ", flush=True)
            try:
                prediction = parse(source_path)
                out_path.write_text(json.dumps(prediction, indent=2))
                print("ok")
            except Exception as e:
                print(f"FAILED: {e}")


def main() -> int:
    """Entry point: parse CLI args and call generate()."""
    parser = argparse.ArgumentParser(
        description="Generate Docling predictions for bundled fixtures"
    )
    parser.add_argument(
        "--predictions-dir",
        type=Path,
        default=Path("/tmp/doc-bench-predictions"),
        help="Output directory for prediction JSON files",
    )
    args = parser.parse_args()

    print(f"Generating predictions -> {args.predictions_dir}")
    generate(args.predictions_dir)
    print(f"\nDone. Predictions written to: {args.predictions_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
