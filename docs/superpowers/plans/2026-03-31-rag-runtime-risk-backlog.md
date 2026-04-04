# Health AI Platform Residual Risk Backlog

> For agentic workers: this document is a planning artifact only. It enumerates remaining non-blocking risks after the validated RAG PDF extraction remediation slice and defines bounded follow-up slices without opening implementation automatically.

## Goal

Convert the current non-blocking residual risks into a concrete backlog so future slices can improve RAG quality, runtime hygiene, and validation depth without widening public contracts or destabilizing the release-ready platform.

## Scope

This backlog focuses only on currently known non-blocking residual risks in:

- the RAG PDF extraction path
- benchmark observability
- runtime dependency signaling
- backend hygiene and validation coverage

It does not authorize:

- public API contract changes
- semantic chunking or LLM-assisted chunking
- write-capable Agent tools
- evidence-panel or chat contract widening

---

## Priority Order

1. PDF low-text-density diagnostics
2. OCR fallback capability signaling
3. Loader fallback warning cleanup
4. `section_title` stabilization enhancement
5. `page_range` capability evaluation
6. Pydantic deprecation cleanup
7. Cross-browser local execution completion

---

## Slice 1: PDF Low-Text-Density Diagnostics

### Goal

Make low-quality PDF extraction observable at the document level instead of inferring it only from overall benchmark averages.

### Why

The current benchmark proves the corpus can be loaded and split, but it still hides which PDFs remain low-value after extraction and why.

### Requirements

- Extend `backend/rag/benchmark.py` with document-level low-density indicators.
- Add bounded metrics such as:
  - average chunk size
  - blank-page count or ratio
  - OCR-touched page count
  - extremely short chunk count
- Mark documents that fall below a configurable low-density threshold.
- Keep output bounded and benchmark-only; do not change chat routes or runtime payloads.

### Acceptance Criteria

- The benchmark explicitly identifies low-text-density PDFs.
- The output distinguishes “still low density” from “normal extraction.”
- No vector-store writes are introduced.
- No public chat contract changes are introduced.

---

## Slice 2: OCR Fallback Capability Signaling

### Goal

Make it explicit whether OCR fallback is available in the current environment before build and benchmark operations proceed.

### Why

The current extraction enhancement works only when `pdftoppm`, Baidu OCR credentials, and network access are available. This is safe but still too implicit.

### Requirements

- Add a single capability summary for:
  - `pdftoppm`
  - Baidu OCR credentials
  - OCR network dependency availability assumptions
- Surface that summary once in the benchmark/build flow.
- Document the same prerequisites in deployment/runtime docs.
- Preserve current fallback behavior when OCR is unavailable.

### Acceptance Criteria

- Operators can tell whether OCR fallback is available before trusting extraction quality.
- Missing prerequisites produce one clear, bounded warning instead of silent quality degradation.
- Benchmark/build still succeed safely without OCR fallback.

---

## Slice 3: Loader Fallback Warning Cleanup

### Goal

Reduce repetitive loader warnings and make loader selection behavior easier to understand.

### Why

Current benchmark runs emit repeated `PyPDFLoader unavailable` warnings because fallback happens per PDF rather than as one summarized environment note.

### Requirements

- Unify loader selection behavior between:
  - `backend/rag/build_kb.py`
  - `backend/rag/benchmark.py`
- Emit one summarized loader-fallback warning instead of one warning per document.
- Keep current fallback semantics intact.
- Do not change chunking defaults or metadata-floor behavior.

### Acceptance Criteria

- Benchmark/build logs become significantly less noisy.
- Fallback remains functional when `langchain_community` is missing.
- No public contract change is introduced.

---

## Slice 4: `section_title` Stabilization Enhancement

### Goal

Improve optional `section_title` coverage without allowing fabricated titles.

### Why

Current `section_title` handling is safe but conservative, so explainability remains limited for many PDFs.

### Requirements

- Keep `section_title` optional.
- Expand only stable lightweight title rules, such as:
  - numbered headings
  - common chapter labels
  - clearly isolated title lines
- Do not infer fuzzy or probabilistic titles.
- Add focused tests for:
  - titled PDF content
  - untitled PDF content
  - OCR-produced heading text

### Acceptance Criteria

- `section_title` coverage improves on eligible documents.
- No fabricated titles are introduced.
- The metadata floor remains unchanged.

---

## Slice 5: `page_range` Capability Evaluation

### Goal

Determine whether real cross-page provenance can be added safely for current RAG chunks.

### Why

`page_range_coverage` is still `0.0`, which limits provenance richness even though the current behavior is contract-safe.

### Requirements

- Evaluate whether current loader and split behavior can safely preserve cross-page ranges.
- Only emit `page_range` when a chunk truly spans multiple pages.
- Do not synthesize fake ranges.
- Add focused tests for:
  - single-page chunks
  - real cross-page chunks

### Acceptance Criteria

- Either:
  - cross-page ranges are added safely and tested, or
  - the repository records a validated “not safely derivable” conclusion.
- No fabricated provenance is introduced.

---

## Slice 6: Pydantic Deprecation Cleanup

### Goal

Reduce current Pydantic v2 deprecation noise and future-upgrade risk.

### Why

The warnings are not blocking today, but they continue to pollute regression runs and will become real migration pressure later.

### Requirements

- Identify current class-based `Config` usage in high-frequency models.
- Migrate in bounded batches to `ConfigDict`.
- Prioritize startup-critical and test-heavy modules first.
- Preserve response semantics and contracts.

### Acceptance Criteria

- Warning count decreases measurably.
- Full pytest remains green after each batch.
- No route or schema behavior drifts.

---

## Slice 7: Cross-Browser Local Completion

### Goal

Turn current environment-limited cross-browser validation into real local multi-browser execution.

### Why

Chromium already runs locally, but Firefox/WebKit still depend on missing local Playwright browser binaries.

### Requirements

- Install Playwright Firefox/WebKit binaries locally.
- Re-run the existing browser smoke suite across all configured browsers.
- Update QA evidence with the result.
- Do not widen FE/BE contracts in this slice.

### Acceptance Criteria

- Chromium, Firefox, and WebKit all attempt the same smoke flow locally.
- Remaining failures, if any, are clearly classified as environment or product defects.
- No product behavior changes are required for the validation slice.

---

## Recommended Execution Strategy

### Wave 1

- Slice 1: PDF Low-Text-Density Diagnostics
- Slice 2: OCR Fallback Capability Signaling
- Slice 3: Loader Fallback Warning Cleanup

### Wave 2

- Slice 4: `section_title` Stabilization Enhancement
- Slice 5: `page_range` Capability Evaluation

### Wave 3

- Slice 6: Pydantic Deprecation Cleanup
- Slice 7: Cross-Browser Local Completion

## Notes

- Slice 1 through Slice 5 should remain inside the already-frozen RAG contract unless they discover real contract pressure.
- Slice 6 is backend hygiene and should be isolated from feature work.
- Slice 7 is validation-only and should not be used as a pretext for frontend behavior changes.
