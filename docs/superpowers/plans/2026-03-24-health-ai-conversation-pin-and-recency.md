# Health AI Conversation Pin And Recency Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pinned conversations and stronger recent-access ordering so Dr. AI session management feels faster and more intentional.

**Architecture:** Extend the existing `ChatConversation` persistence model with explicit pin and recent-access metadata, keep the ordering logic server-owned inside `ConversationService`, and expose minimal API/front-end controls so the sidebar can always show pinned sessions first and then the most recently accessed active sessions.

**Tech Stack:** FastAPI, SQLModel, Alembic, pytest, Vue 3, Element Plus, Axios, existing Dr. AI conversation sidebar

---

## Chunk 1: Backend Conversation Ordering Semantics

### Task 1: Define the ordering contract with failing tests

**Files:**
- Modify: `tests/test_conversation_service.py`
- Modify: `tests/test_chat_endpoint_contract.py`

- [ ] **Step 1: Write a failing service test for pinned-first ordering**

```python
def test_list_conversations_sorts_pinned_before_recent(session):
    ...
```

- [ ] **Step 2: Run the focused service test and verify it fails**

Run: `pytest tests/test_conversation_service.py -v`
Expected: FAIL because pin metadata and ordering are not implemented

- [ ] **Step 3: Write a failing service test for recent-access refresh on detail load**

```python
def test_get_conversation_detail_refreshes_last_accessed_at(session):
    ...
```

- [ ] **Step 4: Write a failing API contract test for pin/unpin controls**

```python
def test_chat_conversation_pin_and_unpin_endpoints(client, token_headers, monkeypatch):
    ...
```

- [ ] **Step 5: Run the focused API contract test and verify it fails**

Run: `pytest tests/test_chat_endpoint_contract.py -v`
Expected: FAIL because pin/unpin endpoints and summary fields are missing

### Task 2: Implement persistence and service behavior

**Files:**
- Modify: `backend/models.py`
- Create: `backend/alembic/versions/20260324_add_chat_conversation_pin_and_access.py`
- Modify: `backend/services/conversation_service.py`

- [ ] **Step 1: Add persistence fields**

Fields:
- `pinned_at: Optional[datetime]`
- `last_accessed_at: Optional[datetime]`

- [ ] **Step 2: Implement service helpers**

Required helpers:
- `pin_conversation(...)`
- `unpin_conversation(...)`
- access timestamp refresh when a conversation is opened

- [ ] **Step 3: Enforce server-owned ordering**

Ordering rules:
1. pinned conversations first
2. within pinned, latest pin first
3. within unpinned, latest accessed first
4. final tie-break by `updated_at` then `id`

- [ ] **Step 4: Re-run focused backend tests**

Run:
- `pytest tests/test_conversation_service.py -v`
- `pytest tests/test_chat_endpoint_contract.py -v`

Expected:
- all new pin/recency tests pass

## Chunk 2: API And Frontend Controls

### Task 3: Expose pin/unpin and recency metadata through the chat API

**Files:**
- Modify: `backend/api/api_v1/endpoints/chat.py`

- [ ] **Step 1: Extend the conversation summary schema**

Fields:
- `pinned`
- `last_accessed_at`

- [ ] **Step 2: Add pin/unpin endpoints**

Routes:
- `POST /chat/conversations/{conversation_id}/pin`
- `POST /chat/conversations/{conversation_id}/unpin`

- [ ] **Step 3: Keep archive/search behavior compatible**

Constraint:
- pinning must not silently unarchive archived sessions unless explicitly touched by existing restore/open flows

### Task 4: Add sidebar pin controls and sorting cues

**Files:**
- Modify: `frontend/src/views/chat/DrAI.vue`
- Modify: `tests/test_drai_conversation_sidebar.py`

- [ ] **Step 1: Write a failing sidebar test for pin controls**

Assertions should cover:
- `toggleConversationPin`
- pin/unpin labels or icon markers
- pinned metadata handling in the list

- [ ] **Step 2: Run the sidebar test and verify it fails**

Run: `pytest tests/test_drai_conversation_sidebar.py -v`
Expected: FAIL because pin controls are absent

- [ ] **Step 3: Implement minimal UI changes**

Requirements:
- pinned conversations show a visible marker
- pin/unpin action is available per row
- active ordering still comes from the backend

- [ ] **Step 4: Re-run frontend-focused verification**

Run:
- `pytest tests/test_drai_conversation_sidebar.py -v`
- `npm.cmd run build`

Expected:
- sidebar test passes
- production build remains green

## Chunk 3: Validation And Workflow Sync

### Task 5: Run regression and update governance artifacts

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `docs/data-model-contract.md`
- Modify: `docs/qa-report.md`
- Modify: `docs/blackboard/state.yaml`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] **Step 1: Run focused regression**

Run:
- `pytest tests/test_conversation_service.py tests/test_chat_endpoint_contract.py tests/test_drai_conversation_sidebar.py -v`

- [ ] **Step 2: Run full regression**

Run:
- `pytest tests`

- [ ] **Step 3: Update contracts and architecture notes**

Document:
- new conversation summary fields
- pin/unpin endpoints
- ordering semantics owned by backend conversation service

- [ ] **Step 4: Update QA and blackboard**

Expected:
- blackboard reflects the validated post-release session-ordering slice
- QA notes include focused and full verification evidence

## Definition Of Done

- Conversations can be pinned and unpinned from the Dr. AI sidebar
- Opening a conversation refreshes recent-access ordering
- Sidebar ordering is stable and backend-owned: pinned first, then recent sessions
- Focused tests, full pytest regression, and frontend build all pass
- Workflow records, contracts, and blackboard reflect the validated slice
