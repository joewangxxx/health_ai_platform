# Health AI Platform Release Notes

## Ownership

- Owner: `general`
- Status: `prepared_for_review`

## Purpose

Summarize the approved release slice, what changed, what did not change, and what residual risk remains for operator review.

## Current Candidate Release Scope

- Slice: structured human takeover for high-risk and insufficient-evidence assistant turns
- Scope type: backend-owned assistant metadata and frontend presentation hardening
- Public surface impact: additive only
- QA state: passed

## What Changed In This Slice

- Assistant turns may now carry a backend-owned `takeover` object with frozen `schema_version`, `status`, `trigger_reason`, and `summary` fields.
- The takeover object uses `schema_version="takeover.v1"` and is emitted consistently across `/chat/send`, `/chat/stream` final payloads, and conversation replay.
- `required` takeover means the backend crossed the human-handoff boundary; `suppressed` means the backend evaluated the boundary and chose not to surface it.
- Dr. AI now renders the takeover object as a separate guidance surface without redefining `evidence_panel` or `response_verdict`.
- Deployment now requires the migration [20260402_add_chat_message_takeover.py](E:\health_ai_platform_2.0\backend\alembic\versions\20260402_add_chat_message_takeover.py) before backend traffic resumes.

## What Did Not Change

- No new public route or SSE event type was introduced.
- The takeover surface does not replace `response_verdict`, `evidence_panel`, or `suggestion_card`.
- The takeover object does not authorize transcript retention, prompt retention, raw tool-result retention, or raw medical-payload retention.

## Governance Version Tracking

- Takeover schema for new rows: `takeover.v1`
- Answer-level verdict baseline remains: `response_verdict.v1`
- Normative semantics stay frozen in [architecture.md](E:\health_ai_platform_2.0\docs\architecture.md), [api-contract.md](E:\health_ai_platform_2.0\docs\api-contract.md), and [data-model-contract.md](E:\health_ai_platform_2.0\docs\data-model-contract.md)
- Rollout state remains orchestrator-owned in [state.yaml](E:\health_ai_platform_2.0\docs\blackboard\state.yaml)

## Verification Evidence

- Fresh compile safety passed:
  - `python -m py_compile backend/models.py backend/api/api_v1/endpoints/chat.py backend/services/chat_service.py backend/services/conversation_service.py backend/alembic/versions/20260402_add_chat_message_takeover.py tests/test_chat_agent_service.py tests/test_chat_agent_api.py tests/test_chat_endpoint_contract.py`
- Focused QA regression passed:
  - `python -m pytest tests/test_chat_agent_service.py tests/test_chat_agent_api.py tests/test_chat_endpoint_contract.py -q`
  - result: `69 passed`
- QA also confirmed:
  - urgent turns still short-circuit into a required takeover with `trigger_reason="high_risk"`
  - medication refusal turns stay in the suppressed boundary instead of becoming a required takeover
  - replay returns the stored takeover object for assistant rows and `null` for user rows and legacy assistant rows
  - Dr. AI only projects backend-owned takeover semantics

## Migration And Deployment Note

- Apply `alembic -c backend/alembic.ini upgrade head` during rollout.
- The migration adds the new bounded takeover column without introducing a new route or SSE event.
- Historical assistant rows remain valid if they have no `takeover` object; no backfill is required before release review.

## Residual Risks

- QA evidence for this slice is backend/runtime focused and uses mocked provider behavior rather than a live external model-provider run.
- The workspace does not contain the FE-reported Playwright takeover smoke spec, so browser-level coverage in this pass is limited to build plus source inspection.
- Mixed historical assistant rows will remain without `takeover` until older sessions age out or a later replay repair slice is approved.

## Operator Notes

- Use [deployment.md](E:\health_ai_platform_2.0\docs\deployment.md) as the rollout checklist for the migration and privacy boundary checks.
- Use [qa-report.md](E:\health_ai_platform_2.0\docs\qa-report.md) as the authoritative QA evidence source for this slice.
- Use [handoff.md](E:\health_ai_platform_2.0\docs\handoff.md) for the orchestrator handoff summary and next-owner request.

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
