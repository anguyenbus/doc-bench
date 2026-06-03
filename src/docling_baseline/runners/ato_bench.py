"""
ATO-Bench evaluation runner.

ATO-Bench contains 5 multi-page PDF forms with page-level ground truth
annotations in OmniDocBench format.
"""

import json
import re
from pathlib import Path
from typing import Any

from docling_baseline.runners.base import BaseRunner
from docling_baseline.runners.omnidocbench import extract_gold_text_from_omnidocbench


def _sort_page_files(page_files: list[str]) -> list[str]:
    """Sort page files by page number (p1, p2, p3, ...)."""
    def page_number(file_path: str) -> int:
        match = re.search(r"_p(\d+)", file_path)
        if match:
            return int(match.group(1))
        return 0
    return sorted(page_files, key=page_number)


class ATOBenchRunner(BaseRunner):
    """Evaluation runner for ATO-Bench dataset."""

    def get_dataset_name(self) -> str:
        """Return 'ato_bench'."""
        return "ato_bench"

    def evaluate(self) -> dict[str, Any]:
        """
        Run ATO-Bench evaluation.

        ATO-Bench is multi-page. We combine all page gold annotations into
        one document-level gold, then compare against full PDF prediction.

        Returns:
            Dict with evaluation results.

        """
        items = self.manifest.get("ato_bench", [])
        ato_dir = self.fixtures_dir / "ato_bench"

        print(f"=== ATO-BENCH ({len(items)} docs, multi-page) ===")

        all_doc_results = []

        for item in items:
            doc_id = item["doc_id"]
            pdf_path = ato_dir / item["pdf"].split("/")[-1]
            doc_type = item.get("doc_type", "")

            # Find all page JSON files for this document
            page_pattern = f"{doc_id}_p*.json"
            page_files = sorted(ato_dir.glob(page_pattern))

            print(f"\n[{doc_id}] {doc_type} - {len(page_files)} pages")

            if not page_files:
                print(f"  SKIP: no page JSONs found")
                continue

            # Generate prediction for entire PDF
            if not pdf_path.exists():
                print(f"  SKIP: PDF not found")
                continue

            prediction = self.generate_prediction(pdf_path)
            if prediction is None:
                continue

            pred_markdown = self.prediction_to_markdown(prediction)

            # Combine all page gold annotations into one document
            combined_gold_parts = []

            for gold_path in page_files:
                with open(gold_path) as f:
                    gold_data = json.load(f)

                page_text = extract_gold_text_from_omnidocbench(gold_data)
                if page_text:
                    combined_gold_parts.append(page_text)

            combined_gold = " ".join(combined_gold_parts)

            if not combined_gold or not pred_markdown:
                print(f"  SKIP: empty gold or prediction")
                continue

            # Calculate metrics on document level
            metrics = self.calculate_metrics(combined_gold, pred_markdown)

            result = {
                "query_id": doc_id,
                "doc_id": doc_id,
                "doc_type": doc_type,
                "error": "",
                **metrics,
            }
            all_doc_results.append(result)

            print(f"  NID={metrics['nid']} BLEU={metrics['bleu']} METEOR={metrics['meteor']} MHS={metrics['mhs']} ARD={metrics['ard']}")

        # Calculate averages
        averages = self.compute_averages(all_doc_results)

        print(f"\n--- ATO-BENCH AVERAGES ({len(all_doc_results)} docs) ---")
        for metric, value in averages.items():
            print(f"  {metric:8s}: {value}")

        return {
            "total": len(all_doc_results),
            "successful": len(all_doc_results),
            "errors": 0,
            "averages": averages,
            "results": all_doc_results,
        }
