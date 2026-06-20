"""
CLI runner for parsing evaluation.

File-based evaluation only (pre-computed predictions).

Usage:
    doc-bench --dataset dp_bench --predictions ./predictions
    doc-bench --dataset omnidocbench --predictions ./predictions
    doc-bench --dataset ato_bench --predictions ./predictions
"""

import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from doc_bench.adapters.schema_validator import SchemaValidationError, validate
from doc_bench.config import load_config
from doc_bench.datasets.dp_bench import build_gold_markdown
from doc_bench.identity import doc_id_for
from doc_bench.metrics.parsing.markdown_converter import parser_output_to_markdown
from doc_bench.metrics.parsing.ned import ned_score
from doc_bench.metrics.parsing.table_teds import (
    TEDSEvaluator,
    _extract_tables_from_markdown,
    _markdown_table_to_html,
    evaluate_table,
)
from doc_bench.predictions import load_prediction
from doc_bench.rejections import (
    RejectionReason,
    RejectionTracker,
    format_rejection_detail,
)


@dataclass(frozen=True)
class GoldItem:
    """Normalised ground-truth for one document, dataset-agnostic."""

    doc_id: str
    text: str
    html_tables: list[str]


def _extract_gold_text_from_omnidocbench(page: dict) -> str:
    """
    Extract gold text from OmniDocBench page annotations.

    Args:
        page: OmniDocBench page dict with layout_dets.

    Returns:
        Concatenated text from all layout_dets in reading order.

    """
    layout_dets = page.get("layout_dets", [])

    def sort_key(x):
        order = x.get("order")
        if order is None:
            return float("inf")
        return order

    sorted_dets = sorted(layout_dets, key=sort_key)

    # NOTE: equation blocks have no text field — excluding them keeps the gold string
    # length comparable to parsers that don't emit LaTeX, making NED fair.
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
    r"""
    Strip LaTeX equation markup from a prediction string.

    OmniDocBench gold excludes equation content (text field is always empty for
    equation_isolated/equation_semantic blocks). Parsers that perform math
    extraction (MinerU, Nougat, etc.) emit LaTeX, making the prediction 2-6x
    longer than gold and collapsing NED even when text extraction is correct.
    Stripping equations from the prediction before NED makes the comparison fair.

    Patterns removed (non-greedy, DOTALL):
      $$...$$   display math (most common in MinerU output)
      $...$     inline math
      \\[...\\] display math (LaTeX block)
      \\(...\\) inline math (LaTeX block)

    Args:
        text: Prediction markdown string.

    Returns:
        String with all LaTeX equation content removed.

    """
    import re

    # NOTE: Order matters — match $$ before $ to avoid consuming half a display block.
    text = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
    text = re.sub(r"\$[^$\n]+?\$", "", text)
    text = re.sub(r"\\\[[\s\S]*?\\\]", "", text)
    text = re.sub(r"\\\([\s\S]*?\\\)", "", text)
    # Collapse whitespace left by removed blocks
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _page_to_gold_item(page: dict) -> GoldItem:
    """Build a GoldItem from one OmniDocBench page dict."""
    return GoldItem(
        doc_id=doc_id_for("omnidocbench", page),
        text=_extract_gold_text_from_omnidocbench(page),
        html_tables=[
            det["html"]
            for det in page.get("layout_dets", [])
            if det.get("category_type") == "table" and det.get("html")
        ],
    )


def _dp_bench_to_gold_item(item: tuple) -> GoldItem:
    """Build a GoldItem from one dp_bench (doc_id, pdf_path, gold_elements) tuple."""
    doc_id, _pdf_path, gold_elements = item
    return GoldItem(
        doc_id=doc_id,
        text=build_gold_markdown(gold_elements),
        html_tables=[
            elem["content"]["html"]
            for elem in gold_elements.get("elements", [])
            if elem.get("category") == "Table"
            and isinstance(elem.get("content"), dict)
            and elem["content"].get("html")
        ],
    )


def load_dataset(dataset_name: str, root: Path | None):
    """
    Load dataset by name, yielding GoldItem for each document.

    Args:
        dataset_name: Name of dataset ('omnidocbench', 'dp_bench', or 'ato_bench').
        root: Path to dataset directory, or None to use bundled fixtures.

    Returns:
        Iterator over GoldItem.

    """
    if dataset_name == "omnidocbench":
        from doc_bench.datasets import load_omnidocbench

        for page in load_omnidocbench(root):
            gold = _page_to_gold_item(page)
            if gold.text:
                yield gold

    elif dataset_name == "dp_bench":
        from doc_bench.datasets import load_dp_bench

        for item in load_dp_bench(root):
            yield _dp_bench_to_gold_item(item)

    elif dataset_name == "ato_bench":
        from doc_bench.datasets import load_ato_bench

        if root is None:
            import doc_bench

            root = Path(doc_bench.__file__).parent / "fixtures"
        for doc_id, gold_text in load_ato_bench(root):
            if gold_text:
                yield GoldItem(doc_id=doc_id, text=gold_text, html_tables=[])

    else:
        print(f"ERROR: Unknown dataset: {dataset_name}")
        print("Supported datasets: omnidocbench, dp_bench, ato_bench")
        sys.exit(1)


def _grade(gold: GoldItem, pred_markdown: str) -> tuple[float, float, float]:
    """
    Compute NED-similarity, TEDS, and TEDS-S for one document.

    Args:
        gold: Normalised ground-truth for the document.
        pred_markdown: Parser prediction as a markdown string.

    Returns:
        Tuple of (ned_similarity, teds, teds_s) all in [0.0, 1.0].

    """
    ned_sim = ned_score(gold.text, _strip_equations(pred_markdown))

    if gold.html_tables:
        pred_tables_md = _extract_tables_from_markdown(pred_markdown)
        if pred_tables_md:
            gold_html = f"<html><body>{gold.html_tables[0]}</body></html>"
            pred_html = f"<html><body>{_markdown_table_to_html(pred_tables_md[0])}</body></html>"
            teds = TEDSEvaluator(structure_only=False).evaluate(pred_html, gold_html)
            teds_s = TEDSEvaluator(structure_only=True).evaluate(pred_html, gold_html)
        else:
            teds, teds_s = 0.0, 0.0
    else:
        teds, teds_s = evaluate_table(gold.text, pred_markdown)

    return (
        ned_sim if ned_sim is not None else 0.0,
        teds if teds is not None else 0.0,
        teds_s if teds_s is not None else 0.0,
    )


def _safe_float(x) -> float:
    return round(x, 4) if x is not None else 0.0


def main() -> None:
    """Run the parsing evaluation CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate document parsing on public benchmarks")
    parser.add_argument(
        "--dataset",
        choices=["omnidocbench", "dp_bench", "ato_bench"],
        required=True,
        help="Dataset to evaluate on",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help=(
            "Directory containing pre-computed prediction JSON files (<doc_id>.json). "
            "Predictions must follow parser_output.schema.json format."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Output directory for CSV results",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=(
            "Path to dataset directory containing ground truth. "
            "When omitted, uses bundled fixtures. "
            "DP-Bench: reference.json + pdfs/; OmniDocBench: OmniDocBench.json + images/"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of items to process (for testing)",
    )
    parser.add_argument(
        "--max-rejection-rate",
        type=float,
        default=None,
        help=(
            "Maximum acceptable rejection rate (0.0-1.0). "
            "If exceeded, a warning is printed. "
            "Special case: 0 means never warn. "
            "Default: 0.5 (or DOC_BENCH_MAX_REJECTION_RATE env var)."
        ),
    )

    args = parser.parse_args()

    if not args.predictions.exists():
        print(f"ERROR: Predictions directory not found: {args.predictions}")
        sys.exit(1)

    rejection_threshold = args.max_rejection_rate
    if rejection_threshold is None:
        rejection_threshold = float(os.environ.get("DOC_BENCH_MAX_REJECTION_RATE", "0.5"))

    # Config is optional — only load when the file exists.
    root: Path | None = None
    config_path = Path("eval_config.yaml")
    if config_path.exists():
        try:
            config = load_config(config_path)
            dataset_path = config.get("datasets", {}).get(args.dataset, {}).get("path")
            if dataset_path:
                root = Path(dataset_path)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    # --data-dir always wins over config.
    if args.data_dir:
        root = args.data_dir.resolve()
        print(f"Using data directory: {root}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset: {args.dataset}")
    dataset = load_dataset(args.dataset, root)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{args.dataset}_predictions_results_{timestamp}.csv"
    output_file = args.output_dir / filename
    file_exists = output_file.exists()

    rejected_csv = args.output_dir / f"{args.dataset}_predictions_rejected_{timestamp}.csv"
    rejection_tracker = RejectionTracker(rejected_csv)

    from doc_bench import get_bundled_schema_path

    schema_path = get_bundled_schema_path()

    fieldnames = ["query_id", "error", "ned_similarity", "teds", "teds_s"]
    zero_row = {"ned_similarity": 0.0, "teds": 0.0, "teds_s": 0.0}

    csv_file = open(output_file, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()

    processed = 0
    errors = 0
    examined = 0

    for gold in dataset:
        if args.limit and examined >= args.limit:
            break
        examined += 1

        print(f"Processing {gold.doc_id}...")

        pred_dict = load_prediction(args.predictions, gold.doc_id)
        if pred_dict is None:
            pred_path = args.predictions / f"{gold.doc_id}.json"
            reason = (
                RejectionReason.MISSING_PREDICTION
                if not pred_path.exists()
                else RejectionReason.INVALID_JSON
            )
            detail = (
                ""
                if reason == RejectionReason.MISSING_PREDICTION
                else format_rejection_detail(reason, "File exists but contains invalid JSON")
            )
            rejection_tracker.record_rejection(gold.doc_id, reason, f"{gold.doc_id}.json", detail)
            writer.writerow(
                {
                    "query_id": gold.doc_id,
                    "error": f"{reason.value}: {detail}" if detail else reason.value,
                    **zero_row,
                }
            )
            csv_file.flush()
            errors += 1
            continue

        try:
            validate(pred_dict, schema_path)
        except SchemaValidationError as e:
            reason = RejectionReason.INVALID_SCHEMA
            detail = format_rejection_detail(
                reason, f"{e.field_path}: {e.original_error}" if e.field_path else e.original_error
            )
            rejection_tracker.record_rejection(gold.doc_id, reason, f"{gold.doc_id}.json", detail)
            writer.writerow(
                {"query_id": gold.doc_id, "error": f"{reason.value}: {detail}", **zero_row}
            )
            csv_file.flush()
            errors += 1
            continue

        try:
            pred_markdown = parser_output_to_markdown(pred_dict)
            ned_sim, teds, teds_s = _grade(gold, pred_markdown)
            writer.writerow(
                {
                    "query_id": gold.doc_id,
                    "error": "",
                    "ned_similarity": _safe_float(ned_sim),
                    "teds": _safe_float(teds),
                    "teds_s": _safe_float(teds_s),
                }
            )
            csv_file.flush()
            processed += 1
        except Exception as e:
            reason = RejectionReason.EVALUATION_ERROR
            detail = format_rejection_detail(reason, str(e))
            rejection_tracker.record_rejection(gold.doc_id, reason, gold.doc_id, detail)
            writer.writerow(
                {"query_id": gold.doc_id, "error": f"{reason.value}: {detail}", **zero_row}
            )
            csv_file.flush()
            errors += 1

    csv_file.close()
    rejection_tracker.close()

    print(f"\nResults written to: {output_file}")
    total_rejections = rejection_tracker.get_total_rejections()
    rejection_counts = rejection_tracker.get_rejection_counts()
    print(f"Evaluated: {processed} / Total documents")
    print(
        f"Rejected: {total_rejections} "
        f"({rejection_counts[RejectionReason.MISSING_PREDICTION]} missing, "
        f"{rejection_counts[RejectionReason.INVALID_SCHEMA]} bad schema, "
        f"{rejection_counts[RejectionReason.INVALID_JSON]} bad json, "
        f"{rejection_counts[RejectionReason.EVALUATION_ERROR]} eval errors)"
    )
    print(f"-> see {rejection_tracker.output_path} for the full list")

    total = processed + total_rejections
    if total > 0 and rejection_threshold > 0:
        rejection_rate = total_rejections / total
        if rejection_rate > rejection_threshold:
            print(
                f"WARNING: Rejection rate ({rejection_rate:.1%}) exceeds threshold "
                f"({rejection_threshold:.1%}). Results may be unreliable."
            )

    df = pd.read_csv(output_file)
    metrics = ["ned_similarity", "teds", "teds_s"]
    averages = {}
    if not df.empty:
        valid_df = df[df["error"].isna() | (df["error"] == "")]
        if len(valid_df) > 0:
            print("\nMetric averages:")
            for metric in metrics:
                avg = valid_df[metric].mean()
                averages[metric] = round(float(avg), 4)
                print(f"  {metric}: {avg:.4f}")

    json_file = output_file.with_suffix(".json")
    summary = {
        "dataset": args.dataset,
        "parser": "predictions",
        "timestamp": timestamp,
        "csv_file": str(output_file.name),
        "metrics_avg": averages,
        "evaluated_samples": processed,
        "rejected_samples": rejection_tracker.get_rejection_counts_serializable(),
    }
    with open(json_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to: {json_file}")

    sys.exit(0)


if __name__ == "__main__":
    main()
