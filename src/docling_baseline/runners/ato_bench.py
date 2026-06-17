"""
ATO-Bench evaluation runner.

ATO-Bench contains multi-page Australian Tax Office form PDFs. Each document
has a single ParserOutput-format gold JSON (``{"pages", "elements"}``) referenced
via the ``gold`` key in the manifest.
"""

import json
from pathlib import Path
from typing import Any

from doc_bench.datasets.ato_bench import _extract_gold_text
from docling_baseline.runners.base import BaseRunner


class ATOBenchRunner(BaseRunner):
    """Evaluation runner for ATO-Bench dataset."""

    def get_dataset_name(self) -> str:
        """Return 'ato_bench'."""
        return "ato_bench"

    def evaluate(self) -> dict[str, Any]:
        """
        Run ATO-Bench evaluation.

        ATO-Bench is multi-page. Gold text is extracted from the document-level
        ParserOutput JSON (``elements`` array), then compared against the full
        PDF prediction.

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
            gold_rel = item.get("gold", "")

            gold_path = (self.fixtures_dir / gold_rel) if gold_rel else None

            print(f"\n[{doc_id}] {doc_type}")

            if not gold_path or not gold_path.exists():
                print(f"  SKIP: gold JSON not found ({gold_rel!r})")
                continue

            # Generate prediction for entire PDF
            if not pdf_path.exists():
                print(f"  SKIP: PDF not found")
                continue

            prediction = self.generate_prediction(pdf_path)
            if prediction is None:
                continue

            pred_markdown = self.prediction_to_markdown(prediction)

            with open(gold_path) as f:
                gold_data = json.load(f)

            combined_gold = _extract_gold_text(gold_data)

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

            print(f"  NED={metrics['ned']} TEDS={metrics['teds']} TEDS-S={metrics['teds_s']}")

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
