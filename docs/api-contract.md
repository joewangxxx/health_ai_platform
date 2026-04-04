# Health AI Platform API Contract

## Ownership

- Owner: `architect`
- Status: `approved`
- Scope baseline: approved P0 core loop from [PRD.md](E:\health_ai_platform_2.0\docs\PRD.md)
- Review basis: full tracked-code scan completed on 2026-03-24

## Purpose

Freeze the minimal HTTP contract used by the approved P0 product loop so `fe` and `be` can implement and refine behavior without inventing incompatible request/response semantics.

## 1. Contract Scope

### 1.1 In Scope

- Auth
- Current-user bootstrap
- User profile read/write
- OCR upload
- User document list/delete
- Comprehensive risk analysis
- Dr. AI chat
- Health history list and trends
- Internal provider-native read-only tool contracts used by the Dr. AI runtime

### 1.2 Out Of Scope For This Freeze

- Admin research and ETL management
- Family-account switching contract freeze
- Nutrition plan public contract freeze
- IoT mutation contract freeze
- PDF export contract freeze

## 2. Cross-Cutting Rules

### 2.1 Base URL And Auth

- Base backend host is currently the FastAPI app served from `http://127.0.0.1:8000`
- Auth scheme: `Authorization: Bearer <token>`
- Token issue endpoint: `/auth/token`

### 2.2 Response Envelope Conventions

This repository mixes two response styles:

- Pure model response, for example auth token response
- Object envelope with `status`, `message`, and `data`-like fields

This contract does not rewrite all responses into a new envelope. It freezes the current route-level behavior and marks normalization as future work.

### 2.3 Error Semantics

- `400`: invalid input, missing required state, unsupported file type, empty message
- `401`: unauthenticated or invalid bearer token
- `403`: authenticated but not authorized
- `404`: resource not found
- `500`: unexpected processing failure where the backend cannot return one of the frozen business states below

Degraded-path rule:

- once a durable business outcome is known, the backend must return that business outcome instead of collapsing it into a generic `500`
- specifically, "document saved but OCR unavailable or deferred" is not a generic `500`; it is the frozen OCR business state `stored_unprocessed`

### 2.4 Serialization Rules

- JSON request/response payloads use current field names from the repository
- OCR upload uses multipart file upload
- Auth login uses `application/x-www-form-urlencoded`

### 2.5 Internal Tool Contract Boundary

The read-only tools in this document are backend-internal contracts for the provider-native function-calling path used by Dr. AI.

Rules:

- These tools do not create or change public HTTP routes.
- These tools are exposed to provider-native function calling through the backend tool registry and `get_tool_definitions()` path only.
- `POST /chat/send` and `POST /chat/stream` remain the only user-facing chat-entry HTTP routes in this slice.
- Each tool is self-only and read-only. No tool may read another user's data, mutate storage, enqueue jobs, or trigger autonomous medical action.
- Tool outputs are backend-internal evidence payloads. The backend may use them to generate assistant text, `decision_summary.tool_used`, `evidence_tags`, or future evidence metadata, but FE must not call these tools directly.

### 2.6 Persisted JSON Compatibility Exposure

This repository currently has two kinds of read surfaces for shape-variable persisted JSON fields:

- Compatibility passthrough surfaces:
  - `GET /user/profile` may expose `profile.risk_history`
  - `GET /api/v1/user/documents` may expose `documents[].ocr_summary`
- Bounded normalized tool surfaces:
  - `medication_summary_lookup`
  - `recent_metric_anomaly_lookup`
  - `report_comparison_lookup`

Rules:

- Passthrough surfaces may contain legacy payloads or canonical envelopes during migration. Clients must treat them as opaque compatibility fields and must not assume missing subfields can be inferred.
- Bounded tool surfaces must normalize legacy payloads into the architect-frozen output shapes below.
- `UserProfile.risk_history` remains a single latest-snapshot compatibility field despite its legacy name; it is not an array contract in this freeze.
- FE and BE may not silently upgrade a passthrough field into a new implicit frontend schema without an architect-owned contract update.

### 2.7 Internal Audit Responsibility Boundary

Audit persistence is an internal backend concern and is not exposed as a public chat API. In this slice it is frozen as a responsibility record, not as a raw transcript or generic call trace.

Rules:

- No audit-read or audit-write public route is introduced by this slice.
- `POST /chat/send` and `POST /chat/stream` keep their existing response contracts; they do not expose audit payloads, audit ids, audit lookup handles, or audit-derived snippets.
- Audit metadata must not be copied into assistant `reply`, `sources`, `evidence_panel`, `suggestion_card`, SSE status events, or any other chat response field.
- The logger-based runtime audit trail remains in place for operational tracing even after durable audit rows are added.
- Persisted audit rows are append-only internal responsibility records for finalized assistant outcomes only. User turns, prompt drafts, intermediate planner states, tool-start/tool-done events, and partial SSE status stages are out of scope for audit persistence in this slice.
- FE, public API callers, and provider-native tools must not be given a path to read or widen audit records directly.
- Any future request to expose audit search, export, or filtering through chat routes is contract pressure and must return through `architect` before implementation.

Frozen internal responsibility payload for new rows:

```json
{
  "schema_version": "agent_audit_responsibility.v2",
  "governance_version": "agent_runtime_governance.v1",
  "timestamp": "2026-04-01T12:00:00Z",
  "user_id": 1,
  "conversation_id": 12,
  "intent": "guideline_lookup",
  "lane": "general_health",
  "verdict": "general_guidance",
  "selected_rule": "general_health",
  "policy_version": "explicit_policy.v1",
  "response_mode": "bounded_answer",
  "evidence_sufficiency": "limited",
  "degraded_reason": "insufficient_evidence",
  "human_escalation_required": false,
  "model_name": "moonshot-v1-8k",
  "tool_plan_source": "native_function_calling",
  "tool_used": ["search_medical_guidelines"],
  "tool_count": 1,
  "cache_hit": false,
  "fallback_used": false,
  "safety_level": "normal",
  "evidence_tags": ["guideline_search"],
  "context_budget_summary": {
    "profile": {"budget": 500, "used": 120},
    "rag": {"budget": 1500, "used": 420},
    "tools": {"budget": 800, "used": 90},
    "query": {"budget": 300, "used": 18},
    "history": {"budget": 320}
  },
  "rag_quality_summary": {
    "retrieval_status": "ok",
    "hit_count": 3,
    "unique_source_count": 2,
    "source_kind": "mixed",
    "density_status": "low_density",
    "ocr_fallback_state": "available",
    "provenance_state": "partial",
    "chunk_quality": "mixed"
  },
  "tool_latency_ms": 17,
  "response_latency_ms": 93
}
```

Internal contract semantics:

- `schema_version` is required for every new row and must be `agent_audit_responsibility.v2`. Historical `audit_event.v1` rows remain a read-compatibility concern only.
- `governance_version` is the architect-owned runtime-governance baseline. The frozen value in this docs set is `agent_runtime_governance.v1`.
- `policy_version` must mirror `decision_summary.policy.policy_version`.
- `lane`, `verdict`, `selected_rule`, `response_mode`, `evidence_sufficiency`, `degraded_reason`, and `human_escalation_required` are the responsibility fields that explain why the runtime answered, degraded, or escalated the way it did.
- `intent` remains a backward-compatible trace field only; it is no longer sufficient by itself to describe the audit responsibility of the turn.
- `model_name` is a bounded sanitized model identifier and may be `null` when no new model call contributed to the emitted reply, such as urgent short-circuit or cache replay.
- `tool_plan_source` is required and must be one of `native_function_calling`, `local_fallback_planner`, `no_tool_path`, `cache_replay`, or `urgent_short_circuit`.
- `cache_hit` is required and records whether the emitted reply body came from cache for the current turn.
- `fallback_used` is required and records whether the runtime fell back from native tool calling to the local planner for the current turn.
- `degraded_reason` must be `null` or one of `insufficient_evidence`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `policy_guardrail`, `urgent_risk_detected`, `unsafe_medication_request`, `diagnosis_sensitive_request`, or `urgent_symptom`.
- `evidence_sufficiency` must be one of `sufficient`, `limited`, or `insufficient`.
- `response_mode` must be one of `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, or `urgent_care_disclaimer`.
- `context_budget_summary` may contain only the bounded keys `profile`, `rag`, `tools`, `query`, and `history`, with integer `budget` and optional integer `used`.
- `rag_quality_summary` may contain only the bounded query-time quality fields frozen in section 2.8.1. It is optional on urgent short-circuit or retrieval-bypass paths.

Privacy and exposure constraints:

- Audit rows must not store raw query text, raw assistant reply text, raw prompt text, raw tool arguments, raw tool results, large RAG text, or unsanitized medical payloads.
- Audit rows must not store raw OCR summaries, raw risk snapshots, raw report comparisons, raw profile dumps, or any other large structured medical object.
- `tool_used`, `evidence_tags`, and `context_budget_summary` are bounded metadata only and must not be used to smuggle prompt fragments, retrieved passages, or medical payload slices.
- `rag_quality_summary` is bounded metadata only and must not be used to smuggle similarity scores, raw passages, OCR text, benchmark traces, or loader exception payloads.
- Runtime-governance version tracking is split across internal layers:
- architect-owned docs freeze the normative `governance_version`
- `docs/blackboard/state.yaml` records approval and rollout evidence, and only `orchestrator` may write it
- persisted rows may echo `governance_version`, but BE may not invent or auto-bump it independently of the docs

### 2.7.1 Internal Assistant Answer Replay Boundary

The replay slice in this pass is an internal-only bounded reconstruction package for one assistant answer turn. It is not a transcript export, prompt archive, or public conversation-detail expansion.

Rules:

- No new public route is introduced.
- `POST /chat/send`, `POST /chat/stream`, and `GET /chat/conversations/{conversation_id}/messages` keep their existing public payloads and must not expose replay-package fields.
- Replay data must not be appended onto `ChatMessage` public-history payloads as additive fields such as `context_budget_summary`, `tool_result_summary`, `rag_source_refs`, `tool_plan_source`, `fallback_used`, or `model_name`.
- Freeze a new backend-internal one-to-one replay structure/table for assistant turns only: `AgentAnswerReplay`.
- One replay row corresponds to one finalized assistant `ChatMessage` and one `AgentAuditEvent`.
- No internal/admin HTTP replay route is required in this freeze. Any future read route for replay must be separate from `/chat/*`, internal-only or superuser-only, read-only, and limited to the bounded payload below.

Frozen internal replay payload:

```json
{
  "schema_version": "agent_answer_replay.v1",
  "user_id": 1,
  "conversation_id": 12,
  "chat_message_id": 88,
  "audit_event_id": 144,
  "policy_snapshot": {
    "lane": "general_health",
    "verdict": "general_guidance",
    "selected_rule": "general_health",
    "policy_version": "explicit_policy.v1",
    "response_mode": "bounded_answer",
    "evidence_sufficiency": "limited",
    "medical_risk_level": "medium",
    "human_escalation_required": false,
    "degraded_reason": "insufficient_evidence"
  },
  "execution_snapshot": {
    "governance_version": "agent_runtime_governance.v1",
    "model_name": "moonshot-v1-8k",
    "tool_plan_source": "native_function_calling",
    "cache_hit": false,
    "fallback_used": false,
    "tool_count": 1,
    "tool_latency_ms": 17,
    "response_latency_ms": 93
  },
  "context_budget_summary": {
    "profile": {"budget": 500, "used": 120},
    "rag": {"budget": 1500, "used": 420},
    "tools": {"budget": 800, "used": 90},
    "query": {"budget": 300, "used": 18},
    "history": {"budget": 320}
  },
  "rag_quality_summary": {
    "retrieval_status": "ok",
    "hit_count": 3,
    "unique_source_count": 2,
    "source_kind": "mixed",
    "density_status": "low_density",
    "ocr_fallback_state": "available",
    "provenance_state": "partial",
    "chunk_quality": "mixed"
  },
  "tool_result_summary": [
    {
      "tool_name": "search_medical_guidelines",
      "status": "ok",
      "summary_label": "Guideline evidence retrieved",
      "count": 1,
      "freshness": "recent",
      "coverage": "partial",
      "confidence": "medium",
      "blocked_reason": null,
      "source_refs": ["guideline.pdf"]
    }
  ],
  "rag_source_refs": [
    {
      "source": "guideline.pdf",
      "page": 12,
      "chunk_index": 3,
      "page_range": [12, 12]
    }
  ],
  "created_at": "2026-04-01T12:00:00Z"
}
```

Exposure and privacy constraints:

- Replay rows must not store or return raw query text, raw assistant reply text, prompt text, planning messages, or any other full-context transcript material.
- Replay rows must not store or return large RAG text, retrieved-passage text, raw tool results, raw tool arguments, raw OCR payloads, raw risk payloads, or unsanitized medical payloads.
- `rag_quality_summary` is bounded metadata only and must not be used to smuggle similarity scores, raw passages, OCR text, benchmark traces, or loader exception payloads.
- `tool_result_summary` is bounded metadata only. Allowed fields are stable tool name, compact status, bounded counts, bounded quality metadata (`freshness`, `coverage`, `confidence`), bounded block/failure reason, and stable `source_refs`.
- `rag_source_refs` is provenance-only. Allowed fields are stable source label plus optional page/chunk/page-range coordinates. No passage text, snippet text, or chunk body is allowed.
- Replay rows must reference the existing assistant message by `chat_message_id`; they must not duplicate `ChatMessage.content`.
- FE remains out of scope. No public or frontend-owned contract is created for replay in this slice.

### 2.8 Internal RAG Build Boundary

The knowledge-base build and rebuild flow for RAG is backend-internal and does not create a new public API surface.

Rules:

- `build_knowledge_base` or any equivalent KB refresh entrypoint remains an internal maintenance operation.
- `POST /chat/send` and `POST /chat/stream` keep their current request and response contracts.
- Query-time retrieval remains behind backend services and the existing internal `rag_service.search_context` path; no new public retrieval endpoint is introduced by this slice.
- Chunking parameters, chunk metadata, and vector-store refresh behavior are implementation details unless architect explicitly freezes a future public citation or KB-management contract.
- Any future request to expose page-level citations, KB rebuild controls, or retrieval filters to frontend or external callers is contract pressure and must return through `architect`.

### 2.8.1 Query-Time RAG Quality And Degrade Mapping

Query-time retrieval may produce a backend-only `rag_quality_summary` object. It is internal runtime metadata for chat-time gating and replay accountability, not a public route field.

Canonical internal shape:

```json
{
  "retrieval_status": "ok",
  "hit_count": 3,
  "unique_source_count": 2,
  "source_kind": "mixed",
  "density_status": "low_density",
  "ocr_fallback_state": "available",
  "provenance_state": "partial",
  "chunk_quality": "mixed"
}
```

Rules:

- `POST /chat/send`, `POST /chat/stream`, and `GET /chat/conversations/{conversation_id}/messages` must not expose `rag_quality_summary`.
- `rag_quality_summary` must not appear in `reply`, `sources`, `evidence_tags`, `evidence_panel`, `suggestion_card`, SSE status events, or any other public chat response field.
- `rag_quality_summary` may be used to derive or tighten `decision_summary.policy.evidence_state`, `decision_summary.policy.degrade_reason`, and `decision_summary.policy.disclaimer_mode`, but it must not change `lane` or `verdict`.
- `retrieval_status="ok"` means the retriever returned at least one attributable chunk, `empty` means no attributable chunks were found, and `unavailable` means retrieval could not be trusted because a vector-store, loader, or OCR dependency was unavailable.
- `source_kind` is inferred from existing chunk metadata and `ocr_touched`; it may be `pdf_text`, `ocr_text`, `mixed`, or `unknown` and must not introduce a new corpus taxonomy.
- `density_status="low_density"` or `provenance_state="partial"` may support only conservative or limited behavior. They must not by themselves justify a confident answer.
- `chunk_quality="weak"` or `chunk_quality="empty"` should drive the runtime toward `insufficient` evidence or the appropriate missing-context/tool-unavailable degrade reason, depending on the root cause.
- The full benchmark report remains build-time only. If the runtime needs to retain any signal, it may retain only the bounded summary above, not the raw benchmark diagnostics.
- This freeze does not add a new public retrieval endpoint, and it does not require FE to consume any new field.

### 2.9 Frozen Chat Lane Metadata

This contract freeze keeps `POST /chat/send` and `POST /chat/stream` unchanged at the route level and carries the routing result through the existing `decision_summary` object.

Rules:

- `decision_summary.intent` remains a backward-compatible backend trace field. It is not the frontend routing contract.
- `decision_summary.lane` is the frozen backend-owned routing lane that FE may consume.
- `decision_summary.verdict` is the frozen backend-owned result code that FE may consume.
- FE must not infer lane or verdict from `intent`, `reply`, `evidence_tags`, tool names, or user-entered text when `lane` / `verdict` metadata is present.
- BE may add internal heuristics, but it may not emit lane names or verdict codes outside the frozen sets below without an architect-owned contract update.
- No new chat request field, query parameter, or route is required for this freeze.

Frozen lane enum:

- `general_health`
- `report_interpretation`
- `trend_review`
- `medication_related`
- `urgent_symptom`
- `diagnosis_sensitive`

Frozen verdict enum:

- `general_guidance`
- `report_context_only`
- `trend_context_only`
- `medication_context_only`
- `seek_urgent_care`
- `needs_clinical_diagnosis`
- `insufficient_evidence`

Allowed lane / verdict combinations:

- `general_health` -> `general_guidance` or `insufficient_evidence`
- `report_interpretation` -> `report_context_only` or `insufficient_evidence`
- `trend_review` -> `trend_context_only` or `insufficient_evidence`
- `medication_related` -> `medication_context_only` or `insufficient_evidence`
- `urgent_symptom` -> `seek_urgent_care`
- `diagnosis_sensitive` -> `needs_clinical_diagnosis` or `insufficient_evidence`

### 2.10 Explicit Policy Envelope

The backend also freezes a nested policy object inside `decision_summary`:

```json
{
  "policy_version": "explicit_policy.v1",
  "evaluation_order": [
    "urgent_symptom",
    "diagnosis_sensitive",
    "medication_related",
    "trend_review",
    "report_interpretation",
    "general_health"
  ],
  "selected_rule": "general_health",
  "risk_level": "low",
  "evidence_state": "limited",
  "tool_availability": "partial",
  "answer_mode": "bounded_answer",
  "disclaimer_mode": "conservative",
  "degrade_reason": "evidence_insufficient"
}
```

Contract semantics:

- `decision_summary.policy` is additive backend-owned runtime metadata nested under the existing `decision_summary` object.
- `policy_version` is compatibility-gated by major version. Same-major additive changes are compatible if they preserve the frozen lane/verdict meanings and keep the answer-mode set stable.
- Rule evaluation is first-match-wins and follows the frozen priority order listed above.
- `selected_rule` is the question-type/routing rule id for this slice, so no separate `question_type` field is required.
- `risk_level` is the backend risk assessment for the selected rule. It is typically `low`, `medium`, or `high`.
- `evidence_state` uses the exact enum `sufficient`, `limited`, or `insufficient`.
- `missing` is deprecated and reserved only as a legacy replay synonym for `insufficient`; BE must not emit `missing` on new assistant turns.
- `tool_availability` is the backend summary of whether the selected rule has full, partial, or no usable tools available.
- `degrade_reason` is `null` or one of `evidence_insufficient`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `unsafe_medication_request`, `diagnosis_sensitive_request`, or `urgent_symptom`.
- The allowed answer-mode categories are `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, and `urgent_care_disclaimer`.
- The allowed disclaimer-mode categories are `none`, `conservative`, `diagnosis_guardrail`, and `urgent_care`.
- Degrade order when evidence or tool availability is insufficient is `direct_answer` -> `bounded_answer` -> `clarify_missing_context` -> `refusal_with_disclaimer`, while `urgent_care_disclaimer` short-circuits for urgent routing.
- `disclaimer_mode="conservative"` is used when the request is safe to answer but evidence is limited or tool availability is partial; the reply must stay bounded, surface uncertainty, and avoid implied certainty.
- Refusal and disclaimer triggers remain backend-owned. Typical triggers are urgent symptoms, diagnosis requests, medication start/stop/titration/substitution requests, evidence conflicts, missing evidence with a safety-sensitive request, and other unsafe asks that exceed the frozen lane guardrails.
- FE may continue to consume only `decision_summary.lane` and `decision_summary.verdict` as the routing contract. It must not derive routing semantics from `policy`, `intent`, `reply`, or tool names.
- Historical rows may omit `decision_summary.policy`; lane/verdict remain the backward-compatible contract for replay.

### 2.10.1 Frozen Evidence Sufficiency Gate

The evidence sufficiency gate is part of the frozen backend policy contract and must run before the final assistant reply is emitted.

Tool applicability is evaluated first, and sufficiency is evaluated second.

- pre-execution applicability checks run before any tool call is executed
- post-execution sufficiency checks run after tool outputs are available and before the final assistant reply is emitted
- both checks are backend-owned hard checks; they are not prompt hints, model suggestions, or frontend policy decorations
- no new public route, request field, response field, tool name, parameter, or result shape is required for this slice

Rule inputs that participate in the gate:

- profile evidence from persisted profile, latest risk snapshot, or anomaly-derived health context
- report evidence from persisted report summaries, report comparisons, or uploaded-document projections
- trend/history evidence from persisted historical records and bounded trend projections
- knowledge-base / RAG evidence from attributable retrieval results
- tool evidence from successful read-only tool outputs, plus blocked or empty tool outcomes

Source rules:

- profile evidence is usable only when at least one query-relevant user-owned fact is available
- report evidence is usable only when persisted report-summary or comparison facts are available; file existence alone is not sufficient
- trend evidence is sufficient only when at least two comparable historical points exist for the requested trend claim; one point may support only `limited`
- knowledge-base / RAG evidence may contextualize a reply but cannot by itself make `report_interpretation`, `trend_review`, `medication_related`, or `diagnosis_sensitive` sufficient
- tool evidence is usable only when a tool returns `status="ok"` and bounded factual content; blocked, empty, or non-owned results count as unavailable

Decision priority:

1. `urgent_symptom` short-circuits first and does not wait on profile, RAG, or tool evidence.
2. Any unresolved contradiction across relevant evidence forces `decision_summary.policy.evidence_state="insufficient"` and `decision_summary.policy.degrade_reason="conflicting_evidence"`.
3. If the lane-specific minimum evidence floor is not met, `evidence_state="insufficient"`.
4. If some lane-relevant evidence exists but the minimum floor is only partially met, `evidence_state="limited"`.
5. Only when the lane-specific floor is met and no material contradiction remains unresolved may `evidence_state="sufficient"`.

Lane-specific minimum evidence floors:

- `general_health`: at least one usable personalized source or attributable guideline support for bounded general guidance; guideline-only support for a personalized question is at most `limited`
- `report_interpretation`: usable report-summary or report-comparison evidence
- `trend_review`: at least two comparable historical records
- `medication_related`: at least one persisted medication fact from report or profile-backed medication evidence
- `diagnosis_sensitive`: enough bounded context to summarize available facts while still refusing diagnosis-like certainty; this never authorizes a diagnosis claim
- `urgent_symptom`: fixed to the safety short-circuit path and therefore exposed as `insufficient` on the answer-level verdict path

Hard-gate behavior:

- When `evidence_state="insufficient"`, `decision_summary.policy.answer_mode` must not be `direct_answer`.
- The backend must keep the selected lane fixed; it must not silently switch lanes because evidence is thin or conflicting.
- Non-urgent lanes may emit only their lane-specific success verdict or `insufficient_evidence`; `urgent_symptom` always keeps `seek_urgent_care`.
- Reply text must refuse over-inference, explicitly state uncertainty, identify the missing or conflicting evidence class, and give at least one concrete next step such as uploading a report, providing exact metric values and dates, adding another comparable record, supplying medication name/dose, or seeking clinician follow-up.
- `urgent_symptom` and `diagnosis_sensitive` still require their mandatory offline care reminder on every response. Other lanes may add clinician-review guidance when evidence is conflicting or too weak.
- if a tool result is empty, weak, or mismatched to the selected lane, the backend must treat it as unavailable or insufficient evidence rather than as support for a stronger answer mode
- if a blocked tool was the only candidate evidence, the backend must still emit the frozen degrade signals and stop at the bounded answer or clarification boundary rather than continuing with unsupported medical explanation

### 2.11 Response Verdict Envelope

The backend also freezes one additive top-level assistant-reply verdict object:

```json
{
  "schema_version": "response_verdict.v1",
  "response_mode": "bounded_answer",
  "medical_risk_level": "medium",
  "evidence_sufficiency": "limited",
  "human_escalation_required": false,
  "degraded_reason": "insufficient_evidence"
}
```

Contract semantics:

- The container name is exactly `response_verdict`.
- Naming is intentional: `response_verdict` avoids collision with the already-frozen `decision_summary.verdict`, which remains the six-lane routing-matrix result code.
- `response_verdict` is additive top-level assistant metadata. It must not be moved under `decision_summary`, and BE/FE may not introduce aliases such as `answer_verdict`, `final_verdict`, or another top-level `verdict`.
- Required fields for every new assistant reply are:
  - `schema_version`: must be `response_verdict.v1`
  - `response_mode`: one of `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, or `urgent_care_disclaimer`
  - `medical_risk_level`: one of `low`, `medium`, or `high`
  - `evidence_sufficiency`: one of `sufficient`, `limited`, or `insufficient`
  - `human_escalation_required`: boolean
  - `degraded_reason`: `null` or one of `insufficient_evidence`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `policy_guardrail`, or `urgent_risk_detected`
- Coexistence rules:
  - `decision_summary.verdict` remains the routing-matrix verdict and must not be reinterpreted as the answer-level verdict object.
  - `decision_summary.policy` remains the explicit policy-engine trace envelope and may carry richer internal evaluation detail than `response_verdict`.
  - `response_verdict` is the public answer-level summary for the emitted assistant reply.
- Consistency rules:
  - `POST /chat/send`, `POST /chat/stream` final payloads, and `GET /chat/conversations/{conversation_id}/messages` assistant rows must use the same top-level `response_verdict` shape.
  - For one assistant turn, replay should surface the same stored `response_verdict` object rather than recomputing it from newer runtime heuristics.
  - When `decision_summary.policy` is present, backend implementation should keep `response_verdict.response_mode` aligned with `decision_summary.policy.answer_mode`, keep `medical_risk_level` aligned with policy risk, and derive `evidence_sufficiency` from policy evidence state without inventing a second policy model.
  - The mapping is exact: `decision_summary.policy.evidence_state=sufficient|limited|insufficient` maps to the same `response_verdict.evidence_sufficiency` value. New turns must never emit `missing`.
- Compatibility rules:
  - legacy stored assistant rows may lack `response_verdict`; historical replay must remain valid in that case
  - backend replay must not synthesize `response_verdict` for legacy rows by guessing from `decision_summary.verdict`, `decision_summary.policy`, reply text, or tool names
  - when a replayed assistant row predates this slice, `response_verdict` should be `null`
  - user turns in history replay should also return `response_verdict=null`
- `human_escalation_required=true` means the assistant answer explicitly requires offline human follow-up as part of the safe answer boundary. It is mandatory for `urgent_symptom` and `diagnosis_sensitive`, and may also be true for medication-guardrail refusals.
- `degraded_reason` is the stable public reason for answer degradation. If multiple causes apply, expose one dominant reason using this priority: `urgent_risk_detected` -> `policy_guardrail` -> `conflicting_evidence` -> `tool_unavailable` -> `missing_required_context` -> `insufficient_evidence`.
- Non-goals:
  - no new chat request field or query parameter
  - no new SSE event type; this slice only changes the `final` payload shape
  - no FE-owned derivation of answer-level verdict metadata
  - no mandatory backfill before historical replay remains valid

### 2.12 Human Takeover Envelope

The backend also freezes one additive assistant-reply human-handoff object:

```json
{
  "schema_version": "takeover.v1",
  "status": "required",
  "trigger_reason": "high_risk",
  "summary": "Backend-owned handoff summary explaining why human review is required."
}
```

Contract semantics:

- The container name is exactly `takeover`.
- `takeover` is additive assistant metadata. It must not be moved under `decision_summary`, and BE/FE may not introduce aliases such as `human_takeover`, `handoff`, or another top-level escalation object.
- Required fields for every emitted takeover object are:
  - `schema_version`: must be `takeover.v1`
  - `status`: one of `required` or `suppressed`
  - `trigger_reason`: one of `high_risk`, `insufficient_evidence`, `boundary_false_positive`, or `boundary_not_triggered`
  - `summary`: short backend-authored handoff text
- `status="required"` means the backend crossed the human-handoff boundary and FE may render the takeover surface.
- `status="suppressed"` means the backend explicitly evaluated takeover and chose not to surface it. FE must not synthesize a hidden handoff state from other metadata.
- `trigger_reason="high_risk"` corresponds to a high-risk or urgent boundary. It should align with the urgent safety path. `response_verdict.human_escalation_required=true` is broader than takeover and does not by itself require takeover.
- `trigger_reason="insufficient_evidence"` corresponds to an evidence boundary. It should align with an insufficient-evidence answer path and with `response_verdict.evidence_sufficiency="insufficient"`.
- `trigger_reason="boundary_false_positive"` means the backend detected a near-hit but vetoed it as a false positive.
- `trigger_reason="boundary_not_triggered"` means the backend evaluated the turn and concluded that no takeover boundary was crossed.
- `summary` is backend-owned presentation text only. It must stay neutral, bounded, and non-diagnostic. FE may display it, but it may not infer new medical state from it.
- `evidence_panel` may support the takeover decision with evidence provenance, but it does not own takeover semantics.
- `suggestion_card` remains an ordinary guidance card. It must not be repurposed into a takeover workflow, ticket, or disclaimer substitute.
- `POST /chat/send`, `POST /chat/stream` final payloads, and `GET /chat/conversations/{conversation_id}/messages` assistant rows must use the same takeover shape when it is present.
- For one assistant turn, replay must surface the same stored `takeover` object rather than recomputing it from newer runtime heuristics.
- Legacy stored assistant rows may lack `takeover`; historical replay must remain valid in that case.
- User turns in history replay should also return `takeover=null`.
- `takeover.status="suppressed"` must not be used by FE to infer a hidden clinical state; FE may only render the backend-authored summary when the backend chooses to emit the object.

Non-goals:

- no new chat request field or query parameter
- no new SSE event type; this slice only changes the final payload shape and the stored assistant metadata
- no FE-owned derivation of takeover state or medical escalation meaning
- no mandatory backfill before historical replay remains valid

## 3. Endpoint Inventory

### 3.1 Auth

#### `POST /auth/register`

Purpose: create a new user and initial empty profile

Request body:

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "secret123"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Rules:

- Username must be unique
- Email, if provided, must be unique
- Password length must satisfy current backend validation

#### `POST /auth/token`

Purpose: exchange username/password for bearer token

Form fields:

- `username`
- `password`

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

### 3.2 Current User Bootstrap

#### `GET /user/me`

Purpose: return authenticated user summary and embedded profile snapshot

Response shape:

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "profile": { "...profile fields..." },
  "is_superuser": false
}
```

#### `GET /user/profile`

Purpose: return full user profile payload

Response shape:

```json
{
  "status": "success",
  "profile": { "...profile fields..." }
}
```

If profile does not exist:

```json
{
  "status": "empty",
  "profile": null,
  "message": "..."
}
```

#### `POST /user/profile`

Purpose: upsert the user profile and create a history snapshot when relevant metrics exist

Request body:

- Free-form JSON keyed by existing profile field names
- May include:
  - `user_snps`
  - `risk_report`
  - clinical numeric fields such as `BMI`, `SBP`, `Glucose_Fasting`
  - `extra_data`

Response shape:

```json
{
  "status": "success",
  "message": "...",
  "profile": { "...updated profile..." }
}
```

Rules:

- Protected fields such as `id` and `user_id` are not client-writable
- Dict JSON fields are serialized by backend before SQLite persistence
- Successful update invalidates the user cache
- `risk_history`, when present in the response profile, is a compatibility field only; it may be legacy raw risk payload or canonical `risk_snapshot.v1`
- callers must not treat `risk_history` as a timeline array or infer missing disease findings, timestamps, or CKM state from absent fields
- later BE work in this slice may add additive backend-owned profile metadata such as `field_state_snapshot`; FE may render it when present but must not invent its own field-state taxonomy before that implementation lands

### 3.3 OCR And Document Management

#### `POST /api/v1/ocr/upload`

Purpose: upload a medical report, persist the file and document record, run OCR/parsing when available, and return the frozen OCR processing outcome

Request:

- Multipart form field: `file`
- Allowed content types:
  - `image/jpeg`
  - `image/png`
  - `image/jpg`
  - `application/pdf`

Canonical response shape:

```json
{
  "status": "success|partial_success|stored_unprocessed|error",
  "message": "...",
  "document_id": 123,
  "file_url": "/static/medical_reports/...",
  "raw_text": "...",
  "extraction_method": "llm|regex_fallback|regex_only|null",
  "data": { "...structured findings..." },
  "ocr_processing_status": {
    "schema_version": "ocr_processing_status.v1",
    "status": "success",
    "reason": null,
    "structured_data_present": true,
    "raw_text_present": true
  }
}
```

Frozen business-state semantics:

- `success`: document save succeeded and the backend produced canonical structured OCR output for normal downstream merge.
- `partial_success`: document save succeeded and OCR recovered some bounded extraction output, but the result is incomplete and must be treated as partial evidence rather than a fully populated report.
- `stored_unprocessed`: document save succeeded but OCR could not produce a usable parsed result because an OCR prerequisite was unavailable or deferred. This is the canonical state for missing Baidu OCR credentials, unready OCR clients, or equivalent approved OCR-unavailable runtime states.
- `error`: the backend could not determine a durable upload outcome or another unrecoverable failure prevented the route from reporting one of the three successful storage outcomes above.

HTTP rules:

- `400` for unsupported file type
- `200` for `success`, `partial_success`, and `stored_unprocessed`
- `500` only for true route failure where the backend cannot safely report a durable business state

Contract rules:

- `stored_unprocessed` must not be rewritten as a generic HTTP 500 after the document row is already durable.
- `partial_success` must preserve sparse extraction semantics; FE must not assume that every clinically important field was extracted.
- `ocr_processing_status` is additive and backend-owned. It does not replace `ocr_summary.v1`.

#### `GET /api/v1/user/documents`

Purpose: list uploaded medical documents for current user

Response shape:

```json
{
  "status": "success",
  "documents": [
    {
      "id": 123,
      "file_name": "report.pdf",
      "file_url": "/static/medical_reports/...",
      "upload_date": "2026-03-24 12:00",
      "ocr_summary": {},
      "has_data": true,
      "ocr_processing_status": {
        "schema_version": "ocr_processing_status.v1",
        "status": "partial_success",
        "reason": "structured_data_incomplete",
        "structured_data_present": true,
        "raw_text_present": true
      }
    }
  ],
  "total": 1
}
```

Rules:

- `ocr_summary` is a compatibility field only; it may be a legacy extraction payload or canonical `ocr_summary.v1`
- callers must not assume a narrative summary string, normalized metric container, or unit/reference metadata unless those fields are explicitly present
- `has_data` indicates only that some persisted summary payload was successfully parsed; it does not guarantee canonical shape completeness
- when present, `ocr_processing_status` is the backend-owned source of truth for whether the document is fully processed, partially processed, merely stored, or truly failed
- FE must not guess a document's OCR state from `ocr_summary == null` alone once `ocr_processing_status` exists

#### `DELETE /api/v1/user/documents/{doc_id}`

Purpose: delete one user-owned medical document

Response shape:

```json
{
  "status": "success",
  "message": "...",
  "file_deleted": true
}
```

### 3.4 Analysis And History

#### `POST /analyze/comprehensive`

Purpose: compute comprehensive risk using merged clinical/profile context and optional SNP data

Request body:

```json
{
  "clinical": {
    "Age": 45,
    "Gender": 1,
    "BMI": 24.5
  },
  "user_snps": {}
}
```

Response shape:

```json
{
  "status": "success",
  "risk_report": { "...engine output..." },
  "analysis_context": {
    "schema_version": "analysis_context.v1",
    "analysis_mode": "final|provisional|blocked",
    "provisional_reasons": [],
    "blocking_fields": [],
    "field_state_summary": {
      "recognized": ["Age"],
      "derived": ["BMI"],
      "missing": [],
      "user_confirmed": [],
      "user_entered": ["Weight"]
    }
  }
}
```

Frozen analysis-mode semantics:

- `final` means the backend's required input floor for the selected path is satisfied without prohibited estimates.
- `provisional` means the backend computed a bounded report, but at least one material field remains `derived` or some non-blocking fields remain `missing`.
- `blocked` means required non-derivable fields are still missing or the request otherwise fails the frozen input-quality gate for a report.

Contract rules:

- The existing `risk_report` shape remains backend-owned and is not replaced by `analysis_context`.
- FE may render `analysis_context`, but FE may not infer provisional/final meaning from local heuristics once backend-owned metadata is present.
- BE must not fabricate missing required values to avoid `blocked` or `provisional` states.
- Only the frozen derivation set approved in the architecture and data-model contracts may contribute `derived` field states.

#### `GET /history/list`

Purpose: list user health-record snapshots

Response shape:

```json
[
  {
    "id": 1,
    "date": "2026-03-24 10:00",
    "source": "manual_update",
    "summary": "..."
  }
]
```

#### `GET /history/trends`

Purpose: return series data for timeline/trend visualizations

Response shape:

```json
{
  "dates": ["2026-03-20", "2026-03-24"],
  "metrics": {
    "BMI": [24.0, 23.8],
    "Glucose_Fasting": [5.4, 5.2],
    "SBP": [130, 126],
    "HbA1c": [5.9, 5.8],
    "Cholesterol_Total": [5.3, 5.0]
  }
}
```

#### `POST /analysis/detect_anomalies`

Purpose: classify abnormalities from provided clinical data payload

Response shape:

```json
{
  "status": "success",
  "anomalies": [],
  "summary": {}
}
```

#### `GET /analysis/detect_anomalies/profile`

Purpose: classify abnormalities from stored profile state

Response shape follows the same structure as `/analysis/detect_anomalies`.

### 3.5 Chat

#### `POST /chat/send`

Purpose: send one Dr. AI query using user context and RAG retrieval

Request body:

```json
{
  "message": "我最近血糖偏高应该注意什么？",
  "conversation_id": 12,
  "force_refresh": false
}
```

Response shape:

```json
{
  "conversation_id": 12,
  "reply": "...",
  "sources": ["guide.pdf"],
  "evidence_tags": ["profile_summary", "guideline_search"],
  "decision_summary": {
    "intent": "guideline_lookup",
    "lane": "general_health",
    "verdict": "general_guidance",
    "tool_needed": true,
    "tool_used": ["get_user_profile_summary", "search_medical_guidelines"],
    "safety_level": "normal"
  },
  "response_verdict": {
    "schema_version": "response_verdict.v1",
    "response_mode": "bounded_answer",
    "medical_risk_level": "medium",
    "evidence_sufficiency": "limited",
    "human_escalation_required": false,
    "degraded_reason": "insufficient_evidence"
  },
  "evidence_panel": {
    "chips": [
      {
        "key": "profile_summary",
        "label": "Health Profile"
      },
      {
        "key": "guideline_search",
        "label": "Guideline Evidence"
      }
    ],
    "sections": [
      {
        "label": "Health Profile",
        "summary": "Recent profile context influenced the answer.",
        "key_facts": [
          "Recent fasting-glucose context was considered",
          "Known profile risk context was considered"
        ],
        "decision_basis": "The reply prioritizes guidance that matches the user's current profile state.",
        "source_refs": ["profile_summary"],
        "source_items": [
          {
            "source_type": "profile",
            "title": "Recent profile snapshot",
            "snippet": "Recent fasting-glucose context was considered.",
            "timestamp": "2026-03-24T12:00:00Z",
            "confidence": 0.86
          }
        ]
      },
      {
        "label": "Guideline Evidence",
        "summary": "Retrieved medical guidance supported the recommendation.",
        "key_facts": [
          "Diet and follow-up guidance came from retrieved material"
        ],
        "decision_basis": "RAG evidence strengthened the medical framing and safety wording.",
        "source_refs": ["guide.pdf"],
        "source_items": [
          {
            "source_type": "guideline",
            "title": "Guideline excerpt",
            "snippet": "Retrieved guidance supported the recommendation.",
            "timestamp": "2026-03-24T12:00:00Z",
            "relevance": 0.91
          }
        ]
      }
    ]
  },
  "suggestion_card": {
    "headline": "血糖偏高时的近期管理建议",
    "risk_level": "medium",
    "key_actions": [
      "继续监测空腹血糖和餐后血糖",
      "优先控制精制糖和高升糖负荷饮食"
    ],
    "follow_up_hint": "结合近期趋势和既往体检结果持续观察 1 至 2 周",
    "when_to_seek_care": "如合并明显口渴、多尿、乏力或持续升高，请尽快线下就诊"
  }
}
```

Rules:

- Empty message returns `400`
- `force_refresh=true` bypasses cache
- `conversation_id=null` starts a new server-owned conversation and the returned id must be reused for follow-up turns
- `decision_summary.lane` and `decision_summary.verdict` are the frozen FE-consumable routing semantics for this slice
- `decision_summary.intent` remains a backend trace field for compatibility and must not be treated by FE as the authoritative lane model
- if a specialized non-urgent lane lacks enough evidence, the backend must keep the selected lane and fall back to `verdict="insufficient_evidence"` rather than silently switching semantics
- `urgent_symptom` responses must still return `decision_summary.lane="urgent_symptom"` and `decision_summary.verdict="seek_urgent_care"` even when the normal LLM flow is bypassed
- new assistant replies must include non-null top-level `response_verdict`
- `response_verdict` is the answer-level verdict object for the reply and does not replace `decision_summary.verdict`
- `response_verdict.response_mode` should remain aligned with `decision_summary.policy.answer_mode` when the nested policy object is present
- `evidence_panel` is optional and additive in this freeze; clients must tolerate `null` or omission during rollout
- when `evidence_panel` is present, backend owns chip ordering and section grouping
- `evidence_panel.chips` is the compact-summary layer for the hybrid UI and contains objects with `key` and `label`
- `evidence_panel.sections` is the expanded-detail layer and contains ordered section objects with `label`, `summary`, `key_facts`, `decision_basis`, `source_refs`, and `source_items`
- each `key_facts` entry and `source_refs` entry must stay concise enough for the current chat surface; backend should prefer a few high-signal items over exhaustive dumps
- `source_refs` should reuse top-level `sources` labels when the section is grounded in external or retrieved references; internally derived evidence may use stable backend-owned refs such as `profile_summary`
- `source_items` is the renderable source-detail drill-down layer for each section
- each source item must include `source_type`, `title`, `snippet`, and a `timestamp` field; `timestamp` may be `null` when no reliable capture time is available, and the item may also include `confidence` or `relevance`
- initial `source_type` values are limited to `profile`, `trend`, `report`, and `guideline`
- source items must contain safe summaries only; they may not expose raw large JSON payloads or unbounded tool dumps

Implemented runtime note as of 2026-03-24:

- `POST /chat/send` accepts optional `conversation_id`
- the response returns `conversation_id`, `reply`, `sources`, `evidence_tags`, `decision_summary`, and optional `suggestion_card`
- urgent symptom prompts may bypass the normal LLM flow and return immediate safety guidance
- `evidence_tags` and `decision_summary` are backend-owned runtime hints for controlled Agent behavior
- `decision_summary` is now the frozen carrier for backend-owned `lane` and `verdict` metadata; FE may consume those fields only and may not reinterpret legacy `intent` values as substitute lane semantics
- `decision_summary.policy` is the additive backend-owned explicit policy envelope; it stays backend-owned and does not replace the FE-consumable lane/verdict contract
- `response_verdict` is the additive top-level answer-level verdict object and is intentionally named to avoid colliding with `decision_summary.verdict`
- `suggestion_card` is an optional backend-owned structured summary intended to complement, not replace, the free-text reply
- `evidence_panel` is now present in the live response model and remains an architect-owned backend-authored shape that FE/BE must not silently redesign

#### Dr. AI Answer-Explanation View Boundary

This slice freezes the frontend presentation layer for the existing "why did Dr. AI answer this way" UI as a read-only projection over backend-owned metadata. It does not introduce a new response envelope, a new status taxonomy, or a new medical verdict system.

FE may directly consume these existing backend-owned fields:

- `decision_summary.lane`
- `decision_summary.verdict`
- `decision_summary.policy.policy_version`
- `decision_summary.policy.selected_rule`
- `decision_summary.policy.evidence_state`
- `decision_summary.policy.tool_availability`
- `decision_summary.policy.answer_mode`
- `decision_summary.policy.disclaimer_mode`
- `response_verdict`
- `sources`
- `evidence_tags`
- `evidence_panel`
- `suggestion_card`

FE may do display-only mapping, but may not change medical semantics:

- render `lane` and `verdict` as badges, chips, headers, or summary labels
- render `response_verdict.response_mode` and `response_verdict.evidence_sufficiency` as explanation copy or status text
- surface `decision_summary.policy.selected_rule` and `decision_summary.policy.disclaimer_mode` as human-readable rationale labels
- group or order `sources`, `evidence_tags`, and `evidence_panel` content for layout purposes
- localize or restyle labels while keeping the backend-owned meaning unchanged

FE may not infer new status labels from the existing metadata:

- no new labels such as `partial_answer`, `likely_correct`, `doctor_reviewed`, `policy_blocked`, or `model_confidence` unless the backend explicitly emits them
- no separate FE-owned "explanation verdict" that competes with `decision_summary.verdict` or `response_verdict`
- no derivation of lane, verdict, or clinical certainty from `reply`, `source text`, `tool names`, or `evidence_panel` content when explicit backend fields are present

Consistency rules across send, stream final, and replay:

- `/chat/send` final payloads, `/chat/stream` terminal `final` payloads, and `GET /chat/conversations/{conversation_id}/messages` replayed assistant turns must expose the same meaning for the fields listed above
- if a row predates a frozen field, replay must return the stored nullable value or omission rather than fabricating a replacement
- FE may not treat stream-only stage text as authoritative explanation state
- the same assistant turn must not present contradictory verdict semantics between live and replayed views

`evidence_panel` versus explanation UI:

- `evidence_panel` is the structured evidence drill-down owned by the backend
- the explanation UI is the FE presentation of existing verdict and policy metadata
- FE may render `evidence_panel` alongside the explanation UI, but it must not use the explanation UI to invent extra evidence provenance or to replace the backend-owned `evidence_panel` structure
- if `evidence_panel` is absent, the explanation UI still renders from the other frozen metadata; the absence of `evidence_panel` is not itself a new status

No new field is required for this slice:

- FE must consume the existing route payloads only
- BE must not add a new explanation field, explanation status field, or explanation verdict field for this freeze
- any later desire for a separate explanation schema must return through `architect` as a new contract request

#### `POST /chat/stream`

Purpose: send one Dr. AI query and receive staged SSE progress plus a terminal final payload

Request body:

```json
{
  "message": "结合我的趋势继续说明一下",
  "conversation_id": 12,
  "force_refresh": false
}
```

SSE event types:

- `status`: staged progress updates such as `conversation_ready`, `reading_profile`, `planning_tools`, `running_tool`, `generating_answer`
- `tool_start`: emitted when one concrete backend tool begins running and includes the backend tool name plus a short user-facing message
- `tool_done`: emitted when one concrete backend tool finishes and includes the backend tool name plus a short user-facing message
- `final`: terminal payload matching the `POST /chat/send` response shape, including `response_verdict` and optional `evidence_panel`
- `error`: terminal error event when streaming fails

#### `GET /chat/conversations`

Purpose: list the authenticated user's recent Dr. AI conversations for history switching

Query parameters:

- `query` optional substring filter against current title/preview
- `archived` optional boolean filter; default `false`

Response shape:

```json
[
  {
    "conversation_id": 12,
    "title": "最近血糖偏高应该注意什么？",
    "preview": "请继续监测血糖，并结合饮食与运动管理。",
    "message_count": 4,
    "updated_at": "2026-03-24T12:00:00",
    "last_accessed_at": "2026-03-24T12:05:00",
    "pinned": true,
    "archived": false,
    "group_key": "pinned",
    "group_label": "Pinned"
  }
]
```

Rules:

- Result order is backend-owned: pinned conversations first, then most recently accessed active sessions, then `updated_at desc, id desc` as a stable tie-break
- `title` is backend-owned and currently derived from a lightweight summary of the first user message rather than a raw first-30-character slice
- `archived=false` returns the active sidebar set; `archived=true` returns archived sessions
- `group_key` and `group_label` are backend-owned display metadata only; they do not change the underlying flat list or sort order
- `group_key` is derived from the conversation's backend recency timestamp, using `last_accessed_at` when present and otherwise `updated_at`; bucket boundaries use backend UTC time
- `group_key` values for non-pinned rows are `today`, `last_7_days`, or `older`; pinned rows always use `pinned`
- `group_label` is the human-readable section label for the current `group_key`

#### `PATCH /chat/conversations/{conversation_id}`

Purpose: manually rename one stored conversation without adding a message turn

Request body:

```json
{
  "title": "Weekly glucose check-in"
}
```

Rules:

- `title` is required and must contain non-whitespace characters after trimming
- `title` is capped by the existing conversation-title length limit
- A successful rename updates only the stored conversation title; it does not create a new message, change pin/archive state, or refresh access ordering
- Manual titles take precedence over backend auto-generated titles until the user renames the conversation again
- There is no bulk-rename, title-clear, or client-editable grouping mutation contract in this freeze

Response shape:

```json
{
  "conversation_id": 12,
  "title": "Weekly glucose check-in"
}
```

#### `POST /chat/conversations/{conversation_id}/pin`

Purpose: pin one stored conversation so it stays at the top of the sidebar ordering

Response shape:

```json
{
  "conversation_id": 12,
  "pinned": true
}
```

#### `POST /chat/conversations/{conversation_id}/unpin`

Purpose: remove one stored conversation from the pinned section while keeping it available in recent-session ordering

Response shape:

```json
{
  "conversation_id": 12,
  "pinned": false
}
```

#### `POST /chat/conversations/{conversation_id}/archive`

Purpose: archive one stored conversation so it is hidden from the default active-session list

Response shape:

```json
{
  "conversation_id": 12,
  "archived": true
}
```

#### `POST /chat/conversations/{conversation_id}/restore`

Purpose: restore one archived conversation back to the default active-session list

Response shape:

```json
{
  "conversation_id": 12,
  "archived": false
}
```

#### `POST /chat/conversations/batch/archive/prepare`

Purpose: validate a selected set of conversation ids before bulk archive is executed

Request body:

```json
{
  "conversation_ids": [12, 13, 14]
}
```

Response shape:

```json
{
  "requested_conversation_ids": [12, 13, 14],
  "archiveable_conversation_ids": [12, 14],
  "already_archived_conversation_ids": [13],
  "missing_conversation_ids": [],
  "duplicate_conversation_ids": [],
  "archiveable_count": 2
}
```

Rules:

- This is read-only validation only; it does not mutate conversation state
- Only conversations owned by the authenticated user are considered
- Duplicate ids are deduplicated before archiveability is evaluated
- The frontend may use this response to enable or disable the batch archive action
- Batch delete, hard delete, and message purge are explicitly out of scope

#### `POST /chat/conversations/batch/archive`

Purpose: archive multiple owned conversations in one request

Request body:

```json
{
  "conversation_ids": [12, 13, 14]
}
```

Response shape:

```json
{
  "requested_conversation_ids": [12, 13, 14],
  "archived_conversation_ids": [12, 14],
  "already_archived_conversation_ids": [13],
  "missing_conversation_ids": [],
  "duplicate_conversation_ids": [],
  "archived_count": 2
}
```

Rules:

- The endpoint archives rows by updating `archived_at` only
- It does not delete conversations or messages, and it does not create any new persisted batch state
- Duplicate ids are deduplicated before mutation
- Already archived conversations are treated as no-ops and reported separately
- Empty `conversation_ids` is invalid and should return `400`
- Batch delete, hard delete, and message purge are explicitly out of scope

#### `POST /chat/conversations/batch/restore/prepare`

Purpose: validate a selected set of archived conversation ids before bulk restore is executed

Request body:

```json
{
  "conversation_ids": [12, 13, 14]
}
```

Response shape:

```json
{
  "requested_conversation_ids": [12, 13, 14],
  "restorable_conversation_ids": [12, 14],
  "already_active_conversation_ids": [13],
  "missing_conversation_ids": [],
  "duplicate_conversation_ids": [],
  "restorable_count": 2
}
```

Rules:

- This is read-only validation only; it does not mutate conversation state
- Only conversations owned by the authenticated user are considered
- Duplicate ids are deduplicated before restoreability is evaluated
- The frontend may use this response to enable or disable the batch restore action
- Batch restore is limited to clearing `archived_at`; it does not imply delete, purge, folder mutation, or grouping mutation semantics
- Batch delete, hard delete, and message purge are explicitly out of scope

#### `POST /chat/conversations/batch/restore`

Purpose: restore multiple owned archived conversations in one request

Request body:

```json
{
  "conversation_ids": [12, 13, 14]
}
```

Response shape:

```json
{
  "requested_conversation_ids": [12, 13, 14],
  "restored_conversation_ids": [12, 14],
  "already_active_conversation_ids": [13],
  "missing_conversation_ids": [],
  "duplicate_conversation_ids": [],
  "restored_count": 2
}
```

Rules:

- The endpoint restores rows by clearing `archived_at` only
- It does not delete conversations or messages, and it does not create any new persisted batch state
- Duplicate ids are deduplicated before mutation
- Already active conversations are treated as no-ops and reported separately
- The endpoint does not change `pinned_at`, `last_accessed_at`, manual titles, or derived grouping metadata
- Empty `conversation_ids` is invalid and should return `400`
- Batch delete, hard delete, and message purge are explicitly out of scope

#### `GET /chat/conversations/{conversation_id}/messages`

Purpose: load one stored conversation and replay its message history plus any persisted assistant metadata in the frontend

Response shape:

```json
{
  "conversation_id": 12,
  "title": "最近血糖偏高应该注意什么？",
  "messages": [
    {
      "role": "user",
      "content": "最近血糖偏高应该注意什么？",
      "sequence": 1,
      "created_at": "2026-03-24T12:00:00",
      "sources": [],
      "evidence_tags": [],
      "decision_summary": {},
      "response_verdict": null,
      "evidence_panel": null
    },
    {
      "role": "assistant",
      "content": "请继续监测血糖，并结合饮食与运动管理。",
      "sequence": 2,
      "created_at": "2026-03-24T12:00:03",
      "sources": ["guide.pdf"],
      "evidence_tags": ["profile_summary", "guideline_search"],
      "decision_summary": {
        "intent": "guideline_lookup",
        "lane": "general_health",
        "verdict": "general_guidance",
        "policy": {
          "policy_version": "explicit_policy.v1",
          "evaluation_order": [
            "urgent_symptom",
            "diagnosis_sensitive",
            "medication_related",
            "trend_review",
            "report_interpretation",
            "general_health"
          ],
          "selected_rule": "general_health",
          "answer_mode": "bounded_answer",
          "degrade_reason": "evidence_insufficient"
        },
        "tool_needed": true,
        "tool_used": ["get_user_profile_summary", "search_medical_guidelines"],
        "safety_level": "normal"
      },
      "response_verdict": {
        "schema_version": "response_verdict.v1",
        "response_mode": "bounded_answer",
        "medical_risk_level": "medium",
        "evidence_sufficiency": "limited",
        "human_escalation_required": false,
        "degraded_reason": "insufficient_evidence"
      },
      "evidence_panel": {
        "chips": [
          {
            "key": "profile_summary",
            "label": "Health Profile"
          },
          {
            "key": "guideline_search",
            "label": "Guideline Evidence"
          }
        ],
        "sections": [
      {
        "label": "Health Profile",
        "summary": "Recent profile context influenced the answer.",
        "key_facts": [
          "Recent fasting-glucose context was considered"
        ],
        "decision_basis": "The reply prioritized guidance that matches current profile state.",
        "source_refs": ["profile_summary"],
        "source_items": [
          {
            "source_type": "profile",
            "title": "Recent profile snapshot",
            "snippet": "Recent fasting-glucose context was considered.",
            "timestamp": "2026-03-24T12:00:00Z",
            "confidence": 0.86
          }
        ]
      },
      {
        "label": "Guideline Evidence",
        "summary": "Retrieved medical guidance supported the recommendation.",
        "key_facts": [
          "Retrieved guidance informed the follow-up advice"
        ],
        "decision_basis": "RAG evidence reinforced the medical framing and safety wording.",
        "source_refs": ["guide.pdf"],
        "source_items": [
          {
            "source_type": "guideline",
            "title": "Guideline excerpt",
            "snippet": "Retrieved guidance supported the recommendation.",
            "timestamp": "2026-03-24T12:00:00Z",
            "relevance": 0.91
          }
        ]
      }
    ]
  },
      "suggestion_card": {
        "headline": "血糖偏高时的近期管理建议",
        "risk_level": "medium",
        "key_actions": [
          "继续监测空腹血糖和餐后血糖"
        ],
        "follow_up_hint": "结合近期趋势和既往体检结果持续观察 1 至 2 周",
        "when_to_seek_care": "如合并明显口渴、多尿、乏力或持续升高，请尽快线下就诊"
      }
    }
  ]
}
```

Rules:

- Nonexistent or cross-user `conversation_id` returns `404`
- `sources`, `evidence_tags`, `decision_summary`, `response_verdict`, `evidence_panel`, and `suggestion_card` are persisted on each `ChatMessage` row when available and replayed for historical assistant turns
- `response_verdict` is assistant-message metadata; new assistant rows should replay the same stored object that was emitted live
- user turns should return `response_verdict=null`
- `evidence_panel` is assistant-message metadata; user turns should return `null` or omit it
- historical replay must carry the same `evidence_panel.sections[*].source_items` shape as `/chat/send` and `/chat/stream` final payloads
- this route must not expose internal replay-package fields such as `context_budget_summary`, `rag_quality_summary`, `tool_result_summary`, `rag_source_refs`, `tool_plan_source`, `fallback_used`, `cache_hit`, `model_name`, or `audit_event_id`
- frontend-visible replay through this route remains `ChatMessage`-only; postmortem replay uses the separate internal `AgentAnswerReplay` boundary
- Older stored rows created before metadata persistence may still return empty metadata objects/lists
- Older stored rows created before the response-verdict slice may return `response_verdict=null`; BE must not fail replay or guess a synthetic object for them
- Older stored rows created before the C3 evidence-panel slice may return `null` for `evidence_panel` even when other metadata fields are present
- Loading one stored conversation refreshes its backend-owned `last_accessed_at` timestamp for recent-session ordering
- Batch archive and batch restore preparation/execution operate only on `conversation_id` lists and do not alter the message replay contract

### 3.6 Provider-Native Read-Only Tool Contracts

These contracts are frozen for backend implementation and provider-native function exposure. FE/BE may not silently rename the tools, change parameter names, or widen the output scope.

#### `medication_summary_lookup`

Purpose:

- Retrieve a bounded medication summary for the authenticated user so the model can answer questions about already-persisted medication facts without prescribing, titrating, or editing treatment.

Read-only scope and boundary:

- Read from the authenticated user's persisted medication facts only.
- Primary source: normalized medication-related facts embedded in `MedicalDocument.ocr_summary`.
- Fallback source: stable medication facts already stored in `UserProfile.extra_data` when present.
- No OCR rerun, no prescription editing, no pharmacy workflow, no cross-user access.

Input schema:

```json
{
  "type": "object",
  "properties": {
    "document_id": {
      "type": ["integer", "null"],
      "description": "Optional user-owned document id. If omitted, use the latest document or profile medication facts that contain a persisted medication summary."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 5,
      "description": "Maximum medication items to return after backend normalization."
    }
  },
  "required": []
}
```

Output shape at the backend tool boundary:

```json
{
  "has_medication_summary": true,
  "document_id": 123,
  "file_name": "report.pdf",
  "summary_source": "medical_document_ocr_summary",
  "medication_summary": {
    "schema_version": "medication_summary.v1",
    "status": "info",
    "count": 2,
    "message": "2 medication facts found",
    "medication_items": [
      {
        "name": "Metformin",
        "dose": "500",
        "unit": "mg",
        "frequency": "BID",
        "route": "oral",
        "instruction": "after meals",
        "source_ref": "report:123",
        "source_type": "report"
      }
    ],
    "medication_items_truncated": false,
    "source_refs": ["report:123"]
  }
}
```

Rules and exposure constraints:

- If `document_id` is provided but does not belong to the current user or has no medication facts, the tool returns `has_medication_summary=false`; it must not leak document existence across users.
- `medication_summary` is a bounded normalized projection over persisted medication facts, not a raw pass-through blob or a dosing recommendation engine.
- `medication_items` is a bounded list of normalized medication rows using only safe summary fields already present in stored data.
- `source_ref` and `source_refs` must remain backend-stable labels; the tool may not invent new evidence buckets or expose raw OCR text.
- Non-goals: prescribing advice, refill workflow, medication reconciliation writes, allergy management, or pharmacy-facing action creation.

#### `recent_metric_anomaly_lookup`

Purpose:

- Return a bounded recent metric-anomaly view so the model can explain what currently looks abnormal without recomputing analysis through write-capable flows.

Read-only scope and boundary:

- Read from the authenticated user's latest persisted `HealthRecord.metrics` when available.
- Fallback to the authenticated user's current `UserProfile` metric fields when no usable history snapshot exists.
- Reuse the existing anomaly-detection rules already frozen elsewhere in the backend domain.
- No profile writeback, no report merge, no simulation, no clinical recommendation generation.

Input schema:

```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 5,
      "description": "Maximum abnormal metrics to return after backend ranking."
    }
  },
  "required": []
}
```

Output shape at the backend tool boundary:

```json
{
  "has_metric_anomalies": true,
  "evaluated_at": "2026-03-24T12:00:00",
  "evaluated_source": "health_record",
  "summary": {
    "status": "warning",
    "count": 2,
    "message": "2 abnormal metrics found"
  },
  "items": [
    {
      "metric_key": "Glucose_Fasting",
      "display_name": "Glucose_Fasting",
      "value": 6.8,
      "unit": "",
      "status": "High",
      "tag": "Diabetes_Risk",
      "message": "Glucose_Fasting high",
      "detection_source": "standard_range",
      "source_ref": "health_record_metrics"
    }
  ]
}
```

Rules and exposure constraints:

- `items` must be backend-ranked and truncated to `limit`; do not dump every anomaly if many exist.
- `evaluated_source` is `health_record` when derived from the latest usable history snapshot, otherwise `user_profile`.
- This tool returns anomaly facts and anomaly-summary metadata only; it must not generate treatment plans or autonomous escalation behavior.
- The backend may map the resulting evidence into `trend`- or `profile`-type source items, but it may not invent a new source taxonomy for this slice.
- Non-goals: timeline comparison, document parsing, simulation, diagnosis, or clinician-facing triage logic.

#### `report_comparison_lookup`

Purpose:

- Compare two persisted report summaries for the authenticated user so the model can explain the bounded differences between reports without exporting raw files or scanning arbitrary history.

Read-only scope and boundary:

- First source of truth: two user-owned `MedicalDocument.ocr_summary` payloads.
- Fallback behavior: if explicit document ids are omitted, the backend may choose the latest two user-owned documents with persisted OCR summaries and compare them in chronological order.
- Read-only retrieval and bounded normalization only.
- No OCR rerun, no PDF export, no cross-user access, no multi-document free-form diffing.

Input schema:

```json
{
  "type": "object",
  "properties": {
    "baseline_document_id": {
      "type": ["integer", "null"],
      "description": "Optional older user-owned document id to compare from."
    },
    "comparison_document_id": {
      "type": ["integer", "null"],
      "description": "Optional newer user-owned document id to compare against."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 5,
      "description": "Maximum comparison items to return after backend ranking."
    }
  },
  "required": []
}
```

Output shape at the backend tool boundary:

```json
{
  "has_report_comparison": true,
  "baseline_document_id": 123,
  "comparison_document_id": 456,
  "baseline_file_name": "report-a.pdf",
  "comparison_file_name": "report-b.pdf",
  "comparison_basis": "medical_document_ocr_summary",
  "summary": {
    "status": "different",
    "count": 3,
    "message": "3 bounded differences found"
  },
  "delta_items": [
    {
      "field": "Glucose_Fasting",
      "baseline_value": 5.6,
      "comparison_value": 6.8,
      "change": "up",
      "source_refs": ["baseline_report", "comparison_report"]
    }
  ],
  "shared_metric_count": 4,
  "new_findings_count": 1,
  "removed_findings_count": 0,
  "source_refs": ["baseline_report", "comparison_report"]
}
```

Rules and exposure constraints:

- `delta_items` must be backend-ranked and truncated to `limit`; do not dump every possible field diff.
- `comparison_basis` is a bounded normalized OCR-summary comparison, not a raw file diff or generalized history browser.
- The tool may only compare the two selected reports and may not widen into arbitrary multi-report export or discovery behavior.
- The backend may map the resulting evidence into `report`-type source items only; it may not introduce a new source type for report comparisons.
- Non-goals: raw text diffing, PDF export, cross-user comparisons, or free-form report history browsing.

### 3.6.1 Shared Tool Evidence Metadata Envelope

Every read-only tool in this slice may attach an additive `evidence_metadata` object to its backend tool result. The object is backend-owned, compact, and bounded. It exists to explain result quality, not to carry raw evidence or replace the normal tool result body.

Canonical envelope:

```json
{
  "evidence_metadata": {
    "schema_version": "tool_evidence_metadata.v1",
    "freshness": "recent",
    "coverage": "partial",
    "confidence": "medium",
    "missing_fields": ["HbA1c"],
    "comparable_fields_count": 2
  }
}
```

Rules:

- `freshness` is one of `fresh`, `recent`, `stale`, or `unknown`.
- `coverage` is one of `full`, `partial`, `empty`, or `unknown`.
- `confidence` is one of `high`, `medium`, `low`, or `unknown`.
- `missing_fields` is a backend-stable list of normalized field labels; it must not be a raw OCR dump, raw payload dump, SQL column list, or prompt text.
- `comparable_fields_count` is a non-negative integer and is only meaningful when the tool compared aligned evidence units. It may be omitted or `null` when not applicable.
- Empty, stale, or conflicting results must not report `confidence="high"`.
- `coverage="empty"` means the tool could not produce a usable bounded projection. It does not mean the backend should invent a fallback summary.
- This envelope is additive. It must never be used to smuggle raw payloads or to widen the business payload beyond the frozen result shape.
- The chat runtime may observe the envelope for transparency, but the existing tool `status`, `has_*`, `count`, `items`, `shared_metric_count`, `evaluated_source`, `captured_at`, and similar business fields remain the authoritative inputs for sufficiency checks.

### 3.6.2 Tool Applicability Matrix And Failure Fallbacks

The backend tool registry keeps the current tool names and result shapes, but the chat runtime now freezes applicability checks for each tool as backend-owned hard checks.

Applicability matrix:

| Tool | Applicability prerequisites | Forbidden / not-applicable scenarios | Pre-check failure fallback | Post-check sufficiency rule | Required metadata bundle |
|------|-----------------------------|--------------------------------------|----------------------------|-----------------------------|--------------------------|
| `get_user_profile_summary` | Current authenticated user has a usable profile and the turn needs current personal facts | Cross-user access, report-only explanation, medication change requests, urgent symptom triage, diagnosis certainty requests | Block before execution and reuse the existing blocked/error envelope with a backend-owned reason such as `missing_required_context` or `tool_not_allowed_for_lane` | Profile facts can support bounded general-health context, but they do not authorize diagnosis certainty or override stronger report/trend evidence | `summary_min` |
| `get_latest_risk_report` | Current authenticated user has a persisted normalized risk snapshot or an equivalent profile-backed snapshot | New risk prediction, cross-user access, urgent symptom triage, diagnosis certainty requests | Block before execution when no usable persisted risk snapshot exists | A persisted risk snapshot can support bounded explanation, but it is not sufficient for diagnosis-like certainty or for overriding conflicting report/trend evidence | `summary_min` |
| `get_history_trends` | At least one comparable history record exists; two records are required for a full trend claim | Single-point trend questions that would require forecasting, diagnosis certainty, medication changes, cross-user access | Block or return an empty/partial result when no usable history exists; the backend must still count the tool as unavailable evidence | One record may support limited context, but at least two comparable points are required for `trend_review` sufficiency | `comparison_min` |
| `get_uploaded_documents_summary` | User-owned documents exist and the turn needs document inventory context | Raw OCR export, cross-user access, free-form report diffing, diagnosis certainty requests | Block when there are no user-owned documents or when the question does not need document inventory | Document inventory alone is not sufficient for report interpretation; it can only support bounded guidance or a request to upload / identify a report | `summary_min` |
| `report_summary_lookup` | The selected user-owned document has a persisted OCR summary | Cross-user lookups, empty document summaries, raw OCR text requests, diagnosis certainty requests | Block before execution when no usable OCR summary exists for the chosen document | A usable report summary is sufficient only for bounded report interpretation; it does not support diagnosis or medication changes on its own | `summary_min` |
| `report_comparison_lookup` | Two user-owned persisted report summaries exist and the turn asks for comparison or change over time | Raw file diffing, multi-document browsing, cross-user comparison, arbitrary history export | Block before execution when two usable summaries do not exist | The comparison can support bounded report interpretation or trend-like explanation, but it still degrades if the compared fields do not directly answer the question | `comparison_min` |
| `recent_metric_anomaly_lookup` | A current health record or profile metric set exists and the turn asks what looks abnormal | Diagnosis certainty, treatment planning, profile writeback, cross-user access | Block before execution when no usable metric source exists; treat the tool as unavailable evidence | The tool may support bounded explanation of abnormal values, but it must not be treated as diagnosis or treatment evidence by itself | `summary_min` |
| `recent_abnormal_metrics_lookup` | Same applicability as `recent_metric_anomaly_lookup` | Same forbidden scenarios as `recent_metric_anomaly_lookup` | Same fallback as `recent_metric_anomaly_lookup` | Same post-check rule as `recent_metric_anomaly_lookup`; this is a compatibility alias, not a new contract class | `summary_min` |
| `latest_analysis_snapshot_lookup` | A persisted risk snapshot exists on the latest health record or profile | New analysis generation, diagnosis certainty, cross-user access, urgent symptom triage | Block before execution when no normalized snapshot exists | The snapshot can support bounded context, but it is not sufficient for diagnosis-like certainty or for overriding stronger report or trend evidence | `summary_min` |
| `medication_summary_lookup` | User-owned medication facts exist in a persisted report summary or profile-backed medication facts and the turn asks about existing medications | Prescribing, titration, start/stop/change requests, refill workflow, allergy management, cross-user access | Block before execution when no persisted medication facts exist or when the question is about changing treatment rather than summarizing it | A medication summary is sufficient only for factual medication recall and bounded safety language; it must degrade to a refusal or clarification when the user asks for treatment changes | `summary_min` |
| `search_medical_guidelines` | The turn needs attributable guideline context and a query string is present | Raw patient-data retrieval, cross-user access, replacement for personal evidence, diagnosis certainty on its own | Block before execution if the query is missing or the lane forbids guidance-only support | Guideline retrieval may contextualize a reply, but it never by itself satisfies report, trend, medication, or diagnosis sufficiency | `none` |

Failure fallback rules:

- blocked tools remain blocked even if other allowed tools succeed
- blocked tools do not count as usable evidence for `decision_summary.policy.evidence_state`
- empty or weak tool results may still be useful as context, but they cannot upgrade the answer to a stronger mode than the evidence supports
- when the evidence gate is not satisfied, the backend must emit the frozen degrade signals and stop at the bounded answer or clarification boundary rather than continuing with unsupported medical explanation

### 3.7 Runtime Exposure Through Existing Chat Routes

The three new tools are exposed only through the existing Dr. AI runtime:

- `POST /chat/send` may cause the backend to surface these tool schemas to a provider-native function-calling model.
- `POST /chat/stream` may emit `tool_start` and `tool_done` events for these tool names during execution.
- No public REST caller is expected to invoke these tools directly.
- `decision_summary.tool_used` may include these exact tool names once implemented.
- No new public chat route, chat request field, or chat response field is required for this slice; any future request to expose the tools directly is contract pressure and must return through `architect`.

## 4. Contract Constraints

- Route shapes remain as currently implemented; no namespace cleanup is implied by this document.
- Field naming remains mixed and domain-specific where already used by frontend or backend.
- Response normalization is deferred; consumers should integrate against the frozen route-level shapes above.
- FE may consume only backend-emitted `decision_summary.lane` and `decision_summary.verdict` for chat-lane UX after this freeze; FE may not infer or redefine lane semantics from `intent`, `reply`, `evidence_tags`, or tool names.
- FE may ignore `decision_summary.policy`; it is backend-owned runtime metadata and not part of the FE routing contract.
- FE may read `response_verdict`, but it may not redefine it, infer it from `decision_summary.verdict`, or introduce a second answer-level verdict object.
- FE may read `takeover`, but it may not derive new clinical meaning, infer a hidden handoff state from `summary`, or repurpose the object into a workflow, ticketing, or disclaimer system.
- FE and BE may not silently replace `evidence_tags` with `evidence_panel`, or redesign the `evidence_panel` section shape, without an architect-owned contract update.
- FE and BE may not silently rename `medication_summary_lookup`, `recent_metric_anomaly_lookup`, or `report_comparison_lookup`, or widen them into write-capable behaviors, without an architect-owned contract update.
- FE and BE may not silently emit additional lane names, verdict codes, or lane / verdict combinations beyond the frozen matrix in section 2.9 without an architect-owned contract update.
- FE and BE may not silently change the `decision_summary.policy` field shape, policy-version compatibility rule, or answer-mode set without an architect-owned contract update.
- FE and BE may not silently rename `response_verdict`, move it under `decision_summary`, widen its enum sets, or synthesize it for legacy replay rows without an architect-owned contract update.
- FE and BE may not silently rename `takeover`, move it under `decision_summary`, widen its status or trigger enums, or synthesize a different human-handoff object for legacy replay rows without an architect-owned contract update.
- FE and BE may not silently expose `AgentAuditEvent` through a new route, chat response field, SSE event, export path, or tool surface, and BE may not silently change the `agent_audit_responsibility.v2` field set or governance-version semantics without an architect-owned contract update.
- FE and BE may not silently add internal answer-replay fields onto `ChatMessage` payloads, route responses, SSE events, or cache payloads; bounded replay belongs in the separate internal `AgentAnswerReplay` structure only.
- BE may not silently create a replay or admin route under `/chat/*`; any future replay-read surface must be reviewed as a separate internal/admin contract change.
- FE and BE may not silently widen the conversation API into destructive batch delete, hard delete, message purge, or archived-folder mutation semantics; only single-item archive/restore plus the frozen batch archive and batch restore hooks are in scope for this freeze.

## 5. Open Issues For Later Normalization

- Some user/profile routes live outside `/api/v1`
- Response envelopes are inconsistent across modules
- Pydantic/SQLModel schemas are not fully separated from persistence models
- `build_knowledge_base` still needs page-aware chunk metadata in the internal RAG path, but that work remains backend-only and does not justify a new public retrieval endpoint
- Export/PDF and some simulation paths remain outside the current freeze
- Current runtime conflict: `GET /user/profile` and `GET /api/v1/user/documents` still expose compatibility payloads directly, so FE must not treat those fields as already-normalized schemas.
- Current runtime conflict: `medication_summary_lookup` and `report_comparison_lookup` in [agent_tools.py](E:\health_ai_platform_2.0\backend\services\agent_tools.py) still need bounded normalized projections over OCR-backed medication and report data; BE must not pass raw parsed OCR payloads through unchecked.
- Current runtime conflict: [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) still assumes optional OCR `summary` text and still truncates raw `risk_history` strings for context, which is weaker than the frozen normalized boundary.
- Current runtime conflict: [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) still emits open-ended `intent` values and tool-keyword planning rather than the frozen six-lane matrix, so BE must add authoritative `decision_summary.lane` / `decision_summary.verdict` emission through the existing chat routes.
- Current runtime conflict: [backend/models.py](E:\health_ai_platform_2.0\backend\models.py), [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py), and [backend/api/api_v1/endpoints/chat.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\chat.py) still have no frozen `takeover` field, so BE must add the new object across send, stream final, and history replay if it implements the contract.
- Current runtime conflict: [agent_safety.py](E:\health_ai_platform_2.0\backend\services\agent_safety.py) currently classifies only urgent-vs-normal routing and therefore does not yet enforce the frozen `diagnosis_sensitive` boundary or the full six-lane matrix.
- Current data-shape conflict: there is still no dedicated persisted medication entity, so `medication_summary_lookup` continues to depend on normalized OCR-backed facts plus a stable `UserProfile.extra_data` fallback.
- Current data-shape conflict: `report_comparison_lookup` depends on comparing two user-owned normalized OCR summaries and must not widen into raw file diffing or arbitrary history browsing.
- Current replay-boundary conflict: [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) still has no dedicated `AgentAnswerReplay` storage, so the frozen bounded replay package cannot yet be persisted separately from `ChatMessage` and `AgentAuditEvent`.
- Current replay-boundary conflict: [backend/services/conversation_service.py](E:\health_ai_platform_2.0\backend\services\conversation_service.py) and [backend/api/api_v1/endpoints/chat.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\chat.py) currently expose only `ChatMessage` metadata on history replay, which must remain public-safe and must not silently absorb the new internal replay bundle.

## 6. Decision Log

| Decision | Rationale |
|----------|-----------|
| Freeze current route shapes instead of redesigning namespaces | Preserves the working frontend/backend integration baseline |
| Keep contract scope to the approved P0 loop | Avoids over-freezing lower-priority admin and research surfaces |
| Document current mixed response styles instead of masking them | More honest and safer for implementers than pretending a normalized API already exists |
| Freeze `evidence_panel` as an additive chat-metadata field | Supports richer evidence rendering without breaking the current reply- and chip-based UI during rollout |
| Freeze section-level `source_items` as bounded drill-down metadata | Adds renderable source detail without exposing raw payloads or changing the outer chat contract |
| Freeze the next read-only expansion as internal chat tools instead of new REST routes | Keeps the user-visible capability additive while avoiding public API churn |
| Freeze `medication_summary_lookup` as a bounded medication-facts projection rather than prescribing advice | Keeps the tool retrieval-only and backend-internal |
| Freeze `recent_metric_anomaly_lookup` as a bounded anomaly summary over latest metric inputs | Reduces medical-domain overexposure of raw anomaly payloads |
| Freeze `report_comparison_lookup` as a pairwise normalized OCR-summary comparison | Gives BE a bounded diff surface without raw file export semantics |
| Freeze query-time RAG quality summary as backend-only runtime metadata and keep the full benchmark report out of `/chat/*` | Preserves conservative degrade behavior without exposing retrieval internals |
| Keep the next tool slice backend-internal through the provider-native function-calling path | Avoids public chat API churn while preserving the current route surface |
| Reuse existing `report`, `profile`, and `trend` source types for evidence mapping in this slice | Prevents inventing a new taxonomy just for the tool boundary |
| Keep `GET /user/profile` and `GET /api/v1/user/documents` as compatibility passthroughs while freezing stricter tool outputs | Allows migration without pretending those legacy fields are already stable frontend schemas |
| Freeze batch archive as an additive preparation-plus-execution contract over flat conversation ids while excluding bulk delete | Preserves the current conversation model and keeps destructive bulk semantics out of scope |
| Freeze batch restore as an additive preparation-plus-execution contract over flat conversation ids while excluding folder mutation and bulk delete | Keeps restore behavior symmetric with batch archive while preserving the existing archived-session model |
| Carry the six-lane routing freeze through `decision_summary` instead of new chat routes | Preserves the current public route surface while giving FE a bounded metadata contract |
| Keep `intent` as backward-compatible backend trace and freeze `lane` / `verdict` for FE consumption | Prevents FE/BE from continuing to treat ad hoc intent strings as authoritative medical-routing semantics |
| Freeze `decision_summary.policy` as an additive backend-owned explicit policy envelope | Makes rule priority, answer mode, and degrade behavior explicit without changing the public route surface |
| Freeze top-level `response_verdict` for answer-level reply state | Avoids semantic collision with `decision_summary.verdict` while keeping send, stream-final, and replay on one shape |
| Freeze `takeover` as a separate backend-owned human-handoff projection | Gives FE a bounded handoff signal without turning the API surface into a workflow, ticketing, or disclaimer system |
| Freeze the evidence sufficiency gate to `sufficient`, `limited`, and `insufficient`, and add `conflicting_evidence` as an explicit degrade reason | Removes `missing` vs `insufficient` drift while keeping existing chat routes and metadata fields |
| Freeze internal audit as `agent_audit_responsibility.v2` rather than a transcript-like call record | Keeps backend accountability aligned to policy/verdict outcomes without creating any public audit API surface |
| Freeze answer replay as a separate internal `AgentAnswerReplay` package instead of widening `GET /chat/conversations/{conversation_id}/messages` | Keeps postmortem reconstruction available for BE/ops while preserving the existing frontend-safe chat-history contract |
