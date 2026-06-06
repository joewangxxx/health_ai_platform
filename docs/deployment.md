# Health AI Platform Deployment Notes

## Ownership

- Owner: `general`
- Status: `final_docs_refresh_after_qa_pass`

## Purpose

Capture operator-facing rollout notes for the current QA-passed repository state, including the 2026-05-13 Lifestyle behavior upload timeline slice, while release-state closure remains orchestrator-owned.

## Current Deployment Slice (2026-05-13)

- Scope: Lifestyle page platform-standard behavior-day CSV/JSON upload.
- Backend route: `POST /api/v1/lifestyle/import-behavior-day`.
- Auth and transport: bearer-authenticated `multipart/form-data`.
- Runtime behavior: parse-only and validation-only; the backend returns a preview payload and does not persist the raw file, parsed rows, generated timeline, `lifestyle_context`, profile fields, IoT rows, health-history rows, medical documents, or risk snapshots.
- Success response: import metadata plus `behavior_day` with nested `lifestyle_context.v1`; all generated behavior data remains `data_mode="user_uploaded"` and provenance-labeled as `source_provenance.source_type="user_uploaded"`.
- Selector behavior: optional multipart `patient_id` and `local_date` are assertions and reject mismatches with structured `400` validation errors.
- Error semantics: structured `400` validation errors, `413` for upload size over 1 MB, and `415` for unsupported extension or content type.
- Demo/device boundary: existing demo scenarios remain available; real-device API remains placeholder-only and is not connected to wearable, vendor, Health Connect, Apple Health, background sync, or `/api/v1/iot/sync/batch`.
- Gate posture: QA PASS accepted by orchestrator; final `release_ready` transition remains orchestrator-owned.

## Current Deployment Slice (2026-04-23)

- Scope: CORS/runtime/config remediation + model-governance documentation + training-path de-hardcoding.
- Public API impact: no new public routes; CORS behavior aligned to credentialed allowlisted-origin echo under frozen contract.
- Frontend impact: production build remains green; no contract-redefining FE change required in this round.
- Gate posture: required QA evidence is green, including strict model compatibility; final release-state transition remains orchestrator-owned.

## Rollout Checklist

- Confirm backend health:
  - `GET /health`
- Verify Lifestyle behavior upload contract when this slice is in rollout scope:
  - `python -m pytest tests/test_behavior_day_import.py tests/test_demo_behavior_scenarios.py tests/test_profile_csv_import.py -q`
  - expected result from QA evidence: `18 passed`
  - `node --test frontend\tests\lifestyle-demo-simulator.node.test.mjs frontend\tests\lifestyle-behavior-import.node.test.mjs`
  - expected result from QA evidence: `15 passed`
  - Confirm contract-probe coverage for 200 success, selector mismatch `400`, malformed upload `400`, oversize `413`, and unsupported media `415`.
  - Confirm headed browser upload evidence in `output/playwright/behavior-upload-live-e2e.json` before using the upload flow in a live demo.
- Re-run baseline verification:
  - `python -m pytest tests -q`
  - expected result for the latest Lifestyle upload QA pass: `269 passed`
  - `python -m pytest tests/test_cors_config.py -q`
  - expected result: `3 passed`
- Verify the frontend bundle:
  - `npm.cmd run build` in `frontend`
  - expected result: Vite build success
- Verify targeted browser smoke:
  - `npx.cmd playwright test tests/dr-ai-takeover.spec.js --project=chromium --reporter=line`
  - `npx.cmd playwright test tests/ocr-guided-completion.spec.js --project=chromium --reporter=line`
- Execute strict model compatibility gate:
  - `python ai_core/check_model_compatibility.py --strict`
  - expected result: `OK: no compatibility issues detected.` (`exit code 0`)
  - expected package baseline:
    - `xgboost==2.1.4`
    - `torch==2.5.1`
    - `torchvision==0.20.1`
    - `scikit-learn==1.6.1`
    - `joblib==1.5.3`
- Compatibility maintenance if drift recurs:
  - `pip install -r ai_core/requirements-ml-baseline.txt`
  - run `python ai_core/reexport_joblib_artifacts.py`
  - rerun `python ai_core/check_model_compatibility.py --strict` until it exits `0`

## Governance Version Tracking

- CORS contract baseline: credentialed allowlisted-origin echo (no wildcard origin with credentials).
- Configuration ownership baseline: `backend/core/config.py` owns runtime env; `backend/config.py` owns repo-local paths/constants.
- Fusion semantics baseline: `base x gene_modifier x lifestyle_modifier` is heuristic multiplicative scaling, not strict Bayesian posterior semantics.
- Approval and rollout state remain orchestrator-owned in [state.yaml](E:\health_ai_platform_2.0\docs\blackboard\state.yaml).

## Privacy Boundary Reminder

- Baidu OCR, Moonshot/Kimi-compatible LLM calls, and RAG retrieval remain backend-mediated.
- Raw provider payloads, raw OCR payload text, and raw RAG passages must not be exposed via public APIs.
- Logs/audit/replay must stay bounded metadata and must not persist raw health content or prompt/reply transcripts.
- Any API-visible semantic change to `risk_report`, `analysis_context`, chat metadata, or fusion interpretation requires architect review before rollout.

## Known Deployment Caveats

- Lifestyle behavior upload QA evidence is green for focused backend/frontend tests, full backend regression, frontend build, live contract probes, and headed browser upload artifacts.
- Backend regression, CORS-focused tests, frontend build, and targeted Playwright smoke are all green in the prior stability round.
- Strict model compatibility gate is also green in this round.
- Residual warnings are non-blocking:
  - `torch.load(..., weights_only=False)` `FutureWarning` appears in compatibility/smoke logs.
  - optional Redis degraded warning may appear in local Playwright webserver logs when Redis is unavailable.
- This document does not change blackboard gate state directly.

## Optional Dependency Release Policy

This repository now distinguishes acceptable degraded release from release-blocking dependency drift.

Allowed degraded release cases:

- Redis unavailable:
  - allowed when runtime degrades cleanly without user-facing route failure
  - one concise degraded warning is acceptable
- Fusion enhancement unavailable because lifestyle/XGBoost-backed fusion cannot initialize:
  - allowed only when `/analyze/comprehensive` still returns a backend-owned consumable `risk_report`
  - release notes must explicitly call out degraded fusion fallback
- OCR unavailable because credentials or client readiness are missing:
  - allowed only for environments whose release scope explicitly accepts manual-entry fallback
  - FE must show the frozen `stored_unprocessed` document state instead of a generic upload failure

Release-blocking conditions:

- any generic 500 on a path that should now surface a frozen degraded business state
- repeated import-time warning spam for optional dependencies
- missing OCR credentials in an environment that still advertises OCR as a normal available feature
- scikit-learn / joblib model-compatibility warnings in steady-state production

Model compatibility policy:

- canonical remediation is model re-export against the target runtime dependency baseline
- temporary runtime version pinning is containment only, not the approved long-term release policy
