# Health AI Platform Handoff

## Ownership

- Owner: `general`
- Status: `final_docs_refresh_after_qa_pass`

## Purpose

Provide the repository-facing handoff package for the current QA-passed release/demo documentation state.

## Current Stage

- `general` is completing the Lifestyle behavior upload timeline repository-facing handoff documentation after QA PASS.
- This handoff reflects current state: the Lifestyle page has platform-standard CSV/JSON behavior-day upload, focused backend/frontend tests, full backend regression, frontend build success, live contract probes, and headed browser upload artifacts; earlier Lifestyle demo and stability/model-compatibility evidence remain documented below.

## Updated Artifacts

- [README.md](E:\health_ai_platform_2.0\README.md)
- [demo-script.md](E:\health_ai_platform_2.0\docs\showcase\demo-script.md)
- [presentation-checklist.md](E:\health_ai_platform_2.0\docs\showcase\presentation-checklist.md)
- [defense-demo-runbook.md](E:\health_ai_platform_2.0\docs\showcase\defense-demo-runbook.md)
- [deployment.md](E:\health_ai_platform_2.0\docs\deployment.md)
- [release.md](E:\health_ai_platform_2.0\docs\release.md)
- [handoff.md](E:\health_ai_platform_2.0\docs\handoff.md)

## Lifestyle Behavior Upload Timeline Handoff (2026-05-13)

- Capability: the Lifestyle page now exposes platform-standard behavior-day `.csv` / `.json` upload beside the existing demo scenario flow.
- Backend route: authenticated multipart `POST /api/v1/lifestyle/import-behavior-day`.
- Backend behavior: parse-only and validation-only; no raw upload, parsed event, generated `lifestyle_context`, profile, IoT, health-history, medical-document, or risk-snapshot persistence.
- Success response: import metadata plus `behavior_day` with nested `lifestyle_context.v1`; all returned upload-derived data remains `data_mode="user_uploaded"` and provenance-labeled with `source_provenance.source_type="user_uploaded"`.
- Selector behavior: optional `patient_id` and `local_date` multipart fields are assertions, not overrides; mismatches are rejected.
- Error semantics: structured `400` validation responses, `413` oversize responses, and `415` unsupported media responses.
- Demo/device boundary: existing demo scenarios remain available and the real-device API remains placeholder-only/not connected.
- QA status: PASS. Evidence is focused backend `18 passed`, focused frontend `15 passed`, full backend `269 passed`, frontend build success, live contract probes, and headed browser upload artifacts under `output/playwright`.

## Lifestyle Digital Twin Demo Handoff (2026-05-07)

- Recommended demo placement: after Clinical/OCR and before risk analysis, so the speaker can bridge from clinical profile evidence into optional behavior context.
- What to show: load/select one of three demo scenarios in Lifestyle, replay the day timeline, inspect event detail, show summary metrics, show diet_vision nutrition sync, then run demo-aware analysis with `lifestyle_context.v1`.
- Required wording: this is `simulated_demo` / Demo-only behavior replay, not real device, wearable, IoT, or real food-image evidence.
- Fusion wording: `/analyze/comprehensive` uses optional `lifestyle_context.v1` only as provenance-labeled heuristic context for explanation; do not describe the output as a clinically calibrated posterior probability.
- Persistence wording: replay and demo analysis do not auto-save profile data, do not call IoT batch sync, do not upload documents or food images, and do not create health-history or risk-snapshot rows.
- QA status: PASS. Evidence is backend focused tests `6 passed`, frontend node tests `13 passed`, frontend build success, and a real Vite browser check using mocked demo APIs.
- Residual risk: QA did not run a full live authenticated FastAPI login/API/browser E2E path across all three demo patients.

## Residual Notes (Non-Blocking)

- Lifestyle demo browser validation used mocked scenario APIs rather than a full live authenticated FastAPI E2E path.
- Full UI interaction coverage for selecting and replaying all three demo patients remains future validation.
- `torch.load(..., weights_only=False)` `FutureWarning` appears in strict compatibility and smoke logs.
- Optional Redis degraded warning may appear in local Playwright webserver logs when Redis is unavailable.
- Release-state transition remains orchestrator-owned in [state.yaml](E:\health_ai_platform_2.0\docs\blackboard\state.yaml).

## Next Stage

- `orchestrator` should review and accept this repository-facing Lifestyle demo handoff. Only the orchestrator may update blackboard state if it wants to record the documentation handoff as closed.

## Oversized File Split Plan (Contract-Safe)

- Context:
  - `backend/services/chat_service.py` is large and mixes orchestration, normalization, and response shaping concerns.
  - `frontend/src/views/chat/DrAI.vue` is large and mixes conversation data orchestration, UI rendering state, and transport fallback.
  - `frontend/src/views/ClinicalView.vue` is large and mixes OCR ingestion, field-state guidance, and anomaly/analysis refresh behavior.
- Phase 1 (safe extraction, no API-visible change):
  - Extract pure helpers from `chat_service.py` into internal modules (normalizers, evidence-panel shaping, decision-summary helpers) with unchanged input/output signatures.
  - Extract DrAI sidebar selection/archive/rename logic into composables while preserving existing props/events and route calls.
  - Extract Clinical OCR mapping and guided-missing state helpers into composables; keep existing store contracts unchanged.
- Phase 2 (targeted tests before structural move):
  - Backend: add focused unit tests for extracted helper modules and keep current endpoint contract tests green.
  - Frontend: add source-level tests for extracted composables and retain current build + smoke coverage.
- Phase 3 (optional deeper split, only if needed):
  - Evaluate splitting stream transport and message rendering in DrAI into separate components after Phase 1/2 prove no regressions.
  - Any API-visible semantics or payload-shape pressure discovered during split must route back through `architect` as an architecture change request.

## Files Read / Files Changed

- Files read:
  - [AGENTS.md](E:\health_ai_platform_2.0\AGENTS.md)
  - [.codex/config.toml](E:\health_ai_platform_2.0\.codex\config.toml)
  - [.codex/agents/general.toml](E:\health_ai_platform_2.0\.codex\agents\general.toml)
  - [state.yaml](E:\health_ai_platform_2.0\docs\blackboard\state.yaml)
  - [qa-report.md](E:\health_ai_platform_2.0\docs\qa-report.md)
  - [architecture.md](E:\health_ai_platform_2.0\docs\architecture.md)
  - [api-contract.md](E:\health_ai_platform_2.0\docs\api-contract.md)
  - [data-model-contract.md](E:\health_ai_platform_2.0\docs\data-model-contract.md)
  - [README.md](E:\health_ai_platform_2.0\README.md)
  - [deployment.md](E:\health_ai_platform_2.0\docs\deployment.md)
  - [demo-script.md](E:\health_ai_platform_2.0\docs\showcase\demo-script.md)
  - [presentation-checklist.md](E:\health_ai_platform_2.0\docs\showcase\presentation-checklist.md)
  - [defense-demo-runbook.md](E:\health_ai_platform_2.0\docs\showcase\defense-demo-runbook.md)
  - [release.md](E:\health_ai_platform_2.0\docs\release.md)
  - [handoff.md](E:\health_ai_platform_2.0\docs\handoff.md)
- Files changed:
  - [README.md](E:\health_ai_platform_2.0\README.md)
  - [deployment.md](E:\health_ai_platform_2.0\docs\deployment.md)
  - [demo-script.md](E:\health_ai_platform_2.0\docs\showcase\demo-script.md)
  - [presentation-checklist.md](E:\health_ai_platform_2.0\docs\showcase\presentation-checklist.md)
  - [defense-demo-runbook.md](E:\health_ai_platform_2.0\docs\showcase\defense-demo-runbook.md)
  - [release.md](E:\health_ai_platform_2.0\docs\release.md)
  - [handoff.md](E:\health_ai_platform_2.0\docs\handoff.md)

## Decisions Made

- Updated only allowed general-owner documents:
  - [README.md](E:\health_ai_platform_2.0\README.md)
  - [deployment.md](E:\health_ai_platform_2.0\docs\deployment.md)
  - [release.md](E:\health_ai_platform_2.0\docs\release.md)
  - [handoff.md](E:\health_ai_platform_2.0\docs\handoff.md)
- Treated showcase edits as an orchestrator-approved narrow showcase handoff update for defense/demo materials:
  - [demo-script.md](E:\health_ai_platform_2.0\docs\showcase\demo-script.md)
  - [presentation-checklist.md](E:\health_ai_platform_2.0\docs\showcase\presentation-checklist.md)
  - [defense-demo-runbook.md](E:\health_ai_platform_2.0\docs\showcase\defense-demo-runbook.md)
- Replaced stale Lifestyle demo-only wording with the current Lifestyle behavior upload QA PASS state where it affects release readiness.
- Kept architect-frozen semantics language intact:
  - fusion is heuristic multiplicative scaling, not strict Bayesian posterior semantics
  - Baidu OCR/Moonshot-Kimi/RAG boundaries remain backend-mediated and privacy-bounded
- Added Lifestyle behavior upload release/demo wording:
  - authenticated parse-only `POST /api/v1/lifestyle/import-behavior-day`
  - structured 400/413/415 error semantics and optional selector mismatch rejection
  - `user_uploaded` data-mode/provenance labels
  - existing demo scenarios remain available
  - real-device API remains placeholder-only/not connected
- Preserved earlier Lifestyle demo wording:
  - `simulated_demo` / Demo-only behavior timeline only
  - optional `lifestyle_context.v1` fusion explanation
  - no profile, IoT, document/food-image, health-history, or risk-snapshot auto-save path

## Assumptions / Risks / Open Questions

- Assumption: this stage refreshes repository-facing docs only and does not modify gate state directly.
- Assumption: QA PASS in the blackboard is the authoritative release-readiness input for this documentation refresh.
- Assumption: the Lifestyle scenario artifacts remain demo assets with `data_mode="simulated_demo"` and visible provenance labels.
- Assumption: uploaded behavior-day files remain preview/runtime payloads only; any future save/import-to-record capability requires a separate architect contract.
- Risk (non-blocking): QA accepted parent-thread headed browser upload evidence and did not rerun a fresh full cross-browser upload matrix during revalidation.
- Risk (non-blocking): current Lifestyle demo-engine browser evidence remains a mock-API browser check for the three scenario flow, while the upload slice has live headed browser artifact coverage.
- Risk (non-blocking): `torch.load(..., weights_only=False)` warning remains until checker hardening is implemented.
- Risk (non-blocking): optional Redis degraded warning can still appear in local smoke environments.
- Open question: none blocking this handoff.

## Evidence for Requested Gate Changes

- Blackboard currently shows `qa_passed: true`, `release_ready: false`, and `next_owner: general` for the Lifestyle behavior upload timeline slice.
- Lifestyle behavior upload timeline QA evidence confirms:
  - `python -m pytest tests/test_behavior_day_import.py tests/test_demo_behavior_scenarios.py tests/test_profile_csv_import.py -q` -> `18 passed`
  - `node --test frontend\tests\lifestyle-demo-simulator.node.test.mjs frontend\tests\lifestyle-behavior-import.node.test.mjs` -> `15 passed`
  - `python -m pytest tests -q` -> `269 passed`
  - `npm.cmd run build` in `frontend` -> passed
  - live contract probes in `output/playwright/behavior-upload-contract-probes.json` confirm 200 success, selector mismatch `400`, malformed upload `400`, unsupported media `415`, and oversize `413`.
  - headed browser upload evidence in `output/playwright/behavior-upload-live-e2e.json` records upload route `200`, `/analyze/comprehensive` `200`, no console errors, upload UI visible, and real-device placeholder visible.
- Earlier Lifestyle demo QA evidence confirms:
  - `python -m pytest tests/test_demo_behavior_scenarios.py -q` -> `6 passed`
  - frontend node tests -> `13 passed`
  - frontend production build -> success
  - real Vite browser check with mocked demo APIs -> passed
- Earlier stability QA final evidence confirms its required checks were green:
  - `python -m pytest tests -q` -> `235 passed in 57.62s`
  - `python -m pytest tests/test_cors_config.py -q` -> `3 passed in 0.33s`
  - `npm.cmd run build` -> success (`built in 52.03s`)
  - `npx.cmd playwright test tests/dr-ai-takeover.spec.js --project=chromium --reporter=line` -> `3 passed`
  - `npx.cmd playwright test tests/ocr-guided-completion.spec.js --project=chromium --reporter=line` -> `4 passed`
  - `python ai_core/check_model_compatibility.py --strict` -> `exit code 0` (`OK: no compatibility issues detected.`)
- Requested gate interpretation:
  - `qa_passed` should remain `true`.
  - `release_ready` can be considered by the orchestrator after reviewing this repository-facing documentation refresh.

## Requested Next Owner

- `orchestrator`
