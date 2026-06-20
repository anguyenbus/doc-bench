# GPU Benchmark Report — parser-service (Docling) + doc-bench

**Date:** 2026-06-08
**Parser:** parser-service 0.1.0 (Docling pipeline backend, VLM/Bedrock enrichment **disabled**)
**Eval harness:** doc-bench 0.1.0
**Run mode:** Docling on **GPU** (CUDA), doc-bench scoring on CPU

> **How this differs from `mineru.md`.** `mineru.md` benchmarks a *MinerU*-based
> parser (the sibling `mineru-vlm` project). This report benchmarks **this repo's
> own parser** — `parser_service`, a **Docling + AWS-Bedrock-VLM hybrid** — on the
> **same 11 doc-bench documents** and the **same RTX 3060**, so the two reports are
> directly comparable. VLM enrichment was disabled here (no Bedrock credentials in
> the environment), so this measures the **Docling-only** path. That is the same
> "VLM disabled" footing `mineru.md` ran on.

---

## 1. Executive summary

All three datasets (ato_bench, dp_bench, omnidocbench — **11 documents total**) were
parsed end-to-end on an **NVIDIA GeForce RTX 3060 Laptop GPU** and scored with
doc-bench.

| Phase | Wall time |
|-------|-----------|
| Prediction generation (Docling, all 11 docs, GPU, one process) | **91 s (1 m 31 s)** |
| Scoring / metrics (all 3 datasets, CPU) | **~3.6 s** (0.69–2.2 s each) |
| **Total** | **~1 m 35 s** |

The benchmark cost is almost entirely document parsing; the doc-bench scoring step
(NED/TEDS computation) is effectively free at this corpus size. Because the whole
batch runs in **one process**, Docling's model pipeline loads **once** (~25 s on the
first document) and is reused for the rest — every subsequent document parses in
**3–10 s**. The first document alone accounts for ~31.9 s of the 91 s; the other ten
finish in **~57 s combined**.

**Headline accuracy (NED = text similarity ↑, TEDS = table-structure similarity ↑):**

| Dataset | Docs | NED | TEDS | TEDS-S | Rejected |
|---------|------|-----|------|--------|----------|
| ato_bench | 1 | 0.1194 | 0.0 | 0.0 | 0 |
| dp_bench | 5 | **0.8994** | 0.0 | 0.0 | 0 |
| omnidocbench | 5 | 0.6976 | **0.2621** | **0.3278** | 0 |

This Docling path **reproduces the doc-bench docling-baseline almost exactly** on
text (dp_bench 0.8994 vs baseline 0.8993; ato_bench 0.1194 vs 0.1193 — see §5) — which
is expected, since the baseline *is* a Docling parser — and additionally emits real
table structure on omnidocbench (TEDS **0.2621**), which the baseline lacks.

---

## 2. Hardware & software

| Component | Detail |
|-----------|--------|
| GPU | NVIDIA GeForce RTX 3060 Laptop GPU, 12 GB VRAM, compute capability 8.6 (Ampere) |
| GPU driver | 570.169 (supports up to CUDA 12.8) |
| CPU | Intel Xeon E5-2620 v3 @ 2.40 GHz, 12 threads |
| OS | Linux 6.8.0-64-generic, x86_64 |
| Python | 3.12.13 |
| PyTorch | **2.11.0+cu128** (CUDA runtime 12.8), cuDNN 9.19.0 |
| torchvision | 0.26.0+cu128 |
| Docling | 2.98.0 (docling-core 2.79.0, docling-ibm-models 3.13.3, docling-parse 6.2.0) |
| Layout model | `docling-project/docling-layout-heron` |
| Table model | `docling-project/docling-models` TableFormer v2.3.0 |
| OCR engine | **RapidOCR (PyTorch backend) on `cuda:0`** — PP-OCRv4 mobile det/cls/rec |

**Why a specific torch build.** The project's default resolution installs a
CUDA-13.0 torch wheel (`torch 2.12.0`, with `nvidia-*-cu13` deps — see `uv.lock`).
The host driver (570.169) only supports CUDA ≤ 12.8, so that build reports
`torch.cuda.is_available() == False` and Docling silently runs on CPU. The **cu128**
build (torch 2.11.0 / torchvision 0.26.0) is what makes the RTX 3060 usable; this
is pinned in `pyproject.toml` (`[[tool.uv.index]] pytorch-cu128` + `[tool.uv.sources]`).
This is the same CUDA-13-vs-driver-12.8 mismatch documented in `mineru.md`.

**Disk constraint & how the GPU stack was obtained.** The writable overlay had only
~6.6 GB free, and a self-contained cu128 torch wheel (~7 GB extracted) does not fit
(the first install attempt failed with `No space left on device`). Rather than
install a second multi-GB CUDA stack, the run uses a venv (`.venv-gpu`) created with
`--system-site-packages` from the host's pre-existing `/venv/main` (which already
has `torch 2.11.0+cu128`), and **only Docling + the light deps** were installed on
top (~1.5 GB of new files). torch/torchvision are inherited, not duplicated. A
constraints file pinned the inherited torch so nothing downgraded it.

**Confirmation the GPU was actually used:**
- Docling logged `Accelerator device: 'cuda:0'` for layout, table, and OCR on every
  document.
- RapidOCR logged `Using engine_name: torch` and `Using GPU device with ID: 0`.
- `torch.cuda.get_device_name(0)` → `NVIDIA GeForce RTX 3060 Laptop GPU`.
- VRAM rose from **~226 MiB idle** to a peak of **~2.7 GiB** during inference, and
  GPU utilization peaked at **76 %**.

---

## 3. Methodology

1. The 11 doc-bench source documents (1 ato_bench PDF, 5 dp_bench PDFs, 5
   omnidocbench page images) were staged into `eval_run/exported/` named by `doc_id`.
   These are the wheel's bundled fixtures — the same 11 documents `mineru.md` used.
2. `scripts/parse_batch.py` runs the markdown-first pipeline
   (`markdown_pipeline.parse_to_markdown`) over every document and, with
   `--emit-test-json`, writes the schema-valid prediction `eval_run/predictions/<doc_id>.json`
   that doc-bench grades (markdown → wrapped JSON → grade).
3. `doc_bench.runners.run_parsing_eval` (the `doc-bench` CLI) scores each prediction
   against gold using **NED** (Normalized Edit Distance similarity, text) and
   **TEDS / TEDS-S** (Table Edit Distance similarity).

Commands used:

```bash
# GPU prediction generation (VLM disabled: BEDROCK_VLM_MODEL intentionally unset,
# so call_vlm() returns instantly and the pipeline falls back to Docling).
CUDA_VISIBLE_DEVICES=0 PARSER_LOG_LEVEL=INFO .venv-gpu/bin/python scripts/parse_batch.py \
  --input eval_run/exported --output eval_run/predictions --emit-test-json --concurrency 1

# Scoring (reads ./eval_config.yaml from the CWD; ato_bench gold ships in the wheel).
for ds in ato_bench dp_bench omnidocbench; do
  doc-bench --dataset $ds --predictions eval_run/predictions --output-dir eval_run/results
done
```

> **Note on dataset data.** The `references/doc-bench/baseline/{dp_bench,omnidocbench}`
> directory that `eval_config.yaml` points at is git-ignored and absent from a fresh
> checkout. It was reconstructed from the doc-bench wheel's bundled fixture gold
> (5 dp_bench `{elements}` files → `reference.json` + `pdfs/`; 5 omnidocbench
> `layout_dets` pages → `OmniDocBench.json` + `images/`). ato_bench gold loads from
> the wheel's packaged fixtures directly.

---

## 4. Timing & latency

### 4.1 Per-document latency (GPU, single process)

| Document | Dataset | Parse time | Route | Pages | MD chars |
|----------|---------|-----------|-------|-------|----------|
| 01030000000001 | dp_bench | **31.9 s** ⟵ one-time model load | docling-kept | 1 | 2805 |
| 01030000000002 | dp_bench | 3.6 s | docling-kept | 1 | 2758 |
| 01030000000017 | dp_bench | 3.6 s | docling-kept | 1 | 1694 |
| 01030000000027 (chart) | dp_bench | 4.8 s | vlm→docling fallback | 1 | 627 |
| 01030000000040 | dp_bench | 3.3 s | docling-kept | 1 | 2674 |
| 1371-6.1997 (2 pages) | ato_bench | 8.7 s | vlm→docling fallback ×2 | 2 | 6615 |
| PPT_english…_002 | omnidocbench | 4.6 s | docling-kept | 1 | 711 |
| jiaocaineedrop_Chapter9_46 (exam) | omnidocbench | 6.7 s | docling-kept | 1 | 1523 |
| jiaocaineedrop_c04_6 (textbook) | omnidocbench | 10.1 s | docling-kept | 1 | 1739 |
| page-573c437e (book) | omnidocbench | 6.3 s | docling-kept | 1 | 1037 |
| page-c1c135ad (academic, equation-hard) | omnidocbench | 5.6 s | docling-kept | 1 | 1943 |
| **Total (all 11 docs, one run)** | | **89.2 s** (wall 91 s) | | 12 | |

**The first document absorbs the one-time model load.** Docling downloads + loads
the layout (heron), TableFormer, and RapidOCR PP-OCRv4 models once (~25 s of the
first doc's 31.9 s). Because `parse_batch` runs the whole batch in one process and
Docling caches its pipeline by options-hash, every subsequent document reuses the
resident models and parses in **3–10 s** — pure inference. The ten non-first
documents complete in **~57 s combined**.

**Whole-benchmark runtime, this report vs. `mineru.md` (all 11 docs):**

| Configuration | Total time | Notes |
|---------------|-----------|-------|
| MinerU GPU, per-doc subprocess (`mineru.md` original) | 6 m 33 s | fresh subprocess + model load per doc |
| **parser-service / Docling GPU, one process (this run)** | **1 m 31 s** | models load once; 3–10 s/doc after the first |
| MinerU GPU, in-process model reuse (`mineru.md` §8) | 1 m 00 s | models load once; 3–6 s/doc after the first |

This Docling run lands between MinerU's two configurations: it already gets the
model-reuse benefit (single process), so it is ~4.3× faster than MinerU's
per-subprocess run and within ~30 s of MinerU's optimized in-process run.

### 4.2 Where the latency goes

| Stage | Cost (GPU) | Notes |
|-------|-----------|-------|
| One-time model download + load | **~25 s** | first document only; cached for the rest |
| Layout (docling-layout-heron) | sub-second/page | on `cuda:0` |
| OCR (RapidOCR PP-OCRv4, torch) | ~1–4 s/page | on `cuda:0`; dominates image pages |
| Table structure (TableFormer) | a few seconds | only on table pages |
| VLM enrichment | **0 (disabled)** | `call_vlm` returns instantly; Docling fallback used |

After the first document, per-doc time tracks page content: text-only PDF pages run
~3–4 s, image/OCR-heavy pages ~5–10 s.

### 4.3 Scoring latency (CPU)

| Dataset | Scoring time |
|---------|-------------|
| ato_bench | 2.21 s (first invocation — includes interpreter/import warm-up) |
| dp_bench | 0.69 s |
| omnidocbench | 0.69 s |

---

## 5. Performance (accuracy)

All 11 documents evaluated; **0 rejected** (no missing predictions, schema, JSON, or
eval errors).

### Per-document scores

**dp_bench** — the four paragraph docs score 0.98–0.99; the lone chart doc
(`01030000000027`, NED 0.5601) drags the average down (its tick-labels are
rasterized). Note RapidOCR still recovered enough of the chart text to match the
baseline's 0.5601 exactly.

| Doc | Category | NED | TEDS |
|-----|----------|-----|------|
| 01030000000001 | Paragraph | 0.9855 | 0.0 |
| 01030000000002 | Paragraph | 0.9780 | 0.0 |
| 01030000000017 | Paragraph | 0.9799 | 0.0 |
| 01030000000027 | Chart | 0.5601 | 0.0 |
| 01030000000040 | Paragraph | 0.9937 | 0.0 |

**omnidocbench** — the two pages carrying gold tables produce non-zero TEDS:

| Doc | Category | NED | TEDS | TEDS-S | Gold table |
|-----|----------|-----|------|--------|------------|
| page-c1c135ad | academic_literature (equation-hard) | 0.6019 | 0.0 | 0.0 | — |
| jiaocaineedrop_Chapter9_46 | exam_paper | 0.6122 | **0.8065** | 0.8889 | ✓ |
| jiaocaineedrop_c04_6 | colorful_textbook | 0.9194 | 0.0 | 0.0 | — |
| page-573c437e | book | 0.3628 | **0.5042** | 0.75 | ✓ |
| PPT_english…_002 | PPT2PDF | 0.9915 | 0.0 | 0.0 | — |

### 5.1 This run vs. the doc-bench baseline (and vs. MinerU)

The doc-bench **baseline** is its bundled reference parser (the *docling-baseline*
runner), recorded in `mineru.md` §5.1. Since this repo's parser is *also*
Docling-based, the expectation is that it reproduces the baseline on text — and it
does.

| Dataset | Baseline NED | This run NED | Δ NED | MinerU NED (`mineru.md`) | This run TEDS | Baseline TEDS |
|---------|-------------|--------------|-------|--------------------------|---------------|---------------|
| ato_bench | 0.1193 | **0.1194** | +0.0001 | 0.1669 | 0.0 | 0.0 |
| dp_bench | 0.8993 | **0.8994** | +0.0001 | 0.7921 | 0.0 | 0.0 |
| omnidocbench | 0.7702 | 0.6976 | −0.0726 | 0.7086 | **0.2621** | 0.0 |

Key takeaways:
- **dp_bench / ato_bench: we reproduce the docling-baseline to 4 decimals.** Per-doc
  dp_bench NED matches the baseline almost exactly (e.g. chart 0.5601 = 0.5601,
  0.9937 = 0.9937). This validates that `parser_service`'s Docling path is faithful
  to the reference Docling parser.
- **TEDS: the baseline emits no structured tables (0.0 everywhere); this run does**
  — TEDS **0.2621** on omnidocbench, with the two gold-table pages scoring 0.81 and
  0.50. That is a capability the baseline lacks entirely, and it is comparable to
  MinerU's 0.2806.
- **omnidocbench NED is ~0.07 below the docling-baseline.** Two factors: (a) the
  `book` page (NED 0.363) is a reading-order/coverage outlier — it accounts for most
  of the gap; (b) OCR-engine differences — this run's RapidOCR (PP-OCRv4 *mobile*,
  a CJK-leaning model) on English images differs from whatever OCR produced the
  recorded baseline. The two table pages partly offset the dip with TEDS the
  baseline does not have.

### 5.2 Is the difference statistically significant?

**No — the NED differences vs. the docling-baseline are not statistically
significant.** Scores are paired (same documents, two parsers), so differences were
tested with the **Wilcoxon signed-rank test** and a **paired t-test** (computed with
SciPy). ato_bench has a single document, so no test is possible there.

| Comparison | n | mean ΔNED | paired t (p) | Wilcoxon p | 95 % CI of ΔNED | Significant @ α=0.05 |
|------------|---|-----------|--------------|------------|-----------------|----------------------|
| dp_bench | 5 | +0.0001 | t=+1.63, p=0.178 | 0.500 | [−0.000, +0.000] | **No** |
| omnidocbench | 5 | −0.0726 | t=−1.13, p=0.323 | 0.625 | [−0.199, +0.054] | **No** |
| Combined dp+omni | 10 | −0.0363 | t=−1.11, p=0.297 | 0.813 | [−0.100, +0.028] | **No** |

**Interpretation.**
- dp_bench's mean Δ is **+0.0001** — statistically and practically zero; this run *is*
  the baseline on that dataset.
- The omnidocbench dip is **driven by one outlier** (the `book` page) and is not
  significant at n=5; the 95 % CI straddles zero. With only 5 documents per dataset
  the test is underpowered by construction (the smallest achievable two-sided
  Wilcoxon p at n=5 is 0.0625 — it is mathematically impossible to reach p<0.05).
- **TEDS is a categorical capability difference, not a sampling question:** the
  baseline emits zero tables, so there is no distribution to test against. Any
  non-zero TEDS (0.81 and 0.50 on the two gold-table pages) is a capability the
  baseline lacks.

**Bottom line:** the deltas should be read as **descriptive** (what happened on these
specific 11 documents), not as evidence of a reliable accuracy difference. A
properly powered claim would need dozens of documents per dataset.

### Note on GPU vs. accuracy

GPU vs. CPU does **not** change accuracy — it's the same Docling/RapidOCR/TableFormer
models, just on a different device. The GPU's contribution is **speed** (§4), not
these scores.

---

## 6. Operational notes

- **CUDA build mismatch (root cause of the GPU work).** Default resolution pulls
  `torch 2.12.0` + `nvidia-*-cu13`; the driver caps at CUDA 12.8, so that build
  reports `cuda.is_available()==False` and runs on CPU. Fix: the **cu128** build
  (torch 2.11.0 / torchvision 0.26.0), pinned via a `pytorch-cu128` index in
  `pyproject.toml`.
- **Disk is tight (16 GB overlay, ~6.6 GB free).** A second full cu128 torch stack
  (~7 GB) does not fit and the first `uv sync` died with `No space left on device`.
  Resolution: reuse the host's existing `torch 2.11.0+cu128` via a
  `--system-site-packages` venv (`.venv-gpu` from `/venv/main`) and install only
  Docling on top. Use `--no-cache-dir` for the pip install to avoid doubling disk.
- **VLM enrichment was disabled** (no Bedrock credentials). `parse_batch.py` was run
  directly (not via `run_eval.py`, which would inject `BEDROCK_VLM_MODEL` and trigger
  slow boto3 connection attempts). With the var unset, `call_vlm()` returns
  `{"error": ...}` instantly and the pipeline keeps the Docling output. 3 pages (the
  chart doc and the 2 ATO pages) were *routed* to the VLM by the quality gate but
  fell back to Docling; the other 9 documents stayed `docling-kept`.
- **OCR engine.** Docling auto-selected **RapidOCR with the torch backend** (bundled
  with docling-slim) and ran it on `cuda:0`. EasyOCR / RapidOCR-onnxruntime /
  Tesseract were not installed; this did not matter because the torch RapidOCR
  variant is present and GPU-capable.

---

## 7. What would change the numbers

| Lever | Effect |
|-------|--------|
| Enable VLM enrichment (Bedrock Claude Sonnet) | Would lift the chart doc (NED 0.56) and the rasterized/figure pages, and could add table TEDS on more pages; adds VLM latency + cost |
| A higher-accuracy OCR engine (e.g. RapidOCR `server` models or EasyOCR) | Likely closes the omnidocbench NED gap vs. baseline on the English image pages |
| Reading-order fix on the `book` page | The single largest NED outlier (0.363); reduces the omnidocbench dip |
| Larger corpus | Inference scales with content; the one-time ~25 s model load dominates only on tiny corpora like this 11-doc set |
| Faster/larger GPU | Marginal here — after warm-up, per-doc inference is already a small fraction of wall time |

---

## 8. Reproduction artifacts

| Artifact | Path |
|----------|------|
| GPU venv (inherits cu128 torch, + Docling) | `.venv-gpu/` |
| Reconstructed dataset gold | `references/doc-bench/baseline/{dp_bench,omnidocbench}/` |
| Source documents (11, by doc_id) | `eval_run/exported/` |
| Predictions (graded JSON + markdown) | `eval_run/predictions/` |
| Per-doc results + summaries | `eval_run/results/` |
| Routing telemetry | `eval_run/predictions/route_stats.csv` |
