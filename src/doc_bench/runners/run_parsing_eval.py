"""
CLI runner for parsing evaluation.

Usage:
    uv run eval-parsing --dataset omnidocbench --parser docling
    uv run eval-parsing --dataset omnidocbench --parser stub
    uv run eval-parsing --dataset dp_bench --parser stub
    uv run eval-parsing --dataset dp_bench --predictions ./predictions
"""

import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from doc_bench.adapters.parser_adapter import ParserAdapter
from doc_bench.adapters.schema_validator import SchemaValidationError, validate
from doc_bench.config import load_config
from doc_bench.datasets.dp_bench import build_gold_markdown
from doc_bench.identity import doc_id_for
from doc_bench.metrics.parsing.markdown_converter import parser_output_to_markdown
from doc_bench.metrics.parsing.mhs import evaluate_heading_level
from doc_bench.metrics.parsing.nid import evaluate_reading_order as evaluate_nid
from doc_bench.metrics.parsing.reading_order import ard_score
from doc_bench.metrics.parsing.table_teds import evaluate_table
from doc_bench.metrics.parsing.text_similarity import bleu_score, meteor_score
from doc_bench.predictions import load_prediction
from doc_bench.rejections import (
    RejectionReason,
    RejectionTracker,
    format_rejection_detail,
)


def _compute_sha256(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hexadecimal SHA-256 hash string.

    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_doc_bench_version() -> str:
    """
    Get doc-bench package version.

    Returns:
        Version string.

    """
    try:
        from importlib.metadata import version

        return version("doc-bench")
    except Exception:
        # Fallback to reading from package
        try:
            from doc_bench import __version__

            return __version__
        except Exception:
            return "0.1.0"


def _get_dataset_version(dataset_name: str, config: dict) -> str:
    """
    Get dataset version from config or manifest.

    Args:
        dataset_name: Name of dataset.
        config: Configuration dictionary.

    Returns:
        Version string.

    """
    # Try to read from MANIFEST.yaml if available
    manifest_path = Path("data/MANIFEST.yaml")
    if manifest_path.exists():
        try:
            import yaml

            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            if dataset_name in manifest:
                return manifest[dataset_name].get("version", "unknown")
        except Exception:
            pass

    # Fallback to current date-based version
    return "2026.05"


def load_dataset(dataset_name: str, config: dict):
    """
    Load dataset by name.

    Args:
        dataset_name: Name of dataset ('omnidocbench' or 'dp_bench').
        config: Configuration dictionary.

    Returns:
        Iterator over dataset items.

    """
    if dataset_name == "omnidocbench":
        from doc_bench.datasets import load_omnidocbench

        root = Path(config["datasets"]["omnidocbench"]["path"])
        return load_omnidocbench(root)

    elif dataset_name == "dp_bench":
        from doc_bench.datasets import load_dp_bench

        root = Path(config["datasets"]["dp_bench"]["path"])
        return load_dp_bench(root)

    else:
        print(f"ERROR: Unknown dataset: {dataset_name}")
        print("Supported datasets: omnidocbench, dp_bench")
        sys.exit(1)


def get_parser(parser_name: str) -> tuple[ParserAdapter, str]:
    """
    Get parser adapter by name.

    Args:
        parser_name: Name of parser ('stub', 'docling', or path to parser module).

    Returns:
        Tuple of (ParserAdapter instance, parser_type).

    """
    if parser_name == "stub":
        from doc_bench.stubs.stub_parser import parse as parse_func

        return ParserAdapter(parse_func), "stub"

    elif parser_name == "fast":
        from doc_bench.stubs.digital_pdf_parser import parse as parse_func

        return ParserAdapter(parse_func), "fast"

    elif parser_name == "docling":
        try:
            from doc_bench.stubs.docling_parser import parse as parse_func

            return ParserAdapter(parse_func), "docling"
        except ImportError as e:
            print(f"ERROR: {e}")
            print("Install docling with: uv add docling")
            sys.exit(1)

    else:
        # For future: import custom parser module
        print(f"WARNING: Custom parser '{parser_name}' not implemented, using stub")
        from doc_bench.stubs.stub_parser import parse as parse_func

        return ParserAdapter(parse_func), "stub"


def _extract_gold_text_from_omnidocbench(page: dict) -> str:
    """
    Extract gold text from OmniDocBench page annotations.

    Args:
        page: OmniDocBench page dict with layout_dets.

    Returns:
        Concatenated text from all layout_dets in reading order.

    """
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


def _get_pdf_path_for_page(page: dict, dataset_root: Path) -> Path:
    """
    Get image/PDF path for an OmniDocBench page.

    OmniDocBench uses PNG images, not PDFs.

    Args:
        page: OmniDocBench page dict.
        dataset_root: Root path of dataset.

    Returns:
        Path to the image file.

    """
    # OmniDocBench structure: root/images/{filename} or root/{filename} (baseline)
    page_info = page.get("page_info", {})
    image_name = page_info.get("image_path", "")

    # Try standard images directory first
    image_path = dataset_root / "images" / image_name
    if image_path.exists():
        return image_path

    # Fallback to flat layout (baseline structure)
    image_path = dataset_root / image_name
    return image_path


def main() -> None:
    """Run the parsing evaluation CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate document parsing on public benchmarks")
    parser.add_argument(
        "--dataset",
        choices=["omnidocbench", "dp_bench"],
        required=True,
        help="Dataset to evaluate on",
    )
    parser.add_argument(
        "--parser",
        default=None,
        choices=["stub", "fast", "docling"],
        help=(
            "Parser to use (fast=pypdf for digital PDFs, docling=full parsing with OCR). "
            "Exactly one of --parser or --predictions must be specified."
        ),
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=None,
        help=(
            "Directory containing pre-computed prediction JSON files (<doc_id>.json). "
            "Exactly one of --parser or --predictions must be specified."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("eval_config.yaml"),
        help="Path to eval_config.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Output directory for CSV results",
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

    # Validate mutual exclusivity of --parser and --predictions
    has_parser = args.parser is not None
    has_predictions = args.predictions is not None

    if has_parser and has_predictions:
        print(
            "ERROR: Specify exactly one of --parser (run a parser in-process) "
            "or --predictions (grade pre-computed predictions). You provided both."
        )
        sys.exit(1)

    if not has_parser and not has_predictions:
        print(
            "ERROR: Specify exactly one of --parser (run a parser in-process) "
            "or --predictions (grade pre-computed predictions). You provided neither."
        )
        sys.exit(1)

    # Get rejection threshold from CLI flag, env var, or default
    rejection_threshold = args.max_rejection_rate
    if rejection_threshold is None:
        rejection_threshold = float(os.environ.get("DOC_BENCH_MAX_REJECTION_RATE", "0.5"))
    if rejection_threshold is None:
        rejection_threshold = 0.5

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    print(f"Loading dataset: {args.dataset}")
    dataset = load_dataset(args.dataset, config)

    # Get evaluation mode info
    if has_parser:
        print(f"Using parser: {args.parser}")
        parser_adapter, parser_type = get_parser(args.parser)
        predictions_mode = False
    else:
        print(f"Using predictions from: {args.predictions}")
        parser_type = "predictions"  # For naming output files
        predictions_mode = True
        # Verify predictions directory exists
        if not args.predictions.exists():
            print(f"ERROR: Predictions directory not found: {args.predictions}")
            sys.exit(1)

    # Setup output file for incremental writes with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{args.dataset}_{parser_type}_results_{timestamp}.csv"
    output_file = args.output_dir / filename
    file_exists = output_file.exists()

    # Setup rejection tracker for file-based evaluation
    rejection_tracker = None
    if predictions_mode:
        rejected_csv = args.output_dir / f"{args.dataset}_{parser_type}_rejected_{timestamp}.csv"
        rejection_tracker = RejectionTracker(rejected_csv)

    # Path to parser output schema for validation
    from doc_bench import get_bundled_schema_path

    schema_path = get_bundled_schema_path()

    # Define all CSV columns
    fieldnames = [
        "query_id",
        "error",
        "nid",
        "nid_s",
        "teds",
        "teds_s",
        "mhs",
        "mhs_s",
        "ard",
        "bleu",
        "meteor",
    ]

    # Open CSV for incremental appending
    csv_file = open(output_file, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

    # Write header if new file
    if not file_exists:
        writer.writeheader()

    processed = 0
    errors = 0
    examined = 0  # Count all items looked at (for OCR limit)

    for idx, item in enumerate(dataset):
        if args.limit and examined >= args.limit:
            break
        examined += 1

        query_id = f"{args.dataset}_{idx}"

        try:
            if args.dataset == "omnidocbench":
                # Extract gold text from OmniDocBench annotations
                gold_text = _extract_gold_text_from_omnidocbench(item)

                if not gold_text:
                    # Skip pages without text (count toward limit to avoid infinite OCR)
                    continue

                # Get doc_id
                doc_id = doc_id_for("omnidocbench", item)

                # Get PDF path for parser mode
                dataset_root = Path(config["datasets"]["omnidocbench"]["path"])
                pdf_path = _get_pdf_path_for_page(item, dataset_root)

                if predictions_mode and not pdf_path.exists():
                    writer.writerow(
                        {
                            "query_id": query_id,
                            "error": f"Image not found: {pdf_path}",
                            "nid": 0.0,
                            "nid_s": 0.0,
                            "teds": 0.0,
                            "teds_s": 0.0,
                            "mhs": 0.0,
                            "mhs_s": 0.0,
                            "ard": 0.0,
                            "bleu": 0.0,
                            "meteor": 0.0,
                        }
                    )
                    csv_file.flush()
                    errors += 1
                    continue

                print(f"Processing page {idx + 1}...")

                # Get prediction (either from file or parser)
                if predictions_mode:
                    # Load prediction from file
                    prediction_dict = load_prediction(args.predictions, doc_id)
                    if prediction_dict is None:
                        # Distinguish between missing and invalid JSON
                        prediction_path = args.predictions / f"{doc_id}.json"
                        if not prediction_path.exists():
                            reason = RejectionReason.MISSING_PREDICTION
                            source_file = f"{doc_id}.json"
                            detail = ""
                        else:
                            reason = RejectionReason.INVALID_JSON
                            source_file = f"{doc_id}.json"
                            detail = format_rejection_detail(
                                reason, "File exists but contains invalid JSON"
                            )

                        rejection_tracker.record_rejection(doc_id, reason, source_file, detail)
                        writer.writerow(
                            {
                                "query_id": query_id,
                                "error": f"{reason.value}: {detail}" if detail else reason.value,
                                "nid": 0.0,
                                "nid_s": 0.0,
                                "teds": 0.0,
                                "teds_s": 0.0,
                                "mhs": 0.0,
                                "mhs_s": 0.0,
                                "ard": 0.0,
                                "bleu": 0.0,
                                "meteor": 0.0,
                            }
                        )
                        csv_file.flush()
                        errors += 1
                        continue

                    # Validate prediction against schema
                    try:
                        validate(prediction_dict, schema_path)
                    except SchemaValidationError as e:
                        reason = RejectionReason.INVALID_SCHEMA
                        source_file = f"{doc_id}.json"
                        detail = format_rejection_detail(
                            reason,
                            (
                                f"{e.field_path}: {e.original_error}"
                                if e.field_path
                                else e.original_error
                            ),
                        )
                        rejection_tracker.record_rejection(doc_id, reason, source_file, detail)
                        writer.writerow(
                            {
                                "query_id": query_id,
                                "error": f"{reason.value}: {detail}",
                                "nid": 0.0,
                                "nid_s": 0.0,
                                "teds": 0.0,
                                "teds_s": 0.0,
                                "mhs": 0.0,
                                "mhs_s": 0.0,
                                "ard": 0.0,
                                "bleu": 0.0,
                                "meteor": 0.0,
                            }
                        )
                        csv_file.flush()
                        errors += 1
                        continue
                else:
                    # Parse document
                    output = parser_adapter.parse(pdf_path)
                    prediction_dict = output

                # Convert parser output to markdown for comparison
                pred_markdown = parser_output_to_markdown(prediction_dict)

                # For OmniDocBench, gold_text is just concatenated text
                gt_markdown = gold_text

                # Calculate all metrics
                nid, nid_s = evaluate_nid(gt_markdown, pred_markdown)
                teds, teds_s = evaluate_table(gt_markdown, pred_markdown)
                mhs, mhs_s = evaluate_heading_level(gt_markdown, pred_markdown)
                # ARD uses token lists
                ard = ard_score(gt_markdown.split(), pred_markdown.split())
                bleu = bleu_score(gt_markdown, pred_markdown)
                meteor = meteor_score(gt_markdown, pred_markdown)

                # Convert None to 0.0
                def safe_float(x):
                    return round(x, 4) if x is not None else 0.0

                writer.writerow(
                    {
                        "query_id": query_id,
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
                )
                csv_file.flush()
                processed += 1

            elif args.dataset == "dp_bench":
                doc_id, pdf_path, gold_elements = item
                print(f"Processing document {doc_id}...")

                # Get prediction (either from file or parser)
                if predictions_mode:
                    # Load prediction from file
                    prediction_dict = load_prediction(args.predictions, doc_id)
                    if prediction_dict is None:
                        # Distinguish between missing and invalid JSON
                        prediction_path = args.predictions / f"{doc_id}.json"
                        if not prediction_path.exists():
                            reason = RejectionReason.MISSING_PREDICTION
                            source_file = f"{doc_id}.json"
                            detail = ""
                        else:
                            reason = RejectionReason.INVALID_JSON
                            source_file = f"{doc_id}.json"
                            detail = format_rejection_detail(
                                reason, "File exists but contains invalid JSON"
                            )

                        rejection_tracker.record_rejection(doc_id, reason, source_file, detail)
                        writer.writerow(
                            {
                                "query_id": doc_id,
                                "error": f"{reason.value}: {detail}" if detail else reason.value,
                                "nid": 0.0,
                                "nid_s": 0.0,
                                "teds": 0.0,
                                "teds_s": 0.0,
                                "mhs": 0.0,
                                "mhs_s": 0.0,
                                "ard": 0.0,
                                "bleu": 0.0,
                                "meteor": 0.0,
                            }
                        )
                        csv_file.flush()
                        errors += 1
                        continue

                    # Validate prediction against schema
                    try:
                        validate(prediction_dict, schema_path)
                    except SchemaValidationError as e:
                        reason = RejectionReason.INVALID_SCHEMA
                        source_file = f"{doc_id}.json"
                        detail = format_rejection_detail(
                            reason,
                            (
                                f"{e.field_path}: {e.original_error}"
                                if e.field_path
                                else e.original_error
                            ),
                        )
                        rejection_tracker.record_rejection(doc_id, reason, source_file, detail)
                        writer.writerow(
                            {
                                "query_id": doc_id,
                                "error": f"{reason.value}: {detail}",
                                "nid": 0.0,
                                "nid_s": 0.0,
                                "teds": 0.0,
                                "teds_s": 0.0,
                                "mhs": 0.0,
                                "mhs_s": 0.0,
                                "ard": 0.0,
                                "bleu": 0.0,
                                "meteor": 0.0,
                            }
                        )
                        csv_file.flush()
                        errors += 1
                        continue
                else:
                    # Parse document
                    output = parser_adapter.parse(pdf_path)
                    prediction_dict = output

                # Convert parser output to markdown for comparison
                pred_markdown = parser_output_to_markdown(prediction_dict)

                # Build ground truth markdown from DP-Bench elements (shared function)
                gt_markdown = build_gold_markdown(gold_elements)

                # Calculate all metrics
                nid, nid_s = evaluate_nid(gt_markdown, pred_markdown)
                teds, teds_s = evaluate_table(gt_markdown, pred_markdown)
                mhs, mhs_s = evaluate_heading_level(gt_markdown, pred_markdown)
                ard = ard_score(gt_markdown.split(), pred_markdown.split())
                bleu = bleu_score(gt_markdown, pred_markdown)
                meteor = meteor_score(gt_markdown, pred_markdown)

                # Convert None to 0.0
                def safe_float(x):
                    return round(x, 4) if x is not None else 0.0

                writer.writerow(
                    {
                        "query_id": doc_id,
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
                )
                csv_file.flush()
                processed += 1

        except Exception as e:
            writer.writerow(
                {
                    "query_id": query_id,
                    "error": str(e),
                    "nid": 0.0,
                    "nid_s": 0.0,
                    "teds": 0.0,
                    "teds_s": 0.0,
                    "mhs": 0.0,
                    "mhs_s": 0.0,
                    "ard": 0.0,
                    "bleu": 0.0,
                    "meteor": 0.0,
                }
            )
            csv_file.flush()
            errors += 1

    # Close CSV file
    csv_file.close()

    # Close rejection tracker
    if rejection_tracker:
        rejection_tracker.close()

    # Print summary
    print(f"\nResults written to: {output_file}")
    if rejection_tracker and predictions_mode:
        total_rejections = rejection_tracker.get_total_rejections()
        rejection_counts = rejection_tracker.get_rejection_counts()

        print(f"Evaluated: {processed} / Total documents")
        print(
            f"Rejected: {total_rejections} ({rejection_counts[RejectionReason.MISSING_PREDICTION]} missing, {rejection_counts[RejectionReason.INVALID_SCHEMA]} bad schema, {rejection_counts[RejectionReason.INVALID_JSON]} bad json, {rejection_counts[RejectionReason.EVALUATION_ERROR]} eval errors)"
        )

        # Get path to rejected.csv
        rejected_csv_path = rejection_tracker.output_path
        print(f"→ see {rejected_csv_path} for the full list")
    else:
        print(f"Total items processed: {processed}")
        print(f"Errors: {errors}")

    # Calculate rejection rate
    total = processed + (rejection_tracker.get_total_rejections() if rejection_tracker else errors)
    if total > 0 and rejection_threshold > 0:
        rejection_rate = (
            rejection_tracker.get_total_rejections() if rejection_tracker else errors
        ) / total
        if rejection_rate > rejection_threshold:
            print(
                f"WARNING: Rejection rate ({rejection_rate:.1%}) exceeds threshold "
                f"({rejection_threshold:.1%}). Results may be unreliable."
            )

    # Calculate metric averages (excluding error rows) - reload CSV
    df = pd.read_csv(output_file)
    metrics = [
        "nid",
        "nid_s",
        "teds",
        "teds_s",
        "mhs",
        "mhs_s",
        "ard",
        "bleu",
        "meteor",
    ]

    averages = {}
    if not df.empty:
        # Filter out error rows (error column is NaN or empty)
        valid_df = df[df["error"].isna() | (df["error"] == "")]
        if len(valid_df) > 0:
            print("\nMetric averages:")
            for metric in metrics:
                avg = valid_df[metric].mean()
                averages[metric] = round(float(avg), 4)
                print(f"  {metric}: {avg:.4f}")

    # Write JSON summary with same base filename
    json_file = output_file.with_suffix(".json")
    summary = {
        "dataset": args.dataset,
        "parser": parser_type,
        "timestamp": timestamp,
        "csv_file": str(output_file.name),
        "metrics_avg": averages,
    }

    # Add evaluated_samples and rejected_samples for file-based evaluation
    if rejection_tracker and predictions_mode:
        summary["evaluated_samples"] = processed
        summary["rejected_samples"] = rejection_tracker.get_rejection_counts_serializable()
    else:
        # For parser mode, use legacy fields
        summary["total_processed"] = processed
        summary["errors"] = errors

    with open(json_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to: {json_file}")

    sys.exit(0)


if __name__ == "__main__":
    main()
