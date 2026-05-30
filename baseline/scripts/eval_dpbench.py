#!/usr/bin/env python3
"""
Evaluate dp-bench PDFs with docling parser.

Usage:
    uv run python baseline/scripts/eval_dpbench.py
    python baseline/scripts/eval_dpbench.py  # in container
"""
import json

# Force CPU usage for docling
import os
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["DOCLING_DEVICE"] = "cpu"

# Add src to path (handles both repo and container contexts)
script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from doc_bench.adapters.parser_adapter import docling_parse
from doc_bench.datasets.dp_bench import build_gold_markdown
from doc_bench.metrics.parsing.markdown_converter import parser_output_to_markdown
from doc_bench.metrics.parsing.mhs import evaluate_heading_level
from doc_bench.metrics.parsing.nid import evaluate_reading_order as evaluate_nid
from doc_bench.metrics.parsing.reading_order import ard_score
from doc_bench.metrics.parsing.table_teds import evaluate_table
from doc_bench.metrics.parsing.text_similarity import bleu_score, meteor_score


def safe_float(x):
    """Convert to float, return 0.0 if None."""
    return round(x, 4) if x is not None else 0.0


def main():
    # Resolve paths relative to repo root
    baseline_dir = repo_root / "baseline"
    dp_bench_dir = baseline_dir / "dp_bench"

    json_file = dp_bench_dir / "reference.json"
    pdfs_dir = dp_bench_dir / "pdfs"

    # Load ground truth
    with open(json_file) as f:
        ref_data = json.load(f)

    # Get all PDFs in the reference (representative set: 12 docs)
    pdf_names = sorted(ref_data.keys())

    print(f"Loaded {len(ref_data)} docs from {json_file}")
    print(f"Evaluating all {len(pdf_names)} docs")

    results = []
    errors = 0

    for idx, pdf_name in enumerate(pdf_names):
        pdf_path = pdfs_dir / pdf_name

        query_id = f"dpbench_{idx}"

        print(f"\n[{idx+1}/{len(pdf_names)}] Processing: {pdf_name}")

        if not pdf_path.exists():
            print(f"  ERROR: PDF not found: {pdf_path}")
            errors += 1
            results.append({
                "query_id": query_id,
                "pdf": pdf_name,
                "error": "PDF not found",
                "nid": 0.0, "nid_s": 0.0,
                "teds": 0.0, "teds_s": 0.0,
                "mhs": 0.0, "mhs_s": 0.0,
                "ard": 0.0,
                "bleu": 0.0, "meteor": 0.0,
            })
            continue

        try:
            # Build gold markdown from reference (shared function with grader)
            gt_markdown = build_gold_markdown(ref_data[pdf_name])

            if not gt_markdown:
                print("  WARNING: No gold text found")
                results.append({
                    "query_id": query_id,
                    "pdf": pdf_name,
                    "error": "No gold text",
                    "nid": 0.0, "nid_s": 0.0,
                    "teds": 0.0, "teds_s": 0.0,
                    "mhs": 0.0, "mhs_s": 0.0,
                    "ard": 0.0,
                    "bleu": 0.0, "meteor": 0.0,
                })
                errors += 1
                continue

            print(f"  Gold markdown length: {len(gt_markdown)} chars")

            # Parse PDF with docling
            print("  Parsing with docling...")
            output = docling_parse(pdf_path)

            # Convert to markdown
            pred_markdown = parser_output_to_markdown(output)
            print(f"  Pred markdown length: {len(pred_markdown)} chars")

            # Calculate metrics
            nid, nid_s = evaluate_nid(gt_markdown, pred_markdown)
            teds, teds_s = evaluate_table(gt_markdown, pred_markdown)
            mhs, mhs_s = evaluate_heading_level(gt_markdown, pred_markdown)
            ard = ard_score(gt_markdown.split(), pred_markdown.split())
            bleu = bleu_score(gt_markdown, pred_markdown)
            meteor = meteor_score(gt_markdown, pred_markdown)

            result = {
                "query_id": query_id,
                "pdf": pdf_name,
                "error": "",
                "nid": safe_float(nid),
                "nid_s": safe_float(nid_s),
                "teds": safe_float(teds),
                "teds_s": safe_float(teds_s),
                "mhs": safe_float(mhs),
                "mhs_s": safe_float(mhs_s),
                "ard": safe_float(ard),
                "bleu": safe_float(bleu),
                "meteor": safe_float(meteor),
            }
            results.append(result)

            # Print metrics
            print(f"  NID: {result['nid']} | NID_s: {result['nid_s']}")
            print(f"  TEDS: {result['teds']} | TEDS_s: {result['teds_s']}")
            print(f"  MHS: {result['mhs']} | MHS_s: {result['mhs_s']}")
            print(f"  ARD: {result['ard']}")
            print(f"  BLEU: {result['bleu']}")
            print(f"  METEOR: {result['meteor']}")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            errors += 1
            results.append({
                "query_id": query_id,
                "pdf": pdf_name,
                "error": str(e),
                "nid": 0.0, "nid_s": 0.0,
                "teds": 0.0, "teds_s": 0.0,
                "mhs": 0.0, "mhs_s": 0.0,
                "ard": 0.0,
                "bleu": 0.0, "meteor": 0.0,
            })

    # Calculate averages
    print("\n" + "="*60)
    print("DP-BENCH EVALUATION RESULTS (DOCLING)")
    print("="*60)

    metrics = ["nid", "nid_s", "teds", "teds_s", "mhs", "mhs_s", "ard", "bleu", "meteor"]

    valid_results = [r for r in results if not r.get("error")]
    print(f"\nTotal docs: {len(pdf_names)}")
    print(f"Successful: {len(valid_results)}")
    print(f"Errors: {errors}")

    if valid_results:
        print("\nMetric averages:")
        for metric in metrics:
            avg = sum(r[metric] for r in valid_results) / len(valid_results)
            print(f"  {metric:8s}: {avg:.4f}")

    # Save JSON results
    output_file = dp_bench_dir / "dpbench_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "total": len(pdf_names),
            "successful": len(valid_results),
            "errors": errors,
            "averages": {m: round(sum(r[m] for r in valid_results)/len(valid_results), 4) if valid_results else 0.0 for m in metrics},
            "results": results,
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
