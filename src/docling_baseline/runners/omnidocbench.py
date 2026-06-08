"""
OmniDocBench evaluation runner.

OmniDocBench contains 16 document images with ground truth layout annotations
in OmniDocBench format (layout_dets array).
"""

import json
from pathlib import Path
from typing import Any

from docling_baseline.metrics.table_teds import (
    TEDSEvaluator,
    _extract_tables_from_markdown,
    _markdown_table_to_html,
)
from docling_baseline.runners.base import BaseRunner, safe_float


def extract_gold_text_from_omnidocbench(gold_json: dict) -> str:
    """
    Extract gold text from OmniDocBench JSON format.

    Args:
        gold_json: OmniDocBench page dict with layout_dets array.

    Returns:
        Concatenated text from all detections in reading order.

    """
    layout_dets = gold_json.get("layout_dets", [])

    def sort_key(x):
        order = x.get("order")
        if order is None:
            return float("inf")
        return order

    sorted_dets = sorted(layout_dets, key=sort_key)

    # NOTE: equation blocks have no text field — excluding keeps gold length fair
    # against parsers that render equations as LaTeX.
    _EXCLUDED_CATEGORIES = {"equation_isolated", "equation_semantic"}

    texts = []
    for det in sorted_dets:
        if det.get("category_type") in _EXCLUDED_CATEGORIES:
            continue
        text = det.get("text", "")
        if text:
            texts.append(text)

    return " ".join(texts)


def _strip_equations(text: str) -> str:
    """Strip LaTeX equation markup from a prediction string.

    Gold excludes equation content (text field always empty for equation blocks).
    Parsers that emit LaTeX make pred 2-6x longer than gold, collapsing NED.

    Args:
        text: Prediction markdown string.

    Returns:
        String with LaTeX equation content removed.

    """
    import re

    text = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
    text = re.sub(r"\$[^$\n]+?\$", "", text)
    text = re.sub(r"\\\[[\s\S]*?\\\]", "", text)
    text = re.sub(r"\\\([\s\S]*?\\\)", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _evaluate_teds(page: dict, pred_markdown: str) -> tuple[float, float]:
    """Compute TEDS/TEDS-S for one OmniDocBench page using HTML from layout_dets.

    Args:
        page: OmniDocBench page dict with layout_dets.
        pred_markdown: Predicted markdown string.

    Returns:
        Tuple of (teds, teds_s) in [0.0, 1.0].

    """
    gold_html_tables = [
        det["html"]
        for det in page.get("layout_dets", [])
        if det.get("category_type") == "table" and det.get("html")
    ]
    if not gold_html_tables:
        return 0.0, 0.0

    pred_tables_md = _extract_tables_from_markdown(pred_markdown)
    if not pred_tables_md:
        return 0.0, 0.0

    gold_html = f"<html><body>{gold_html_tables[0]}</body></html>"
    pred_html = f"<html><body>{_markdown_table_to_html(pred_tables_md[0])}</body></html>"

    teds = TEDSEvaluator(structure_only=False).evaluate(pred_html, gold_html)
    teds_s = TEDSEvaluator(structure_only=True).evaluate(pred_html, gold_html)
    return teds, teds_s


class OmniDocBenchRunner(BaseRunner):
    """Evaluation runner for OmniDocBench dataset."""

    def get_dataset_name(self) -> str:
        """Return 'omnidocbench'."""
        return "omnidocbench"

    def evaluate(self) -> dict[str, Any]:
        """
        Run OmniDocBench evaluation.

        Returns:
            Dict with evaluation results.

        """
        items = self.manifest.get("omnidocbench", [])
        omnidoc_dir = self.fixtures_dir / "omnidocbench"

        # Load reference from full dataset
        reference_path = Path(self.manifest.get("reference_paths", {}).get("omnidocbench"))

        if not reference_path.exists():
            print(f"WARNING: Reference not found at {reference_path}")
            return {"total": 0, "successful": 0, "errors": len(items), "averages": {}, "results": []}

        with open(reference_path) as f:
            reference_pages = json.load(f)

        # Create lookup by image path
        reference_by_image = {}
        for page in reference_pages:
            page_info = page.get("page_info", {})
            image_name = page_info.get("image_path", "")
            if image_name:
                reference_by_image[image_name] = page

        print(f"=== OMNIDOCBENCH ({len(items)} images) ===")

        results = []

        for item in items:
            doc_id = item["doc_id"]
            image_file = item["image"].split("/")[-1]
            image_path = omnidoc_dir / image_file

            print(f"\n[{doc_id}]")

            # Load gold
            if image_file not in reference_by_image:
                print(f"  WARNING: {image_file} not in reference")
                continue

            gold_data = reference_by_image[image_file]

            # Generate prediction
            if not image_path.exists():
                print(f"  WARNING: Image not found: {image_path}")
                continue

            prediction = self.generate_prediction(image_path)
            if prediction is None:
                continue

            # Extract gold text and prediction markdown
            gold_text = extract_gold_text_from_omnidocbench(gold_data)
            pred_markdown = self.prediction_to_markdown(prediction)

            print(f"  Gold: {len(gold_text)} chars, Pred: {len(pred_markdown)} chars")

            if not gold_text or not pred_markdown:
                print(f"  WARNING: Empty gold or prediction")
                continue

            # NED: strip equations from pred before comparing (gold has no equation text)
            ned = self.calculate_metrics(gold_text, _strip_equations(pred_markdown))["ned"]
            # TEDS: compare gold HTML table (from layout_dets) vs predicted markdown table
            teds, teds_s = _evaluate_teds(gold_data, pred_markdown)
            metrics = {
                "ned": ned,
                "teds": safe_float(teds),
                "teds_s": safe_float(teds_s),
            }

            result = {
                "query_id": doc_id,
                "image": image_file,
                "doc_type": item.get("doc_type", ""),
                "error": "",
                **metrics,
            }
            results.append(result)

            # Print key metrics
            print(f"  NED: {metrics['ned']} | TEDS: {metrics['teds']} | TEDS-S: {metrics['teds_s']}")

        # Calculate averages
        averages = self.compute_averages(results)

        print(f"\n--- OMNIDOCBENCH AVERAGES ({len(results)} images) ---")
        for metric, value in averages.items():
            print(f"  {metric:8s}: {value}")

        return {
            "total": len(results),
            "successful": len(results),
            "errors": 0,
            "averages": averages,
            "results": results,
        }
