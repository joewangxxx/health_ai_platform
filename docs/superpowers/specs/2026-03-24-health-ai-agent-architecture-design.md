# Health AI Platform 2.0 Agent Architecture Design

## Meta

- Author: `orchestrator + architect`
- Date: `2026-03-24`
- Status: `approved_for_planning`
- Scope: `Design only, no runtime implementation in this document`
- Repository: `E:\health_ai_platform_2.0`

## 1. Background

The current Health AI Platform already includes:

- Vue 3 frontend interaction surfaces
- FastAPI backend APIs
- OCR upload and parsing
- RAG-based medical knowledge retrieval
- Health-risk analysis
- User profile and historical trend management

However, the current intelligent experience is still closer to a "single-turn RAG chat service" than a true Agent system. The current implementation in [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) primarily performs:

- user profile context injection
- RAG retrieval
- one-shot model response generation
- cache lookup and writeback

It does not yet provide:

- server-side multi-turn conversation state
- structured tool registration and execution
- explicit safety interception for tool use
- bounded Agent reasoning and action loops
- auditable Agent decision records

To make the platform richer and more academically complete as an undergraduate graduation project, this design proposes a controlled Agent upgrade built on the existing repository rather than a full autonomous agent platform rewrite.

## 2. Design Goal

Upgrade the platform from a plain chat-based health assistant into a controlled medical-health Agent that can:

- maintain short multi-turn context
- decide when tools are needed
- call internal read-only tools safely
- ground answers in profile data, risk outputs, trends, OCR, and RAG evidence
- provide stronger system-level safety and auditability

This design intentionally avoids over-engineering. It does not aim to build an unrestricted autonomous system. It aims to build a practical, explainable, and defendable Agent architecture that is suitable for a graduation project.

## 3. Non-Goals

The following are explicitly out of scope for the first Agent upgrade:

- autonomous write-back to medical records
- autonomous modification of user profile state
- autonomous diagnosis or prescription behavior
- long-term vectorized conversation memory
- generalized workflow planning across the whole platform
- multi-agent collaboration at runtime

These exclusions are deliberate. They reduce medical safety risk and keep the implementation aligned with the current system maturity.

## 4. Option Analysis

### Option A: Strengthen Existing Chat Only

Keep the current chat architecture and only improve:

- system prompt
- RAG retrieval quality
- answer formatting
- profile context injection

Pros:

- minimal cost
- easiest to deliver

Cons:

- weak Agent identity
- limited design novelty for a graduation project
- no tool governance or decision-layer structure

### Option B: Controlled Lightweight Agent

Build a bounded Agent layer on top of the current chat service with:

- sliding-window conversation memory
- read-only tool registry
- bounded tool loop
- safety interception
- audit records

Pros:

- significantly richer than plain chat
- still aligned with current codebase
- easy to explain in thesis and defense
- safer for medical scenarios

Cons:

- requires moderate refactoring of chat flow
- needs new conversation and tool abstractions

### Option C: Full Autonomous Agent

Introduce:

- complex planning
- persistent memory
- read/write tools
- broader autonomous execution

Pros:

- strongest "Agent" label

Cons:

- too risky for medical domain
- too large for current repository maturity
- difficult to justify and verify in an undergraduate project

## 5. Recommended Approach

Choose **Option B: Controlled Lightweight Agent**.

This option provides the best balance between:

- project richness
- architecture clarity
- implementation feasibility
- medical safety
- thesis explainability

## 6. Architecture Summary

### 6.1 High-Level Flow

`User Query -> Safety Classifier -> Context Builder -> Sliding Window -> Agent Reasoning -> Tool Execution -> Evidence Synthesis -> Final Answer -> Audit Log`

### 6.2 Key Principle

The model must not be treated as the source of truth.

Truth must come from:

- user profile
- health history
- OCR summaries
- risk outputs
- platform knowledge base

The Agent's role is to organize, retrieve, and explain these facts, not invent them.

## 7. Architecture Layers

### 7.1 Conversation Layer

This layer introduces minimal server-side conversation management.

Responsibilities:

- create and track `conversation_id`
- persist recent conversation turns
- reconstruct the active prompt window
- slice history using a sliding window

Design choice:

- keep only the system prompt plus the latest 5 to 10 rounds
- do not build vectorized long-term chat memory in phase 1

Rationale:

- the platform already has durable fact memory in profile, history, OCR, and RAG
- vectorized conversation memory would add complexity without strong initial value

### 7.2 Safety Classification Layer

This layer runs before the Agent planning loop.

Responsibilities:

- identify urgent health-risk prompts
- detect disallowed operations
- route high-risk content to safe response templates

Target trigger examples:

- chest pain
- severe shortness of breath
- syncope
- suicidal ideation
- acute drug reaction

If such patterns are detected, the system should prioritize urgent-care guidance and avoid open-ended tool reasoning.

### 7.3 Context Builder Layer

This layer gathers and compresses the minimum necessary system facts for the current turn.

Sources:

- current `UserProfile`
- latest risk report or risk history snapshot
- OCR-derived medical document summaries
- health history trends
- RAG search results

Responsibilities:

- convert raw structured data into compact model-facing context
- avoid passing entire records directly when not needed
- generate a stable evidence summary used by the Agent loop

### 7.4 Agent Reasoning Layer

This is the decision layer.

Responsibilities:

- determine user intent
- decide whether tools are necessary
- choose which tools to call
- decide whether enough evidence exists for a grounded answer

Important constraint:

This design does **not** depend on exposing raw full chain-of-thought to users.

Instead, the system records a structured internal decision summary such as:

- `intent`
- `tool_needed`
- `tool_plan`
- `evidence_source`
- `safety_level`

This gives explainability without relying on unstable or privacy-sensitive full hidden reasoning output.

### 7.5 Tool Execution Layer

This layer executes internal tools under strict safety constraints.

A new module is proposed:

- [agent_tools.py](E:\health_ai_platform_2.0\backend\services\agent_tools.py)

Core mechanism:

- register tools using an `@agent_tool(...)` decorator
- attach metadata such as name, description, scope, read/write nature, and schema
- validate arguments before execution
- reject unauthorized calls

Recommended initial decorator metadata:

- `name`
- `description`
- `read_only`
- `scope`
- `args_schema`

Example scopes:

- `self_only`
- `admin_only`
- `system_only`

### 7.6 Evidence Synthesis Layer

This layer merges tool outputs and prepared evidence into the final answer prompt.

Responsibilities:

- combine retrieved facts
- preserve citations and sources
- instruct the model to answer conservatively
- prevent unsupported speculation

### 7.7 Audit Layer

This layer records Agent execution behavior for monitoring and later thesis analysis.

Recommended audit fields:

- `user_id`
- `conversation_id`
- `query`
- `intent`
- `tool_used`
- `tool_args_summary`
- `tool_result_status`
- `safety_level`
- `latency_ms`
- `cache_hit`

This layer is critical for both engineering visibility and defense presentation value.

## 8. Tool Strategy

### 8.1 Phase-1 Tool Policy

Only read-only tools are enabled in the first version.

This is a hard system policy.

The Agent must not be allowed to:

- modify patient profile
- write risk state
- delete reports
- trigger admin data pipelines
- mutate records autonomously

### 8.2 Recommended Initial Tools

#### `get_user_profile_summary`

Purpose:

- retrieve a safe summary of the current user's profile

Use cases:

- explain health status
- answer personalized advice questions

#### `get_latest_risk_report`

Purpose:

- retrieve the latest available risk result or parsed risk snapshot

Use cases:

- explain risk levels
- answer follow-up questions about previous analysis

#### `get_history_trends`

Purpose:

- return recent trends for key indicators

Use cases:

- compare changes over time
- answer "is it getting better?" style questions

#### `search_medical_guidelines`

Purpose:

- query platform RAG knowledge base for guideline evidence

Use cases:

- support evidence-grounded medical explanations
- answer disease-management questions

#### `get_uploaded_documents_summary`

Purpose:

- retrieve OCR summaries from uploaded documents

Use cases:

- help the Agent reference extracted health findings

## 9. Integration With Existing Repository

### 9.1 Current Relevant Files

Current foundation files include:

- [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py)
- [chat.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\chat.py)
- [rag_service.py](E:\health_ai_platform_2.0\backend\services\rag_service.py)
- [ocr_service.py](E:\health_ai_platform_2.0\backend\services\ocr_service.py)
- [models.py](E:\health_ai_platform_2.0\backend\models.py)
- [healthStore.js](E:\health_ai_platform_2.0\frontend\src\stores\healthStore.js)
- [DrAI.vue](E:\health_ai_platform_2.0\frontend\src\views\chat\DrAI.vue)

### 9.2 Proposed New Backend Modules

Recommended additions:

- [agent_tools.py](E:\health_ai_platform_2.0\backend\services\agent_tools.py)
- `conversation_service.py`
- `agent_safety.py`
- `agent_audit.py`

These can remain lightweight modules with clear single responsibilities.

### 9.3 Main Backend Refactor Target

The primary implementation focus should be [chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py).

It should evolve from:

- profile + RAG + single-turn completion

into:

- context builder
- sliding-window prompt assembly
- bounded Agent loop
- tool execution orchestration
- audit and safety integration

### 9.4 Frontend Impact

The chat UI in [DrAI.vue](E:\health_ai_platform_2.0\frontend\src\views\chat\DrAI.vue) should be enhanced to support:

- `conversation_id`
- multi-turn rendering
- optional evidence/source badges
- optional lightweight status hints such as:
  - "已参考体检档案"
  - "已检索医学指南"
  - "已结合趋势数据"

The frontend should not display full internal reasoning.

## 10. Memory Strategy

### 10.1 Decision

Use only a **sliding window** for conversation memory in phase 1.

### 10.2 Rationale

- simpler implementation
- lower latency
- lower token cost
- easier to explain academically
- avoids premature memory-system over-design

### 10.3 Long-Term Fact Memory Source

Long-term factual memory should come from:

- user profile
- risk records
- trend history
- OCR summaries
- RAG knowledge base

This keeps the platform grounded in structured system facts rather than chat transcript accumulation.

## 11. Safety Design

### 11.1 Medical Safety Rules

The system must:

- avoid diagnosis claims framed as definitive medical conclusions
- avoid treatment or prescription instructions beyond general advice
- encourage formal medical consultation for serious findings
- prioritize emergency referral for urgent symptom patterns

### 11.2 Tool Safety Rules

- write tools are disabled in phase 1
- all tool arguments must be schema-validated
- unauthorized tool calls return structured rejection payloads
- the model should then generate a compliant refusal or apology

### 11.3 Privacy Rules

- do not expose full hidden reasoning externally
- keep audit logs structured and minimal
- ensure only current-user data is visible to self-scoped tools

## 12. Cache Design Adjustment

The current chat cache design is based mostly on user and normalized query.

That is insufficient for a multi-turn Agent conversation.

The upgraded cache key should include at least:

- `conversation_id`
- recent history hash
- profile-context hash
- current query hash

This prevents incorrect cache reuse when the same question appears in different contexts.

## 13. Verification Plan

### 13.1 Unauthorized Tool Use

Test case:

- induce the model to perform a write-style action

Expected:

- tool layer rejects the operation
- final response remains compliant and apologetic

### 13.2 Sliding Window Behavior

Test case:

- create more than 20 dialogue turns

Expected:

- only the configured window is sent to the model
- token growth remains bounded

### 13.3 Multi-Step Tool Logic

Test case:

- ask a question requiring both guideline lookup and risk lookup

Expected:

- tool order is logical
- max step count is respected

### 13.4 Emergency Routing

Test case:

- send urgent symptom text such as chest pain and dyspnea

Expected:

- system returns urgent medical guidance
- no unnecessary free-form tool loop

### 13.5 Cache Correctness

Test case:

- same question under different recent-history contexts

Expected:

- different context hashes produce different cache behavior

## 14. Implementation Phases

### Phase 1: Multi-Turn Foundation

- add `conversation_id`
- persist conversation turns
- implement sliding-window prompt assembly

### Phase 2: Read-Only Agent Tools

- create tool registry
- connect profile, risk, trend, OCR, and guideline tools
- add bounded tool loop

### Phase 3: Safety And Audit

- add urgent safety classifier
- add structured decision summaries
- add audit log recording

### Phase 4: UX Enrichment

- show conversation continuity
- show evidence/source indicators
- improve Agent-state visibility in chat UI

Implementation note as of 2026-03-24:

- Phase 1 is implemented
- Phase 2 is implemented with backend-owned read-only tools and bounded tool selection
- Phase 3 is implemented for the current runtime slice with urgent safety routing, structured decision summaries, and audit records
- Phase 4 is partially implemented with conversation continuity and evidence/source indicators in the chat UI

## 15. Expected Graduation-Project Value

After the upgrade, the platform can present the following as key project innovations:

- transformation from plain Q and A into a medical-health Agent
- controlled tool calling under safety constraints
- multi-turn personalized context management
- evidence-grounded health explanation
- auditable Agent execution
- lightweight and explainable architecture suitable for real healthcare scenarios

This is strong enough to significantly enrich the graduation project without making the system unreasonably complex.

## 16. Final Decision

The platform should adopt a **controlled lightweight Agent architecture** rather than a full autonomous agent system.

This design is the best match for:

- current repository maturity
- medical-domain safety needs
- implementation feasibility
- thesis explainability
- demonstration richness

## 17. Next Step

After user review of this design document, the next stage should be an implementation plan that decomposes the work into backend, frontend, safety, testing, and rollout tasks.
