"""
OmniDocBench evaluation runner.

OmniDocBench contains 16 document images with ground truth layout annotations
in OmniDocBench format (layout_dets array).
"""

import json
from pathlib import Path
from typing import Any

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

    texts = []
    for det in sorted_dets:
        text = det.get("text", "")
        if text:
            texts.append(text)

    return " ".join(texts)


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

            # Calculate metrics
            metrics = self.calculate_metrics(gold_text, pred_markdown)

            result = {
                "query_id": doc_id,
                "image": image_file,
                "doc_type": item.get("doc_type", ""),
                "error": "",
                **metrics,
            }
            results.append(result)

            # Print key metrics
            print(f"  NID: {metrics['nid']} | BLEU: {metrics['bleu']} | METEOR: {metrics['meteor']}")

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
