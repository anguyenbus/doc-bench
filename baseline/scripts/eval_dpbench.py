#!/usr/bin/env python3
"""
Evaluate dp-bench PDFs with docling parser.

Usage:
    uv run python eval_dpbench.py
"""
import json
import sys
from pathlib import Path

# Force CPU usage for docling
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["DOCLING_DEVICE"] = "cpu"

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stubs.docling_parser import parse as docling_parse
from eval_harness.metrics.parsing.nid import evaluate_reading_order as evaluate_nid
from eval_harness.metrics.parsing.table_teds import evaluate_table
from eval_harness.metrics.parsing.mhs import evaluate_heading_level
from eval_harness.metrics.parsing.reading_order import ard_score
from eval_harness.metrics.parsing.text_similarity import bleu_score, meteor_score
from eval_harness.metrics.parsing.markdown_converter import parser_output_to_markdown


def extract_gold_text(doc_data: dict) -> str:
    """Extract gold text from dp-bench document annotations."""
    elements = doc_data.get("elements", [])

    # Sort by page, then by reading order (dp-bench uses coordinates)
    def sort_key(x):
        page = x.get("page", 0)
        # Use top-left coordinate for rough reading order
        coords = x.get("coordinates", [])
        if coords:
            y = coords[0].get("y", 0)
            x = coords[0].get("x", 0)
            return (page, y, x)
        return (page, 0, 0)

    sorted_elements = sorted(elements, key=sort_key)

    # Extract text
    texts = []
    for elem in sorted_elements:
        content = elem.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""
        if text:
            texts.append(text)

    return " ".join(texts)


def safe_float(x):
    """Convert to float, return 0.0 if None."""
    return round(x, 4) if x is not None else 0.0


def main():
    base_dir = Path("/home/an/atoprojects/evaluation/baseline_images")
    dp_bench_root = Path("/home/an/projects/docbenchmark/references/dp-bench/dataset")

    json_file = dp_bench_root / "reference.json"
    pdfs_dir = base_dir  # Use local PDFs

    # Load ground truth
    with open(json_file) as f:
        ref_data = json.load(f)

    # Get first 10 PDFs
    pdf_names = sorted(ref_data.keys())[:10]

    print(f"Loaded {len(ref_data)} docs from {json_file}")
    print(f"Evaluating first {len(pdf_names)} docs")

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
                "error": f"PDF not found",
                "nid": 0.0, "nid_s": 0.0,
                "teds": 0.0, "teds_s": 0.0,
                "mhs": 0.0, "mhs_s": 0.0,
                "ard": 0.0,
                "bleu": 0.0, "meteor": 0.0,
            })
            continue

        try:
            # Extract gold text
            gold_text = extract_gold_text(ref_data[pdf_name])

            if not gold_text:
                print(f"  WARNING: No gold text found")
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

            print(f"  Gold text length: {len(gold_text)} chars")

            # Parse PDF with docling
            print(f"  Parsing with docling...")
            output = docling_parse(pdf_path)

            # Convert to markdown
            pred_markdown = parser_output_to_markdown(output)
            print(f"  Pred text length: {len(pred_markdown)} chars")

            # Calculate metrics
            nid, nid_s = evaluate_nid(gold_text, pred_markdown)
            teds, teds_s = evaluate_table(gold_text, pred_markdown)
            mhs, mhs_s = evaluate_heading_level(gold_text, pred_markdown)
            ard = ard_score(gold_text.split(), pred_markdown.split())
            bleu = bleu_score(gold_text, pred_markdown)
            meteor = meteor_score(gold_text, pred_markdown)

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
    print("DP-BENCH EVALUATION RESULTS (DOCILING)")
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
    output_file = base_dir / "dpbench_results.json"
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
