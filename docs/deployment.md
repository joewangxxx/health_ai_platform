# Health AI Platform Deployment Notes

## Ownership

- Owner: `general`
- Status: `validated`

## Purpose

Capture operator-facing rollout notes for the approved structured human-takeover slice. The backend now emits a bounded `takeover` object for high-risk and insufficient-evidence assistant turns, and the deployment notes below document how to roll it out safely.

## Current Deployment Slice

- Scope: add backend-owned `takeover.v1` metadata to assistant turns across `/chat/send`, `/chat/stream` final payloads, and historical replay.
- Public API impact: additive only. No new route or SSE event type is introduced.
- Frontend impact: Dr. AI consumes the existing backend-owned takeover metadata and does not redefine the medical semantics.
- Required backend rollout item: apply [20260402_add_chat_message_takeover.py](E:\health_ai_platform_2.0\backend\alembic\versions\20260402_add_chat_message_takeover.py) before resuming backend traffic.

## Rollout Checklist

- Confirm backend health:
  - `GET /health`
- Apply the migration:
  - `alembic -c backend/alembic.ini upgrade head`
- Re-run the focused verification:
  - `python -m py_compile backend/models.py backend/api/api_v1/endpoints/chat.py backend/services/chat_service.py backend/services/conversation_service.py backend/alembic/versions/20260402_add_chat_message_takeover.py tests/test_chat_agent_service.py tests/test_chat_agent_api.py tests/test_chat_endpoint_contract.py`
  - `python -m pytest tests/test_chat_agent_service.py tests/test_chat_agent_api.py tests/test_chat_endpoint_contract.py -q`
  - expected result: `69 passed`
- Verify the frontend bundle:
  - `cmd /c npm run build` in `frontend`

## Governance Version Tracking

- Takeover schema for new rows: `takeover.v1`
- Answer-level verdict baseline remains: `response_verdict.v1`
- Approval and rollout state remain orchestrator-owned in [state.yaml](E:\health_ai_platform_2.0\docs\blackboard\state.yaml); implementation and deployment must not invent new takeover status or trigger strings during rollout.

## Privacy Boundary Reminder

- The takeover object is backend-owned assistant metadata.
- It must only contain the frozen `schema_version`, `status`, `trigger_reason`, and `summary` fields.
- It must not persist raw query text, assistant reply text, prompt text, large RAG text, raw tool results, or unsanitized medical payloads.
- Deployment validation should treat any extra takeover field, any rewritten medical semantic, or any public-route drift as a release blocker for this slice.

## Known Deployment Caveats

- Historical assistant rows remain valid if they have no `takeover` object; no backfill is required before release review.
- QA evidence for this slice is backend/runtime focused and uses mocked provider behavior rather than a live external model-provider run.
- The workspace does not contain the FE-reported Playwright takeover smoke spec, so browser-level coverage in this pass is limited to build plus source inspection.
- If future backend producers begin writing takeover metadata outside the reviewed chat paths, they must preserve the same bounded field set and frozen semantics or route back through architect/orchestrator review.

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
