# Health AI Platform Optimization Backlog Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue enriching the released Health AI Platform with higher-value platform improvements in session management, Agent UX, and runtime observability without expanding into unsafe write-capable medical autonomy.

**Architecture:** Treat the current release-ready controlled Agent runtime as the stable base. The next wave should stay additive and user-visible: first finish session-management quality-of-life gaps, then deepen Agent response presentation and streaming visibility, and finally strengthen audit and read-only tool coverage behind the same backend-owned contracts.

**Tech Stack:** FastAPI, SQLModel, Alembic, pytest, Vue 3, Element Plus, Axios/fetch SSE, existing controlled Agent runtime, Markdown docs under `docs/`

---

## Chunk 1: Session Management Refinement

### Task 1: Add manual conversation rename

**Files:**
- Modify: `backend/api/api_v1/endpoints/chat.py`
- Modify: `backend/services/conversation_service.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: `tests/test_conversation_service.py`
- Test: `tests/test_chat_endpoint_contract.py`
- Test: `tests/test_drai_conversation_sidebar.py`

- [ ] **Step 1: Write failing tests for manual rename**
- [ ] **Step 2: Run focused tests and verify they fail**

Run:
- `pytest tests/test_conversation_service.py tests/test_chat_endpoint_contract.py tests/test_drai_conversation_sidebar.py -v`

- [ ] **Step 3: Add backend rename action**

Requirements:
- current user only
- trim empty input
- preserve existing title-summary fallback for unnamed sessions

- [ ] **Step 4: Add sidebar rename UI**

Requirements:
- inline or dialog rename
- preserve existing search/archive/pin layout

- [ ] **Step 5: Re-run focused tests and frontend build**

Run:
- `pytest tests/test_conversation_service.py tests/test_chat_endpoint_contract.py tests/test_drai_conversation_sidebar.py -v`
- `npm.cmd run build`

### Task 2: Add conversation grouping and recent sections

**Files:**
- Modify: `backend/services/conversation_service.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: `tests/test_conversation_service.py`
- Test: `tests/test_drai_conversation_sidebar.py`

- [ ] **Step 1: Write failing tests for grouped sidebar sections**
- [ ] **Step 2: Implement backend-friendly group metadata or frontend grouping helper**

Suggested groups:
- pinned
- today
- last 7 days
- older

- [ ] **Step 3: Render grouped sections in the sidebar**
- [ ] **Step 4: Re-run focused tests and frontend build**

### Task 3: Add batch archive/delete preparation hooks

**Files:**
- Modify: `backend/api/api_v1/endpoints/chat.py`
- Modify: `backend/services/conversation_service.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: `tests/test_conversation_service.py`
- Test: `tests/test_chat_endpoint_contract.py`

- [ ] **Step 1: Write failing tests for multi-select session operations**
- [ ] **Step 2: Implement backend batch archive first**

Constraint:
- do not add destructive delete unless batch archive path is stable first

- [ ] **Step 3: Add minimal frontend multi-select flow**
- [ ] **Step 4: Re-run focused regression**

## Chunk 2: Agent UX Enrichment

### Task 4: Add tool-level SSE status events

**Files:**
- Modify: `backend/services/chat_service.py`
- Modify: `backend/api/api_v1/endpoints/chat.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: `tests/test_chat_agent_service.py`
- Test: `tests/test_chat_endpoint_contract.py`

- [ ] **Step 1: Write failing streaming tests for tool-level events**

Expected events:
- `tool_start`
- `tool_done`
- optional `tool_skip`

- [ ] **Step 2: Extend the stream runtime without breaking current `status`/`final` contract**
- [ ] **Step 3: Render richer process feedback in Dr. AI**

Examples:
- 正在读取健康档案
- 正在检索医学指南
- 正在分析历史趋势

- [ ] **Step 4: Re-run focused streaming regression and frontend build**

### Task 5: Add a structured health suggestion card

**Files:**
- Modify: `backend/services/chat_service.py`
- Modify: `backend/api/api_v1/endpoints/chat.py`
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: `tests/test_chat_agent_api.py`
- Test: `tests/test_chat_agent_service.py`

- [ ] **Step 1: Write failing tests for optional card payload**

Suggested schema:
- `headline`
- `risk_level`
- `key_actions`
- `follow_up_hint`
- `when_to_seek_care`

- [ ] **Step 2: Generate cards only for matching intents**

Examples:
- lifestyle suggestions
- trend explanations
- follow-up reminders

- [ ] **Step 3: Render the card below the assistant reply**
- [ ] **Step 4: Re-run focused API/service tests and frontend build**

### Task 6: Add a richer evidence panel

**Files:**
- Modify: `frontend/src/views/chat/DrAI.vue`
- Possibly modify: `backend/api/api_v1/endpoints/chat.py`
- Test: `tests/test_drai_conversation_sidebar.py`

- [ ] **Step 1: Design compact evidence grouping**

Suggested groups:
- user profile
- trend/history
- uploaded report
- guideline/knowledge

- [ ] **Step 2: Implement panel without overloading the current card layout**
- [ ] **Step 3: Re-run frontend build and source-level regression**

## Chunk 3: Runtime Observability And Tooling

### Task 7: Expand Agent audit detail

**Files:**
- Modify: `backend/services/agent_audit.py`
- Modify: `backend/services/chat_service.py`
- Test: `tests/test_agent_audit.py`
- Test: `tests/test_chat_agent_service.py`

- [ ] **Step 1: Write failing tests for expanded audit fields**

Suggested fields:
- `context_budget_summary`
- `tool_latency_ms`
- `tool_count`
- `response_latency_ms`
- `fallback_used`

- [ ] **Step 2: Implement minimal structured audit expansion**
- [ ] **Step 3: Re-run focused audit/runtime regression**

### Task 8: Add more read-only tools safely

**Files:**
- Modify: `backend/services/agent_tools.py`
- Modify: `backend/services/chat_service.py`
- Test: `tests/test_agent_tools.py`
- Test: `tests/test_chat_agent_service.py`

- [ ] **Step 1: Freeze the next safe tool set**

Recommended candidates:
- report-summary lookup
- recent abnormal metrics lookup
- latest analysis snapshot lookup

- [ ] **Step 2: Write failing tests for schema validation and safe exposure**
- [ ] **Step 3: Implement tools under current read-only boundary**
- [ ] **Step 4: Re-run focused tool/runtime regression**

### Task 9: Add legacy-title repair path

**Files:**
- Modify: `backend/services/conversation_service.py`
- Possibly create: `scripts/repair_conversation_titles.py`
- Test: `tests/test_conversation_service.py`

- [ ] **Step 1: Write failing tests for refreshing default/legacy titles**
- [ ] **Step 2: Implement a safe repair path**

Options:
- on-read repair for default titles only
- one-off script for local data cleanup

- [ ] **Step 3: Re-run focused regression**

## Chunk 4: Execution And Governance

### Task 10: Execute slices in this priority order

**Files:**
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`
- Modify: `docs/qa-report.md`
- Modify: `docs/blackboard/state.yaml`

- [ ] **Step 1: Start with the highest-visibility slice**

Priority:
1. structured health suggestion card
2. tool-level SSE status events
3. manual conversation rename
4. richer evidence panel
5. expanded audit detail
6. conversation grouping
7. safer read-only tool expansion
8. legacy-title repair
9. batch archive hooks

- [ ] **Step 2: After each slice, run fresh verification**

Minimum:
- focused pytest
- `npm.cmd run build` when frontend changes
- `pytest tests` after slice completion

- [ ] **Step 3: Sync QA, contracts, and blackboard after every validated slice**

Constraint:
- only the orchestrator updates `docs/blackboard/state.yaml`

## Definition Of Done

- The backlog is sequenced around visible product value and safe runtime growth
- Session-management gaps have clear follow-up slices
- Agent UX enhancements are separated from runtime observability work
- Unsafe write-capable tools remain explicitly out of scope
- Each slice includes exact file targets and verification expectations
