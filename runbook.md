# Evaluating doc-parser with doc-bench — Runbook

How to measure doc-parser's quality against a frozen benchmark using the
**doc-bench** Docker image. Written for a teammate reproducing the run.

## Mental model (read this first)

The work is split deliberately:

- **Docker container = the measuring instrument.** The `doc-bench:latest` image
  bakes in the *complete, hash-verified, version-pinned* datasets (DP-Bench +
  OmniDocBench) and the grader. We never run our parser inside it.
- **Host = the parser.** `parser_service` runs on the host because it needs AWS
  Bedrock credentials + Docling. It emits one prediction JSON per document.
- **They meet via file-based grading.** The container reads our host-produced
  predictions (`<doc_id>.json`) and scores them against the frozen gold.

```
[container] dump-dataset ──► exported/*.png   (source files, named by doc_id)
[host]      parser_service ──► predictions/<doc_id>.json
[container] grade --predictions ──► results/*.csv  (the scorecard)
```

So the flow is: **export data from the container → parse on the host → grade in
the container.**

---

## Prerequisites

- Linux host with `sudo`, ~3 GB free disk.
- **AWS Bedrock access.** On our eval VM this comes from the **IAM instance
  role** automatically — no keys needed. Confirm with:
  ```bash
  cd /home/admin/projects/doc-parser
  AWS_REGION=ap-southeast-2 BEDROCK_VLM_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0 \
    uv run python -c "from parser_service.vlm_client import call_vlm; \
    import pathlib; img=sorted(pathlib.Path('data/parsing/omnidocbench_english/images').glob('*.png'))[0].read_bytes(); \
    r=call_vlm(img,'page'); print('VLM OK' if 'error' not in r else r['error'])"
  ```
  Expect `VLM OK`.
- `uv` installed (we always use `uv run`, never bare `python`).
- The doc-bench source checked out at `references/doc-bench` (already present).

> **Note:** `parser_service`'s VLM client is **Bedrock-only**. The two env vars
> below are required and are **not** auto-loaded from `.env` — export them in
> your shell.

---

## Step 0 — One-time: install Docker and build the image

```bash
# 0a. Install Docker engine
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io
sudo systemctl start docker
sudo docker version          # sanity check

# 0b. Build the doc-bench image (downloads the FULL frozen datasets — slow,
#     a few minutes; final image ~1.44 GB).
cd /home/admin/projects/doc-parser/references/doc-bench
sudo docker build -t doc-bench:latest .
```

Verify the datasets baked in:
```bash
sudo docker run --rm --entrypoint sh doc-bench:latest -c \
  "ls /opt/doc-bench/data/parsing && \
   echo omni_pages: \$(ls /opt/doc-bench/data/parsing/omnidocbench_english_large/images | wc -l) && \
   echo dp_pdfs: \$(ls /opt/doc-bench/data/parsing/dp_bench/dataset/pdfs | wc -l)"
# expect: omnidocbench_english_large + dp_bench, ~593 omni pages, ~200 dp pdfs
```

All remaining steps run from the project root:
```bash
cd /home/admin/projects/doc-parser
mkdir -p docker_eval/exported docker_eval/predictions docker_eval/results
```

---

## Step 1 — Export dataset source files from the container

We use a **20-page sample** of OmniDocBench here (`--limit 20`) to keep cost/time
small. Drop `--limit` for the full 593-page run (see "Scaling up").

```bash
sudo docker run --rm --entrypoint doc-bench-dump-dataset \
  -v "$PWD/docker_eval/exported:/work/output" \
  doc-bench:latest \
  --dataset omnidocbench --output /work/output --limit 20
```

Result: `docker_eval/exported/` now holds `page-<uuid>.png` files (each filename
stem **is** the `doc_id`) plus a `manifest.json`.

> File ownership: the container's user is UID 1000, same as our host user, so
> exported files are owned by you. If your host UID differs, add
> `-u $(id -u):$(id -g)` to the `docker run`.

---

## Step 2 — Run the parser on the host → predictions

This makes one Bedrock call per page that the quality gate escalates (most pages
stay on Docling). ~20 pages takes a few minutes.

```bash
export AWS_REGION=ap-southeast-2
export BEDROCK_VLM_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
export PARSER_LOG_LEVEL=WARNING          # quieter; optional

for f in docker_eval/exported/*.png; do
  uv run python scripts/parse_one.py --input "$f" --output docker_eval/predictions
done
```

Result: `docker_eval/predictions/<doc_id>.json`, one per page. The filename stem
matches the exported file's stem, which is what the grader joins on.

Sanity check you have one prediction per exported file:
```bash
echo "preds=$(ls docker_eval/predictions/*.json | wc -l) exported=$(ls docker_eval/exported/*.png | wc -l)"
```

> **Batch alternative:** for large/overnight runs use
> `uv run python scripts/parse_batch.py --input docker_eval/exported --output docker_eval/predictions --concurrency 4`
> which also writes a routing report automatically (see Step 4).

---

## Step 3 — Grade the predictions in the container

We pass `--limit 20` so the grader scores exactly the 20 pages we exported.
`dump-dataset --limit N` and the grader iterate the dataset in the **same
order**, so the first 20 line up and there are **0 rejections**. (For a full run,
drop `--limit` in both Step 1 and here.)

```bash
sudo docker run --rm \
  -v "$PWD/docker_eval/predictions:/work/predictions:ro" \
  -v "$PWD/docker_eval/results:/work/results:rw" \
  doc-bench:latest \
  --dataset omnidocbench --predictions /work/predictions --output-dir /work/results --limit 20
```

Output in `docker_eval/results/`:
- `omnidocbench_predictions_results_<ts>.csv` — per-document metrics
- `omnidocbench_predictions_results_<ts>.json` — averages + counts
- `omnidocbench_predictions_rejected_<ts>.csv` — anything that failed schema/join
  (should be empty here)

The console prints `Evaluated: 20`, `Rejected: 0`, and the metric averages.

---

## Step 4 — Routing report (which docs used the VLM)

Shows, per document, whether the VLM was used or Docling output was kept, and why.

```bash
uv run python scripts/route_report.py --input docker_eval/predictions
# prints a table + writes docker_eval/predictions/route_stats.csv
```

Columns: `doc_id, route, elems, vlm_el, warn_codes, reason`.
`route` ∈ {`vlm`, `vlm-failed`, `docling-kept`}. The `reason` column shows the
quality-gate trigger (e.g. `Layer 2: heuristic_failed: dict_hit_rate=0.17`).

(`scripts/parse_batch.py` writes this `route_stats.csv` automatically.)

---

## How to read the scorecard

On OmniDocBench, **trust NID, BLEU, and ARD.** Two metrics are *not* meaningful
here and are NOT parser failures:

| Metric | Meaning | Status on OmniDocBench |
|---|---|---|
| **NID** | text similarity | ✅ meaningful (higher = better) |
| **BLEU** | n-gram overlap | ✅ meaningful (higher = better) |
| **ARD** | reading-order distance | ✅ meaningful (lower = better) |
| TEDS | table structure | ⚠️ ~0 — the OmniDocBench gold is plain concatenated text with no markdown tables, so there's nothing to score against |
| MHS | heading hierarchy | ⚠️ ~0 — same reason (gold has no markdown headings) |
| **METEOR** | stemmed overlap | ❌ **0 — bug in the image.** It lacks NLTK `omw-1.4`, so METEOR errors out and returns 0. Ignore it until the image is patched. |

Reference numbers from our 20-page sample run (2026-05-29): NID 0.695, BLEU 0.20,
ARD 0.128; 1 of 20 pages routed to the VLM, 19 kept on Docling.

> **Important interpretation:** because the image quality gate keeps most pages on
> Docling, a clean-PDF/clean-scan OmniDocBench sample mostly measures **Docling**,
> not the VLM. To actually exercise the VLM path, use low-quality/scanned pages
> (which trip the gate) or the DP-Bench table path (VLM is called per table).

---

## Scaling up to the full dataset

Remove `--limit` from **both** Step 1 (dump) and Step 3 (grade):

```bash
# Step 1: export all OmniDocBench pages
sudo docker run --rm --entrypoint doc-bench-dump-dataset \
  -v "$PWD/docker_eval/exported:/work/output" \
  doc-bench:latest --dataset omnidocbench --output /work/output

# Step 2: parse them all (use the batch script for concurrency)
uv run python scripts/parse_batch.py --input docker_eval/exported \
  --output docker_eval/predictions --concurrency 4

# Step 3: grade everything
sudo docker run --rm \
  -v "$PWD/docker_eval/predictions:/work/predictions:ro" \
  -v "$PWD/docker_eval/results:/work/results:rw" \
  doc-bench:latest --dataset omnidocbench --predictions /work/predictions --output-dir /work/results
```

⚠️ The full OmniDocBench is 593 pages → up to 593 Bedrock calls (only escalated
pages actually call the VLM). Budget cost/time accordingly.

To run **DP-Bench** instead, swap `--dataset omnidocbench` for `--dataset dp_bench`
in Steps 1 and 3 (the exported files are PDFs; Step 2 is unchanged).

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `VLM` check prints an error, or all pages `vlm-failed` | Bedrock not reachable. Confirm the instance role and `AWS_REGION` / `BEDROCK_VLM_MODEL` are exported. The bare model ID `anthropic.claude-3-5-sonnet-20241022-v2:0` works in `ap-southeast-2`; inference profiles are SCP-blocked. |
| Grader reports high `Rejected` | Prediction filenames don't match `doc_id`, or `--limit` differs between dump and grade. Keep them equal and don't rename predictions. |
| METEOR = 0 everywhere | Known image bug (missing NLTK `omw-1.4`). Ignore METEOR, or rebuild the image with that corpus added. |
| `permission denied` on `docker run` | Use `sudo`, or add your user to the `docker` group. |
| Exported file owned by `root`/UID 1000 you can't read | Add `-u $(id -u):$(id -g)` to the `docker run`. |
```
