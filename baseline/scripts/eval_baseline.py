#!/usr/bin/env python3
"""
Evaluate baseline PPT images with docling parser.

Usage:
    uv run python eval_baseline.py
"""
import json
import sys
from pathlib import Path

# Force CPU usage for docling
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["DOCLING_DEVICE"] = "cpu"

# Add src to path (handles both repo and container contexts)
script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
sys.path.insert(0, str(repo_root / "src"))

from doc_bench.stubs.docling_parser import parse as docling_parse
from doc_bench.metrics.parsing.nid import evaluate_reading_order as evaluate_nid
from doc_bench.metrics.parsing.table_teds import evaluate_table
from doc_bench.metrics.parsing.mhs import evaluate_heading_level
from doc_bench.metrics.parsing.reading_order import ard_score
from doc_bench.metrics.parsing.text_similarity import bleu_score, meteor_score
from doc_bench.metrics.parsing.markdown_converter import parser_output_to_markdown


# Resolve paths relative to repo root
script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent


def extract_gold_text(page: dict) -> str:
    """Extract gold text from OmniDocBench page annotations."""
    layout_dets = page.get("layout_dets", [])

    # Sort by order field, handling None values
    def sort_key(x):
        order = x.get("order")
        if order is None:
            return float("inf")
        return order

    sorted_dets = sorted(layout_dets, key=sort_key)

    # Extract text, maintaining order
    texts = []
    for det in sorted_dets:
        text = det.get("text", "")
        if text:
            texts.append(text)

    return " ".join(texts)


def safe_float(x):
    """Convert to float, return 0.0 if None."""
    return round(x, 4) if x is not None else 0.0


def main():
    # Resolve paths relative to repo root
    baseline_dir = repo_root / "baseline"
    omnidir = baseline_dir / "omnidocbench"
    json_file = omnidir / "OmniDocBench.json"

    # Load ground truth
    with open(json_file) as f:
        pages = json.load(f)

    print(f"Loaded {len(pages)} pages from {json_file}")

    results = []
    errors = 0

    for idx, page in enumerate(pages):
        page_info = page.get("page_info", {})
        image_name = page_info.get("image_path", "")
        image_path = omnidir / image_name

        query_id = f"baseline_{idx}"

        print(f"\n[{idx+1}/{len(pages)}] Processing: {image_name}")

        if not image_path.exists():
            print(f"  ERROR: Image not found: {image_path}")
            errors += 1
            results.append({
                "query_id": query_id,
                "image": image_name,
                "error": f"Image not found",
                "nid": 0.0, "nid_s": 0.0,
                "teds": 0.0, "teds_s": 0.0,
                "mhs": 0.0, "mhs_s": 0.0,
                "ard": 0.0,
                "bleu": 0.0, "meteor": 0.0,
            })
            continue

        try:
            # Extract gold text
            gold_text = extract_gold_text(page)

            if not gold_text:
                print(f"  WARNING: No gold text found")
                results.append({
                    "query_id": query_id,
                    "image": image_name,
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

            # Parse image with docling
            print(f"  Parsing with docling...")
            output = docling_parse(image_path)

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
                "image": image_name,
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
            errors += 1
            results.append({
                "query_id": query_id,
                "image": image_name,
                "error": str(e),
                "nid": 0.0, "nid_s": 0.0,
                "teds": 0.0, "teds_s": 0.0,
                "mhs": 0.0, "mhs_s": 0.0,
                "ard": 0.0,
                "bleu": 0.0, "meteor": 0.0,
            })

    # Calculate averages
    print("\n" + "="*60)
    print("BASELINE EVALUATION RESULTS")
    print("="*60)

    metrics = ["nid", "nid_s", "teds", "teds_s", "mhs", "mhs_s", "ard", "bleu", "meteor"]

    valid_results = [r for r in results if not r.get("error")]
    print(f"\nTotal pages: {len(pages)}")
    print(f"Successful: {len(valid_results)}")
    print(f"Errors: {errors}")

    if valid_results:
        print("\nMetric averages:")
        for metric in metrics:
            avg = sum(r[metric] for r in valid_results) / len(valid_results)
            print(f"  {metric:8s}: {avg:.4f}")

    # Save JSON results
    output_file = omnidir / "omnidocbench_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "total": len(pages),
            "successful": len(valid_results),
            "errors": errors,
            "averages": {m: round(sum(r[m] for r in valid_results)/len(valid_results), 4) if valid_results else 0.0 for m in metrics},
            "results": results,
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
