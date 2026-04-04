# Task Plan: Adapt Multi-Agent Workflow To Health AI Platform

## Goal
Operate the adapted multi-agent workflow inside `E:\health_ai_platform_2.0`, keeping governance state, PM scope, and architect contracts aligned with the real codebase.

## Current Phase
Phase 53

## Phases

### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify source workflow materials
- [x] Document current-project constraints and fit points
- **Status:** complete

### Phase 2: Workflow Mapping
- [x] Identify reusable orchestration patterns
- [x] Identify project-specific role and gate changes
- [x] Define minimal viable migration scope
- **Status:** complete

### Phase 3: Migration Plan Drafting
- [x] Draft phased rollout plan
- [x] List files/processes to add or adapt
- [x] Capture risks, assumptions, and validation steps
- **Status:** complete

### Phase 4: Review & Alignment
- [x] Present approaches and recommendation
- [x] Present proposed design for approval
- [x] Refine plan based on feedback
- **Status:** complete

### Phase 5: Delivery
- [x] Deliver the non-executing migration plan
- [x] Leave repository ready for later execution
- [x] Install the approved workflow scaffold
- **Status:** complete

### Phase 6: Full Codebase Review & Gate Advancement
- [x] Browse the full tracked codebase before advancing architect review
- [x] Reconcile architect docs against actual routes, models, services, ETL, frontend views, and tests
- [x] Open downstream implementation gates only after repository-wide review
- **Status:** complete

### Phase 7: Agent Upgrade Design
- [x] Analyze whether the current platform should adopt a lightweight or heavy Agent model
- [x] Define the target Agent architecture based on current repository reality
- [x] Write a formal design spec for user review before implementation planning
- **Status:** complete

### Phase 8: Agent Upgrade Implementation Planning
- [x] Convert the approved Agent design into executable implementation chunks
- [x] Identify exact backend, frontend, safety, and test files for the rollout
- [x] Save a formal implementation plan document for later execution
- **Status:** complete

### Phase 9: Agent Upgrade Implementation - Phase 1 Conversation Foundation
- [x] Add persistent conversation and message models
- [x] Add conversation service helpers and sliding-window builder
- [x] Extend `/chat/send` with `conversation_id`
- [x] Persist user/assistant messages in `chat_service`
- [x] Update the chat frontend to keep session continuity
- [x] Add targeted backend tests and run focused verification
- **Status:** complete

### Phase 10: Agent Upgrade Implementation - Controlled Runtime Slice
- [x] Add read-only Agent tool registry
- [x] Add tool safety policy and urgent-query routing
- [x] Add audit helper and structured decision summary output
- [x] Refactor `chat_service` to use bounded tool selection and evidence synthesis
- [x] Extend chat API/front-end contract with `evidence_tags` and Agent metadata
- [x] Run focused backend/API verification and frontend production build
- [x] Sync blackboard and architecture/API/data-model docs to the implemented slice
- **Status:** complete

### Phase 11: Agent Upgrade Implementation - SSE Feedback Layer
- [x] Add a streaming chat endpoint that emits staged Agent progress events
- [x] Refactor the backend chat runtime so sync and stream paths share the same controlled flow
- [x] Update Dr. AI to render live SSE process feedback with a standard-request fallback
- [x] Add focused streaming tests and re-run full regression
- [x] Sync blackboard and QA records to the SSE-enhanced slice
- **Status:** complete

### Phase 12: Frontend Bundle Optimization
- [x] Convert main routed views to lazy-loaded imports
- [x] Add Vite manual chunking for Vue core, markdown, Element Plus, and ECharts/ZRender
- [x] Add focused regression coverage for bundle-splitting configuration
- [x] Re-run frontend production build and verify the large-chunk warning is removed
- [x] Re-run full repository regression and sync workflow records
- **Status:** complete

### Phase 13: Deployment Smoke Rehearsal
- [x] Execute a real Docker Compose smoke rehearsal against the current workspace
- [x] Identify and fix runtime deployment blockers in compose and container startup configuration
- [x] Add regression coverage for deployment runtime config
- [x] Re-run tests after deployment fixes
- [x] Record smoke outcome and gate decision in QA and blackboard
- [x] Rebuild the backend image and validate deployed auth/chat behavior end to end
- **Status:** complete

### Phase 14: Post-Release Roadmap Planning
- [x] Define the next upgrade horizon after the release-ready Agent baseline
- [x] Group future work into runtime, frontend, delivery, and thesis-support tracks
- [x] Save a formal roadmap plan document under `docs/superpowers/plans`
- [x] Sync planning records to task/progress/findings docs
- **Status:** complete

### Phase 15: Post-Release Runtime Hardening - Context Budgeting
- [x] Review the current chat runtime and choose the smallest safe insertion point for bounded context assembly
- [x] Add failing tests for section trimming and history-budget retention
- [x] Implement a dedicated context builder and connect it to `chat_service`
- [x] Run focused tests and full repository regression
- [x] Sync architecture and workflow records to the validated slice
- **Status:** complete

### Phase 16: Post-Release Runtime Hardening - Native Function Calling
- [x] Add failing tests for OpenAI-compatible tool definitions and native tool-calling preference
- [x] Extend the read-only tool registry with provider-facing function schemas and argument validation
- [x] Refactor `chat_service` to prefer native tool calling and fall back to deterministic local planning
- [x] Re-run focused tool/service/API tests and full repository regression
- [x] Sync architecture, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 17: Post-Release Session UX - Conversation History
- [x] Add failing tests for conversation summaries, stored-message loading, and auto-generated titles
- [x] Extend the backend conversation service and chat API with history-list and history-detail reads
- [x] Update `DrAI.vue` with a history sidebar, session switching, and a new-conversation reset
- [x] Re-run focused chat/session tests, frontend build, and full repository regression
- [x] Sync contract, architecture, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 18: Post-Release Session UX - Historical Metadata Replay
- [x] Add failing tests for persisted assistant metadata in conversation detail responses
- [x] Persist `sources`, `evidence_tags`, and `decision_summary` on `ChatMessage`
- [x] Replay stored assistant metadata through the history-detail API and `DrAI.vue`
- [x] Re-run focused metadata tests, frontend build, and full repository regression
- [x] Sync contract, architecture, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 19: Post-Release Session UX - Search, Archive, and Title Summaries
- [x] Add failing tests for natural title summaries plus search/archive conversation management
- [x] Add backend archive state, conversation filters, and title-summarization heuristics
- [x] Update `DrAI.vue` with conversation search and archive/restore controls
- [x] Re-run focused conversation-management tests, frontend build, and full repository regression
- [x] Sync contract, architecture, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 20: Post-Release Session UX - Pinning And Recent-Access Ordering
- [x] Add failing tests for pinned-first ordering, recent-access refresh, and pin/unpin controls
- [x] Add backend pin/access metadata and stable server-owned ordering semantics
- [x] Extend chat conversation APIs with pin/unpin actions and ordering metadata
- [x] Update `DrAI.vue` with visible pin state and pin/unpin controls
- [x] Re-run focused session-ordering tests, frontend build, and full repository regression
- [x] Sync contract, architecture, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 21: Post-Release Platform Optimization Planning
- [x] Re-scan the current post-release roadmap and latest implemented slices
- [x] Convert remaining platform-only optimization opportunities into a formal backlog plan
- [x] Exclude thesis/defense deliverables from this planning pass
- [x] Save the optimization backlog under `docs/superpowers/plans`
- [x] Sync planning records to task/progress/findings docs
- **Status:** complete

### Phase 22: Post-Release Agent UX - Suggestion Cards And Tool-Level SSE
- [x] Confirm the minimum design for structured suggestion cards and tool-level SSE events before implementation
- [x] Add failing tests for `suggestion_card` API/history behavior and `tool_start`/`tool_done` SSE events
- [x] Persist assistant `suggestion_card` metadata and return it through sync, stream, and replay paths
- [x] Extend the Dr. AI frontend to render suggestion cards and tool-level progress events
- [x] Re-run focused chat/frontend tests, frontend production build, and full repository regression
- [x] Sync contract, architecture, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 23: Post-Release Session UX - Manual Rename And Backend-Owned Grouping
- [x] Freeze the contract for manual rename and backend-owned grouping metadata through an architect handoff
- [x] Run backend implementation in a dedicated BE agent with TDD-first focused tests
- [x] Run frontend implementation in a dedicated FE agent with grouped sidebar rendering and rename UI
- [x] Run QA as a separate validation agent across focused tests, full pytest, and frontend production build
- [x] Sync contract, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 24: Post-Release Agent UX - C3 Evidence Panel
- [x] Freeze the C3 evidence panel contract through an architect-only stage
- [x] Run backend implementation in a dedicated BE agent with TDD-first focused tests
- [x] Run frontend implementation in a dedicated FE agent against the frozen contract
- [x] Run QA as a separate validation agent across focused tests, full pytest, and frontend production build
- [x] Sync contract, QA, and workflow records to the validated slice
- **Status:** complete

### Phase 25: Post-Release Read-Only Tool Expansion
- [x] Freeze the next safe read-only tool slice through an architect-only stage
- [x] Run backend implementation in a dedicated BE agent with TDD-first focused tests
- [x] Review backend handoff, update workflow records, and report the stage result
- **Status:** in progress

### Phase 26: Canonical Health Payload Normalization
- [x] Freeze canonical shapes and normalization boundaries for `ocr_summary`, `risk_snapshot`, and `risk_history`
- [x] Review architect handoff, update workflow records, and report the stage result
- [x] Run backend implementation for the shared normalization layer, canonical write path, and scan path
- [x] Review backend handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA validation for canonical health-payload normalization
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 27: Expanded Agent Audit Detail
- [x] Select the next unfinished backlog slice according to the approved priority order
- [x] Run backend implementation for additive audit metadata under the current contract boundary
- [x] Review backend handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA validation for expanded Agent audit detail
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 28: Legacy Conversation Title Repair
- [x] Re-sync the next slice against the current blackboard and backlog before dispatch
- [x] Confirm no contract-refresh is needed for the repair slice
- [x] Run backend implementation for default-title repair and optional repair tooling
- [x] Review backend handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA validation for the legacy-title repair slice
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 29: Batch Archive Hooks Contract Refresh
- [x] Re-sync the next slice against the current blackboard and backlog before dispatch
- [x] Recognize batch archive/delete preparation as a contract-affecting slice
- [x] Run architect-only contract freeze for additive batch archive operations
- [x] Review architect handoff, run parent-thread doc verification, and update workflow records
- [x] Dispatch implementation only after the contract is frozen
- [x] Run BE implementation for batch archive prepare/archive backend behavior and focused backend tests
- [x] Run FE implementation for sidebar multi-select archive flow under the frozen contract
- [x] Review implementation handoffs, run fresh parent-thread verification, and update workflow records
- [x] Run QA validation for the batch archive hooks slice
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 30: Batch Restore Hooks Contract Refresh
- [x] Re-sync the next slice against the current blackboard and existing batch archive contract
- [x] Recognize batch restore hooks as a contract-affecting slice
- [x] Run architect-only contract freeze for additive batch restore operations
- [x] Review architect handoff, run parent-thread doc verification, and update workflow records
- [x] Dispatch implementation only after the contract is frozen
- [x] Run BE implementation for batch restore prepare/restore backend behavior and focused backend tests
- [x] Run FE implementation for archived-sidebar multi-select restore flow under the frozen contract
- [x] Review implementation handoffs, run fresh parent-thread verification, and update workflow records
- [x] Run QA validation for the batch restore hooks slice
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 31: Conversation Management Browser Smoke / E2E Validation
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the slice is validation-only and does not require an architecture change request
- [x] Dispatch FE only for browser-level smoke test infrastructure and Dr. AI conversation-management coverage
- [x] Review FE handoff, run fresh parent-thread verification, and update workflow records
- [x] Dispatch QA only after FE delivery is verified
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 32: Legacy Health Payload Repair / Backfill
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the slice stays within the frozen canonical payload contract and does not require a new architecture change request
- [x] Dispatch BE only for repair/backfill implementation and focused backend verification
- [x] Review BE handoff, run fresh parent-thread verification, and update workflow records
- [x] Dispatch QA only after backend delivery is verified
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 33: Live Backend Integrated E2E
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the slice is validation/integration-only and does not require a new architecture change request
- [x] Dispatch FE only for live-backend integrated E2E implementation and focused verification
- [x] Review FE handoff, run fresh parent-thread verification, and update workflow records
- [x] Dispatch QA only after FE delivery is verified
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 34: Backend Startup Hygiene For Live E2E
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the slice is backend-owned runtime hygiene and does not require a new architecture change request
- [x] Dispatch BE only for startup hygiene implementation and focused verification
- [x] Review BE handoff, run fresh parent-thread verification, and update workflow records
- [x] Perform manual file restoration after BE retry limit was reached
- [x] Re-verify restored backend files compile cleanly before re-dispatch
- [x] Dispatch QA only after backend delivery is verified
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- [x] Re-review the revised BE handoff after the parent-thread defect return
- **Status:** complete

### Phase 35: Evidence Source Drill-Down Contract Refresh
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the slice is contract-affecting and requires an architecture change request
- [x] Dispatch architect only for additive evidence-source drill-down contract freeze
- [x] Review architect handoff, run parent-thread doc verification, and update workflow records
- [x] Dispatch BE/FE implementation only after the contract is frozen
- [x] Review BE/FE implementation handoffs, run fresh parent-thread verification, and update workflow records
- [x] Run QA after implementation evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 36: Audit Persistence Contract Refresh
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the slice is contract-affecting and requires an architecture change request
- [x] Dispatch architect only for audit-store persistence boundary freeze
- [x] Review architect handoff, run parent-thread doc verification, and update workflow records
- [x] Dispatch BE implementation only after the contract is frozen
- [x] Review BE handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after implementation evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 37: Startup Noise Cleanup
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Re-sync the optimization backlog against the validated audit-persistence slice
- [x] Select `startup noise cleanup` as the next backend-owned remediation slice
- [x] Confirm no architecture change request is required if the work stays within runtime hygiene and log-noise cleanup
- [x] Dispatch BE only for startup-noise cleanup implementation and focused verification
- [x] Review BE handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after implementation evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 38: Broader Logging-Policy Cleanup
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Re-sync the remaining backend hygiene backlog against the validated startup-noise cleanup slice
- [x] Select `broader logging-policy cleanup` as the next backend-owned remediation slice
- [x] Confirm no architecture change request is required if the work stays within backend runtime hygiene and log-policy normalization
- [x] Dispatch BE only for broader logging-policy cleanup implementation under the frozen contract boundary
- [x] Review BE handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after implementation evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 39: Comprehensive Test Cases And Browser Validation
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Classify the request as a QA-only validation slice with no contract or implementation changes
- [x] Dispatch QA only for detailed test-case authoring in `docs/qa-report.md` plus browser-driven verification
- [x] Review QA handoff, run fresh parent-thread browser verification, and update workflow records
- **Status:** complete

### Phase 40: Cross-Browser E2E
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Confirm the remaining gap is browser-coverage only and does not require an architecture change request
- [x] Dispatch FE only for minimal Playwright config/test updates to extend coverage beyond Chromium
- [x] Review FE handoff, run fresh parent-thread browser verification, and update workflow records
- [x] Run QA after cross-browser evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 41: Additional Safe Read-Only Tools
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Classify the slice as contract-affecting because it expands backend-internal tool boundaries and approved fact-source usage
- [x] Route the slice to `architect` first so tool names, scopes, bounded result shapes, and evidence exposure rules are frozen before any BE work begins
- [x] Review architect handoff, run fresh parent-thread doc verification, and update workflow records
- [x] Dispatch `be` only for backend implementation under the frozen contract
- [x] Review `be` handoff, run fresh parent-thread focused/full verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 42: RAG Chunking Optimization
- [x] Re-read workflow rules and current blackboard state before dispatch
- [x] Classify the slice as contract-affecting because it changes internal KB chunking boundaries, metadata expectations, and retrieval assumptions
- [x] Route the slice to `architect` first so recursive chunking rules, metadata floor, and explicit non-goals are frozen before any BE work begins
- [x] Review architect handoff, run fresh parent-thread doc verification, and update workflow records
- [x] Dispatch `be` only for backend implementation under the frozen contract
- [x] Review `be` handoff, run fresh parent-thread focused/full verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 43: RAG Chunk Metadata Stabilization
- [x] Re-read workflow rules, blackboard state, and frozen RAG chunking contract before dispatch
- [x] Confirm the slice stays within the already-frozen internal RAG metadata contract and does not require a new architecture change request
- [x] Dispatch `be` only for backend-owned `section_title` / `page_range` stabilization and focused tests
- [x] Review `be` handoff, run fresh parent-thread focused/full verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 44: RAG Live Corpus Benchmark
- [x] Re-read workflow rules, blackboard state, and frozen RAG chunking contract before dispatch
- [x] Confirm the slice stays within the already-frozen internal RAG contract and does not require a new architecture change request
- [x] Dispatch `be` only for backend-owned live-corpus benchmark tooling and focused tests
- [x] Review `be` handoff, run fresh parent-thread focused/full verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 45: RAG PDF Extraction Quality Remediation
- [x] Re-read workflow rules, blackboard state, and current RAG benchmark evidence before dispatch
- [x] Confirm the slice stays within the already-frozen internal RAG contract and does not require a new architecture change request
- [x] Dispatch `be` only for backend-owned PDF extraction quality remediation and focused tests
- [x] Review `be` handoff, run fresh parent-thread focused/full verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 46: Residual Risk Backlog Formalization
- [x] Re-read workflow rules and current blackboard state before planning
- [x] Consolidate current non-blocking residual risks from blackboard, findings, and QA records
- [x] Convert residual risks into a formal backlog document with bounded slice definitions
- [x] Recommend an execution order grouped by value and implementation cost
- [x] Sync planning records to task/progress/findings docs
- **Status:** complete

### Phase 47: PDF Low-Text-Density Diagnostics
- [x] Re-read workflow rules, blackboard state, and the formal residual-risk backlog before dispatch
- [x] Confirm the slice stays inside the frozen RAG contract and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 48: OCR Fallback Capability Signaling
- [x] Re-read workflow rules, current blackboard state, and the residual-risk backlog before dispatch
- [x] Confirm the slice stays inside the frozen RAG contract and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 49: Loader Fallback Warning Cleanup
- [x] Re-read workflow rules, current blackboard state, and the residual-risk backlog before dispatch
- [x] Confirm the slice stays inside the frozen RAG contract and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 50: Section Title Stabilization Enhancement
- [x] Re-read workflow rules, current blackboard state, and the residual-risk backlog before dispatch
- [x] Confirm the slice stays inside the frozen RAG contract and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 51: Page Range Capability Evaluation
- [x] Re-read workflow rules, current blackboard state, and the residual-risk backlog before dispatch
- [x] Confirm the slice stays inside the frozen RAG contract and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 52: Section Title Coverage Uplift
- [x] Re-read workflow rules, current blackboard state, and the remaining residual-risk backlog before dispatch
- [x] Confirm the slice stays inside the frozen RAG contract and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 53: Pydantic Deprecation Cleanup
- [x] Re-read workflow rules, current blackboard state, and the remaining residual-risk backlog before dispatch
- [x] Confirm the slice stays inside backend/runtime hygiene boundaries and does not require an architecture change request
- [x] Advance blackboard and tracking records to route the slice to `be`
- [x] Review `be` handoff, run fresh parent-thread verification, and update workflow records
- [x] Run QA after backend evidence exists
- [x] Re-run fresh parent-thread verification after QA and update workflow records
- **Status:** complete

### Phase 54: Repository Optimization Re-Scan And Planning
- [x] Re-scan the current repository state across runtime behavior, regression status, RAG quality, frontend build output, and repository hygiene
- [x] Convert the scan into a formal optimization checklist and phased execution plan
- [x] Save the optimization plan under `docs/superpowers/plans`
- [x] Sync planning records to `task_plan.md`, `progress.md`, and `findings.md`
- **Status:** complete

## Key Questions
1. Which parts of the MutiData-Nexus workflow are process-only and can transfer directly?
2. Which parts depend on that repository's architecture and need to be redefined for the health AI platform?
3. What is the smallest safe rollout that introduces orchestration discipline without disrupting current development?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Start with discovery and planning only | User explicitly asked for a plan before any execution |
| Use file-backed planning notes in the project root | This task spans multiple artifacts and comparisons |
| Base the migration on governance primitives from the source workflow | Orchestrator, blackboard, gate, and handoff patterns are already validated there |
| Recommend an adapted, incremental rollout instead of a literal copy | The target repo differs in stack, docs, and active development state |
| Remove the `designer` role from the target workflow | This repository does not need a Figma-to-code role in its multi-agent operating model |
| Install only the governance scaffold in this execution pass | This keeps the rollout additive and avoids interfering with the repository's active feature work |
| Require a full tracked-code scan before approving architect contracts | Prevents advancing gates based on partial repository context |
| Prefer a controlled lightweight Agent over a full autonomous Agent | Better fits the current codebase, the medical domain, and undergraduate project scope |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `rg.exe` could not run due to access denied | 1 | Switched to PowerShell file enumeration commands |
| Recursive scan for local instruction files timed out | 1 | Narrow future scans to targeted directories |

## Notes
- Prioritize transferable process rules over project-specific implementation details.
- Reassign any design-token or UI-consistency concerns to `fe` instead of creating a separate `designer` lane.
- Current workflow state is past planning: PM and architect contracts are approved and `implementation_ready` is open.
- Agent-upgrade implementation should not begin until the written design spec is reviewed and accepted as the execution baseline.
- Agent-upgrade design is now accepted and the execution baseline is the implementation plan in `docs/superpowers/plans/2026-03-24-health-ai-agent-architecture-implementation.md`.
- Phase 1 implementation is now complete; the next planned slice is the read-only tool registry and execution boundary.
- The controlled Agent runtime slice is now complete; the next likely slice is richer frontend Agent-state feedback and broader integration verification.
- Richer frontend Agent-state feedback and focused QA closure are now complete; the next likely slice is broader cross-module regression and any optional UX streaming enhancements.
- Broader cross-module regression is now complete; the next likely slice is general handoff/release preparation or optional streaming-style UX improvements.
- General handoff/release preparation is now complete; the next likely slice is orchestrator release review or a real deployment smoke rehearsal.
- Orchestrator release review is now complete; the next likely slice is a real deployment smoke rehearsal before opening `release_ready`.
- SSE-style live Agent feedback is now complete; the next likely slice is a real deployment smoke rehearsal or final release sign-off.
- Frontend bundle optimization is now complete; the next likely slice is still a real deployment smoke rehearsal or final release sign-off.
- Deployment smoke rehearsal is now fully validated, and `release_ready` is open for the current increment.
- The next planning slice is now the post-release roadmap for richer graduation-project value after the release-ready baseline.
- The current execution slice is now runtime hardening through bounded context assembly and token budgeting.
- The current execution slice is now runtime hardening through native function-calling preference with deterministic local fallback.
- The current execution slice is now session UX enrichment through conversation history listing and historical session switching.
- The current execution slice is now session UX enrichment through historical replay of stored assistant metadata in conversation history.
- The current execution slice is now session UX enrichment through conversation search, archive/restore management, and more natural title summaries.
- The current execution slice is now session UX enrichment through conversation pinning and stronger recent-access ordering.
- The next likely session-management refinement is conversation-level grouping, batch actions, or smarter title regeneration for old sessions that still use legacy titles.
- The current planning slice is now the post-release platform optimization backlog focused only on product/runtime improvements, not thesis or defense materials.
- The current execution slice is now Agent UX enrichment through structured suggestion cards and tool-level SSE progress events.
- The current execution slice is now session UX refinement through manual conversation rename and backend-owned grouping metadata, executed via architect -> be/fe parallel -> qa handoffs.
- The current execution slice is now Agent UX enrichment through the architect-approved C3 evidence panel contract; BE and FE implementation are the next active stage.
- The current execution slice is now Agent UX enrichment through QA validation of the C3 evidence panel implementation.
- The C3 evidence panel slice is now validated end to end under the repository multi-agent workflow; the next optimization slice can be selected from the remaining backlog.
- The current execution slice is now the safe read-only tool expansion: architect has frozen the three-tool contract and backend implementation is the active next stage.
- The current execution slice is now the QA handoff for the safe read-only tool expansion; backend implementation is complete and awaiting validation.
- The current execution slice is now canonical health-payload normalization: architect has frozen `ocr_summary.v1` and `risk_snapshot.v1`, and backend normalization is the next stage.
- The current execution slice is now QA validation for canonical health-payload normalization; backend normalization, canonical write-path alignment, and legacy scan reporting are complete.
- The current execution slice is now QA validation for expanded Agent audit detail; backend audit instrumentation is complete and awaiting independent validation.
- The current execution slice is now backend-only legacy-title repair for conversations that still carry default or stale auto-generated titles.
- The current execution slice is now architect-only contract refresh for batch archive hooks before any FE/BE implementation starts.
- The current execution slice is now architect-only contract refresh for batch restore hooks before any FE/BE implementation starts.
- The current execution slice is now browser-level smoke / E2E coverage for Dr. AI conversation management and evidence interactions.
- The current execution slice is now backend-owned legacy health payload repair/backfill under the already-frozen canonical payload contract.
- The current execution slice remains backend-owned startup hygiene for live E2E, but the first fresh BE handoff after manual restore has been returned for a narrow runtime-fix revision.
- The current execution slice is now QA validation for backend startup hygiene after the backend-only revision cleared parent-thread verification.
- The backend startup-hygiene slice is now validated end to end; the next step is to let the orchestrator choose the next backlog item.
- The current execution slice is now the architect-frozen evidence source drill-down contract; implementation dispatch is the next step.
- The evidence source drill-down slice is now validated end to end; the next step is to let the orchestrator choose the next backlog item.
