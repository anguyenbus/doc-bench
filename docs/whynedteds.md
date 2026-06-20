# Why We Should Standardize on NED and TEDS for Document Parsing Evaluation

**TL;DR:** We propose adopting two metrics as our standard for evaluating document parsing quality: **Normalized Edit Distance (NED)** for text and reading order, and **Tree Edit Distance-based Similarity (TEDS)** for tables. Together they cover the two failure modes that account for most real-world quality differences between parsers, they are deterministic and cheap to run in CI, and they are the de facto industry standard — meaning every number we produce is directly comparable to published leaderboards and research papers. This document defines the metrics, makes the case for the pair, addresses the known criticisms honestly, and explains how to run them.

---

## 1. Why we need standardized parsing metrics

Document parsing — converting PDFs and scans into structured, machine-readable text — sits at the start of our data pipelines, and errors made there propagate into everything downstream. Yet "parsing quality" is not one thing: a parser can transcribe characters perfectly while scrambling the reading order of a two-column page, or render every cell of a table correctly while destroying its row/column structure. A useful evaluation standard therefore needs to (a) capture distinct error types, (b) be reproducible and cheap enough to run on every pipeline change, and (c) produce numbers we can compare against the outside world when selecting vendors and open-source tools.

NED and TEDS are the pair that best satisfies all three requirements.

## 2. The two metrics

### 2.1 Normalized Edit Distance (NED)

NED measures character-level similarity between the parser's serialized output and a ground-truth reference. It is the Levenshtein distance (minimum number of character insertions, deletions, and substitutions) normalized by the length of the longer string:

```
NED(gt, pred) = Levenshtein(gt, pred) / max(len(gt), len(pred))
```

A score of 0 is a perfect match; 1 is complete dissimilarity. (Many leaderboards report the similarity form, 1 − NED.) Because it is computed over the full serialized page, NED simultaneously penalizes misrecognized characters, omitted content, hallucinated content, and — critically — text emitted out of reading order, since out-of-order text produces large edit distances even when every character is individually correct. This is exactly how the reference benchmark in the field implements it: OmniDocBench (CVPR 2025) uses NED as its metric for both plain text and reading order [1][2].

### 2.2 Tree Edit Distance-based Similarity (TEDS)

TEDS was introduced by Zhong, ShafieiBavani, and Jimeno Yepes (IBM Research) in the ECCV 2020 paper that released PubTabNet, specifically because string-level metrics fail on tables: the authors designed it to capture multi-hop cell misalignment and structural errors that the previously established metrics missed [3]. It represents both the predicted and ground-truth tables as HTML trees and computes:

```
TEDS(Ta, Tb) = 1 − TreeEditDist(Ta, Tb) / max(|Ta|, |Tb|)
```

where |T| is the number of nodes in the tree [3][4]. Because the comparison happens at the tree level, TEDS detects structural damage — merged cells split apart, rows shifted, headers detached from their columns — that character-level comparison cannot see. A variant, TEDS-S, scores structure only (ignoring cell text), which is useful for isolating layout-model errors from OCR errors [3].

## 3. The case for this pair

**They cover complementary failure modes.** NED's known blind spot is structured content: a table can be near-perfect at the character level while its rows and columns are destroyed. TEDS is precisely the metric built to close that gap [3]. Conversely, TEDS says nothing about prose, omissions, or reading order, which NED covers. Modern parsers differ from one another far more on tables and complex layouts than on plain text — a recent benchmark study found that text-recognition scores stay relatively robust across document difficulty while table (TEDS) scores deteriorate sharply, with one model holding 86.1% text accuracy while its table score fell from 91.8% to 52.5% on harder documents [5]. A metric suite that omits TEDS would therefore hide exactly the dimension where parser choice matters most.

**They are the industry standard, which buys us comparability.** OmniDocBench, the CVPR 2025 benchmark widely treated as the reference evaluation for document parsing, scores text and reading order with NED and tables with TEDS (plus NED) [1][2]. The same pairing appears across the literature: CC-OCR uses NED for content structuring and TEDS for tables [6]; READoc (ACL Findings 2025) scores its text and table units with edit-distance similarity and TEDS [7]; and recent parser papers report results in exactly these terms [8]. The practical consequence: any NED/TEDS number we produce internally can be placed directly alongside published leaderboard results when we evaluate a new vendor or open-source release. No alternative metric pair offers this.

**They are deterministic, interpretable, and cheap.** Both metrics are pure algorithms — no LLM judges, no API costs, no run-to-run variance. They execute in milliseconds per page, which makes them suitable not just for one-off bake-offs but as regression tests wired into CI: any change to our parsing configuration can be gated on "NED and TEDS did not regress on the golden set."

**They compose into a single headline number when needed.** The OmniDocBench v1.5 protocol defines an overall score as the average of (1 − text NED) × 100, table TEDS, and formula CDM [9]. For corpora without significant mathematical content, the natural two-metric summary is simply the pair reported side by side — which is also more informative for debugging than any single composite.

## 4. Known limitations — and why they don't change the recommendation

Intellectual honesty requires acknowledging the criticisms, because they are real and published.

**Criticism 1: string metrics penalize harmless representation differences.** Generative parsers can emit the same content in multiple semantically equivalent forms, and edit-distance-style metrics penalize valid variation; this is the motivation behind alternative designs such as olmOCR-Bench's binary "unit test" checks and Unstructured's token-recall/token-addition metrics [10][11]. This is true, and it means NED differences of a few points between two parsers should not be over-interpreted.

**Criticism 2: parsing fidelity is not the same as downstream task performance.** OHR-Bench (ICCV 2025) showed that OCR noise cascades into retrieval-augmented generation systems, with even the best parsers causing roughly a 14% downstream F1 drop, and that *semantic* noise (wrong content) harms consistently while *formatting* noise affects systems unevenly [12]. A follow-up benchmark found that models with near-perfect OmniDocBench scores can decline sharply on harder industrial documents, and that high character accuracy can coexist with retrieval failures [5].

Both criticisms argue for *supplementing* NED and TEDS in specific contexts (e.g., adding a task-level evaluation when parsing feeds a specific application), not for replacing them. As engineering metrics, NED and TEDS remain the right foundation precisely because the proposed alternatives trade away the properties we need: LLM-judged or task-level evaluations are expensive, non-deterministic, and incomparable across organizations, and unit-test approaches require hand-writing checks per document. Notably, even the benchmarks that critique string metrics still report them: OHR-Bench itself reports parser quality in edit distance alongside its downstream scores [12]. The field's critique is "NED and TEDS are not sufficient," not "NED and TEDS are not necessary" — and for a standard, fast, comparable quality gate, necessary is exactly the job description.

## 5. Implementation

The reference implementation for both metrics is the OmniDocBench evaluation repository (github.com/opendatalab/OmniDocBench) [2]. It computes character-level NED via the Levenshtein package and TEDS for tables in a single configurable run, and — importantly — wraps NED in its "Adjacency Search Match" pre-matching step, which merges and splits paragraphs on both sides before scoring so that parsers are not unfairly penalized for segmenting paragraphs differently from the ground truth [1]. TEDS reference code was originally released by IBM alongside PubTabNet (github.com/ibm-aur-nlp/PubTabNet) [4]. For lightweight internal regression tests against our own ground truth, NED is a one-liner with the `rapidfuzz` or `Levenshtein` Python packages using the formula in §2.1.

One caution when comparing against other tools' numbers: not every "edit distance" is the same edit distance. The docling-eval framework, for example, computes its text edit distance over word tokens rather than characters, and DP-Bench uses NID, an insertion/deletion-only variant [13] — neither is directly comparable to OmniDocBench-style character-level NED. This is itself an argument for standardizing: by fixing the exact definitions above, we avoid silent apples-to-oranges comparisons.

## 6. Recommendation

Adopt **character-level NED (text and reading order)** and **TEDS (tables)** as our standard document parsing metrics, computed with the OmniDocBench evaluation pipeline against a maintained internal golden set, reported per document type, and wired into CI as a regression gate. Where parsing output feeds a specific downstream application, supplement — never replace — this pair with a task-level evaluation appropriate to that application.

---

## References

1. Ouyang, L. et al. *OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations.* CVPR 2025. arXiv:2412.07626. https://arxiv.org/abs/2412.07626
2. OmniDocBench evaluation framework (GitHub, OpenDataLab). https://github.com/opendatalab/OmniDocBench
3. Zhong, X., ShafieiBavani, E., Jimeno Yepes, A. *Image-Based Table Recognition: Data, Model, and Evaluation.* ECCV 2020. arXiv:1911.10683. https://arxiv.org/abs/1911.10683
4. PubTabNet repository with TEDS reference implementation (GitHub, IBM). https://github.com/ibm-aur-nlp/PubTabNet
5. Sun, L. et al. *When Good OCR Is Not Enough: Benchmarking OCR Robustness for Retrieval-Augmented Generation.* arXiv:2605.00911. https://arxiv.org/abs/2605.00911
6. Yang, Z. et al. *CC-OCR: A Comprehensive and Challenging OCR Benchmark for Evaluating Large Multimodal Models in Literacy.* arXiv:2412.02210. https://arxiv.org/abs/2412.02210
7. Li, Z. et al. *READoc: A Unified Benchmark for Realistic Document Structured Extraction.* Findings of ACL 2025. arXiv:2409.05137. https://arxiv.org/abs/2409.05137
8. Wang, B. et al. *Infinity Parser: Layout Aware Reinforcement Learning for Scanned Document Parsing.* arXiv:2506.03197. https://arxiv.org/abs/2506.03197 (describes the standard OmniDocBench metric protocol: NED for text/formula/reading order, TEDS for tables)
9. OmniDocBench v1.5 overall-score protocol, as documented in: *OCRVerse: Towards Holistic OCR in End-to-End Vision-Language Models.* arXiv:2601.21639. https://arxiv.org/pdf/2601.21639
10. *OmniDocBench is Saturated, What's Next for OCR Benchmarks?* LlamaIndex blog. https://www.llamaindex.ai/blog/omnidocbench-is-saturated-what-s-next-for-ocr-benchmarks
11. *Introducing SCORE-Bench: An Open Benchmark for Document Parsing.* Unstructured blog. https://unstructured.io/blog/introducing-score-bench-an-open-benchmark-for-document-parsing
12. Zhang, J. et al. *OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented Generation.* ICCV 2025. arXiv:2412.02592. https://arxiv.org/abs/2412.02592 — code: https://github.com/opendatalab/OHR-Bench
13. DP-Bench dataset and NID metric definition (Upstage, Hugging Face). https://huggingface.co/datasets/upstage/dp-bench