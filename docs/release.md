# Health AI Platform Release Notes

## Ownership

- Owner: `general`
- Status: `prepared_behavior_upload_timeline_handoff_after_qa_pass`

## Purpose

Summarize the current remediation, Lifestyle demo, and Lifestyle behavior upload handoff status, what changed, and the QA-passed evidence package for orchestrator review.

## Current Candidate Release Scope (2026-04-23)

- Slice: stability, engineering hygiene, and model-governance remediation.
- Scope type: CORS/runtime/config hardening + dependency/model-governance controls + training-script path cleanup.
- Public surface impact: no new routes; API-visible semantics remain under architect freeze.
- QA state: **passed** (`qa_passed=true`) with strict model compatibility gate green.

## Lifestyle Behavior Upload Timeline Addendum (2026-05-13)

- Scope: repository-facing release documentation for the QA-passed Lifestyle behavior upload timeline.
- Public surface impact: additive authenticated `POST /api/v1/lifestyle/import-behavior-day` route for platform-standard behavior-day CSV/JSON uploads.
- Upload contract: bearer-authenticated `multipart/form-data`; `file` is required, while `patient_id` and `local_date` are optional selector assertions that reject mismatches.
- Backend behavior: parse-only and validation-only. Success returns import metadata plus `behavior_day` with nested `lifestyle_context.v1`; no raw upload, parsed timeline, context, analysis output, profile field, IoT row, health-history row, medical document, or risk snapshot is persisted.
- Provenance: all generated upload data remains `data_mode="user_uploaded"` with `source_provenance.source_type="user_uploaded"`; uploaded CSV/JSON must not be relabeled as `real_device`.
- Error semantics: structured `400` validation responses, `413` oversize responses, and `415` unsupported media responses are now covered by QA contract probes.
- Demo/device boundary: existing demo scenarios remain available, and the real-device API remains a placeholder only; no live wearable/device connector or background sync is approved by this slice.

## Lifestyle Digital Twin Demo Engine Addendum (2026-05-07)

- Scope: repository-facing handoff documentation for the QA-passed Lifestyle Digital Twin demo engine.
- Public surface impact: additive authenticated read-only `/api/v1/demo/behavior-scenarios` list/detail routes and optional `lifestyle_context.v1` validation on `/analyze/comprehensive` are already contract-approved and QA-passed.
- Demo positioning: present the Lifestyle behavior simulator after Clinical/OCR and before risk analysis, then explain how optional lifestyle context contributes to the fusion narrative.
- Boundary: the timeline is `simulated_demo` / Demo-only behavior data, not real wearable, IoT, or food-camera evidence.
- Persistence boundary: scenario replay and demo analysis must not auto-save profile data, sync IoT records, upload documents/food images, or create health-history/risk-snapshot rows.
- Fusion boundary: `lifestyle_context.v1` is optional provenance-labeled heuristic context for explanation, not a required clinical input floor and not a clinically calibrated posterior probability.

## What Changed In This Slice

- Backend credentialed CORS behavior is now aligned to allowlisted-origin echo under runtime settings, and CORS-focused tests are green.
- Runtime configuration responsibility drift was reduced by clarifying `backend/core/config.py` (env/runtime) vs `backend/config.py` (repo-local paths/constants).
- AI/data governance artifacts were added:
  - `ai_core/check_model_compatibility.py`
  - `ai_core/requirements-ml-baseline.txt`
  - model governance docs for LightGBM, XGBoost, EfficientNet/ResNet, LSTM, GWAS/PRS, and RAG/LLM/OCR boundaries.
- Training scripts removed machine-local absolute paths and now use project/config-resolved paths.

## What Did Not Change

- No new public route or SSE event type was introduced in this remediation round.
- No API contract fields were silently widened by FE/BE/AI-data.
- Fusion output wording is frozen to heuristic multiplicative semantics; no strict Bayesian posterior claim was introduced.
- Provider data boundaries remain unchanged: raw OCR/LLM/RAG payloads are not public response fields.

## Governance Version Tracking

- CORS behavior baseline: credentialed allowlisted-origin echo (`*` with credentials is disallowed).
- Runtime config ownership baseline: `backend/core/config.py` for env/runtime settings; `backend/config.py` for repo-local constants/paths.
- Fusion semantics baseline: `base x gene_modifier x lifestyle_modifier` is heuristic scaling.
- Normative semantics stay frozen in [architecture.md](E:\health_ai_platform_2.0\docs\architecture.md), [api-contract.md](E:\health_ai_platform_2.0\docs\api-contract.md), and [data-model-contract.md](E:\health_ai_platform_2.0\docs\data-model-contract.md)
- Rollout state remains orchestrator-owned in [state.yaml](E:\health_ai_platform_2.0\docs\blackboard\state.yaml)

## Verification Evidence

- Lifestyle behavior upload timeline QA PASS:
  - `python -m pytest tests/test_behavior_day_import.py tests/test_demo_behavior_scenarios.py tests/test_profile_csv_import.py -q` -> `18 passed`
  - `node --test frontend\tests\lifestyle-demo-simulator.node.test.mjs frontend\tests\lifestyle-behavior-import.node.test.mjs` -> `15 passed`
  - `python -m pytest tests -q` -> `269 passed`
  - `npm.cmd run build` in `frontend` -> success
  - live contract probes in `output/playwright/behavior-upload-contract-probes.json` -> 200/400/400/415/413/400 semantics with structured response bodies
  - headed browser upload evidence in `output/playwright/behavior-upload-live-e2e.json` -> upload route `200`, `/analyze/comprehensive` `200`, no console errors, upload UI visible, real-device placeholder visible
- Lifestyle Digital Twin demo engine QA PASS:
  - `python -m pytest tests/test_demo_behavior_scenarios.py -q` -> `6 passed`
  - `node --test .\tests\*.node.test.mjs` in `frontend` -> `13 passed`
  - `npm.cmd run build` in `frontend` -> success
  - real Vite browser check at `/lifestyle` with mocked demo APIs -> passed for scenario loading, `simulated_demo`/Demo-only labels, timeline event display, and replay control
- `python -m pytest tests -q` -> `235 passed in 57.62s`
- `python -m pytest tests/test_cors_config.py -q` -> `3 passed in 0.33s`
- `npm.cmd run build` (`frontend`) -> success (`built in 52.03s`)
- `npx.cmd playwright test tests/dr-ai-takeover.spec.js --project=chromium --reporter=line` -> `3 passed`
- `npx.cmd playwright test tests/ocr-guided-completion.spec.js --project=chromium --reporter=line` -> `4 passed`
- `python ai_core/check_model_compatibility.py --strict` -> exit code `0` (`OK: no compatibility issues detected.`)

## Residual Risks

- Lifestyle behavior upload residual risk:
  - QA accepted parent-thread headed browser evidence for live upload coverage; the revalidation reran automated regressions and contract probes but did not rerun a fresh full cross-browser upload matrix.
  - `output/playwright/behavior-upload-live-e2e.json` records a successful `/analyze/comprehensive` request even though `fusionButtonVisible` was false in that artifact; QA treats this as a visual-observation limitation, not a blocker.
- Lifestyle demo residual risk:
  - earlier demo-engine QA used mocked API responses over the real local frontend rather than a live authenticated FastAPI login/API/browser end-to-end run across all three demo patients
- Non-blocking in this round:
  - `torch.load(..., weights_only=False)` `FutureWarning` appears in compatibility/smoke logs.
  - optional Redis degraded warning may appear in local Playwright webserver logs when Redis is unavailable.
  - backend regression, frontend build, and targeted browser smoke remain green.

## Operator Notes

- Use [deployment.md](E:\health_ai_platform_2.0\docs\deployment.md) for rollout checklist and compatibility baseline maintenance steps.
- Use [qa-report.md](E:\health_ai_platform_2.0\docs\qa-report.md) as the authoritative evidence source for this round.
- Use [handoff.md](E:\health_ai_platform_2.0\docs\handoff.md) for orchestrator review and handoff acceptance.

## Contract-Refresh Release Policy

The latest architect refresh also freezes release-policy boundaries for OCR degradation, incomplete clinical data, and optional runtime dependencies.

Approved release posture:

- Redis remains optional when cache degradation is clean and bounded.
- Degraded fusion fallback is releasable only when `/analyze/comprehensive` still returns a consumable backend-owned `risk_report`.
- OCR-unavailable mode is releasable only when the release scope explicitly accepts manual-entry fallback and FE surfaces `stored_unprocessed` rather than a generic failure.
- Missing OCR credentials are release-blocking for any environment that still advertises OCR as available.
- scikit-learn / joblib model-version compatibility warnings are release-blocking; the canonical fix is model re-export, not indefinite runtime drift acceptance.

Warning policy:

- Acceptable warnings:
  - one concise degraded warning per optional dependency condition
- Release-blocking warnings:
  - repeated degraded warning spam
  - generic stack traces for known degraded paths
  - model-compatibility warnings
  - warnings that leave FE/BE unable to distinguish saved-but-degraded state from true failure
