# Health AI Platform Architecture

## Ownership

- Owner: `architect`
- Status: `approved`
- Scope baseline: approved P0 core loop from [PRD.md](E:\health_ai_platform_2.0\docs\PRD.md)
- Review basis: full tracked-code scan completed on 2026-03-24

## Purpose

Define the repository-level architecture that lets `fe`, `be`, and `ai-data` work in parallel without redefining product scope or silently drifting on interfaces.

## 1. Architecture Summary

Health AI Platform is a single-repository application built around a Vue 3 web frontend and a FastAPI backend, with local persistence, AI/ML services, OCR, RAG, and data-pipeline assets living in the same codebase.  
For the current approved product gate, the architecture focuses on one P0 user loop:

1. User authenticates and loads their profile
2. User uploads or edits health data
3. Backend persists user/profile/document state
4. OCR and parsing convert uploaded reports into structured health data
5. Risk and analysis services compute health outputs
6. RAG chat uses user context plus knowledge-base retrieval
7. Frontend renders profile, risk, and timeline views

## 2. Current Approved Scope

### 2.1 In Scope For This Architecture Set

- Authentication and authenticated user session flow
- User profile read/write
- Medical document upload and OCR extraction
- Comprehensive risk analysis
- Dr. AI context-aware chat
- Health history and trend retrieval
- Supporting knowledge-base retrieval and cache invalidation

### 2.2 Explicitly Deferred From This Contract Freeze

- Family account switching as a formally frozen contract
- Admin ETL and data-center operations
- Nutrition generation as a frozen public contract
- IoT ingestion as a frozen public contract
- PDF export as a release gate
- Mobile/App surfaces

These areas may already exist in code, but they are not part of the current contract freeze for the P0 architecture gate.

## 3. Runtime Topology

### 3.1 Frontend Runtime

- Technology: Vue 3 + Vite + Pinia + Vue Router
- Entry routing: [index.js](E:\health_ai_platform_2.0\frontend\src\router\index.js)
- Main authenticated user views:
  - [DashboardView.vue](E:\health_ai_platform_2.0\frontend\src\views\DashboardView.vue)
  - [ClinicalView.vue](E:\health_ai_platform_2.0\frontend\src\views\ClinicalView.vue)
  - [DrAI.vue](E:\health_ai_platform_2.0\frontend\src\views\chat\DrAI.vue)
  - [HealthTimeline.vue](E:\health_ai_platform_2.0\frontend\src\views\clinical\HealthTimeline.vue)
- Main stores:
  - [authStore.js](E:\health_ai_platform_2.0\frontend\src\stores\authStore.js)
  - [healthStore.js](E:\health_ai_platform_2.0\frontend\src\stores\healthStore.js)

Frontend responsibilities:

- Manage login/register and bearer-token persistence
- Fetch and cache user profile data in Pinia
- Trigger OCR upload, profile save, analysis, chat, and history/trend requests
- Render user-facing health state and explanations
- Render Dr. AI conversation history, conversation switching, and new-session resets without owning server conversation semantics

### 3.2 Backend Runtime

- Technology: FastAPI + SQLModel + SQLite runtime in current repository
- Entry point: [main.py](E:\health_ai_platform_2.0\backend\main.py)
- DB session management: [database.py](E:\health_ai_platform_2.0\backend\database.py)
- Authentication helpers: [auth.py](E:\health_ai_platform_2.0\backend\auth.py)
- Core data models: [models.py](E:\health_ai_platform_2.0\backend\models.py)

Backend responsibilities:

- Authenticate and authorize requests
- Persist user, profile, history, and uploaded document records
- Expose P0 HTTP APIs
- Orchestrate OCR, chat, risk, projection, anomaly, and RAG retrieval services
- Own assistant evidence metadata shaping for Dr. AI replies, including compact chips, any expanded evidence-panel structure, and any backend-owned takeover projection that must be shown to FE
- Invalidate cache when health state changes

Implemented runtime note as of 2026-03-24:

- Dr. AI now uses server-owned conversation continuity through `conversation_id`
- Dr. AI now also exposes a frontend conversation sidebar backed by server-side conversation summaries and stored message history
- the backend chat runtime now includes safety classification, read-only tool execution, bounded evidence synthesis, and structured decision summaries
- the backend chat runtime now applies a dedicated context-building step with per-lane token budgeting for profile, tool evidence, RAG context, query text, and retained conversation history
- the backend chat runtime now prefers provider-native function calling / tool use when the configured model supports it, and falls back to deterministic local tool planning when native tool calls are unavailable or return no tool call decisions
- the backend chat runtime now emits tool-level SSE events (`tool_start` and `tool_done`) in addition to coarse status stages, so the frontend can surface concrete tool progress during long-running turns
- the next approved safe expansion slice keeps the same chat HTTP routes and adds exactly three additive read-only backend tools for the provider-native function path: `medication_summary_lookup`, `recent_metric_anomaly_lookup`, and `report_comparison_lookup`
- the frontend Dr. AI view is responsible for preserving and resending the active `conversation_id`
- conversation management now includes backend-owned manual title rename and read-time grouping metadata for the sidebar, while keeping the list itself flat and backend-ordered
- persisted assistant metadata (`sources`, `evidence_tags`, `decision_summary`) is now replayed when the frontend reopens a stored conversation, so history switching preserves evidence context rather than only plain text
- persisted assistant metadata now also includes an optional `suggestion_card`, allowing historical session replay to preserve the same structured health guidance card the user originally saw
- persisted assistant metadata now also includes an optional backend-owned `takeover` object, allowing historical session replay to preserve the same human-handoff semantics the user originally saw
- conversation management now also includes backend-owned title summarization, active/archived filtering, pinned-session ordering, and recent-access refresh semantics for the history sidebar
- the approved C3 evidence-panel freeze extends assistant metadata with a backend-owned optional `evidence_panel` object for richer evidence rendering, but the current runtime does not yet emit or persist that field

### 3.2.1 Agent Audit Responsibility Record Boundary

The backend now has pressure for durable audit storage, but that storage is intentionally internal-only and is now frozen as a responsibility record rather than a simple call record.

Architecture rules:

- Audit persistence is backend-owned and does not add a public chat route, query parameter, or response field.
- `POST /chat/send` and `POST /chat/stream` keep their current payload contracts; audit data is not surfaced through either route and must not be copied into chat responses.
- The current runtime logger-based audit trail remains in place alongside persisted audit records. Persisted audit records are additive and do not replace operational logs.
- Persisted audit records are append-only responsibility rows for one emitted assistant outcome: normal finalize, cache-hit finalize, provider/model failure fallback finalize, or urgent safety short-circuit.
- One responsibility row is written per finalized assistant turn. User turns, intermediate tool events, prompt-building stages, and partial SSE status events do not create their own audit rows.
- The backend may implement the durable record within the frozen contract, but FE and BE may not widen the shape silently or expose it through the public chat API without architect review.

Frozen persisted responsibility payload:

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
  "tool_latency_ms": 17,
  "response_latency_ms": 93
}
```

Required runtime fields to persist for new rows:

- `schema_version`
- `governance_version`
- `timestamp`
- `user_id`
- `conversation_id`
- `intent`
- `lane`
- `verdict`
- `selected_rule`
- `policy_version`
- `response_mode`
- `evidence_sufficiency`
- `degraded_reason`
- `human_escalation_required`
- `model_name`
- `tool_plan_source`
- `tool_used`
- `tool_count`
- `cache_hit`
- `fallback_used`
- `safety_level`
- `evidence_tags`
- `context_budget_summary`
- `tool_latency_ms`
- `response_latency_ms`

Field semantics:

- `schema_version` is the persisted audit payload version. This freeze opens a new major shape as `agent_audit_responsibility.v2`; historical `audit_event.v1` rows remain readable but are not the target for new writes.
- `governance_version` is the architect-owned runtime-governance baseline for the turn. In this slice the frozen value is `agent_runtime_governance.v1`.
- `policy_version` must mirror `decision_summary.policy.policy_version` for the emitted assistant turn.
- `intent` is retained only as a compatibility trace. Responsibility semantics now come primarily from `lane`, `verdict`, `selected_rule`, `response_mode`, `evidence_sufficiency`, and `degraded_reason`.
- `tool_plan_source` is a bounded enum: `native_function_calling`, `local_fallback_planner`, `no_tool_path`, `cache_replay`, or `urgent_short_circuit`.
- `cache_hit=true` means the emitted assistant reply body came from the cache for the current turn. `fallback_used=true` means the runtime had to fall back from native tool calling to the local planner for the current turn.
- `model_name` is the sanitized provider/model identifier that materially contributed to the emitted reply. It must be `null` for urgent short-circuit responses and may be `null` for cache replay when no new model call occurred.
- `degraded_reason` must align to the dominant final responsibility reason after policy/verdict reconciliation; it must not invent a second free-form taxonomy.
- `context_budget_summary` may contain only the bounded context lanes `profile`, `rag`, `tools`, `query`, and `history`, each with integer `budget` and optional integer `used`.

Privacy, retention, and governance-tracking rules:

- The persisted audit payload is metadata-only. It must not store raw query text, assistant reply text, prompt text, tool arguments, model tokens, provider response ids, or other unbounded content.
- The audit payload must not store large RAG text, raw OCR text, raw risk snapshots, raw tool results, or unsanitized medical payloads. If the runtime needs medical evidence accountability, it must persist only the bounded fields frozen here.
- `context_budget_summary`, `tool_used`, and `evidence_tags` must stay bounded and sanitized. They are not a back door for prompt fragments, report excerpts, or extracted lab payloads.
- Audit records are user-scoped and conversation-scoped, but they are not user-visible and are not part of the public chat contract.
- Retention is now frozen as an internal observability policy: responsibility rows must survive for at least the same operational retention window as the associated conversation history and must not be shortened or widened into general transcript retention without architect review.
- Storage ownership stays with `be`; read access is limited to backend services and internal maintenance/observability workflows. FE, public API callers, provider-native tools, and end users have no access path.
- Runtime-governance version tracking is split intentionally:
- the normative source of truth is these architect-owned docs
- the approval and rollout state is recorded only by `orchestrator` in `docs/blackboard/state.yaml`
- persisted responsibility rows may echo `governance_version`, but implementation agents must not invent new version strings unless the docs are updated first and the blackboard later records approval

Current runtime conflicts called out explicitly for implementation planning:

- [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) still defines `AgentAuditEvent` as a call-oriented `audit_event.v1` row and does not yet carry the frozen responsibility fields.
- [backend/services/agent_audit.py](E:\health_ai_platform_2.0\backend\services\agent_audit.py) still builds and sanitizes only the older field set and must align its bounded-write path to the frozen responsibility schema.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) already has the runtime inputs for `policy_version`, `response_mode`, `evidence_sufficiency`, `degraded_reason`, cache-hit handling, and planner provenance, but it does not yet persist them as one responsibility record across every finalize path.

### 3.2.2 Assistant Answer Replay Package Boundary

The next replay slice is not a transcript-archive feature. Its purpose is narrowly bounded postmortem reconstruction for one finalized assistant answer turn.

Architecture rules:

- Replay storage is internal-only and backend-owned. It does not add a public chat route, query parameter, SSE event, or chat response field.
- Replay storage must not live on `ChatMessage`. `ChatMessage` remains the user-visible conversation-history record and continues to carry only reply text plus frontend-safe assistant metadata such as `sources`, `evidence_tags`, `decision_summary`, `response_verdict`, `evidence_panel`, and `suggestion_card`.
- Replay storage must not be collapsed into `AgentAuditEvent` alone. `AgentAuditEvent` remains the append-only accountability record, while replay needs a bounded per-answer reconstruction bundle keyed directly to the emitted assistant message.
- Freeze a new internal one-to-one replay structure/table for assistant turns only: `AgentAnswerReplay`.
- One `AgentAnswerReplay` row is written per finalized assistant `ChatMessage` row, including normal finalize, cache-hit finalize, provider/model failure finalize, and urgent short-circuit finalize. User turns, partial SSE stages, and intermediate tool events do not create replay rows.
- `AgentAnswerReplay` must link to exactly one assistant `ChatMessage` and exactly one `AgentAuditEvent`, so postmortem readers can correlate public-message metadata, bounded replay facts, and accountability metadata without re-deriving them from raw runtime state.
- No internal/admin HTTP replay interface is required in this freeze. Storage plus backend/internal maintenance access is sufficient. Any future admin replay route must come back through `architect` as a separate contract request rather than piggybacking on `/chat/*`.

Frozen replay package boundary:

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

What may be stored:

- answer-boundary policy and verdict facts needed to explain why the assistant answered, degraded, or escalated the way it did
- bounded execution provenance such as `governance_version`, sanitized `model_name`, tool-plan source, cache/fallback state, and latency/count facts
- the same bounded `context_budget_summary` lane metrics already allowed for audit
- bounded tool-result summaries with stable tool names, compact status, bounded counts, limited quality metadata, and stable source refs
- RAG provenance references only, such as source label plus optional page, chunk index, and optional page range

What must not be stored:

- raw query text, raw assistant reply text, prompt text, planning messages, or any full-context reconstruction payload
- large RAG text, retrieved passage text, citation snippets, or raw vector-store chunk bodies
- raw tool results, tool arguments, provider-native tool payloads, or open-ended tool debug blobs
- raw OCR text, raw report payloads, raw risk snapshots, profile dumps, or any unsanitized medical payload
- copied `ChatMessage.content`; replay rows must reference the existing assistant message rather than duplicating its text

Current runtime conflicts called out explicitly for implementation planning:

- [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) currently has no internal replay table and therefore cannot persist a bounded assistant-turn replay package separately from `ChatMessage` and `AgentAuditEvent`.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) already computes the needed policy, verdict, context-budget, tool, and RAG-reference inputs, but it does not yet materialize a distinct replay row linked to the finalized assistant message and audit row.
- [backend/services/conversation_service.py](E:\health_ai_platform_2.0\backend\services\conversation_service.py) currently replays only `ChatMessage` metadata to `/chat/conversations/{conversation_id}/messages`; it must stay that way and must not silently expose the new internal replay bundle.
- [backend/api/api_v1/endpoints/chat.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\chat.py) currently freezes only public chat and history payloads; it must not grow a replay/admin surface in this slice.
- [backend/services/agent_audit.py](E:\health_ai_platform_2.0\backend\services\agent_audit.py) already sanitizes bounded responsibility fields, but BE still needs a companion bounded sanitizer for replay-specific `tool_result_summary` and `rag_source_refs`.

### 3.2.3 Human Takeover Boundary

This slice adds a backend-owned human-takeover projection for turns where the backend decides that the answer must be handed off to a human reviewer or clinician. It is not a workflow engine, ticketing system, or disclaimer replacement.

Architecture rules:

- The takeover contract is additive and backend-owned. FE may render it, but FE may not invent new medical meaning, new escalation states, or new handoff channels from surrounding text.
- The takeover object is the only contract in this slice that may explicitly say whether a turn crossed the human-handoff boundary.
- The backend must use the same takeover shape in `POST /chat/send`, `POST /chat/stream` final payloads, and stored conversation replay.
- Partial SSE status/tool events must not emit takeover data.
- A missing takeover object means the backend did not choose to surface a human-handoff semantic for that turn.

Frozen takeover payload:

```json
{
  "schema_version": "takeover.v1",
  "status": "required",
  "trigger_reason": "high_risk",
  "summary": "Backend-owned handoff summary explaining why human review is required."
}
```

Required fields:

- `schema_version`
- `status`
- `trigger_reason`
- `summary`

Field semantics:

- `schema_version` is the takeover-envelope version. New writes must use `takeover.v1`.
- `status` is the backend decision about whether the turn should surface a human-handoff UI. Frozen values are `required` and `suppressed`.
- `trigger_reason` is the backend-owned boundary classification. Frozen values are `high_risk`, `insufficient_evidence`, `boundary_false_positive`, and `boundary_not_triggered`.
- `summary` is a short backend-authored explanation of the boundary decision. It must remain neutral, bounded, and non-diagnostic.
- `status="required"` means the backend has crossed the human-handoff boundary and FE may render the takeover surface.
- `status="suppressed"` means the backend explicitly evaluated takeover and chose not to surface it. FE must not synthesize a hidden handoff state from other metadata.
- `trigger_reason="high_risk"` means the turn crossed the high-risk boundary, typically because the backend classified the situation as urgent or clinically unsafe to leave as a normal answer.
- `trigger_reason="insufficient_evidence"` means the turn crossed the evidence boundary, typically because the backend could not answer safely with the available evidence.
- `trigger_reason="boundary_false_positive"` means the backend detected a near-hit but vetoed it as a false positive.
- `trigger_reason="boundary_not_triggered"` means the backend evaluated the turn and concluded that no takeover boundary was crossed.

Consistency rules:

- `takeover.status="required"` must align with the backend-owned human-handoff subset. `response_verdict.human_escalation_required=true` is broader than takeover and does not by itself require takeover; ordinary disclaimer or refusal turns may still set `human_escalation_required=true` without surfacing takeover.
- `takeover.trigger_reason="high_risk"` must align with the urgent safety path, usually `decision_summary.lane="urgent_symptom"` and `response_verdict.degraded_reason="urgent_risk_detected"`.
- `takeover.trigger_reason="insufficient_evidence"` must align with a degraded evidence path, usually `response_verdict.evidence_sufficiency="insufficient"` and an evidence-related degrade reason.
- `takeover.status="suppressed"` must not be used by FE to infer a hidden clinical state; it is simply a backend boundary outcome.
- `evidence_panel` may support the takeover decision with evidence provenance, but it does not own takeover semantics.
- `suggestion_card` remains an ordinary guidance card. It must not be repurposed into a human-handoff workflow, ticket, or disclaimer substitute.
- When the backend emits takeover, the same object must be visible in send, stream-final, and replay responses without FE-side recomputation.

Current runtime conflicts called out explicitly for implementation planning:

- [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) still has no dedicated takeover field on `ChatMessage`.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) still emits `response_verdict`, `decision_summary`, `evidence_panel`, and `suggestion_card`, but it does not yet materialize a frozen takeover object across finalize paths.
- [backend/api/api_v1/endpoints/chat.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\chat.py) and [backend/services/conversation_service.py](E:\health_ai_platform_2.0\backend\services\conversation_service.py) still replay only the existing assistant metadata set, so they must grow the takeover field in lockstep if BE implements the new contract.

### 3.3 AI/Data Runtime

- Model/training assets: `ai_core/*.py`
- ETL assets: `backend/etl/*.py`
- Knowledge base retrieval: [rag_service.py](E:\health_ai_platform_2.0\backend\services\rag_service.py)
- OCR parsing: [ocr_service.py](E:\health_ai_platform_2.0\backend\services\ocr_service.py)
- Chat orchestration: [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py)

AI/data responsibilities:

- Maintain training assets and ETL pipelines
- Provide runtime inference dependencies to backend services
- Maintain vector-store-backed retrieval for Dr. AI
- Support OCR parsing pipeline and health-risk engines

### 3.4 RAG Knowledge-Base Construction Boundary

Knowledge-base rebuilding is an internal backend/data maintenance task. It is not a public chat feature and does not change the `/chat/send` or `/chat/stream` API contracts.

Rules:

- Continue to use `RecursiveCharacterTextSplitter`; do not introduce semantic chunking, embedding-driven chunking, or LLM-assisted chunking.
- Recommended default chunking profile for Chinese medical PDFs: `chunk_size=800`, `chunk_overlap=120`, `length_function=len`, and separators in this order: `["\n\n", "\n", "。", "！", "？", "；", "：", "，", "、", " ", ""]`.
- Chunking should prefer Chinese sentence and clause boundaries first, then whitespace, then character fallback.
- Each chunk must preserve stable source provenance for internal retrieval and citation assembly.
- Minimum internal chunk metadata: `source`, `page`, `chunk_index`.
- Optional internal chunk metadata: `section_title`, `page_range`.
- `page_range` may be present when a chunk spans multiple pages or when the loader emits merged page slices; it is not a substitute for the required `page` field.
- Rebuilds may refresh the vector store, but must remain idempotent and must not widen retrieval behavior into a new public API surface.
- The current retrieval contract in `rag_service.search_context` stays backend-internal; public-facing chat behavior remains unchanged.

### 3.4.1 Query-Time RAG Quality Boundary

Query-time retrieval may produce a backend-only quality summary alongside the text context. This is runtime metadata for chat-time gating and replay accountability, not a public API surface and not a new persisted KB artifact.

Minimum quality signals:

- `retrieval_status`: `ok`, `empty`, `unavailable`
- `hit_count`: number of attributable retrieved chunks
- `unique_source_count`: number of distinct stable sources among the retrieved chunks
- `source_kind`: `pdf_text`, `ocr_text`, `mixed`, `unknown`
- `density_status`: `normal`, `low_density`, `unknown`
- `ocr_fallback_state`: `available`, `degraded`, `unavailable`, `unknown`
- `provenance_state`: `full`, `partial`, `missing`
- `chunk_quality`: `strong`, `mixed`, `weak`, `empty`

Semantics:

- `retrieval_status="ok"` means at least one attributable chunk was found.
- `retrieval_status="empty"` means the retriever ran but returned no attributable chunks.
- `retrieval_status="unavailable"` means the vector store, loader, OCR dependency, or other retrieval dependency prevented a trustworthy result.
- `source_kind` is inferred from existing chunk metadata and `ocr_touched`; it must not introduce a new corpus taxonomy.
- `density_status` may be informed by build-time corpus diagnostics such as low-density coverage, blank-page ratio, and short-chunk ratio, but the runtime only stores the bounded status, not the diagnostic trace.
- `ocr_fallback_state` is based on `describe_ocr_fallback_capability()` and actual OCR-touch behavior, not raw OCR payloads or exception bodies.
- `provenance_state="full"` requires the chunk metadata floor (`source`, `page`, `chunk_index`) and preserves optional `section_title` / `page_range` hints when present; `partial` means the floor exists but optional hints are incomplete; `missing` means provenance cannot be trusted.
- `chunk_quality` is the aggregate summary used by chat runtime. `strong` may support sufficient evidence when the lane is otherwise safe. `mixed` or `partial` provenance must cap the turn at conservative or limited behavior. `weak` or `empty` must not be used to justify a confident answer.
- These signals may only tighten `decision_summary.policy.evidence_state`, `decision_summary.policy.degrade_reason`, and `decision_summary.policy.disclaimer_mode`. They must not change `lane`, `verdict`, or any public route shape.
- Runtime-only details such as per-hit similarity scores, raw retrieved passages, reranker traces, vector-store ids, OCR exception payloads, and full benchmark dumps are not part of this contract.
- If downstream storage needs accountability, only the bounded summary may be carried forward into audit/replay.

Non-goals:

- no new `/chat/*` field, route, SSE event, or retrieval endpoint
- no public citation/filter/rebuild API
- no raw passage text, per-hit score storage, or benchmark-report exposure
- no `ai-data` contract change is required for this freeze because the KB build and OCR boundaries remain in place and only the runtime contract is being frozen

## 4. Module Boundaries

### 4.1 Frontend Boundary

`frontend/src` owns route composition, page composition, local UI state, and API invocation patterns.  
Frontend must not redefine response shapes or create hidden fallback business rules that contradict backend-owned logic.

For the approved C3 evidence panel plan, frontend may decide presentation state such as collapsed versus expanded rendering, but it must not regroup evidence into new semantic buckets or rewrite backend-authored section copy.

### 4.2 Backend Boundary

`backend/main.py` currently contains both route definitions and some orchestration glue.  
For architecture purposes, the backend boundary is:

- Routes and auth at the API layer
- Persistence and entity semantics in SQLModel models
- Domain behavior in `backend/services`

The current controlled Agent runtime is owned by `chat_service`, `conversation_service`, `agent_tools`, `agent_safety`, and `agent_audit`.

The current implementation is not fully separated yet, but the contract assumes business semantics remain backend-owned.

For assistant evidence presentation, backend owns:

- which evidence lanes become compact chips
- which evidence details are elevated into the single expanded `evidence_panel`
- section ordering, section copy, and source-reference attribution
- persistence and replay of the same assistant metadata across live send, stream-final, and stored-history flows

### 4.3 AI/Data Boundary

`ai_core`, `backend/etl`, and model-backed services own:

- Feature engineering assumptions
- Retrieval/index assets
- OCR parsing behavior
- Risk-engine and simulation dependencies

They do not own the public HTTP contract or the user-facing UX semantics.

## 5. Primary Data Flows

### 5.1 Authentication And Profile Bootstrap

1. Frontend calls `/auth/token`
2. Backend returns bearer token
3. Frontend calls `/user/me`
4. Frontend calls `/user/profile`
5. Pinia stores hydrate user and health state

### 5.2 OCR Intake Flow

1. User uploads PDF/image from clinical flow
2. Backend persists uploaded file to `uploads/medical_reports`
3. Backend creates `MedicalDocument`
4. OCR service extracts text
5. LLM parsing or regex fallback builds structured data
6. OCR summary is stored on the document record as persisted extraction payload, with canonical `ocr_summary.v1` now frozen as the target write shape for future backend normalization work
7. Frontend can merge extracted fields into user profile

### 5.2.1 Platform CSV Profile Import Flow

This slice adds a second structured intake path beside OCR. It is a platform-standard profile import, not a raw Synthea CSV ingestion pipeline.

1. Frontend shows a CSV upload control next to the existing `智能识别体检单` OCR control in `ClinicalView.vue`; the CSV control must visually match the OCR button treatment.
2. User uploads one platform-standard profile CSV.
3. Frontend sends the file to `POST /api/v1/profile/import-csv` as multipart field `file`, with optional `demo_patient_id` when the CSV contains multiple rows.
4. Backend validates that the CSV is already in platform profile units and shape.
5. Backend parses the selected row into the same field-oriented profile JSON shape used by `POST /user/profile`.
6. Backend returns the parsed profile, source tags, and import metadata only.
7. Frontend fills the clinical profile form from the returned profile.
8. Existing profile save behavior remains the only persistence path for the imported profile values.

Architecture rules:

- The import endpoint must not persist `UserProfile`, `HealthRecord`, or `MedicalDocument` rows.
- The accepted CSV is the future `platform_demo_profiles.csv`-style export compatible with `data/demo/platform_demo_profiles*.json`; it is not arbitrary raw Synthea multi-file CSV.
- Units must already be platform units. Unit conversion remains an upstream demo-data generation concern, not an import-route behavior.
- Missing CSV cells remain absent or `null`; FE and BE must not fabricate defaults to complete the form.
- CSV-imported values may be treated as `recognized` imported structured source values if field-state metadata is implemented, using a backend-owned source label such as `platform_csv_import`.
- Existing OCR upload, document persistence, and `ocr_summary.v1` contracts are unchanged.

### 5.3 Risk Analysis Flow

1. Frontend submits profile and optional SNP data
2. Backend composes clinical + profile context
3. Fusion/risk engines calculate comprehensive risk
4. Frontend renders risk result and explanations

### 5.4 Chat Flow

1. User sends message to `/chat/send`
2. Backend gathers profile context
3. RAG service searches Chroma vector store
4. Chat service builds a bounded context payload and trims each evidence lane to a fixed token budget
5. Recent conversation history is also trimmed to a separate retained-history budget before prompt assembly
6. Chat service performs a native tool-calling planning pass when supported by the provider/model configuration
7. If native tool calls are unavailable or omitted, the backend falls back to deterministic local read-only tool planning
8. Tool evidence is merged into the final bounded prompt before the answer generation call
9. While tools run, the streaming path emits concrete tool start/finish events in addition to coarse status phases
10. Response returns with source references, structured Agent metadata, an optional structured health suggestion card, and an optional backend-owned `evidence_panel`
11. Redis cache stores response; profile-changing actions invalidate user cache

### 5.4.1 Frozen Medical Risk Routing Matrix

This architecture pass freezes the chat runtime into exactly six backend-owned lanes:

- `general_health`
- `report_interpretation`
- `trend_review`
- `medication_related`
- `urgent_symptom`
- `diagnosis_sensitive`

Lane selection, tool eligibility, output depth, degrade strategy, and care-reminder requirements are backend-owned runtime semantics. FE may render backend-provided metadata, but it may not infer, merge, rename, or restyle these lanes into a different semantic model.

| Lane | Trigger conditions | Allowed tools | Allowed output depth | Degrade / fallback strategy | Mandatory offline / in-person reminder |
|------|--------------------|---------------|----------------------|-----------------------------|----------------------------------------|
| `general_health` | Default lane for ordinary wellness, prevention, lifestyle, and non-acute "what should I pay attention to" questions when no narrower frozen lane preempts it | `get_user_profile_summary`, `get_latest_risk_report`, `recent_metric_anomaly_lookup`, `search_medical_guidelines` | `standard_bounded`: concise answer plus a few concrete next steps; no diagnosis, no medication changes | If profile, tool, or guideline evidence is weak, answer conservatively, state uncertainty, and fall back to general guidance plus `insufficient_evidence` verdict when needed | `No` |
| `report_interpretation` | User asks to explain one report, one uploaded result, or a comparison between persisted reports | `report_summary_lookup`, `report_comparison_lookup`, `get_uploaded_documents_summary`, `search_medical_guidelines` | `structured_bounded`: explain reported values, relative changes, and safe follow-up context only; no diagnosis claim | If no usable persisted report summary exists, do not invent values; state that the report context is unavailable and fall back to upload / exact-value request guidance with `insufficient_evidence` verdict | `No` |
| `trend_review` | User asks about trends, history, changes over time, or whether a metric is going up or down | `get_history_trends`, `recent_metric_anomaly_lookup`, `latest_analysis_snapshot_lookup`, `search_medical_guidelines` | `structured_bounded`: compare stored points and anomalies only; no autonomous forecasting beyond existing stored snapshots | If fewer than two usable records exist, degrade to single-point context, explicitly say trend evidence is insufficient, and emit `insufficient_evidence` when the trend question cannot be answered safely | `No` |
| `medication_related` | User asks about current medications, medication facts already present in records, or medication information tied to persisted reports | `medication_summary_lookup`, `report_summary_lookup`, `search_medical_guidelines` | `brief_bounded`: factual medication summary and safe caution language only; no start/stop, titration, substitution, or prescribing output | If no persisted medication facts exist, do not guess medication use; ask for the medication name or a report upload and fall back to `insufficient_evidence` | `No` |
| `urgent_symptom` | Acute symptom language, emergency-risk phrases, or medication-reaction language that implies immediate safety escalation | No read-only tools before the first safety response; urgent routing must not wait on RAG or tool latency | `safety_only`: immediate escalation guidance, no deep interpretation, no long-form explanation | Immediate short-circuit to urgent safety response; missing profile or report data must never delay the response | `Yes` |
| `diagnosis_sensitive` | User asks for a diagnosis, differential, certainty statement, disease confirmation/exclusion, or similarly diagnosis-like judgment from chat evidence | `get_user_profile_summary`, `report_summary_lookup`, `latest_analysis_snapshot_lookup`, `search_medical_guidelines` | `guardrail_brief`: explain limits, summarize available context, and redirect toward clinician evaluation; no diagnosis or probability-of-diagnosis output | If evidence is weak or absent, explicitly say the system cannot determine a diagnosis from current data and use `insufficient_evidence` while keeping the lane fixed | `Yes` |

Execution boundary rules for this freeze:

- `urgent_symptom` preempts every other lane and must short-circuit before RAG retrieval, native tool calling, or local fallback planning.
- `diagnosis_sensitive` preempts `general_health`, `report_interpretation`, `trend_review`, and `medication_related` when the user is asking for disease confirmation, exclusion, or diagnostic certainty rather than descriptive explanation.
- If no specialized trigger fires, the backend must default to `general_health` rather than inventing a seventh lane.
- The allowed-tool whitelist is frozen per lane. BE may refine internal ranking or argument defaults, but it may not silently widen a lane into a different tool set.
- Output depth is frozen per lane. FE may collapse or expand presentation, but it may not prompt BE to emit more aggressive semantics than the lane allows.
- Mandatory care reminders are frozen per lane. Only `urgent_symptom` and `diagnosis_sensitive` require them on every response in this slice; other lanes may include reminders conditionally, but not as a lane invariant.
- Existing public chat routes stay in place. This freeze relies on additive metadata inside the existing chat response objects, not on route, namespace, or UI information-architecture changes.

Backend-owned explicit policy envelope:

- `decision_summary.policy` is the backend-owned explicit policy object for this slice. It is additive and nested under the existing `decision_summary` runtime field rather than a new public route or top-level response contract.
- Minimum shape:
  - `policy_version`: `explicit_policy.v1`
  - `evaluation_order`: ordered lane/rule ids from highest to lowest priority
  - `selected_rule`: the first matching rule id chosen for the turn
  - `risk_level`: backend risk assessment for the selected rule, typically `low`, `medium`, or `high`
  - `evidence_state`: exactly `sufficient`, `limited`, or `insufficient`; legacy `missing` is replay-only compatibility data and must be treated as `insufficient`
  - `tool_availability`: exactly `full`, `partial`, or `none`
  - `answer_mode`: one of `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, or `urgent_care_disclaimer`
  - `disclaimer_mode`: one of `none`, `conservative`, `diagnosis_guardrail`, or `urgent_care`
  - `degrade_reason`: `null` or one of `evidence_insufficient`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `unsafe_medication_request`, `diagnosis_sensitive_request`, or `urgent_symptom`
- `policy_version` is compatibility-gated by major version. Same-major additive changes are compatible if they preserve the frozen lane/verdict meanings and keep the answer-mode set backward-compatible. Any new major version is backend-internal until architect review updates the contract.
- Rule evaluation is first-match-wins and follows the frozen priority order below.
- `selected_rule` is the question-type/routing rule id for this slice, so no separate `question_type` field is required.
- `answer_mode` is a backend runtime choice, not a FE-owned semantic model. FE may render the resulting reply, chips, and badges, but it may not reinterpret policy state as its own routing contract.
- The evidence sufficiency gate is evaluated after lane selection and before final reply generation, using all lane-relevant evidence inputs that are already available in the current runtime: profile summary, report projections, trend/history projections, knowledge-base retrieval, successful tool outputs, and blocked/empty tool outcomes.
- Source-specific sufficiency rules are frozen as follows:
  - profile evidence is usable only when at least one query-relevant user-owned health fact is available from persisted profile or latest risk/anomaly context
  - report evidence is usable only when persisted report-summary or report-comparison facts are available; document existence alone is not enough
  - trend evidence is sufficient only when at least two comparable historical points exist for the requested trend claim; a single point may support `limited` context but not a sufficient trend verdict
  - knowledge-base / RAG evidence is usable only when retrieval returns attributable guidance, and it may contextualize a reply but cannot by itself raise `report_interpretation`, `trend_review`, `medication_related`, or `diagnosis_sensitive` to `sufficient`
  - tool evidence is usable only when a tool returns `status="ok"` plus bounded factual content; blocked, empty, or non-owned results count as unavailable for the gate
- Gate precedence is frozen:
  1. `urgent_symptom` short-circuit wins immediately and does not wait for profile, RAG, or tool evidence.
  2. unresolved contradiction across user-owned or retrieved evidence forces `evidence_state="insufficient"` with `degrade_reason="conflicting_evidence"`.
  3. if the lane-specific minimum evidence floor is not met, `evidence_state="insufficient"`.
  4. if some lane-relevant evidence exists but the minimum floor is only partially met, `evidence_state="limited"`.
  5. only when the lane-specific floor is met and no material contradiction remains unresolved may `evidence_state="sufficient"`.
- Lane-specific minimum evidence floors are frozen:
  - `general_health`: at least one usable personalized source or attributable guideline support for bounded general guidance; guideline-only evidence for a personalized question is at most `limited`
  - `report_interpretation`: usable report-summary or report-comparison evidence
  - `trend_review`: at least two comparable historical records
  - `medication_related`: at least one persisted medication fact from report or profile-backed medication evidence
  - `diagnosis_sensitive`: enough bounded context to summarize available facts while refusing diagnostic certainty; this never permits a diagnosis claim
  - `urgent_symptom`: always short-circuited and therefore fixed to `evidence_state="insufficient"` for the assistant verdict path
- Hard-gate effects are frozen:
  - when `evidence_state` is `insufficient`, `answer_mode` must not be `direct_answer`
  - a conflict-driven turn must stay in its selected lane; BE must not silently switch to an easier lane just to avoid an insufficiency verdict
  - `decision_summary.verdict` may be the lane-specific success verdict only when the lane-specific evidence floor is met; otherwise non-urgent lanes must emit `insufficient_evidence` while `urgent_symptom` stays `seek_urgent_care`
  - reply text must refuse over-inference, must not invent report values / trend direction / medication use / diagnosis certainty, and must keep the response inside the frozen lane depth limit
- Reply obligations when `evidence_state != "sufficient"` are frozen:
  - explicitly state uncertainty or insufficiency
  - name the missing or conflicting evidence class, such as report data, trend history, medication facts, or attributable guidance
  - give at least one concrete next step, such as uploading a report, providing exact metric values and dates, waiting for another comparable record, supplying medication name/dose, or seeking clinician follow-up
  - include offline care escalation whenever the lane requires it, and permit a conservative clinician-review recommendation for conflict-heavy non-urgent turns
- Conflict handling is frozen:
  - user-owned profile/report/trend/tool facts outrank generic RAG guidance for deciding whether personal evidence is contradictory
  - RAG may contextualize but must not override direct user-owned measurements or persisted report facts
  - if report-vs-trend, report-vs-profile, or personal-data-vs-retrieval conflicts cannot be resolved conservatively, the system must degrade to `conflicting_evidence` instead of reconciling by guesswork
- Degrade order when evidence or tool availability is insufficient is: `direct_answer` -> `bounded_answer` -> `clarify_missing_context` -> `refusal_with_disclaimer` when the request crosses guardrails. `urgent_care_disclaimer` short-circuits ahead of that chain for urgent routing.
- `disclaimer_mode="conservative"` is used when the request is safe to answer but evidence is limited or tool availability is partial; the response must stay bounded, surface uncertainty, and avoid implied certainty.
- Refusal and disclaimer triggers are backend-owned. Typical triggers are urgent symptoms, diagnosis requests, medication start/stop/titration/substitution requests, evidence conflicts, missing evidence with a safety-sensitive request, and other unsafe requests that exceed the frozen lane guardrails.

Backend-owned response verdict envelope:

- The new assistant-reply-level verdict container is frozen as top-level `response_verdict`.
- Naming is intentional: `response_verdict` avoids colliding with the already-frozen `decision_summary.verdict`, which remains the six-lane routing-matrix result code and must not be redefined by this slice.
- `response_verdict` is additive and replay-safe. It is not nested under `decision_summary`, and there is no alternate top-level alias such as `verdict`, `answer_verdict`, or `final_verdict`.
- Minimum shape for every new assistant reply:
  - `schema_version`: `response_verdict.v1`
  - `response_mode`: one of `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, or `urgent_care_disclaimer`
  - `medical_risk_level`: one of `low`, `medium`, or `high`
  - `evidence_sufficiency`: one of `sufficient`, `limited`, or `insufficient`
  - `human_escalation_required`: boolean
  - `degraded_reason`: `null` or one of `insufficient_evidence`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `policy_guardrail`, or `urgent_risk_detected`
- Coexistence rules:
  - `decision_summary.verdict` remains the lane/result code from the frozen routing matrix.
  - `decision_summary.policy` remains the explicit policy-engine trace envelope.
  - `response_verdict` is the backend-owned answer-level summary for the emitted assistant reply and must not silently redefine either existing field.
- Consistency rules:
  - `/chat/send`, `/chat/stream` final payloads, cache-hit final payloads, and persisted assistant-message replay must use the same container name `response_verdict` and the same field meanings.
  - For one stored assistant turn, replay should return the same `response_verdict` object that was emitted live rather than recomputing or translating it from newer runtime heuristics.
  - When `decision_summary.policy` exists, backend implementation should derive `response_verdict` from the same policy evaluation so `response_mode` / risk / degrade state do not drift across channels.
  - `response_verdict.evidence_sufficiency` maps 1:1 from `decision_summary.policy.evidence_state`: `sufficient` -> `sufficient`, `limited` -> `limited`, `insufficient` -> `insufficient`; new turns must never emit `missing`
- Compatibility rules:
  - legacy assistant rows may lack `response_verdict`; replay must remain valid and must not fail because of that omission
  - backend historical replay must not fabricate `response_verdict` for legacy rows by guessing from `decision_summary.verdict`, `reply`, or tool names
  - for legacy rows without the new object, `decision_summary.verdict` and `decision_summary.policy` (if present) remain the backward-compatible metadata surface
  - if historical debugging or replay surfaces a legacy `decision_summary.policy.evidence_state="missing"`, it is a legacy synonym for `insufficient`; BE must not persist or emit that legacy value on new assistant turns
- `human_escalation_required=true` means the assistant answer requires offline human follow-up as part of its safe boundary. It is mandatory for `urgent_symptom` and `diagnosis_sensitive`, and may also be true for medication-guardrail refusals.
- `degraded_reason` is public answer-boundary metadata, not a dump of backend-internal policy details. If multiple degrade causes apply, the backend should expose one dominant reason with this priority: `urgent_risk_detected` -> `policy_guardrail` -> `conflicting_evidence` -> `tool_unavailable` -> `missing_required_context` -> `insufficient_evidence`.
- Non-goals for this slice:
  - no new chat request field, route, or SSE event type
  - no FE-owned reinterpretation of lane, policy, or verdict semantics
  - no requirement to backfill or recompute legacy chat rows before replay works
  - no rewrite of the existing chat runtime beyond freezing this additive assistant-metadata contract

Frozen rule priority:

1. `urgent_symptom`
2. `diagnosis_sensitive`
3. `medication_related`
4. `trend_review`
5. `report_interpretation`
6. `general_health`

Backend implementation pressure called out explicitly:

- [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) currently plans tools by keyword and emits open-ended `intent` values through `_infer_intent()` and `_build_decision_summary()`; BE must replace or wrap that logic so the runtime emits the frozen `lane` and `verdict` semantics without changing the public chat routes.
- [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) currently lets `_plan_tools()`, `_build_suggestion_card()`, `_build_evidence_panel()`, and tool-status text evolve around intent keywords instead of lane ownership; those branches must be aligned to the six frozen lanes so evidence labels, cards, and depth do not drift independently.
- [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) now emits top-level `response_verdict`, but the evidence gate still needs one frozen implementation of `sufficient` / `limited` / `insufficient` plus conflict detection across profile/report/trend/RAG/tool evidence; BE must align the runtime without changing routes or field names.
- [agent_safety.py](E:\health_ai_platform_2.0\backend\services\agent_safety.py) currently carries duplicated `evaluate_chat_policy()` logic and legacy sufficiency drift; BE must collapse that drift to one backend-owned evaluator that emits only the frozen states and reasons.
- [agent_tools.py](E:\health_ai_platform_2.0\backend\services\agent_tools.py) already exposes the read-only tools needed for the frozen lanes, but BE must enforce lane-level tool gating or an equivalent backend-owned whitelist so prompt wording cannot silently widen tool use beyond the approved matrix.
- [chat.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\chat.py) and [models.py](E:\health_ai_platform_2.0\backend\models.py) already expose replay-safe `response_verdict` metadata, so BE must preserve that compatibility while implementing the stricter evidence sufficiency gate and any additive `conflicting_evidence` reason.
- No route contract change is strictly required for this freeze. If implementation later needs a new request field, new route, or direct tool API to realize the lane matrix, that is contract pressure and must return through `architect`.

QA coverage expectations for this freeze:

- Normal consultation coverage must prove `general_health` stays non-diagnostic, uses only the allowed tool set, and degrades to conservative guidance when evidence is thin.
- Urgent symptom coverage must prove `urgent_symptom` short-circuits before tool or RAG work, emits the urgent verdict, and always includes the mandatory care reminder.
- Medication coverage must prove `medication_related` stays factual, uses only the medication/report/guideline tools, and never emits start/stop or dose-change advice.
- Diagnosis-sensitive coverage must prove diagnosis-seeking prompts route to `diagnosis_sensitive`, avoid diagnosis claims, and always include the mandatory clinician / in-person reminder.
- Insufficient-evidence coverage must prove each non-urgent lane can emit its own fallback verdict without switching to a different lane or fabricating missing medical facts.
- Conflict-evidence coverage must prove contradictory personal evidence or weak-retrieval disagreement degrades through `conflicting_evidence`, keeps the selected lane, and recommends clarification or clinician follow-up instead of reconciling by guesswork.

### 5.4.2 C3 Evidence Panel Boundary

The approved C3 evidence panel plan keeps the current hybrid UI direction:

- compact evidence chips remain visible inline with the assistant message
- one expanded block may render sectioned evidence detail for the same assistant message
- the assistant free-text `reply` remains primary and must not be replaced by the panel

Architecture rules for this freeze:

- `evidence_panel` is assistant-message metadata authored by the backend, not derived by the frontend
- `evidence_panel` is additive to `sources`, `evidence_tags`, `decision_summary`, and `suggestion_card`; it does not remove those fields in this freeze
- `evidence_panel.sections[*].source_items` is the renderable source-detail drill-down layer for each expanded section
- each source item is bounded and backend-authored, with `source_type`, `title`, `snippet`, a `timestamp` field, and optional `confidence` or `relevance`; `timestamp` may be `null` when no reliable capture time is available
- initial `source_type` values are limited to `profile`, `trend`, `report`, and `guideline`
- source items must contain safe summaries only; they may not embed raw large JSON payloads or unbounded tool dumps
- `/chat/send`, `/chat/stream` final payloads, and historical replay must converge on the same assistant metadata contract
- the current chat UI may safely ignore `evidence_panel` until FE implementation lands; contract safety comes from additive optionality rather than parallel shapes
- FE and BE must escalate any later shape change for `evidence_panel`, `evidence_tags`, or replay semantics back through `architect`

Current runtime conflict called out explicitly:

- repository code now persists and replays `evidence_panel`, but FE and BE must still treat the backend-owned chip and section semantics as frozen and non-redefinable without architect review
- `backend/rag/build_kb.py` still needs internal chunk metadata enrichment for `page` and `chunk_index`; that enrichment must stay behind the KB build boundary and must not change the public chat contract

### 5.4.3 Next Safe Read-Only Tool Expansion Slice

This architecture pass freezes the next additive read-only tool slice for the provider-native function-calling path. The user-visible goal is better factual retrieval from already-persisted personal health data without introducing write actions, autonomous follow-up behavior, or any new public chat API surface.

Approved tools in this slice:

- `medication_summary_lookup`
- `recent_metric_anomaly_lookup`
- `report_comparison_lookup`

Architecture rules for this slice:

- All three tools are backend-internal chat-runtime tools, not public REST endpoints.
- Public chat routes remain `POST /chat/send` and `POST /chat/stream`; tool invocation stays behind the existing backend chat orchestration boundary.
- Tool registration, parameter schemas, and provider-facing function definitions remain backend-owned through the internal tool registry and `get_tool_definitions()` path.
- All three tools are `read_only=true` and `scope=self_only`; they may only read the authenticated user's persisted state.
- Tool outputs are retrieval and summarization artifacts only. They must not create, update, delete, or queue any medical action.
- FE and BE may not silently rename these tools, widen their scope, or reshape their parameters/results once implemented. Any contract pressure must return through `architect` via `orchestrator`.
- If a future product request wants direct REST exposure, explicit chat-tool selection controls, or any other public API expansion, that is contract pressure and must come back through `architect`; this slice does not authorize it.

Tool intent boundaries:

- `medication_summary_lookup`: fetch a bounded medication summary from already-persisted medication facts and expose it as a factual summary object without prescribing, titrating, or changing treatment.
- `recent_metric_anomaly_lookup`: return a bounded list of recent metric anomalies derived from persisted profile/history data using the existing anomaly-detection semantics; it is for recall and explanation, not diagnosis.
- `report_comparison_lookup`: compare two user-owned persisted report summaries as a bounded normalization-only summary. It is for side-by-side recall, not raw report export or free-form multi-document diffing.

Evidence and source mapping boundaries:

- `medication_summary_lookup` may map into backend-stable `source_ref` labels that point to the report or profile facts it summarizes, and it may expose `source_type` values only from the existing `report` and `profile` set.
- `recent_metric_anomaly_lookup` may map into backend-stable `source_ref` labels for either `health_record`-derived or `profile`-derived metric inputs, and it may expose `source_type` values only from the existing `trend` and `profile` set.
- `report_comparison_lookup` may map into backend-stable `source_ref` labels for the two compared reports, and it may expose `source_type` values only from the existing `report` set.
- Tool-derived `evidence_tags`, `sources`, and `evidence_panel` content must be authored by the backend through stable mappings; FE must not invent new refs or reinterpret tool outputs as new semantic buckets.

Read-only tool evidence metadata:

- The approved read-only tool slice uses an additive backend-authored metadata envelope to describe result quality without inflating the business payload.
- The envelope is separate from the tool's factual result body. It is not a raw dump, not a confidence blob, and not a replacement for the existing applicability or sufficiency checks.
- The shared metadata fields are:
  - `freshness`: `fresh`, `recent`, `stale`, or `unknown`
  - `coverage`: `full`, `partial`, `empty`, or `unknown`
  - `confidence`: `high`, `medium`, `low`, or `unknown`
  - `missing_fields`: ordered backend-stable field labels that were not available for the bounded projection
  - `comparable_fields_count`: non-negative integer count of comparison-aligned fields or points that actually participated in the bounded projection; `null` or omitted when not applicable
- `freshness` describes the source recency of the bounded projection, not the age of the full raw dataset.
- `coverage` describes how much of the requested bounded answer the tool could safely cover; `empty` means the tool could not produce a usable bounded projection.
- `confidence` is a qualitative trust rating for the bounded projection after considering freshness, coverage, and conflict pressure. Empty, stale, or conflicting projections must never be labeled `high`.
- `missing_fields` must name normalized backend-owned field labels, not raw OCR keys, raw payload keys, SQL column names, or prompt text.
- `comparable_fields_count` is only meaningful when the tool actually compares aligned evidence units. It must not be used as a proxy for certainty or completeness.

Tool metadata bundles:

- `summary_min`: `freshness`, `coverage`, `confidence`, and `missing_fields` when `coverage` is not `full`
- `comparison_min`: `summary_min` plus `comparable_fields_count`
- `none`: the tool does not need the metadata envelope for this slice
- `summary_min` is the default for single-source summary, anomaly, snapshot, and document inventory tools.
- `comparison_min` is required for pairwise comparison tools and other bounded comparison tools that need an explicit alignment count.
- The chat runtime may observe the metadata envelope for transparency and boundary logging, but the existing tool `status`, `has_*`, `count`, `items`, `shared_metric_count`, `evaluated_source`, and `captured_at` fields remain the authoritative inputs for evidence sufficiency.

Backend-owned tool gating:

- pre-execution applicability checks are hard checks, not prompt hints
- post-execution sufficiency checks are hard checks, not model self-restraint
- the backend must enforce both checks inside the service layer before it emits the final medical answer
- pre-check failures use the existing tool-result envelope fields `status` and `reason`; post-check failures use the existing policy and verdict envelopes
- no new tool name, parameter, result shape, public route, or frontend policy surface is introduced by this slice
- dominant degrade reason priority stays `urgent_risk_detected` -> `policy_guardrail` -> `conflicting_evidence` -> `tool_unavailable` -> `missing_required_context` -> `insufficient_evidence`

Applicability and sufficiency rules:

- if a tool is not applicable to the selected lane or the question type, the backend must block it before execution
- if a tool is self-only and the target user is not the authenticated user, the backend must block it before execution
- if required arguments are missing or invalid, the backend must block it before execution
- if the tool returns `status="ok"` but the payload is empty, weak, or mismatched to the current lane, the backend must still treat the result as insufficient evidence
- if evidence is contradictory, the backend must preserve the selected lane and degrade through `conflicting_evidence` rather than silently reconciling by guesswork
- if the post-check decides the answer is not sufficiently supported, the backend must stop short of unsupported medical explanation and stay within the bounded or clarifying reply modes already frozen elsewhere in the contract

Applicability matrix:

| Tool | Applicability prerequisites | Forbidden / not-applicable scenarios | Pre-check failure fallback | Post-check sufficiency rule | Required metadata bundle |
|------|-----------------------------|--------------------------------------|----------------------------|-----------------------------|--------------------------|
| `get_user_profile_summary` | Current authenticated user has a usable profile and the turn needs current personal facts | Cross-user access, report-only explanation, medication change requests, urgent symptom triage, diagnosis certainty requests | Block before execution and return the existing blocked/error envelope with a backend-owned reason such as `missing_required_context` or `tool_not_allowed_for_lane` | Profile facts can support bounded general-health context, but they do not authorize diagnosis certainty or override stronger report/trend evidence | `summary_min` |
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
- when the evidence gate is not satisfied, the backend must emit the existing degrade signals and stop at the bounded answer or clarification boundary rather than continuing with unsupported medical explanation

Current runtime conflicts called out explicitly for implementation planning:

- [backend/services/agent_tools.py](E:\health_ai_platform_2.0\backend\services\agent_tools.py) already registers the earlier tool set plus the frozen read-only expansion tools, but the runtime still needs explicit applicability hard checks, lane-aware fallback handling, and post-execution sufficiency enforcement.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) currently hard-codes planner heuristics, status text, evidence-tag mapping, and evidence-panel labels for the earlier tool names and must align those branches to the frozen applicability and sufficiency gates.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) already knows how to expose provider-native function schemas generically, so no public route change is required, but BE still needs to keep tool selection and degraded reply behavior consistent with the frozen hard checks.
- [backend/services/analysis_service.py](E:\health_ai_platform_2.0\backend\services\analysis_service.py) already provides anomaly-detection logic that backs `recent_metric_anomaly_lookup`, but the runtime still needs to treat empty or weak anomaly results as insufficient evidence when the lane does not support them.
- [backend/services/payload_normalization.py](E:\health_ai_platform_2.0\backend\services\payload_normalization.py) already normalizes OCR summaries, but the runtime still needs to project bounded medication summary and pairwise report comparison views through the frozen tool gates.
- [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) has no dedicated medication entity. `medication_summary_lookup` therefore continues to depend on normalized OCR-backed facts plus a stable `UserProfile.extra_data` fallback rather than a new storage model in this architecture-only pass.

### 5.5 Conversation History Flow

1. Frontend loads `/chat/conversations` to display recent sessions
2. Backend derives session summaries from `ChatConversation` plus latest `ChatMessage`, and can filter by `query` and `archived`
3. Backend orders the active list with pinned sessions first and recently accessed sessions next
4. Backend also emits derived `group_key` and `group_label` metadata so the frontend can render sidebar section headers without changing the underlying flat list or sort order
5. Frontend can pin/unpin, archive, restore, or manually rename a stored session without deleting its messages
6. Frontend selects a stored session and loads `/chat/conversations/{conversation_id}/messages`
7. Backend replays persisted messages in sequence order for that user-owned conversation and refreshes `last_accessed_at`
8. Persisted assistant metadata is replayed alongside stored message text when available
9. New sessions are still created lazily on the first `POST /chat/send`
10. Internal postmortem replay for one assistant answer turn is served from `AgentAnswerReplay`, not from the public conversation-detail payload

### 5.5.1 Batch Archive Preparation

Batch archive is a conservative additive extension of the existing archive state model.

Architecture rules:

- Batch archive preparation works only against the existing flat `ChatConversation` list model.
- The frontend may hold selected conversation ids locally, but it does not gain a new persisted grouping or bulk state model.
- The backend stays responsible for validating ownership and applying archive state row by row.
- Batch archive updates the same `archived_at` field used by the current single-item archive flow.
- Batch delete, hard delete, and message purge remain explicitly out of scope for this freeze.
- Single-item archive and restore behavior stay intact and continue to be the canonical fallback for any one-off row action.

### 5.5.2 Batch Restore Hooks

Batch restore is a conservative additive extension of the existing single-item restore and batch archive model.

Architecture rules:

- Batch restore preparation works only against the existing flat `ChatConversation` list model, typically from the archived-session view exposed through the existing `archived=true` query.
- The frontend may hold selected conversation ids locally, but it does not gain a new persisted grouping, folder, or bulk state model.
- The backend stays responsible for validating ownership and applying restore state row by row.
- Batch restore clears the same `archived_at` field used by the current single-item restore and batch archive flows.
- Batch restore does not mutate `pinned_at`, `last_accessed_at`, `title`, or derived grouping metadata; restored rows simply return to the existing active-session list under the current backend ordering rules.
- Batch delete, hard delete, and message purge remain explicitly out of scope for this freeze.
- Single-item restore behavior stays intact and continues to be the canonical fallback for any one-off row action.

### 5.6 History And Trend Flow

1. Profile updates create `HealthRecord` snapshots
2. Frontend reads history list and trend endpoints
3. Timeline view renders time-series progression and comparative views

### 5.7 Lifestyle Digital Twin Demo Engine Flow

The next behavior/vision demo slice is frozen as a presentation and interpretation engine, not as real device ingestion. Its product role is to replay a realistic "one patient day" that combines coarse behavior events, visual food-recognition events, and optional lifestyle context so the Lifestyle view can demonstrate a behavior-aware digital twin without pretending that demo data came from a live wearable or camera stream.

Approved flow:

1. BE exposes read-only demo scenario routes under `/api/v1/demo/behavior-scenarios`.
2. FE fetches a scenario list and one selected scenario, then replays the returned timeline locally.
3. FE may render the scenario alongside existing Lifestyle/IoT and food-vision UI patterns, but it must visibly distinguish demo replay from live Bluetooth/device state.
4. FE may submit an optional `lifestyle_context` object to `/analyze/comprehensive` when the user explicitly runs analysis from a demo scenario.
5. BE validates `lifestyle_context` and may use it only as an explanatory or heuristic modifier context for `analysis_context` and compatible `risk_report.breakdown` fields.
6. No demo scenario read, timeline replay, food event, or lifestyle-context analysis may create `IoTHealthData`, `HealthRecord`, `MedicalDocument`, saved profile fields, or real IoT sync records.

Ownership:

- `fe` owns replay controls, timeline visualization, and demo/live labeling.
- `be` owns scenario read APIs, schema validation, authentication, and read-only source loading.
- `ai-data` owns scenario artifact generation if new JSON/CSV demo assets are needed.
- `qa` owns browser validation for replay, labels, route behavior, and no-persistence evidence.

Relationship to existing surfaces:

- The current `LifestyleView` may be reused, but demo replay must not call `/api/v1/iot/sync/batch` or mutate the existing `iotData` store in a way that looks like a connected device.
- Existing `/analyze/food_image` remains the live/uploaded food vision endpoint. Demo food events use the frozen `diet_vision_event.v1` artifact shape and do not upload image bytes unless a future contract explicitly adds that behavior.
- Existing generated demo profile files in `data/demo` remain valid upstream context. The behavior-day scenario artifact is additive and should reference existing `demo_patient_id` values rather than rewriting platform profile CSV semantics.

### 5.8 Lifestyle Behavior Day Upload Flow

This slice extends the Lifestyle Digital Twin experience from static demo replay to user-supplied, platform-standard one-day behavior files. The upload flow is backend-owned for parse and validation so CSV/JSON interpretation, provenance labeling, timeline construction, and `/analyze/comprehensive` handoff semantics stay stable across FE and later device integrations.

Approved flow:

1. FE presents a Lifestyle import control for platform-standard `.csv` and `.json` behavior-day files.
2. FE submits the selected file to a new authenticated parse-only backend route under `/api/v1/lifestyle/import-behavior-day`.
3. BE validates file type, size, encoding, one-patient/one-day scope, event taxonomy, event times, payload shape, and source provenance.
4. BE returns a non-persisted `behavior_day_scenario.v1`-like object plus `lifestyle_context.v1`, both labeled `data_mode="user_uploaded"` and `source_provenance.source_type="user_uploaded"`.
5. FE renders the returned timeline with a visible user-upload provenance label and keeps the existing `/api/v1/demo/behavior-scenarios` fallback available when no upload is present or validation fails.
6. FE may submit the returned `lifestyle_context.v1` to `/analyze/comprehensive` only when the user explicitly runs analysis from the imported preview.
7. BE may use the uploaded lifestyle context as explanatory heuristic context, but must not persist the upload, parsed events, derived context, or analysis output as IoT, profile, health-history, medical-document, or risk-snapshot state.

Ownership:

- `be` owns file parsing, validation, response shaping, no-persistence behavior, and analysis-context validation.
- `fe` owns upload controls, user-readable validation display, fallback selection, provenance labels, and the real-device placeholder presentation.
- `ai-data` does not need to retrain models or generate new training assets for this slice; it may advise on platform-standard sample files only if routed by the orchestrator.
- `qa` owns upload success/failure, fallback, provenance, and no-persistence evidence after FE/BE implementation.

Real-device placeholder boundary:

- FE may show a disabled or clearly marked real-device API placeholder in the Lifestyle page.
- This slice does not add a live wearable, BLE, Health Connect, Apple Health, cloud vendor, background sync, or real-device import route.
- The placeholder must not call `/api/v1/iot/sync/batch`, must not emit `data_mode="real_device"`, and must not claim live sync readiness.
- Any future real-device upload/import/sync route requires a separate architect contract and orchestrator gate.

Relationship to existing surfaces:

- The existing demo scenario routes remain read-only fallback and quick-start sample paths.
- The upload route must not be implemented by reusing `/api/v1/demo/behavior-scenarios` as a write route.
- The upload route must not be implemented by routing parsed events through `/api/v1/iot/sync/batch`, `/analyze/food_image`, profile save, document upload, health history, or risk snapshot persistence.
- The response may reuse `behavior_timeline_event.v1`, `diet_vision_event.v1`, and `lifestyle_context.v1` shapes, but must change provenance to user-uploaded source semantics rather than simulated demo semantics.

## 6. Persistence Model At A High Level

The current architecture relies on SQLModel entities persisted to the local SQLite database in the repository:

- `User`
- `UserProfile`
- `HealthRecord`
- `MedicalDocument`
- `IoTHealthData`
- `FamilyLink`
- `FamilyInvite`

For the current P0 contract freeze, only `User`, `UserProfile`, `HealthRecord`, and `MedicalDocument` are treated as mandatory architecture entities.

### 6.1 Persisted JSON Normalization Boundary

This architecture pass freezes one boundary model for the three shape-variable persisted fields:

- Persisted raw or legacy payloads:
  - existing database rows may still contain older OCR extraction objects or older raw risk-engine payloads serialized as strings
  - these legacy rows remain valid storage facts until BE repair work runs; this slice does not require backfill
- Normalized backend-internal shape:
  - backend services may normalize legacy payloads into architect-frozen envelopes before using them in business logic
  - the normalized envelopes are `ocr_summary.v1` for `MedicalDocument.ocr_summary` and `risk_snapshot.v1` for both `HealthRecord.risk_snapshot` and `UserProfile.risk_history`
- Tool-facing bounded outputs:
  - internal tools and other backend read models must expose bounded projections derived from the normalized envelopes rather than leaking raw persistence payloads
  - the primary bounded outputs for this slice are `medication_summary_lookup`, `recent_metric_anomaly_lookup`, and `report_comparison_lookup`

Field-specific architecture rules:

- `MedicalDocument.ocr_summary` stores persisted OCR extraction state. The canonical target shape is a metric-oriented object with explicit patient-context fields, metric objects, optional extra findings, and an optional narrative summary field. Legacy flat extraction dicts remain readable through backend normalization only.
- `HealthRecord.risk_snapshot` stores the point-in-time latest saved risk snapshot for that record. Its canonical target shape is a single normalized risk-snapshot envelope, not a raw engine dump.
- `UserProfile.risk_history` is a historical field name but not a timeline contract. Its canonical target shape is also one latest normalized risk-snapshot envelope. FE, BE, and AI/data must not reinterpret it as an append-only array without architect review.

Normalization constraints:

- Read-time normalization may parse serialized JSON, map architect-approved legacy aliases into canonical metric keys, and coerce bounded numeric/risk-level forms into the frozen internal envelopes.
- Read-time normalization must not silently invent missing units, reference ranges, hospital flags, disease findings, CKM stages, timestamps, or narrative summaries.
- FE and BE may not silently redefine these shapes later. Any pressure to widen or reshape them must return through `architect` via `orchestrator`.

Current runtime gaps called out explicitly:

- [backend/api/api_v1/endpoints/ocr.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\ocr.py) still writes `MedicalDocument.ocr_summary` as the raw extracted payload without schema versioning or canonical envelope wrapping.
- [backend/main.py](E:\health_ai_platform_2.0\backend\main.py) still writes `UserProfile.risk_history` from `risk_report` as raw serialized engine output, and still copies that raw payload directly into `HealthRecord.risk_snapshot`.
- [backend/services/agent_tools.py](E:\health_ai_platform_2.0\backend\services\agent_tools.py) already performs tolerant reads over these fields, but parts of the current tool surface still return raw parsed payloads rather than fully bounded normalized views.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) still truncates raw `risk_history` text for prompt context and still assumes an optional `summary` key on OCR payloads that is not guaranteed by current persisted data.

Expected future BE work under this freeze:

- implement one shared normalization layer for the three persisted fields
- switch new writes to the frozen canonical envelopes without requiring immediate backfill
- add scan and repair scripts that can detect legacy shapes safely before any rewrite
- update tool and route read models to consume normalized shapes instead of ad hoc per-call parsing

### 6.2 OCR Document Processing State Boundary

The OCR upload flow is no longer allowed to collapse every post-save OCR problem into a generic HTTP 500. This slice freezes a backend-owned OCR processing-state contract that separates durable storage success from OCR-service availability.

Frozen business states:

- `success`
- `partial_success`
- `stored_unprocessed`
- `error`

Frozen semantics:

- `success` means the document file and `MedicalDocument` row were saved and the backend produced a canonical structured OCR summary suitable for normal downstream merge.
- `partial_success` means the document file and row were saved, OCR execution completed, and the backend recovered some usable extraction output, but the structured result is incomplete and must be treated as bounded partial evidence rather than a fully populated report.
- `stored_unprocessed` means the document file and row were saved successfully, but OCR parsing did not run to a usable result because an OCR prerequisite was unavailable or deferred. This is the canonical state for cases such as missing Baidu OCR credentials, an unready OCR client, or an explicitly disabled OCR runtime. It must not be emitted as a generic 500 after the document is already durable.
- `error` means the backend could not determine a durable saved state for the requested operation, or another unrecoverable failure prevented the contract from reporting one of the three successful storage outcomes above.

Architecture rules:

- The backend remains responsible for durable file persistence and document-row creation before any OCR execution result is interpreted.
- The processing-state contract is additive to `ocr_summary.v1`; it does not replace or widen the canonical OCR summary payload.
- `stored_unprocessed` is a first-class business state, not a disguised error. FE must be able to show "document saved, OCR unavailable or not processed yet" without guessing from empty data.
- `partial_success` is a first-class business state, not a hidden best-effort variant of `success`. FE and BE must treat it as sparse structured evidence with missing fields, not as a fully trusted report.
- Delete and list flows must preserve the same durable document identity regardless of OCR outcome.

Current runtime conflicts called out explicitly:

- [backend/api/api_v1/endpoints/ocr.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\ocr.py) currently saves the document row first but still raises a generic 500 when OCR execution later returns `status="error"`.
- [backend/services/ocr_service.py](E:\health_ai_platform_2.0\backend\services\ocr_service.py) already exposes a real degraded path through `Baidu OCR unavailable` and `Baidu OCR client not ready`, but the current route contract does not preserve that degraded state for FE consumption.

### 6.3 Clinical Field-State And Provisional Analysis Boundary

This slice freezes a backend-owned field-state model for incomplete clinical data so FE, BE, and QA no longer rely on informal "rough estimate" behavior.

Frozen field-state enum:

- `recognized`
- `derived`
- `missing`
- `user_confirmed`
- `user_entered`

Frozen semantics:

- `recognized` means the value came directly from OCR or another imported structured source and has not been silently promoted into a user-asserted value.
- `derived` means the value was computed by a backend-approved deterministic formula from other available fields.
- `missing` means the value is currently absent and must stay absent; the runtime must not invent a default estimate.
- `user_confirmed` means the user explicitly confirmed a previously recognized or derived value.
- `user_entered` means the user manually entered the value without backend inference.

Approved automatic derivation set for this slice:

- `BMI` may be derived from `Height` and `Weight`.
- `eGFR` may be derived from `Creatinine`, `Age`, and `Gender` using the backend-owned approved formula.

Derivation constraints:

- No other clinical field may be auto-derived in this slice.
- Default estimation, placeholder guessing, median-filling, and "roughly enter a value" UX are explicitly forbidden.
- FE may guide the user to complete missing fields, but it may not silently assign numeric placeholders to unblock analysis.

Provisional analysis rules:

- `analysis_mode="provisional"` is allowed only when the backend has enough data to compute a bounded report, but at least one field that materially affects the report remains `derived` or some non-blocking fields remain `missing`.
- A normal non-provisional analysis requires the backend's minimum required field set for the selected path to be satisfied without prohibited estimates.
- If a required non-derivable field is still `missing`, the backend must block or degrade the analysis explicitly rather than pretending a final report is available.
- Provisional analysis must carry backend-owned reasons and user-facing caution semantics so FE can explain that the report is temporary and should be confirmed before relying on it.

Architecture rules:

- Field-state semantics are backend-owned and additive. FE may render them, but FE may not invent its own source-of-truth state taxonomy.
- Field-state metadata is separate from the canonical field values themselves; the existing canonical profile field names remain unchanged.
- The current `risk_snapshot.v1` persistence target remains valid. Provisional/final analysis semantics are additive metadata around how the report should be interpreted, not a replacement for the canonical risk snapshot envelope.
- Later FE and BE implementation may refine which fields are blocking for a specific analysis path, but they may not widen the field-state enum, derivation set, or provisional semantics without architect review.

### 6.4 Multimodal Fusion Semantics Boundary

This slice freezes the meaning of current multimodal fusion outputs to avoid semantic over-claim in API and UI language.

Frozen semantics:

- The runtime formula `base × gene_modifier × lifestyle_modifier` is a heuristic multiplicative risk-scaling rule, not a strict Bayesian posterior update.
- `risk_report[*].final_risk` remains a backend-owned composite risk score under current engine conventions. It must not be presented as a calibrated posterior probability unless a separate architect-approved contract update explicitly redefines it.
- Existing `risk_report[*].breakdown.base_clinical`, `gene_modifier`, and `lifestyle_modifier` fields remain unchanged for compatibility in this slice.

Architecture rules:

- FE, BE, and AI/data must not label the current fusion output as "严格贝叶斯后验" or equivalent certainty claims in API docs, UX copy, release notes, or model-governance docs.
- Any API-visible changes to fusion math semantics, `risk_report` meaning, or `breakdown` field interpretation require an architecture change request before implementation.

Current runtime pressure called out explicitly:

- [backend/services/fusion_service.py](E:\health_ai_platform_2.0\backend\services\fusion_service.py) still contains "贝叶斯融合公式" and related wording while the implemented formula is multiplicative heuristic scaling.

## 7. Synchronous Vs Asynchronous Behavior

### 7.1 Synchronous In Current Contract

- Login and profile fetch
- Profile save
- OCR upload request/response
- CSV profile import request/response
- Chat send/response
- Comprehensive analysis
- History retrieval

### 7.2 Background Or Deferred Infrastructure

- Knowledge-base rebuild
- Admin ETL/training pipelines
- Some admin upload processing

The current P0 contract does not require a generalized job orchestration layer. Existing background tasks remain implementation details outside the current contract freeze.

## 8. External Dependencies

- LLM provider configured through `OPENAI_*` settings
- Baidu OCR credentials for OCR path
- Redis for chat cache
- Chroma vector store + HuggingFace embeddings for RAG
- Local model files and ETL/training assets

### 8.1 Dependency Classification And Release Policy

This slice freezes dependency policy by distinguishing optional degraded operation from release-blocking incompatibility.

Frozen dependency policy:

- Redis cache is optional. The backend may release with cache disabled if the runtime degrades cleanly and no user-facing route fails because Redis is absent.
- The fusion stack may release in degraded mode when lifestyle/XGBoost-backed fusion is unavailable only if `/analyze/comprehensive` still returns a backend-owned consumable `risk_report` through the approved fallback path and the release notes explicitly call out degraded fusion behavior.
- OCR credentials and OCR client readiness are not equivalent to document-storage availability. A deployment may tolerate OCR-unavailable mode only when the release scope explicitly accepts manual-entry fallback and the FE contract surfaces `stored_unprocessed` instead of a generic failure. A production release that advertises OCR as available must treat missing OCR credentials as release-blocking.
- scikit-learn / joblib model compatibility warnings are not acceptable as a steady-state release policy. The canonical fix is to re-export model artifacts against the target runtime dependency baseline. Runtime version pinning may be used only as a short-lived containment action, not as the architect-approved long-term contract.

Warning policy:

- Acceptable warnings are concise, once-per-condition degraded-mode warnings for explicitly optional dependencies such as Redis, approved degraded fusion fallback, or OCR-disabled environments.
- Release-blocking warnings include repeated import-time warning spam, generic stack traces for known degraded paths, scikit-learn model-compatibility warnings, or any warning that leaves FE/BE unable to distinguish saved-but-degraded state from true failure.

### 8.2 Runtime Configuration Ownership Boundary

This slice freezes configuration ownership to reduce drift between `backend/config.py` and `backend/core/config.py`.

Ownership split:

- `backend/core/config.py` is the only architect-frozen source for environment-bound runtime settings (`BACKEND_CORS_ORIGINS`, `OPENAI_*`, `BAIDU_*`, `REDIS_URL`, `DATABASE_URL`/`SQLALCHEMY_DATABASE_URI`, and upload/runtime service endpoints).
- `backend/config.py` is limited to repository-local path constants, model artifact locations, and static simulation defaults that are not environment contracts.
- FE and BE may not define duplicate environment keys across both modules for the same runtime concern.

Implementation guardrails:

- Runtime middleware behavior (including CORS) must consume `settings` rather than hardcoded literals in app bootstrap.
- Any renaming of environment keys, default model identifiers, or precedence rules that changes API-visible runtime behavior requires architect review.

Current runtime pressure called out explicitly:

- [backend/main.py](E:\health_ai_platform_2.0\backend\main.py) hardcodes `allow_origins=["*"]` instead of consuming `settings.BACKEND_CORS_ORIGINS`.
- Multiple services import path constants from [backend/config.py](E:\health_ai_platform_2.0\backend\config.py), while runtime env settings live in [backend/core/config.py](E:\health_ai_platform_2.0\backend\core\config.py), and the ownership boundary was previously implicit.

### 8.3 External Provider Compliance And Privacy Boundary

This slice freezes provider-facing data boundaries for Baidu OCR, Moonshot/Kimi-compatible LLM calls, RAG retrieval, and internal logging/audit.

Boundary rules:

- Baidu OCR receives only the minimum document/image payload required for OCR extraction in this slice; OCR provider payloads are not a public API output.
- Moonshot/Kimi-compatible LLM calls are backend-mediated. FE must not call provider endpoints directly, and provider request/response bodies must not be exposed in `/chat/*` responses.
- RAG retrieval stays backend-internal; only bounded provenance and evidence metadata may flow to public chat metadata fields already frozen by contract.
- User health data, chat text, and report payloads must not be copied into operational logs or audit/replay records beyond already-frozen bounded metadata fields.

Compliance posture:

- This platform provides health guidance support, not diagnosis finality; clinical diagnosis and treatment decisions remain outside automated contract guarantees.
- If deployment policy for provider processing scope changes (for example, cross-border processing constraints or new retained payload classes), it must return through architect before implementation.

## 9. Architecture Constraints

- Current public contract must preserve existing route shapes where already used by frontend.
- Auth model remains bearer-token-based JWT with `/auth/token`.
- Current repository truth for active persistence is SQLite; references to PostgreSQL are future/deployment-direction notes, not current contract assumptions.
- Sensitive genomic data is represented through encrypted persistence semantics in `UserProfile`.
- The current Agent runtime must prefer bounded context assembly over unbounded prompt growth; missing or oversized evidence should degrade by trimming, not by expanding the prompt indefinitely.
- The current Agent runtime must use exactly the six frozen lanes `general_health`, `report_interpretation`, `trend_review`, `medication_related`, `urgent_symptom`, and `diagnosis_sensitive`; FE and BE may not silently redefine lane meaning, lane count, tool eligibility, or output-depth rules.
- Native tool calling is a preferred optimization, not a hard dependency; provider/model incompatibility must degrade to the existing read-only local planning path rather than fail the chat request.
- The C3 evidence panel is an additive contract extension only; until FE and BE implement it, existing assistant metadata fields remain required for backward-compatible rendering.
- The persisted-field normalization freeze in this pass does not authorize FE, BE, or AI/data to redefine `MedicalDocument.ocr_summary`, `HealthRecord.risk_snapshot`, or `UserProfile.risk_history`; later shape changes require architect review.
- FE and BE may not treat OCR service unavailability after durable document save as a generic 500 path; they must preserve the frozen `stored_unprocessed` business state once implementation lands.
- FE and BE may not turn platform CSV profile import into a persistence endpoint; imported profile values are saved only through the existing profile save flow.
- BE may not accept arbitrary raw Synthea export tables through `POST /api/v1/profile/import-csv`; accepted input is the platform-standard profile CSV already mapped into platform field names and units.
- FE and BE may not invent numeric defaults, "rough estimate" placeholders, or silent value fabrication for incomplete clinical fields; only the frozen `derived` formulas for `BMI` and `eGFR` are allowed in this slice.
- FE and BE may not silently widen the field-state enum, derivation set, or provisional-analysis semantics without an architect-owned contract update.
- Optional-dependency degraded releases are allowed only for the frozen dependency classes in section 8.1 and only with explicit release-note/operator disclosure; missing credentials for a feature still advertised as fully available are release-blocking.
- FE and BE may not keep wildcard CORS (`*`) together with credentialed browser flows for protected routes; credentialed CORS must use backend-owned allowlisted origin echo behavior.
- FE, BE, and AI/data may not market or document `base × gene_modifier × lifestyle_modifier` outputs as strict Bayesian posterior semantics under the current contract.
- FE and BE may not expose raw Baidu OCR responses, raw LLM provider payloads, or raw RAG passages through public API responses, replay payloads, or frontend-visible audit surfaces.
- Answer replay is a bounded internal reconstruction package, not a transcript archive: FE and BE may not persist raw query/reply/prompt text, large RAG text, raw tool results, or unsanitized medical payloads under replay-related names.
- `ChatMessage` remains the public/history-facing assistant record and must not absorb internal replay-only fields such as `context_budget_summary`, `tool_result_summary`, or `rag_source_refs`.
- Any future internal/admin replay route must stay separate from `/chat/send`, `/chat/stream`, and `/chat/conversations/{conversation_id}/messages`; this slice freezes persistence only, not a new replay UI or route.
- Lifestyle digital twin scenario reads are demo-only and read-only; FE and BE may not persist `simulated_demo` events as real `IoTHealthData`, `HealthRecord`, `MedicalDocument`, profile updates, or device-sync rows.
- FE and BE may not silently change the existing IoT sync contract or route demo replay through `/api/v1/iot/sync/batch`.
- FE and BE may not allow demo scenario replay, `diet_vision_event.v1`, or `lifestyle_context.v1` to auto-save health profile records or real IoT records.
- FE, BE, and AI-data may not describe a heuristic `lifestyle_modifier` derived from demo behavior as a clinically calibrated posterior probability.
- Demo scenario artifacts must carry `data_mode` and source provenance; unlabeled behavior/day data must be rejected or treated as non-persistable demo context.
- Lifestyle behavior-day uploads are backend parse/validate only; FE and BE may not persist uploaded files, parsed events, generated `lifestyle_context`, or upload-derived analysis output as `IoTHealthData`, `HealthRecord`, `MedicalDocument`, profile fields, risk snapshots, or device-sync rows.
- FE and BE may not relabel user-uploaded CSV/JSON behavior as `real_device`; `data_mode="real_device"` remains reserved for a future real-device integration contract.
- The real-device Lifestyle placeholder is presentation-only in this slice and must not introduce a live sync route, background job, vendor connector, or hidden IoT write path.

### 9.1 Stability Remediation Classification (2026-04-23)

Contract-gated before FE/BE/AI-data implementation:

- CORS behavior and test/deployment alignment for credentialed browser traffic
- Config ownership unification for `backend/config.py` vs `backend/core/config.py` when it affects runtime/API-visible behavior
- Multimodal fusion semantics wording and any interpretation of `risk_report` as Bayesian posterior output
- Compliance/privacy wording for Baidu OCR, Moonshot/Kimi-compatible LLM, RAG, health data, logs, and audit exposure
- Any API-visible change to `risk_report` meaning, `analysis_context` semantics, or chat metadata shapes

Safe implementation-only within current frozen contract:

- Dependency reproducibility cleanup and compatibility pin/re-export work (`xgboost`, `torch`, `torchvision`, `scikit-learn`/`joblib`) when no API shape or output meaning changes
- Model-card/model-governance documentation additions for existing model assets
- Training-script path de-hardcoding from machine-local absolute paths to project-root/config-resolved paths
- Oversized-file split planning and low-risk internal refactors that do not change public route/payload semantics

## 10. Non-Goals For This Phase

- Replatforming route namespaces
- Introducing microservices
- Replacing SQLModel persistence
- Redesigning the frontend information architecture
- Freezing all admin and research surfaces
- Rewriting the chat runtime into a new public API shape
- Moving medical-routing semantics to the frontend
- Replacing the current lane/verdict contract with FE-owned policy logic
- Turning takeover into a new page workflow, ticketing system, or generic disclaimer replacement

## 11. Decision Log

| Decision | Rationale |
|----------|-----------|
| Freeze only the approved P0 user loop in this architecture pass | Keeps architecture aligned with the opened `prd_ready` gate |
| Treat existing route shapes as the baseline contract | Avoids drifting away from the current frontend/backend integration surface |
| Use SQLite-backed SQLModel entities as the current persistence truth | Matches current repository implementation, even if future deployment may evolve |
| Keep AI/data responsibilities behind backend-owned HTTP contracts | Prevents frontend and AI/data code from diverging on public semantics |
| Prefer provider-native function calling with deterministic backend fallback | Gains more stable tool-call schemas when available without coupling runtime correctness to a single model capability |
| Freeze `evidence_panel` as additive backend-owned assistant metadata | Preserves the current chat UI while making richer evidence rendering contractually explicit for FE/BE |
| Freeze section-level `source_items` as bounded drill-down metadata | Adds renderable source details without exposing raw payloads or changing the outer chat contract |
| Freeze Chinese-aware recursive chunking for KB rebuilds while keeping retrieval internal-only | Improves PDF segmentation without semantic chunking or API expansion |
| Freeze the next tool slice as three self-only read-only lookups behind the chat runtime | Expands useful retrieval without changing public routes or opening write-capable medical actions |
| Freeze audit persistence as an internal-only backend record alongside runtime logs | Preserves operational observability while preventing any silent widening of the public chat API |
| Freeze `medication_summary_lookup` as a bounded medication-facts projection rather than prescribing advice | Keeps the tool retrieval-only and backend-internal |
| Freeze `recent_metric_anomaly_lookup` as a bounded anomaly summary over latest metric inputs | Reduces medical-domain overexposure of raw anomaly payloads |
| Freeze `report_comparison_lookup` as a pairwise normalized OCR-summary comparison | Gives BE a bounded diff surface without raw file export semantics |
| Freeze `evidence_metadata` as additive runtime-only quality metadata for read-only tools | Explains freshness, coverage, confidence, and comparison counts without inflating persisted payloads |
| Freeze query-time RAG quality summary as bounded runtime metadata for internal audit/replay only | Keeps conservative degrade behavior observable without widening the public chat contract |
| Keep the next tool slice backend-internal through the provider-native function-calling path | Avoids public chat API churn while preserving the current route surface |
| Reuse existing `report`, `profile`, and `trend` source types for evidence mapping in this slice | Prevents inventing a new taxonomy just for the tool boundary |
| Freeze canonical envelopes for `ocr_summary`, `risk_snapshot`, and `risk_history` while allowing bounded legacy reads | Lets BE build one shared normalizer and later repair scripts without redefining raw persisted history in place |
| Freeze OCR document processing into `success`, `partial_success`, `stored_unprocessed`, and `error` | Separates durable document save outcomes from OCR-service availability and prevents saved-but-unprocessed uploads from collapsing into generic 500 behavior |
| Freeze platform CSV profile import as a parse-only route | Lets FE fill the clinical form from demo-ready platform CSV rows without changing OCR, profile persistence, or raw Synthea ETL boundaries |
| Freeze backend-owned clinical field states plus a narrow derivation set for `BMI` and `eGFR` | Replaces informal "rough estimate" behavior with explicit provenance and keeps incomplete-data semantics out of FE guesswork |
| Allow provisional analysis only as an explicitly labeled backend-owned mode | Preserves bounded reporting when some derived or non-blocking missing data remains without pretending the report is final |
| Treat Redis as optional, OCR-as-advertised and sklearn model compatibility as policy-gated release concerns, and degraded fusion as a disclosed fallback mode | Gives operators and implementers one explicit release-policy boundary instead of ad hoc warning tolerance |
| Allow batch archive as a row-wise additive extension while excluding bulk delete | Preserves the flat conversation list model and keeps destructive bulk semantics out of scope |
| Allow batch restore as a row-wise additive extension over `archived_at` while excluding folder mutation and bulk delete | Restores archived sessions conservatively without redefining conversation grouping or persistence semantics |
| Freeze the chat runtime into exactly six backend-owned medical risk lanes | Prevents FE/BE drift on safety routing, tool eligibility, and response depth |
| Freeze `decision_summary.policy` as an additive backend-owned explicit policy envelope | Makes routing priority, answer mode, and degrade behavior explicit without changing the public route surface |
| Freeze top-level `response_verdict` as the answer-level assistant verdict object | Avoids colliding with the already-frozen `decision_summary.verdict` while keeping live, stream-final, and replay metadata consistent |
| Freeze `takeover` as a separate backend-owned human-handoff projection | Gives FE a bounded handoff signal without turning the view layer into a workflow, ticketing, or disclaimer system |
| Keep lane and verdict semantics inside existing chat metadata instead of adding new routes | Preserves the current chat surface while still giving FE a safe contract to consume |
| Freeze the Dr. AI "why did I answer this way" presentation layer as a read-only projection over existing backend-owned chat metadata | Lets FE render an explanation UI without inventing new medical semantics, new status tags, or a second verdict system |
| Keep send, stream-final, and replay aligned on the same assistant-answer metadata surface | Prevents the UI from seeing different explanation contracts across live and historical turns |
| Keep `evidence_panel` as the structured evidence drill-down while the explanation UI stays a presentation of existing verdict/policy metadata | Prevents the FE from using the explanation surface as a substitute for backend evidence provenance |
| Do not add new fields for this slice | The FE consumes only existing backend-owned fields and display mappings in this contract freeze |
| Freeze the evidence sufficiency gate to `sufficient`, `limited`, and `insufficient`, and add `conflicting_evidence` as an explicit degrade reason | Removes doc/runtime drift and prevents BE from inventing new insufficiency semantics later |
| Upgrade `AgentAuditEvent` from a call record to a responsibility record | Preserves accountable answer-boundary evidence without exposing transcripts, prompts, large RAG text, or unsanitized medical payloads |
| Freeze answer replay as a new internal one-to-one `AgentAnswerReplay` package rather than widening `ChatMessage` or overloading `AgentAuditEvent` | Keeps postmortem reconstruction bounded, internal-only, and linked to one assistant turn without turning replay into raw-context archiving |
| Freeze credentialed CORS to backend-owned allowlist echo behavior instead of wildcard origins | Aligns browser runtime behavior with tests and deployment policy while preventing silent cross-origin drift |
| Freeze runtime configuration ownership between `backend/core/config.py` and `backend/config.py` | Reduces env/path-source drift and prevents hidden API-visible behavior changes from split config entrypoints |
| Freeze multimodal fusion wording to heuristic multiplicative semantics | Prevents over-claiming Bayesian posterior certainty when current formula is heuristic scaling |
| Freeze provider-facing compliance boundaries for OCR/LLM/RAG/logging | Keeps sensitive health data flow bounded and prevents silent exposure of raw provider payloads |
| Approve `AST`, `HGB`, and `UA` as additive report-level `ocr_summary.v1.metrics` keys | Raises canonical OCR extraction coverage while keeping public routes stable and avoiding unsupported automatic `UserProfile` promotion |
| Freeze the Lifestyle Digital Twin Demo Engine as read-only demo replay plus optional analysis context | Lets FE present a top-tier behavior-day timeline while preventing demo data from masquerading as live devices or persisted health evidence |
| Add read-only authenticated demo scenario routes under `/api/v1/demo/behavior-scenarios` | Gives BE a bounded scenario API without changing IoT sync, food upload, profile save, or history persistence contracts |
| Allow optional `lifestyle_context.v1` on `/analyze/comprehensive` only as explanatory heuristic context | Reuses the existing analysis route while preventing lifestyle demo modifiers from being claimed as calibrated clinical posterior probabilities |
| Freeze Lifestyle behavior-day upload as backend-owned parse-only CSV/JSON import | Gives users a platform-standard uploaded timeline while preserving demo fallback, provenance labeling, and no-persistence boundaries |
| Keep real-device import as a visible placeholder only | Makes the future integration path clear without claiming live wearable/device sync or widening IoT contracts in this slice |
