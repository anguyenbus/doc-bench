"""
DP-Bench evaluation runner.

DP-Bench contains 16 PDF documents with ground truth layout annotations.
Gold data comes from reference.json with DP-Bench element format.
"""

import json
from pathlib import Path
from typing import Any

from docling_baseline.runners.base import BaseRunner


# Function to build gold markdown from DP-Bench elements
def build_gold_markdown(gold_elements: dict) -> str:
    """
    Build gold markdown text from DP-Bench elements.

    This constructs the ground truth text in a format compatible with the grader.

    Args:
        gold_elements: Dictionary from reference.json with "elements" array.

    Returns:
        Gold markdown text string.

    """
    elements = gold_elements.get("elements", [])
    gt_lines = []

    for elem in elements:
        category = elem.get("category", "")
        content = elem.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""

        # Tables: render from html, fallback to text
        if category == "Table":
            html = content.get("html", "") if isinstance(content, dict) else ""
            markdown = content.get("markdown", "") if isinstance(content, dict) else ""

            if html:
                from docling_baseline.runners.table_utils import html_table_to_markdown
                table_md = html_table_to_markdown(html)
                if table_md:
                    gt_lines.append(table_md)
            elif markdown:
                gt_lines.append(markdown)
            elif text:
                gt_lines.append(text)
        elif not text:
            continue
        elif category == "Header":
            gt_lines.append(f"# {text}")
        elif category == "Paragraph":
            gt_lines.append(text)
        elif category == "List":
            gt_lines.append(f"- {text}")
        else:
            gt_lines.append(text)

        gt_lines.append("")  # Blank line between elements

    return "\n".join(gt_lines)


class DPBenchRunner(BaseRunner):
    """Evaluation runner for DP-Bench dataset."""

    def get_dataset_name(self) -> str:
        """Return 'dp_bench'."""
        return "dp_bench"

    def evaluate(self) -> dict[str, Any]:
        """
        Run DP-Bench evaluation.

        Returns:
            Dict with evaluation results.

        """
        items = self.manifest.get("dp_bench", [])

        print(f"=== DP-BENCH ({len(items)} docs) ===")

        results = []

        for item in items:
            doc_id = item["doc_id"]
            pdf_name = item["pdf"].split("/")[-1]
            gold_rel = item.get("gold", "")
            pdf_path = self.fixtures_dir / item["pdf"]
            gold_path = self.fixtures_dir / gold_rel

            print(f"\n[{doc_id}]")

            if not gold_path.exists():
                print(f"  WARNING: Gold not found: {gold_path}")
                continue

            with open(gold_path) as f:
                gold_data = json.load(f)

            if not pdf_path.exists():
                print(f"  WARNING: PDF not found: {pdf_path}")
                continue

            prediction = self.generate_prediction(pdf_path)
            if prediction is None:
                continue

            gt_markdown = build_gold_markdown(gold_data)
            pred_markdown = self.prediction_to_markdown(prediction)

            print(f"  Gold: {len(gt_markdown)} chars, Pred: {len(pred_markdown)} chars")

            if not gt_markdown or not pred_markdown:
                print(f"  WARNING: Empty gold or prediction")
                continue

            metrics = self.calculate_metrics(gt_markdown, pred_markdown)

            result = {
                "query_id": doc_id,
                "pdf": pdf_name,
                "category": item.get("category", ""),
                "error": "",
                **metrics,
            }
            results.append(result)

            print(f"  NED: {metrics['ned']} | TEDS: {metrics['teds']} | TEDS-S: {metrics['teds_s']}")

        averages = self.compute_averages(results)

        print(f"\n--- DP-BENCH AVERAGES ({len(results)} docs) ---")
        for metric, value in averages.items():
            print(f"  {metric:8s}: {value}")

        return {
            "total": len(results),
            "successful": len(results),
            "errors": 0,
            "averages": averages,
            "results": results,
        }
