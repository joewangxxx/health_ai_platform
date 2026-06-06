# Architecture Change Request: OCR Canonical Biomarker Extension

## Status

Approved and frozen by `architect` on 2026-04-24.

## Context

Phase 3 OCR evaluation found that the deterministic OCR fallback can extract
`AST`, `HGB`, and `UA`, but the current `ocr_summary.v1` canonical metric list
does not approve these keys as canonical metrics. They therefore remain in
`extra_findings`, which is contract-safe but lowers all-field canonical recall.

## Proposed Change

Extend the approved `ocr_summary.v1.metrics` canonical key set to include:

- `AST`
- `HGB`
- `UA`

## Rationale

- These are common physical-examination biomarkers.
- They are already extracted by the raw fallback path.
- Promoting them would improve report-comparison, evidence-panel, and
  downstream structured-analysis consistency.

## Contract Impact

- Additive data-model contract change.
- No public route shape needs to change.
- Existing clients that treat `metrics` as a dictionary remain compatible.
- FE must not assume these fields exist for all reports.
- This approval is report-level only: it does not create new `UserProfile`
  columns and does not authorize automatic promotion into unsupported profile
  fields.

## Non-Goals

- No diagnosis or treatment inference from these fields.
- No unit conversion beyond bounded metric-object normalization.
- No backfill of legacy rows in this request.

## Requested Owner

`be` may now implement production normalization that promotes `AST`, `HGB`, and
`UA` from raw OCR findings into `ocr_summary.v1.metrics` under the frozen
report-level rules above. `qa` should validate with OCR extraction metrics and
canonical-envelope regression after implementation.
