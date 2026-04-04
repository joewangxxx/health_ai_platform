# Health AI Post-Release Roadmap Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the now-release-ready Health AI Platform increment into a richer graduation-project system with stronger Agent orchestration, better chat/session UX, clearer evidence presentation, and thesis/demo support.

**Architecture:** Treat the current release-ready stack as the stable baseline. Future work should build outward from the deployed Agent slice instead of replacing it: first strengthen delivery/demo packaging, then deepen Agent runtime quality, then enrich the frontend session experience, and finally package the system for thesis and defense workflows.

**Tech Stack:** FastAPI, SQLModel, SQLite, pytest, Vue 3, Element Plus, Axios/fetch SSE, existing OpenAI-compatible LLM client, Redis cache, existing RAG/OCR/risk-analysis services, Markdown docs under `docs/`

---

## Chunk 1: Release Closure And Demo Baseline

### Task 1: Freeze the current release baseline

**Files:**
- Modify: `docs/release.md`
- Modify: `docs/handoff.md`
- Modify: `docs/deployment.md`
- Modify: `docs/qa-report.md`

- [ ] **Step 1: Re-read the current release evidence**

Run:
- `Get-Content -Raw docs/release.md`
- `Get-Content -Raw docs/qa-report.md`
- `Get-Content -Raw docs/handoff.md`

Expected:
- current release scope, smoke evidence, and residual risks are all explicit

- [ ] **Step 2: Add a “defense demo baseline” section to release notes**

Document:
- recommended login account
- recommended demo flow order
- known safe prompts for Dr. AI demonstration
- fallback plan if external LLM latency spikes

- [ ] **Step 3: Add an operator-ready smoke checklist**

Document:
- startup commands
- healthy-service checks
- auth smoke
- chat smoke
- frontend smoke

- [ ] **Step 4: Re-run the release smoke checklist**

Run:
- `docker compose ps -a`
- `pytest tests`

Expected:
- all services healthy
- all tests passing

### Task 2: Create a defense/demo script artifact

**Files:**
- Create: `docs/demo-script.md`
- Modify: `docs/handoff.md`

- [ ] **Step 1: Write the demo script**

Include:
- opening system overview
- patient-facing flow
- Agent evidence flow
- SSE process feedback demonstration
- safety interception demonstration
- closing engineering highlights

- [ ] **Step 2: Add failure fallback notes**

Cover:
- what to do if SSE stalls
- what to do if model latency is high
- what to do if RAG has no local evidence

- [ ] **Step 3: Link the demo script from handoff**

Expected:
- delivery docs point to one canonical demo artifact

## Chunk 2: Agent Runtime Hardening

### Task 3: Add Context Builder token budgeting

**Files:**
- Modify: `backend/services/chat_service.py`
- Possibly create: `backend/services/context_builder.py`
- Modify: `docs/architecture.md`
- Modify: `docs/api-contract.md`
- Test: `tests/test_chat_agent_service.py`

- [ ] **Step 1: Design the token-budget contract**

Budget lanes should be explicit:
- profile budget
- history budget
- OCR/document budget
- RAG budget
- reserved answer budget

- [ ] **Step 2: Write failing tests for budget trimming**

Test examples:
- large profile is summarized/truncated before prompt assembly
- long history only keeps recent bounded turns
- RAG payload is capped to top-k bounded context

- [ ] **Step 3: Implement a dedicated context builder**

Recommended responsibilities:
- normalize inputs from profile/RAG/tools
- trim each lane independently
- expose budget summary for audit/logging

- [ ] **Step 4: Re-run focused runtime tests**

Run:
- `pytest tests/test_chat_agent_service.py tests/test_chat_endpoint_contract.py -v`

Expected:
- prompt assembly still works
- budget enforcement is covered

### Task 4: Prefer native function/tool calling when provider supports it

**Files:**
- Modify: `backend/services/chat_service.py`
- Modify: `backend/services/agent_tools.py`
- Modify: `docs/superpowers/specs/2026-03-24-health-ai-agent-architecture-design.md`
- Test: `tests/test_chat_agent_service.py`

- [ ] **Step 1: Map current provider capability assumptions**

Document:
- which configured model supports tool calling
- what fallback path exists when tool calling is unavailable

- [ ] **Step 2: Write failing tests for provider fallback**

Cases:
- model supports native tool calling
- model does not support tool calling and falls back to current bounded planner

- [ ] **Step 3: Add provider capability branching**

Requirements:
- keep current read-only tool boundary
- do not introduce write-capable tools
- keep audit records consistent across both paths

- [ ] **Step 4: Re-run focused Agent tests**

Run:
- `pytest tests/test_agent_tools.py tests/test_chat_agent_service.py tests/test_chat_agent_api.py -v`

Expected:
- tool selection remains bounded and safe

### Task 5: Strengthen Agent audit and observability

**Files:**
- Modify: `backend/services/agent_audit.py`
- Modify: `backend/services/chat_service.py`
- Create or modify: `docs/architecture.md`
- Test: `tests/test_agent_audit.py`

- [ ] **Step 1: Expand the audit schema**

Suggested fields:
- `intent`
- `tool_reason`
- `tool_used`
- `evidence_present`
- `context_budget_summary`
- `latency_ms`
- `safety_level`

- [ ] **Step 2: Add failing tests for new audit fields**

- [ ] **Step 3: Implement minimal logging changes**

Constraint:
- do not log full chain-of-thought
- avoid storing privacy-heavy raw payloads unless required

- [ ] **Step 4: Re-run audit and chat runtime tests**

Run:
- `pytest tests/test_agent_audit.py tests/test_chat_agent_service.py -v`

Expected:
- audit records remain structured and deterministic

## Chunk 3: Session UX And Frontend Enrichment

### Task 6: Add conversation list and session switching

**Files:**
- Modify: `backend/api/api_v1/endpoints/chat.py`
- Modify: `backend/services/conversation_service.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Possibly create: `tests/test_conversation_service.py`
- Possibly create: `tests/test_chat_agent_api.py`

- [ ] **Step 1: Define the minimal conversation-list contract**

Needed fields:
- conversation id
- title
- updated_at
- preview

- [ ] **Step 2: Write failing backend tests**

Cases:
- list conversations for current user
- fetch recent messages for one conversation
- reject cross-user access

- [ ] **Step 3: Implement backend conversation-list endpoints/helpers**

- [ ] **Step 4: Add frontend conversation sidebar/session switcher**

Constraints:
- preserve existing Dr. AI look and feel
- avoid over-designing a whole messaging product

- [ ] **Step 5: Re-run backend tests and frontend build**

Run:
- `pytest tests/test_conversation_service.py tests/test_chat_agent_api.py -v`
- `npm.cmd run build`

Expected:
- session switch path is stable
- frontend still builds cleanly

### Task 7: Improve evidence and status presentation in Dr. AI

**Files:**
- Modify: `frontend/src/views/chat/DrAI.vue`
- Modify: `docs/release.md`
- Test: manual UI smoke plus existing frontend build

- [ ] **Step 1: Design richer but compact evidence UI**

Possible elements:
- evidence badges grouped by type
- “this answer referenced” summary
- clearer distinction between profile/trend/guideline evidence

- [ ] **Step 2: Design richer process-state presentation**

Possible elements:
- staged status row
- completed-stage markers
- compact fallback note when SSE downgrades to standard request

- [ ] **Step 3: Implement UI changes without changing backend protocol**

- [ ] **Step 4: Run frontend build and manual smoke**

Run:
- `npm.cmd run build`

Manual checks:
- normal consultation flow
- guideline-heavy flow
- urgent safety routing flow

Expected:
- users can see what the Agent consulted and what phase it is in

### Task 8: Add a “health suggestion card” output format

**Files:**
- Modify: `backend/services/chat_service.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: `tests/test_chat_agent_api.py`

- [ ] **Step 1: Define a lightweight structured card schema**

Suggested fields:
- headline
- risk_level
- key_actions
- when_to_seek_care

- [ ] **Step 2: Write failing API/UI contract tests**

- [ ] **Step 3: Generate the card only when response intent matches**

Examples:
- lifestyle suggestion
- trend explanation
- follow-up care reminder

- [ ] **Step 4: Render the card under the assistant reply**

- [ ] **Step 5: Re-run focused tests and frontend build**

Run:
- `pytest tests/test_chat_agent_api.py -v`
- `npm.cmd run build`

Expected:
- richer presentation without breaking plain-text fallback

## Chunk 4: Thesis And Defense Support

### Task 9: Produce architecture and data-flow visuals

**Files:**
- Create: `docs/diagrams/agent-runtime-flow.md`
- Create: `docs/diagrams/deployment-flow.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Freeze diagram scope**

Include:
- user query to Agent runtime flow
- safety routing
- tool execution
- evidence synthesis
- SSE feedback loop

- [ ] **Step 2: Create text-first diagram sources**

Prefer:
- Mermaid diagrams in Markdown
- labels aligned with current code and APIs

- [ ] **Step 3: Link diagrams from architecture docs**

Expected:
- one canonical source of truth for thesis and demo explanations

### Task 10: Prepare thesis/defense engineering narrative

**Files:**
- Create: `docs/thesis-support.md`
- Modify: `docs/demo-script.md`
- Modify: `docs/release.md`

- [ ] **Step 1: Summarize engineering highlights**

Must cover:
- controlled Agent architecture
- multi-turn conversation persistence
- read-only tools
- medical safety interception
- SSE process feedback
- deployment hardening

- [ ] **Step 2: Add before/after comparison framing**

Compare:
- pre-Agent RAG chat
- current controlled Agent runtime

- [ ] **Step 3: Add answer templates for common defense questions**

Examples:
- why use an external LLM
- where the engineering work is
- how medical safety is enforced
- why not build a fully autonomous medical Agent

### Task 11: Optional comparison experiment pack

**Files:**
- Create: `docs/experiments/agent-vs-rag-baseline.md`
- Possibly create: `tests/manual/agent_eval_prompts.md`

- [ ] **Step 1: Define a small fixed evaluation set**

Prompt categories:
- general consultation
- profile-grounded advice
- trend explanation
- urgent triage

- [ ] **Step 2: Define comparison metrics**

Possible dimensions:
- evidence usage
- safety consistency
- answer completeness
- latency

- [ ] **Step 3: Record a lightweight manual evaluation method**

Expected:
- enough structure for thesis discussion without overbuilding a research pipeline

## Definition Of Done

- A post-release roadmap document exists and is approved
- Release/demo assets are strong enough for graduation-project presentation
- The next engineering slice is clearly prioritized and sequenced
- Future Agent runtime work is scoped around bounded, safe improvements rather than autonomous medical writes
- Frontend enrichment, runtime hardening, and thesis-support tasks each have an implementation path and verification strategy

## Suggested Execution Order

1. Freeze release/demo baseline
2. Create the defense/demo script
3. Implement Context Builder token budgeting
4. Add provider-aware native tool-calling preference
5. Strengthen Agent audit/observability
6. Add conversation list and session switching
7. Improve evidence/status presentation
8. Add structured health suggestion cards
9. Produce diagrams and thesis-support materials
10. Run optional Agent-vs-RAG comparison work if time remains

## Notes For Implementers

- Keep the next phase centered on “richer but safer” behavior, not on full autonomy
- Avoid introducing write-capable Agent tools in the graduation-project scope
- Treat deployment health and release documentation as first-class deliverables, not afterthoughts
- Prefer additive UI enrichment over disruptive redesigns
- Keep thesis claims aligned with real code, verified behavior, and actual deployment evidence
