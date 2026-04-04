# Health AI Agent Architecture Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current Dr. AI chat flow into a controlled lightweight medical Agent with short server-side conversation memory, read-only internal tools, safety interception, audit logging, and richer frontend conversation UX.

**Architecture:** Build the Agent as an evolution of the existing chat stack rather than a new runtime. The backend will add conversation persistence, context slicing, tool registration, safety and audit helpers, and a bounded Agent loop inside `chat_service`; the frontend will pass `conversation_id`, render multi-turn sessions, and show lightweight evidence/status cues without exposing internal reasoning.

**Tech Stack:** FastAPI, SQLModel, SQLite, pytest, Vue 3, Element Plus, Axios, existing OpenAI-compatible client, existing Redis cache, existing RAG service

---

## Chunk 1: Conversation Foundation

### Task 1: Add server-side conversation models

**Files:**
- Modify: `backend/models.py`
- Create: `backend/alembic/versions/20260324_add_chat_conversation_tables.py`
- Test: `tests/test_chat_conversation_models.py`

- [ ] **Step 1: Write the failing model test**

```python
from backend.models import ChatConversation, ChatMessage

def test_chat_models_have_expected_fields():
    convo = ChatConversation(user_id=1, title="Dr AI")
    msg = ChatMessage(conversation_id=1, role="user", content="hello")
    assert convo.user_id == 1
    assert msg.role == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_conversation_models.py -v`
Expected: FAIL because `ChatConversation` and `ChatMessage` do not exist yet

- [ ] **Step 3: Add minimal SQLModel tables**

```python
class ChatConversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(default="Dr. AI Conversation")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="chatconversation.id", index=True)
    role: str
    content: str
    evidence_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Add a minimal migration**

```python
def upgrade() -> None:
    op.create_table(...)
```

- [ ] **Step 5: Run the model test again**

Run: `pytest tests/test_chat_conversation_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/alembic/versions/20260324_add_chat_conversation_tables.py tests/test_chat_conversation_models.py
git commit -m "feat: add chat conversation persistence models"
```

### Task 2: Create conversation service and sliding-window logic

**Files:**
- Create: `backend/services/conversation_service.py`
- Test: `tests/test_conversation_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
def test_window_keeps_system_and_recent_turns():
    window = build_message_window(
        system_prompt="sys",
        history=[{"role": "user", "content": str(i)} for i in range(20)],
        max_rounds=5,
    )
    assert window[0]["role"] == "system"
    assert len(window) <= 11
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_conversation_service.py -v`
Expected: FAIL because `build_message_window` does not exist yet

- [ ] **Step 3: Implement minimal conversation helpers**

```python
def build_message_window(system_prompt: str, history: list[dict], max_rounds: int = 5) -> list[dict]:
    keep = history[-max_rounds * 2 :]
    return [{"role": "system", "content": system_prompt}, *keep]
```

- [ ] **Step 4: Add helpers for create/get conversation and append messages**

```python
class ConversationService:
    def create_conversation(...)
    def append_message(...)
    def get_recent_messages(...)
```

- [ ] **Step 5: Run tests again**

Run: `pytest tests/test_conversation_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/conversation_service.py tests/test_conversation_service.py
git commit -m "feat: add conversation service and sliding window"
```

### Task 3: Extend chat endpoint contract for conversations

**Files:**
- Modify: `backend/api/api_v1/endpoints/chat.py`
- Test: `tests/test_chat_endpoint_contract.py`

- [ ] **Step 1: Write the failing endpoint contract test**

```python
def test_chat_send_accepts_and_returns_conversation_id(client, auth_header):
    response = client.post("/chat/send", json={"message": "hi", "conversation_id": None}, headers=auth_header)
    assert response.status_code == 200
    assert "conversation_id" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_endpoint_contract.py -v`
Expected: FAIL because request/response models do not include `conversation_id`

- [ ] **Step 3: Extend request and response models**

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    force_refresh: bool = False

class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    sources: List[str] = []
    evidence_tags: List[str] = []
```

- [ ] **Step 4: Thread `conversation_id` through the endpoint**

```python
response = await chat_service.chat(
    user=current_user,
    query=request.message,
    session=session,
    conversation_id=request.conversation_id,
    force_refresh=request.force_refresh,
)
```

- [ ] **Step 5: Run test again**

Run: `pytest tests/test_chat_endpoint_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api/api_v1/endpoints/chat.py tests/test_chat_endpoint_contract.py
git commit -m "feat: extend chat contract for conversations"
```

## Chunk 2: Agent Tools And Safety

### Task 4: Create read-only tool registry

**Files:**
- Create: `backend/services/agent_tools.py`
- Test: `tests/test_agent_tools.py`

- [ ] **Step 1: Write the failing registry tests**

```python
def test_agent_tool_registry_tracks_read_only_metadata():
    @agent_tool(name="demo", read_only=True, scope="self_only")
    def demo_tool():
        return {"ok": True}

    assert TOOL_REGISTRY["demo"]["read_only"] is True
    assert TOOL_REGISTRY["demo"]["scope"] == "self_only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_tools.py -v`
Expected: FAIL because the registry does not exist yet

- [ ] **Step 3: Implement decorator and registry**

```python
TOOL_REGISTRY: dict[str, dict] = {}

def agent_tool(*, name: str, read_only: bool = True, scope: str = "self_only"):
    def decorator(func):
        TOOL_REGISTRY[name] = {
            "func": func,
            "read_only": read_only,
            "scope": scope,
        }
        return func
    return decorator
```

- [ ] **Step 4: Add initial read-only tools**

```python
@agent_tool(name="get_user_profile_summary", read_only=True, scope="self_only")
def get_user_profile_summary(...): ...

@agent_tool(name="get_latest_risk_report", read_only=True, scope="self_only")
def get_latest_risk_report(...): ...
```

- [ ] **Step 5: Run tests again**

Run: `pytest tests/test_agent_tools.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/agent_tools.py tests/test_agent_tools.py
git commit -m "feat: add read-only agent tool registry"
```

### Task 5: Add tool safety guard

**Files:**
- Create: `backend/services/agent_safety.py`
- Modify: `backend/services/agent_tools.py`
- Test: `tests/test_agent_tool_safety.py`

- [ ] **Step 1: Write the failing safety tests**

```python
def test_write_tool_is_blocked_for_normal_user():
    result = enforce_tool_policy(
        user_is_admin=False,
        tool_meta={"read_only": False, "scope": "admin_only"},
    )
    assert result["allowed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_tool_safety.py -v`
Expected: FAIL because `enforce_tool_policy` does not exist yet

- [ ] **Step 3: Implement safety guard**

```python
def enforce_tool_policy(*, user_is_admin: bool, tool_meta: dict) -> dict:
    if not tool_meta.get("read_only", True) and not user_is_admin:
        return {"allowed": False, "reason": "permission_denied"}
    return {"allowed": True}
```

- [ ] **Step 4: Integrate guard into tool execution**

```python
policy = enforce_tool_policy(...)
if not policy["allowed"]:
    return {"status": "blocked", "reason": policy["reason"]}
```

- [ ] **Step 5: Run tests again**

Run: `pytest tests/test_agent_tool_safety.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/agent_safety.py backend/services/agent_tools.py tests/test_agent_tool_safety.py
git commit -m "feat: add agent tool safety guard"
```

### Task 6: Add urgent-query safety classifier

**Files:**
- Modify: `backend/services/agent_safety.py`
- Test: `tests/test_chat_agent_safety.py`

- [ ] **Step 1: Write the failing classifier tests**

```python
def test_urgent_query_is_flagged():
    result = classify_query_safety("我胸痛而且呼吸困难")
    assert result["safety_level"] == "urgent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_agent_safety.py -v`
Expected: FAIL because `classify_query_safety` does not exist yet

- [ ] **Step 3: Implement minimal keyword classifier**

```python
URGENT_PATTERNS = ["胸痛", "呼吸困难", "昏厥", "自杀", "药物过敏"]

def classify_query_safety(query: str) -> dict:
    if any(token in query for token in URGENT_PATTERNS):
        return {"safety_level": "urgent", "route": "medical_escalation"}
    return {"safety_level": "normal", "route": "agent"}
```

- [ ] **Step 4: Run tests again**

Run: `pytest tests/test_chat_agent_safety.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/agent_safety.py tests/test_chat_agent_safety.py
git commit -m "feat: add urgent query safety classifier"
```

## Chunk 3: Agent Runtime Refactor

### Task 7: Add audit helper for structured Agent logs

**Files:**
- Create: `backend/services/agent_audit.py`
- Test: `tests/test_agent_audit.py`

- [ ] **Step 1: Write the failing audit test**

```python
def test_build_audit_record_contains_core_fields():
    record = build_audit_record(user_id=1, conversation_id=2, intent="guideline_lookup")
    assert record["user_id"] == 1
    assert record["conversation_id"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_audit.py -v`
Expected: FAIL because `build_audit_record` does not exist yet

- [ ] **Step 3: Implement minimal structured audit builder**

```python
def build_audit_record(**kwargs) -> dict:
    return {
        "user_id": kwargs["user_id"],
        "conversation_id": kwargs["conversation_id"],
        "intent": kwargs.get("intent"),
        "tool_used": kwargs.get("tool_used", []),
    }
```

- [ ] **Step 4: Run test again**

Run: `pytest tests/test_agent_audit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/agent_audit.py tests/test_agent_audit.py
git commit -m "feat: add structured agent audit helper"
```

### Task 8: Refactor chat service into bounded Agent loop

**Files:**
- Modify: `backend/services/chat_service.py`
- Modify: `backend/services/conversation_service.py`
- Modify: `backend/services/agent_tools.py`
- Modify: `backend/services/agent_safety.py`
- Modify: `backend/services/agent_audit.py`
- Test: `tests/test_chat_agent_service.py`

- [ ] **Step 1: Write the failing Agent service tests**

```python
def test_chat_service_creates_conversation_and_returns_reply(...):
    result = asyncio.run(service.chat(user=user, query="最近血糖怎么样", session=session, conversation_id=None))
    assert result["conversation_id"] is not None
    assert "reply" in result

def test_same_query_different_history_has_different_cache_key(...):
    key1 = service._build_cache_key(user_id=1, conversation_id=1, history_hash="a", query="hi")
    key2 = service._build_cache_key(user_id=1, conversation_id=1, history_hash="b", query="hi")
    assert key1 != key2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_agent_service.py -v`
Expected: FAIL because the Agent flow and cache-key builder do not exist yet

- [ ] **Step 3: Update `chat()` signature and conversation bootstrap**

```python
async def chat(self, user, query, session, conversation_id=None, force_refresh=False):
    conversation = self.conversation_service.get_or_create(...)
```

- [ ] **Step 4: Add context builder and message window assembly**

```python
profile_summary = self._get_user_context(user, session)
history = self.conversation_service.get_recent_messages(...)
messages = build_message_window(system_prompt, history, max_rounds=5)
```

- [ ] **Step 5: Add bounded Agent loop**

```python
for _ in range(2):
    decision = self._plan_tools(...)
    if not decision["tool_needed"]:
        break
    tool_result = execute_registered_tool(...)
```

- [ ] **Step 6: Add structured decision summary and audit call**

```python
decision_summary = {
    "intent": intent,
    "tool_needed": tool_needed,
    "tool_plan": tool_names,
    "safety_level": safety_level,
}
```

- [ ] **Step 7: Update cache key construction**

```python
cache_key = self._build_cache_key(
    user_id=user.id,
    conversation_id=conversation.id,
    history_hash=history_hash,
    query=query,
    profile_hash=profile_hash,
)
```

- [ ] **Step 8: Persist both user and assistant messages**

```python
self.conversation_service.append_message(... role="user" ...)
self.conversation_service.append_message(... role="assistant" ...)
```

- [ ] **Step 9: Run focused service tests**

Run: `pytest tests/test_chat_agent_service.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/services/chat_service.py backend/services/conversation_service.py backend/services/agent_tools.py backend/services/agent_safety.py backend/services/agent_audit.py tests/test_chat_agent_service.py
git commit -m "feat: refactor chat service into bounded agent loop"
```

## Chunk 4: Frontend UX And End-to-End Verification

### Task 9: Upgrade Dr. AI frontend for conversations and evidence tags

**Files:**
- Modify: `frontend/src/views/chat/DrAI.vue`
- Test: manual browser verification

- [ ] **Step 1: Add `conversationId` local state**

```javascript
const conversationId = ref(null)
```

- [ ] **Step 2: Send `conversation_id` in the chat request**

```javascript
const res = await axios.post("http://127.0.0.1:8000/chat/send", {
  message: content,
  conversation_id: conversationId.value,
  force_refresh: forceRefresh.value,
})
```

- [ ] **Step 3: Store returned `conversation_id`**

```javascript
conversationId.value = res.data.conversation_id
```

- [ ] **Step 4: Render lightweight evidence/status badges**

```javascript
messages.value.push({
  role: "assistant",
  content: res.data.reply,
  sources: res.data.sources || [],
  evidenceTags: res.data.evidence_tags || [],
})
```

- [ ] **Step 5: Show evidence tags in the assistant bubble**

```html
<div v-if="msg.evidenceTags?.length" class="mt-2 text-xs">
  <span v-for="tag in msg.evidenceTags" :key="tag">{{ tag }}</span>
</div>
```

- [ ] **Step 6: Manually verify in browser**

Run: start backend and frontend, open the Dr. AI page, send 3 consecutive questions  
Expected:
- a single session continues across turns
- `conversation_id` remains stable
- assistant message renders sources and evidence tags when present

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/chat/DrAI.vue
git commit -m "feat: upgrade Dr AI chat UI for agent conversations"
```

### Task 10: Add end-to-end Agent behavior tests

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/test_chat_agent_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_urgent_prompt_short_circuits_agent_flow(...):
    response = client.post("/chat/send", json={"message": "我胸痛呼吸困难"}, headers=auth_header)
    assert response.status_code == 200
    assert "请立即就医" in response.json()["reply"]

def test_chat_response_contains_conversation_id(...):
    response = client.post("/chat/send", json={"message": "帮我解释血糖"}, headers=auth_header)
    assert "conversation_id" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_agent_api.py -v`
Expected: FAIL because the upgraded endpoint behavior is not fully wired yet

- [ ] **Step 3: Adjust fixtures and mocks to support Agent flow**

```python
app.dependency_overrides[get_session] = get_session_override
```

- [ ] **Step 4: Run API tests again**

Run: `pytest tests/test_chat_agent_api.py -v`
Expected: PASS

- [ ] **Step 5: Run the final focused suite**

Run: `pytest tests/test_chat_conversation_models.py tests/test_conversation_service.py tests/test_agent_tools.py tests/test_agent_tool_safety.py tests/test_chat_agent_safety.py tests/test_agent_audit.py tests/test_chat_agent_service.py tests/test_chat_endpoint_contract.py tests/test_chat_agent_api.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_chat_agent_api.py
git commit -m "test: cover agent chat flow end to end"
```

### Task 11: Final docs and rollout note

**Files:**
- Modify: `docs/superpowers/specs/2026-03-24-health-ai-agent-architecture-design.md`
- Modify: `docs/architecture.md`
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model-contract.md`
- Modify: `docs/handoff.md`

- [ ] **Step 1: Update docs to reflect implemented Agent runtime**

```markdown
- chat now supports `conversation_id`
- agent runtime is read-only in phase 1
- sliding-window memory is active
```

- [ ] **Step 2: Run a final targeted smoke check**

Run:
- `pytest tests/test_chat_agent_api.py -v`
- manual chat smoke in browser

Expected:
- API path works
- conversation continuity works
- urgent prompts are safely routed

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-03-24-health-ai-agent-architecture-design.md docs/architecture.md docs/api-contract.md docs/data-model-contract.md docs/handoff.md
git commit -m "docs: document implemented health ai agent architecture"
```

## Definition Of Done

- Chat API accepts and returns `conversation_id`
- Recent conversation turns are persisted server-side
- Sliding-window prompt assembly is active
- Read-only Agent tool registry exists and is enforced by policy
- Urgent health-risk prompts are intercepted before open-ended Agent behavior
- Chat cache keys incorporate conversation-aware context
- Assistant replies can reference sources and lightweight evidence tags
- Focused backend tests and end-to-end chat tests pass
- Architecture and contract docs are updated to match the implementation

## Suggested Execution Order

1. Conversation models
2. Conversation service
3. Chat endpoint contract
4. Tool registry
5. Safety guard
6. Urgent-query classifier
7. Audit helper
8. Chat service Agent refactor
9. Frontend conversation UX
10. End-to-end tests
11. Documentation sync

## Notes For Implementers

- Keep phase 1 strictly read-only for tools
- Do not expose full internal reasoning to frontend users
- Prefer structured decision summaries over raw `<think>` capture
- Do not add vector memory in this implementation pass
- Reuse current RAG, OCR, profile, and trend services as the fact layer rather than inventing a new memory system
