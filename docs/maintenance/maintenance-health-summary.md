# Maintenance Health Inventory Summary

Generated on: 2026-04-24

## Current Phase

Phase 1: repository maintenance inventory.

## Scope

This phase scanned the repository for encoding issues, oversized files/modules, and legacy/generated/temp cleanup candidates. It intentionally did not delete, move, split, or rewrite business code.

## Outputs

- `docs/maintenance/encoding-issues.md`
- `docs/maintenance/large-files.md`
- `docs/maintenance/legacy-cleanup-inventory.md`

## Snapshot

- Suspected encoding issue files: 25
- Large files above threshold: 145
- Long source/doc files above threshold: 14
- Legacy/generated/temp candidates: 246

## Initial Priorities

1. Repair high-visibility encoding/garbled Chinese in docs and generated reports first.
2. Split oversized active source files only after owner review and regression coverage.
3. Treat model/data/PDF/database assets as valuable until reference checks prove otherwise.
4. Convert generated/temp artifacts into documented regeneration or ignore policies before removing anything.

## Non-Goals

- No deletion approvals are granted by this inventory.
- No API, data-model, FE, BE, or AI/model contract changes are made.
- No generated metric number is reinterpreted here.

## Recommended Next Phase

Phase 2 should be an encoding remediation slice focused on high-severity, high-visibility docs and user-facing strings. If code comments/docstrings are affected, repair only with local context and run `python -m py_compile` or the relevant build/test command afterward.

## Phase 2 Update

Phase 2 has started with a high-confidence encoding remediation slice. Confirmed mojibake in backend user-facing strings, docstrings, chat tool status text, and one corrupted test assertion was repaired. A focused encoding hygiene regression test was added so the repaired snippets do not silently regress.

This update still grants no deletion approval and does not change API, data-model, frontend, backend, or AI/model contracts. Large-file cleanup and legacy/generated/temp cleanup remain future phases.

## Phase 3 Update

Phase 3 started with a conservative oversized-source split pilot. The first target was `backend/services/chat_service.py`, and only pure chat tool presentation helpers were extracted into `backend/services/chat_tool_presentation.py`.

The split reduced the main chat service from about 2361 lines to 2280 lines, added focused regression coverage in `tests/test_chat_tool_presentation.py`, and kept all public API, data-model, frontend, backend, and AI/model contracts unchanged.

This update still grants no deletion approval. Large data/model/PDF/generated artifact cleanup remains a later owner-reviewed phase.

## Phase 4 Update

Phase 4 completed a conservative historical cleanup slice. The cleanup removed only untracked or ignored local caches, temporary verification folders, generated Playwright output, and rebuildable frontend production artifacts. No tracked business source, model asset, data asset, RAG PDF, vector store, uploaded asset, database, or thesis image asset was intentionally deleted in this phase.

The root `.gitignore` comments were restored to readable UTF-8 Chinese and the ignore policy now explicitly covers `.tmp/`, `frontend/.tmp/`, `tmp_doc_extract/`, and `output/` so these local artifacts do not keep reappearing as repository noise.

Fresh functional verification passed after cleanup: backend full regression returned `240 passed in 66.52s`, and frontend production build completed successfully with `built in 8.93s`.

## Phase 5 Update

Phase 5 completed presentation-polish governance for defense/demo readiness. The README now has a top-level showcase entry, and `docs/showcase/` contains a project one-pager, an 8-10 minute demo script, and a presentation checklist.

This phase also added `docs/maintenance/presentation-polish-phase5.md` and `tests/test_showcase_hygiene.py` so showcase entry points, required presentation sections, UTF-8/no-BOM encoding, and common mojibake fragments are guarded by regression tests.

No API, data-model, FE route, BE service behavior, model I/O, data asset, RAG PDF, vector-store, upload asset, or thesis artifact was changed or deleted by this phase. Fresh verification passed at `3 passed` for showcase hygiene, `243 passed` for full backend regression, and a successful frontend production build.

## Phase 6 Update

Phase 6 completed asset manifest and acceptance governance. The repository now has a machine-readable asset manifest at `docs/maintenance/asset-manifest-phase6.json`, a human-readable strategy at `docs/maintenance/asset-manifest-phase6.md`, and a complete acceptance report at `docs/maintenance/phase6-acceptance-report.md`.

The manifest covers raw data, processed data, model artifacts, RAG documents, vector store, upload samples, runtime databases, and thesis artifacts. The total scanned asset footprint is about 156563.64 MB, so the accepted policy is explicit owner-reviewed externalization rather than direct deletion.

This phase added `tests/test_asset_manifest_phase6.py` to guard the manifest structure, README links, retention policy, demo boundaries, and no-contract/no-asset-deletion acceptance language. Fresh acceptance evidence passed at `6 passed` for focused Phase 5/6 hygiene, `246 passed` for full backend regression, and a successful frontend production build.
