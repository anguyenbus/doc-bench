"""Build a schema-valid ParserOutput prediction and validate it against the bundled schema.

This is the shape your own parser must emit, one file per document named
``<doc_id>.json``. The script constructs a minimal valid prediction, validates it
against the bundled ``parser_output.schema.json``, and writes it to ``--out``.

Run:
    uv run python examples/make_prediction.py --out ./predictions/01030000000001.json
"""

from __future__ import annotations

import argparse
import json
from importlib.resources import files
from pathlib import Path

import jsonschema


def build_prediction(doc_id: str) -> dict:
    """Return a minimal, schema-valid ParserOutput for one single-page document."""
    text = "The quick brown fox jumps over the lazy dog."
    return {
        "schema_version": "1.0.0",
        "parser_version": "example-parser-1.0.0",
        "parsed_at": "2026-06-04T00:00:00Z",
        "source": {
            "doc_id": doc_id,
            "filename": f"{doc_id}.pdf",
            "mime_type": "application/pdf",
            # SHA-256 of empty bytes -- replace with the real source hash.
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "page_count": 1,
            "language": "en",
        },
        "pages": [{"page_index": 0, "width": 612, "height": 792, "rotation": 0}],
        "elements": [
            {
                "element_id": f"{doc_id}_paragraph_000",
                "type": "paragraph",
                "page_index": 0,
                "char_span": [0, len(text)],
                "text": text,
                "content": {"kind": "text"},
                "bbox": {"x0": 72.0, "y0": 110.0, "x1": 540.0, "y1": 128.0},
            }
        ],
        "warnings": [],
    }


def main() -> None:
    """Build, validate, and write a prediction file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc-id", default="01030000000001", help="Document id / filename stem.")
    parser.add_argument("--out", type=Path, default=None, help="Where to write <doc_id>.json.")
    args = parser.parse_args()

    schema = json.loads(
        (files("doc_bench") / "fixtures" / "parser_output.schema.json").read_text()
    )
    prediction = build_prediction(args.doc_id)

    # Raises jsonschema.ValidationError if the prediction is not schema-valid.
    jsonschema.validate(instance=prediction, schema=schema)
    print(f"OK: prediction for {args.doc_id} is valid against ParserOutput.")

    out = args.out or Path("predictions") / f"{args.doc_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _ = out.write_text(json.dumps(prediction, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
