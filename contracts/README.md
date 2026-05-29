# Contract Schemas

This directory contains JSON Schema contracts that define the input/output interfaces for doc-bench.

## parser_output.schema.json

Defines the structured output produced by document parsers. One JSON document per source file. Contains:
- `schema_version`: Semver of this schema (currently "1.0.0")
- `parser_version`: Semver of the parser that produced this output
- `source`: Document provenance (doc_id, filename, mime_type, sha256, etc.)
- `pages`: Per-page metadata (width, height, rotation)
- `elements`: Ordered list of structural elements with type discriminator
- `warnings`: Non-fatal parser warnings (e.g., low OCR confidence)

Elements have 24 possible types including: heading, paragraph, list, table, figure, caption, footnote, header, footer, page_number, code_block, equation. Each element includes:
- `element_id`: Stable unique identifier within document
- `type`: Element type discriminator
- `page_index`: Which page this element appears on
- `char_span`: [start, end) character offsets in full document text
- `text`: Plain text content
- `content`: Type-specific structured content
- Optional: `bbox`, `level`, `parent_id`, `confidence`

## results_v1.schema.json

Defines the output schema for parsing evaluation results. Used for both CSV rows (individual document results) and JSON summary files (aggregated metrics). Contains:
- `query_id`: Unique identifier for the evaluated document
- `error`: Error message if evaluation failed, empty string otherwise
- `nid`: Normalized Intersection over Union for reading order
- `nid_s`: Scaled NID score
- `teds`: Tree Edit Distance Score for tables
- `teds_s`: Scaled TEDS score
- `mhs`: Mean Heading Similarity
- `mhs_s`: Scaled MHS score
- `ard`: Average Reading Displacement
- `bleu`: BLEU score for text similarity
- `meteor`: METEOR score for text similarity

All metrics are numeric scores (typically 0-1 range). Error rows have metrics set to 0.0.
