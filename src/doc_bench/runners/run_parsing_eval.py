"""
CLI runner for parsing evaluation.

File-based evaluation only (pre-computed predictions).

Usage:
    doc-bench --dataset dp_bench --predictions ./predictions
    doc-bench --dataset omnidocbench --predictions ./predictions
"""

import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from doc_bench.adapters.schema_validator import SchemaValidationError, validate
from doc_bench.config import load_config
from doc_bench.datasets.dp_bench import build_gold_markdown
from doc_bench.identity import doc_id_for
from doc_bench.metrics.parsing.markdown_converter import parser_output_to_markdown
from doc_bench.metrics.parsing.ned import ned_score
from doc_bench.metrics.parsing.table_teds import evaluate_table
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

    elif dataset_name == "ato_bench":
        from doc_bench.datasets import load_ato_bench

        # ATO-Bench ground truth ships in the bundled fixture layout
        # (manifest.json + ato_bench/). Use a configured path if present,
        # otherwise fall back to the bundled fixtures inside the package.
        ato_cfg = config.get("datasets", {}).get("ato_bench", {})
        if ato_cfg.get("path"):
            root = Path(ato_cfg["path"])
        else:
            import doc_bench

            root = Path(doc_bench.__file__).parent / "fixtures"
        return load_ato_bench(root)

    else:
        print(f"ERROR: Unknown dataset: {dataset_name}")
        print("Supported datasets: omnidocbench, dp_bench, ato_bench")
        sys.exit(1)


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


def _grade_text_item(
    doc_id: str,
    query_id: str,
    gold_markdown: str,
    predictions_dir: Path,
    schema_path: Path,
    writer,
    csv_file,
    rejection_tracker,
) -> str:
    """
    Grade one document whose gold is a concatenated text string.

    Loads the ``<doc_id>.json`` prediction, records a rejection (missing,
    invalid JSON, or schema-invalid) or computes all metrics, writes one CSV
    row, and returns the outcome.

    Args:
        doc_id: Document identifier; the prediction must be ``<doc_id>.json``.
        query_id: Value written to the ``query_id`` CSV column.
        gold_markdown: Ground-truth text to score against.
        predictions_dir: Directory holding prediction JSON files.
        schema_path: Path to the parser-output schema for validation.
        writer: CSV ``DictWriter`` for the per-document results.
        csv_file: Open CSV file handle (flushed after each row).
        rejection_tracker: Tracker that records non-scoreable documents.

    Returns:
        ``"processed"`` if scored, ``"error"`` if rejected.

    """
    zero_row = {"ned": 0.0, "teds": 0.0, "teds_s": 0.0}

    prediction_dict = load_prediction(predictions_dir, doc_id)
    if prediction_dict is None:
        prediction_path = predictions_dir / f"{doc_id}.json"
        if not prediction_path.exists():
            reason = RejectionReason.MISSING_PREDICTION
            detail = ""
        else:
            reason = RejectionReason.INVALID_JSON
            detail = format_rejection_detail(reason, "File exists but contains invalid JSON")
        rejection_tracker.record_rejection(doc_id, reason, f"{doc_id}.json", detail)
        writer.writerow(
            {
                "query_id": query_id,
                "error": f"{reason.value}: {detail}" if detail else reason.value,
                **zero_row,
            }
        )
        csv_file.flush()
        return "error"

    try:
        validate(prediction_dict, schema_path)
    except SchemaValidationError as e:
        reason = RejectionReason.INVALID_SCHEMA
        detail = format_rejection_detail(
            reason, f"{e.field_path}: {e.original_error}" if e.field_path else e.original_error
        )
        rejection_tracker.record_rejection(doc_id, reason, f"{doc_id}.json", detail)
        writer.writerow({"query_id": query_id, "error": f"{reason.value}: {detail}", **zero_row})
        csv_file.flush()
        return "error"

    pred_markdown = parser_output_to_markdown(prediction_dict)

    # NOTE: We use flat markdown for NED here (degraded mode for ATO-Bench).
    # ATO-Bench gold is plain text, not structured elements, so the structured
    # ASM path is unavailable.  ned_score on flat markdown is the best we can do.
    ned = ned_score(gold_markdown, pred_markdown)
    teds, teds_s = evaluate_table(gold_markdown, pred_markdown)

    def safe_float(x):
        return round(x, 4) if x is not None else 0.0

    writer.writerow(
        {
            "query_id": query_id,
            "error": "",
            "ned": safe_float(ned),
            "teds": safe_float(teds),
            "teds_s": safe_float(teds_s),
        }
    )
    csv_file.flush()
    return "processed"


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
            "Overrides eval_config.yaml. Expected structure: "
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

    # Verify predictions directory exists
    if not args.predictions.exists():
        print(f"ERROR: Predictions directory not found: {args.predictions}")
        sys.exit(1)

    # Get rejection threshold from CLI flag, env var, or default
    rejection_threshold = args.max_rejection_rate
    if rejection_threshold is None:
        rejection_threshold = float(os.environ.get("DOC_BENCH_MAX_REJECTION_RATE", "0.5"))

    # Load configuration
    try:
        config = load_config(Path("eval_config.yaml"))
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Override data path if --data-dir provided
    if args.data_dir:
        data_path = args.data_dir.resolve()
        # setdefault: ato_bench may not be present in eval_config.yaml.
        config.setdefault("datasets", {}).setdefault(args.dataset, {})["path"] = str(data_path)
        print(f"Using data directory: {data_path}")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    print(f"Loading dataset: {args.dataset}")
    dataset = load_dataset(args.dataset, config)

    # File-based evaluation mode
    print(f"Using predictions from: {args.predictions}")
    parser_type = "predictions"  # For naming output files

    # Setup output file for incremental writes with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{args.dataset}_{parser_type}_results_{timestamp}.csv"
    output_file = args.output_dir / filename
    file_exists = output_file.exists()

    # Setup rejection tracker
    rejected_csv = args.output_dir / f"{args.dataset}_{parser_type}_rejected_{timestamp}.csv"
    rejection_tracker = RejectionTracker(rejected_csv)

    # Path to parser output schema for validation
    from doc_bench import get_bundled_schema_path

    schema_path = get_bundled_schema_path()

    # Define all CSV columns
    fieldnames = [
        "query_id",
        "error",
        "ned",
        "teds",
        "teds_s",
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

                print(f"Processing page {idx + 1}...")

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
                            "ned": 0.0,
                            "teds": 0.0,
                            "teds_s": 0.0,
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
                            "ned": 0.0,
                            "teds": 0.0,
                            "teds_s": 0.0,
                        }
                    )
                    csv_file.flush()
                    errors += 1
                    continue

                # Convert parser output to markdown for comparison
                pred_markdown = parser_output_to_markdown(prediction_dict)

                # For OmniDocBench, gold_text is just concatenated text
                gt_markdown = gold_text

                # Calculate metrics: NED (text) and TEDS (tables)
                # NOTE: We use flat markdown NED here because the runner operates on
                # gold_text (concatenated text from layout_dets), not structured elements.
                ned = ned_score(gt_markdown, pred_markdown)
                teds, teds_s = evaluate_table(gt_markdown, pred_markdown)

                # Convert None to 0.0
                def safe_float(x):
                    return round(x, 4) if x is not None else 0.0

                writer.writerow(
                    {
                        "query_id": query_id,
                        "error": "",
                        "ned": safe_float(ned),
                        "teds": safe_float(teds),
                        "teds_s": safe_float(teds_s),
                    }
                )
                csv_file.flush()
                processed += 1

            elif args.dataset == "dp_bench":
                doc_id, pdf_path, gold_elements = item
                print(f"Processing document {doc_id}...")

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
                            "ned": 0.0,
                            "teds": 0.0,
                            "teds_s": 0.0,
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
                            "ned": 0.0,
                            "teds": 0.0,
                            "teds_s": 0.0,
                        }
                    )
                    csv_file.flush()
                    errors += 1
                    continue

                # Convert parser output to markdown for comparison
                pred_markdown = parser_output_to_markdown(prediction_dict)

                # Build ground truth markdown from DP-Bench elements (shared function)
                gt_markdown = build_gold_markdown(gold_elements)

                # Calculate metrics
                # NOTE: We use flat markdown NED for DP-Bench because gold elements are
                # converted to markdown for consistent comparison.
                ned = ned_score(gt_markdown, pred_markdown)
                teds, teds_s = evaluate_table(gt_markdown, pred_markdown)

                # Convert None to 0.0
                def safe_float(x):
                    return round(x, 4) if x is not None else 0.0

                writer.writerow(
                    {
                        "query_id": doc_id,
                        "error": "",
                        "ned": safe_float(ned),
                        "teds": safe_float(teds),
                        "teds_s": safe_float(teds_s),
                    }
                )
                csv_file.flush()
                processed += 1

            elif args.dataset == "ato_bench":
                # ATO-Bench: gold is the document's combined per-page text.
                doc_id, gold_text = item
                print(f"Processing document {doc_id}...")

                if not gold_text:
                    # No gold text to score against; skip.
                    continue

                outcome = _grade_text_item(
                    doc_id=doc_id,
                    query_id=doc_id,
                    gold_markdown=gold_text,
                    predictions_dir=args.predictions,
                    schema_path=schema_path,
                    writer=writer,
                    csv_file=csv_file,
                    rejection_tracker=rejection_tracker,
                )
                if outcome == "processed":
                    processed += 1
                else:
                    errors += 1

        except FileNotFoundError as e:
            # Schema file not found - record as rejection
            reason = RejectionReason.INVALID_SCHEMA
            source_file = "schema"
            detail = format_rejection_detail(reason, str(e))
            rejection_tracker.record_rejection(query_id, reason, source_file, detail)
            writer.writerow(
                {
                    "query_id": query_id,
                    "error": f"{reason.value}: {detail}",
                    "ned": 0.0,
                    "teds": 0.0,
                    "teds_s": 0.0,
                }
            )
            csv_file.flush()
            errors += 1
        except Exception as e:
            # Other evaluation errors - record as rejection
            reason = RejectionReason.EVALUATION_ERROR
            source_file = query_id
            detail = format_rejection_detail(reason, str(e))
            rejection_tracker.record_rejection(query_id, reason, source_file, detail)
            writer.writerow(
                {
                    "query_id": query_id,
                    "error": f"{reason.value}: {detail}",
                    "ned": 0.0,
                    "teds": 0.0,
                    "teds_s": 0.0,
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
    if rejection_tracker:
        total_rejections = rejection_tracker.get_total_rejections()
        rejection_counts = rejection_tracker.get_rejection_counts()

        print(f"Evaluated: {processed} / Total documents")
        print(
            f"Rejected: {total_rejections} ({rejection_counts[RejectionReason.MISSING_PREDICTION]} missing, {rejection_counts[RejectionReason.INVALID_SCHEMA]} bad schema, {rejection_counts[RejectionReason.INVALID_JSON]} bad json, {rejection_counts[RejectionReason.EVALUATION_ERROR]} eval errors)"
        )

        # Get path to rejected.csv
        rejected_csv_path = rejection_tracker.output_path
        print(f"-> see {rejected_csv_path} for the full list")
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
    metrics = ["ned", "teds", "teds_s"]

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
    if rejection_tracker:
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
