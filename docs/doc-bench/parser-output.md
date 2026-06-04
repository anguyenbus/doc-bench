# Parser Output Schema (the prediction contract)

doc-bench grades **predictions**: JSON files your parser writes, one per document, named `<doc_id>.json`. Every prediction must conform to the bundled JSON Schema `ParserOutput`. This page documents that contract.

The authoritative schema ships in the wheel at [`src/doc_bench/fixtures/parser_output.schema.json`](../../src/doc_bench/fixtures/parser_output.schema.json) and is the file `doc-bench` validates against. If a prediction fails validation it is recorded as an `INVALID_SCHEMA` rejection rather than scored.

## Table of Contents

- [Top-level object](#top-level-object)
- [`source`](#source)
- [`pages`](#pages)
- [`elements`](#elements)
- [Content variants](#content-variants)
- [Element types](#element-types)
- [Minimal valid example](#minimal-valid-example)
- [Accessing the schema programmatically](#accessing-the-schema-programmatically)

## Top-level object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | Schema version this output targets (e.g. `"1.0.0"`). |
| `parser_version` | string | yes | Identifier of the parser that produced the output. |
| `parsed_at` | string | no | Timestamp (ISO 8601 recommended). |
| `source` | object | yes | Provenance of the source document — see [`source`](#source). |
| `pages` | array | yes | One entry per page — see [`pages`](#pages). |
| `elements` | array | yes | Detected content elements — see [`elements`](#elements). |
| `warnings` | array | no | Free-form parser warnings. |

## `source`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `doc_id` | string | yes | Stable document identity; must match the prediction filename stem. |
| `filename` | string | yes | Original filename. |
| `mime_type` | string | yes | E.g. `application/pdf`, `image/png`. |
| `sha256` | string | yes | SHA-256 of the source bytes. |
| `page_count` | integer | no | Number of pages. |
| `language` | string | no | Primary language code. |

## `pages`

Each entry describes one page.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `page_index` | integer | yes | Zero-based page index. |
| `width` | number | yes | Page width in the parser's coordinate units. |
| `height` | number | yes | Page height. |
| `rotation` | integer | no | One of `0`, `90`, `180`, `270`. |

## `elements`

Each element is one detected piece of content (a paragraph, table, figure, ...). Required fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `element_id` | string | yes | Unique within the document. |
| `type` | string | yes | One of the [element types](#element-types). |
| `page_index` | integer | yes | Page this element belongs to. |
| `char_span` | array | yes | `[start, end]` character offsets into the document text stream. |
| `text` | string | yes | The element's text (may be empty for pure figures). |
| `content` | object | yes | A typed content variant — see [content variants](#content-variants). |

Optional fields: `level` (integer, heading depth), `parent_id` (string or null), `pages_spanned` (array), `bbox` (object with required `x0`,`y0`,`x1`,`y1`), `confidence` (number).

## Content variants

The `content` object is discriminated by its `kind` field.

| `kind` | Required fields | Optional fields |
|--------|-----------------|-----------------|
| `text` | `kind` | — |
| `table` | `kind`, `rows`, `cols`, `cells` | `header_rows` |
| `figure` | `kind` | `image_uri`, `alt_text`, `caption_element_id` |
| `list` | `kind`, `ordered` | — |

For tables, `cells` carries the structured grid that TEDS scores against, so populate it faithfully.

## Element types

`type` must be one of:

```
heading, paragraph, list, list_item, table, figure, caption,
footnote, header, footer, page_number, code_block, equation
```

## Minimal valid example

```json
{
  "schema_version": "1.0.0",
  "parser_version": "my-parser-1.0.0",
  "parsed_at": "2026-06-04T00:00:00Z",
  "source": {
    "doc_id": "01030000000001",
    "filename": "01030000000001.pdf",
    "mime_type": "application/pdf",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "page_count": 1,
    "language": "en"
  },
  "pages": [
    { "page_index": 0, "width": 612, "height": 792, "rotation": 0 }
  ],
  "elements": [
    {
      "element_id": "01030000000001_paragraph_000",
      "type": "paragraph",
      "page_index": 0,
      "char_span": [0, 27],
      "text": "The quick brown fox jumps.",
      "content": { "kind": "text" },
      "bbox": { "x0": 72.0, "y0": 110.0, "x1": 540.0, "y1": 128.0 }
    }
  ],
  "warnings": []
}
```

This object is produced programmatically in [`examples/make_prediction.py`](../../examples/make_prediction.py) and validated there against the bundled schema.

## Accessing the schema programmatically

```python
from importlib.resources import files
import json

schema = json.loads(
    (files("doc_bench") / "fixtures" / "parser_output.schema.json").read_text()
)
print(schema["title"])  # "ParserOutput"
```

A convenience accessor, `doc_bench.get_bundled_schema_path()`, returns the path to the bundled schema; the evaluator and smoke test resolve it automatically, so you never need a `contracts/` directory in your working tree.
