# Findings & Decisions

## Requirements
- User wants the multi-agent work mode used in `E:\MutiData-Nexus` adapted to `E:\health_ai_platform_2.0`.
- The current turn should stop at planning and must not execute the migration.
- Source materials include `.codex`, `.agents`, `AGENTS.md`, and `docs/blackboard` from the other project.
- User now also wants a formal design for upgrading the platform itself into a richer Agent-based graduation-project system.

## Research Findings
- The source repository uses a parent-thread `Orchestrator` model with a blackboard file as shared workflow state.
- Only the orchestrator is allowed to write workflow state; child agents consume it as read-only context.
- Role ownership is explicit and tied to deliverables, hard limits, and gate order.
- The workflow enforces read order, retry policy, and handoff contents before implementation proceeds.
- The current health AI platform already contains substantial frontend, backend, AI, data, and thesis-related directories, so a direct copy would likely overfit to the source repo's stack and deliverables.
- The source `.codex/config.toml` centralizes project mode, owned docs, workflow stages, gates, and agent registry.
- Source role configs define per-role `entry_gate`, `exit_gate`, allowed reads/writes, forbidden writes, handoff targets, and deliverables.
- The source `shared-policy.md` provides reusable cross-role rules that are likely transferable with minor renaming.
- The source blackboard is not just a status flag file; it is a governance ledger covering gates, dependencies, document status, control ownership, and historically approved notes.
- The health AI platform README and project context indicate a different stack and repo shape from the source project: Vue 3 frontend, FastAPI backend, SQLModel/SQLite persistence, AI/ML modules, data warehouse, and training assets.
- The target repository did not contain an existing `.codex`, `.agents`, or `docs/blackboard` governance scaffold before this change.
- The governance scaffold can be installed additively without touching the currently modified business-code files already present in the dirty worktree.
- PM review found that `docs/PRD.md` and `docs/FEATURE_MAP.md` are directionally aligned on product vision but are not yet approval-ready because acceptance criteria are not crisply auditable and scope/status semantics are inconsistent.
- Architect review found that the same docs are sufficient inputs to begin architecture drafting, but not sufficient to freeze API or data-model contracts.
- PM alignment pass updated `docs/PRD.md` with document-boundary definitions, priority/status semantics, current-version scope, and explicit acceptance criteria for the core flows.
- PM alignment pass updated `docs/FEATURE_MAP.md` to define it as a capability snapshot, clarify that status does not equal gate approval, and reduce misleading top-level priority labels.
- Orchestrator re-review found that the revised PM docs now provide enough scope clarity, acceptance framing, and priority/status semantics to open `prd_ready`.
- Architect drafting pass created a P0-focused architecture baseline, froze the current route-level API surface, and defined canonical current-state entities and model/data boundaries without widening scope into admin or research surfaces.
- A full tracked-code scan has now covered all tracked backend, frontend, ETL, AI-training, root-script, and test files in the repository.
- The codebase scan confirmed that the three architect docs intentionally mirror the current mixed implementation shape: `main.py` still owns several top-level routes, router prefixes are mixed between `/analyze`, `/analysis`, and `/api/v1/*`, and frontend code relies on those current paths rather than a normalized API surface.
- The codebase scan also confirmed that current contracts should stay conservative: response envelopes are mixed, SQLModel table models are still exposed close to API boundaries, and several P1/P2 surfaces already exist in code but should remain outside the current P0 contract freeze.
- Orchestrator review concluded that these mismatches are documented architectural constraints rather than blockers, so `architecture_ready`, `api_contract_ready`, `data_model_contract_ready`, and `implementation_ready` can open together.
- The current `chat_service` is still a single-turn RAG chat service rather than a true Agent runtime: it injects profile context, performs retrieval, calls the model once, strips `<think>` output if present, and caches the final answer.
- A suitable graduation-project Agent upgrade for this repository should therefore be a controlled lightweight Agent with server-side short-memory windows, read-only tool calls, safety interception, and audit logging, rather than a full autonomous write-capable agent.
- Sliding-window conversation memory is the preferred design choice over early vectorized conversation memory because long-term factual memory already exists in structured platform data and the RAG knowledge base.
- The approved design has now been decomposed into an implementation plan covering conversation persistence, tool registration, safety interception, audit logging, chat-service refactor, frontend conversation UX, and end-to-end verification.
- Phase 1 implementation is now in place: the backend has persistent `ChatConversation` and `ChatMessage` models, a reusable conversation service, and `/chat/send` now supports `conversation_id`.
- The current `chat_service` has been upgraded from pure single-turn RAG to a minimal multi-turn foundation: it stores both sides of the exchange and rebuilds the model input from a short recent window.
- The frontend `DrAI` view now keeps the active `conversation_id` and sends it with follow-up messages, enabling server-owned session continuity.
- The Phase 1 verification slice passes in this environment with isolated mocks for RAG/OCR/PDF-related imports.
- The current runtime has now advanced into a controlled Agent slice: read-only tool registry, self-scoped tool access policy, urgent-query safety routing, structured decision summaries, audit-record generation, and evidence-tag output are implemented.
- `/chat/send` now returns backend-owned Agent metadata fields in addition to the reply: `conversation_id`, `sources`, `evidence_tags`, and `decision_summary`.
- Focused backend, API, and frontend verification now all pass for the current Agent slice: 19 targeted pytest cases and a production Vite build.
- The Dr. AI frontend now renders more user-friendly Agent-state feedback, including readable evidence labels and decision-summary cues instead of only raw source chips.
- Multi-turn API verification now explicitly covers conversation reuse and persisted message accumulation across consecutive requests.
- The current slice is strong enough to mark FE and BE delivery readiness for this runtime increment, while still keeping broader `integration_ready` and `qa_passed` gates closed.
- Broader cross-module regression is now clean as well: `pytest tests` passed with 39 tests, and the frontend production build remains green.
- For the current Agent increment, `integration_ready` and `qa_passed` can now open without over-claiming `release_ready`.
- Deployment/release preparation uncovered two concrete runtime gaps and both are now fixed:
  - backend now exposes `/health`
  - config now accepts `DATABASE_URL`
- Handoff, deployment, and release docs are now prepared for review and aligned with the current validated Agent increment.
- Orchestrator release review is now complete.
- Current conclusion: the increment is strong enough for release consideration, but `release_ready` should remain closed until a real deployment smoke rehearsal is executed.
- SSE-based Agent progress feedback is a practical fit for this project: it adds visible Agent behavior without changing the controlled read-only safety boundary.
- The new `/chat/stream` path can coexist safely with `/chat/send` because both now share the same backend runtime and the frontend has a fallback path if streaming fails.
- The SSE upgrade remained regression-safe in this repository: focused streaming tests passed and the full repository test suite increased from `39 passed` to `42 passed`.
- Frontend bundle optimization is also a good fit for this project: route-level lazy loading cuts the default payload without changing product behavior.
- Granular chunking of Element Plus and ECharts/ZRender was necessary after the first optimization pass; simple route lazy loading alone did not remove the large-chunk warning.
- The second optimization pass succeeded: the frontend build no longer emits the previous >500 kB chunk warning, and full repository regression is now `44 passed`.
- A real Docker Compose smoke rehearsal has now been executed against the repository rather than only local test/build verification.
- Deployment smoke exposed two environment-level issues and both now have repository fixes:
  - backend container startup is pinned to a production uvicorn command on `0.0.0.0`
  - frontend container health checks use `127.0.0.1` instead of `localhost`
- Deployment smoke also exposed one application contract gap: the token schema was missing `token_type="bearer"` in local code, and that contract is now fixed and covered by tests.
- The local repository state after deployment-focused fixes is green: `pytest tests` now passes with `49 passed`.
- The rebuilt backend image now validates end to end as well: deployed `/auth/token` returns `token_type="bearer"` and deployed `/chat/send` returns a normal Agent response.
- A fresh deployment smoke uncovered an additional startup root cause: `backend.services.rag_service` eagerly initialized Hugging Face embeddings at import time, which could stall backend startup before Uvicorn began listening.
- That RAG startup path is now lazy and local-only, so missing embedding caches degrade retrieval quality instead of blocking API availability.
- The local repository state after the final deployment fixes is green: `pytest tests` now passes with `51 passed`.
- With `release_ready` now open, the next highest-value work is no longer deployment rescue but post-release enrichment for demo quality, runtime robustness, and thesis presentation.
- The next roadmap should stay additive to the current Agent baseline and avoid reopening unsafe scope such as write-capable medical tools.
- The most valuable next tracks are:
  - release/demo closure artifacts
  - Agent runtime hardening through token budgeting and provider-aware tool calling
  - richer session UX with conversation management and evidence presentation
  - thesis/defense support artifacts such as diagrams, narratives, and comparison framing
- The first post-release platform-only optimization slice is now implemented: the backend chat runtime uses a dedicated context builder to bound profile, tool evidence, RAG context, query text, and retained history before prompt assembly.
- This token-budgeting slice is regression-safe in the current repository: focused tests passed and the full test suite is now `54 passed`.
- The next post-release runtime-hardening slice is now implemented as well: the backend read-only tool registry exposes provider-facing function schemas, validates tool-call arguments, and supports native function-calling execution.
- `chat_service` now prefers provider-native tool calling / tool use when supported by the configured model, but it does not trust plain-text planning responses as final answers; if native tool calls are absent or fail, it deterministically falls back to the local read-only planning path.
- The native function-calling slice is regression-safe in the current repository: focused tool/service/API tests passed and the full repository test suite is now `57 passed`.
- The next post-release session UX slice is now implemented too: the backend exposes conversation summaries and stored-message replay, and the frontend Dr. AI view now supports sidebar-based history switching plus new-session reset.
- Conversation titles are currently generated from the first user message summary, which keeps the feature lightweight and avoids introducing a separate naming workflow.
- The conversation-history slice is regression-safe in the current repository: focused chat/session tests passed, the frontend build passed, and the full repository test suite is now `61 passed`.
- The next post-release session UX refinement is now implemented as well: `ChatMessage` persists `sources`, `evidence_tags`, and `decision_summary`, and the history-detail API replays those fields so reopened conversations preserve assistant evidence context instead of losing it.
- This historical-metadata replay slice is regression-safe in the current repository: focused metadata tests passed, the frontend build remains green, and the full repository test suite is now `63 passed`.
- Final verification exposed a real ordering edge case in `list_conversations`: relying on `updated_at DESC` alone was not stable enough under SQLite, so the backend now uses `updated_at DESC, id DESC` to keep newest-first history ordering deterministic.
- The next session-management slice is now implemented too: conversation titles are summarized more naturally, the backend supports `query`/`archived` filtering plus archive/restore actions, and the Dr. AI sidebar exposes those controls directly.
- This conversation-management slice is regression-safe in the current repository: focused conversation-management tests passed, the frontend build remains green, and the full repository test suite is now `69 passed`.
- The next session-ordering slice is now implemented as well: `ChatConversation` stores backend-owned `pinned_at` and `last_accessed_at`, the conversation list API returns `pinned` and `last_accessed_at`, and the Dr. AI sidebar exposes pin/unpin controls.
- Recent-session ordering is now stronger than a plain `updated_at` sort: pinned sessions are always first, and reopening a stored conversation refreshes `last_accessed_at` so the active reading context rises naturally in the list.
- This conversation-ordering slice is regression-safe in the current repository: focused session-ordering tests passed, the frontend build remains green, and the full repository test suite is now `73 passed`.
- The next pure platform-optimization backlog has now been formalized separately from thesis/defense work, per current user direction.
- The highest-value remaining platform-only items are:
  - structured health suggestion cards
  - tool-level SSE progress events
  - manual conversation rename
  - richer evidence presentation
  - expanded Agent audit detail
  - conversation grouping and legacy-title repair
- The next Agent UX slice is now implemented too: synchronous chat responses, SSE terminal payloads, and historical replay can all carry an optional backend-owned `suggestion_card` for structured health guidance.
- The streaming path is also more expressive now: `/chat/stream` still emits coarse `status` events, but it also emits concrete `tool_start` and `tool_done` events around read-only tool execution so the frontend can show more believable Agent progress.
- This suggestion-card and tool-stream slice is regression-safe in the current repository: focused service/API/frontend tests passed, the frontend build remains green, and the full repository test suite is now `74 passed`.
- The next session-management slice is now implemented too: one stored conversation can be manually renamed through a metadata-only PATCH endpoint, and list responses now carry backend-owned `group_key` / `group_label` metadata for sidebar section rendering.
- The grouping contract intentionally keeps the conversation list flat and backend-ordered; sections are a display concern driven by backend metadata, not a nested API shape.
- This rename-and-grouping slice was executed as a real multi-agent workflow: architect froze the contract first, backend and frontend implemented in parallel, and QA validated the slice independently.
- The rename-and-grouping slice is regression-safe in the current repository: focused rename/grouping tests passed at `27 passed`, the frontend build remains green, and the full repository test suite is now `80 passed`.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Treat the source workflow as a pattern library, not a literal template | The target repository has a different product shape and folder structure |
| Plan a phased adoption | Safer than introducing orchestration, blackboard state, and role gates all at once |
| Reuse governance primitives before role names | Orchestration rules are more portable than source-project deliverables or paths |
| Recommend a minimal-role first rollout for the health AI platform | Reduces setup cost while preserving gate discipline and ownership |
| Exclude `designer` from the adapted role set | The user clarified that this project does not need a dedicated Figma implementation role |
| Initialize the blackboard in a conservative `existing_unreviewed` state | Existing docs and code should be explicitly approved under the new workflow instead of being auto-blessed |
| Implement Agent upgrade incrementally from conversation persistence outward | This keeps the first slice small, visible, and safe while laying the foundation for later tools and safety layers |
| Keep Phase 1 to server-owned conversation continuity and sliding-window support | Avoids prematurely mixing tool execution and safety routing into the first runtime change |
| Keep the current Agent runtime controlled and read-only | Appropriate for the medical domain and sufficient for graduation-project richness without overreaching into unsafe autonomy |
| Expose only structured Agent hints (`evidence_tags`, `decision_summary`) rather than hidden reasoning | Improves explainability without leaking unstable or privacy-sensitive chain-of-thought content |
| Add SSE progress events as a parallel UX channel rather than replacing `/chat/send` | Preserves backward compatibility while making the Agent workflow visible during long-running responses |
| Optimize the frontend bundle with route lazy loading plus granular manual chunking rather than hiding warnings with a higher threshold | Produces a real build-quality improvement while keeping implementation risk low |
| Keep `release_ready` closed until a rebuilt backend image is validated end to end in Docker Compose | Prevents us from overstating deployment readiness when the healthy running stack may still lag behind the latest local code |
| Make RAG embedding initialization lazy and local-only in runtime containers | Preserves API startup availability during Docker deployment instead of blocking on remote model downloads at import time |
| Write a dedicated post-release roadmap plan before starting the next implementation wave | Keeps the graduation-project enhancements sequenced and bounded after the release-ready baseline |
| Introduce a dedicated context builder before adding more Agent complexity | Keeps prompt growth bounded and makes future improvements like tool-calling and audit summaries easier to reason about |
| Prefer native function calling only as a planning optimization, not as a correctness dependency | Keeps runtime compatible across provider/model differences and preserves the tested local fallback path |
| Keep conversation history as a lightweight read model backed by existing `ChatConversation`/`ChatMessage` tables | Delivers a visible UX upgrade without introducing new state stores or background sync complexity |
| Persist assistant evidence metadata on `ChatMessage` instead of recomputing it during history replay | Keeps historical session replay deterministic, cheap, and aligned with what the user originally saw |
| Keep title summarization heuristic and local instead of using another model call | Improves session readability without adding latency, cost, or another AI dependency to the sidebar flow |
| Keep conversation ordering server-owned through `pinned_at` and `last_accessed_at` metadata | Ensures the sidebar reflects one stable sorting rule across live chat, history replay, and future clients |
| Split the remaining work into a platform-only optimization backlog instead of continuing to mix it with thesis/demo items | Keeps the next execution slices aligned with the user's current priority: improve the product itself first |
| Represent richer health guidance as an optional `suggestion_card` alongside the existing free-text reply | Improves product richness and replay fidelity without replacing the main answer contract |
| Extend SSE with `tool_start` and `tool_done` instead of replacing the existing staged `status` events | Adds more concrete Agent progress visibility while keeping the streaming protocol backward-compatible |
| Freeze conversation grouping as flat-list metadata (`group_key` / `group_label`) instead of changing the list response into nested sections | Keeps the API minimal while still letting the frontend render richer session navigation |
| Treat manual rename as metadata-only and preserve user-set titles over later auto-generated summaries | Prevents sidebar naming churn and keeps rename behavior predictable |
| Freeze the C3 `evidence_panel` as additive backend-owned assistant metadata | Preserves current chat rendering while making richer evidence replay and expansion contractually explicit across sync, stream, and history flows |
| Keep FE evidence-panel expansion state local per message while letting BE author the evidence content | Preserves the architect-owned payload shape and gives the chat UI a simple one-expanded-section interaction model |
| Accept the C3 evidence-panel slice as validated with regression-and-build coverage rather than requiring immediate browser E2E before release | Keeps the optimization moving while acknowledging the remaining interaction-testing gap as a residual risk instead of a blocker |
| Freeze the next tool slice as three backend-internal self-only read-only lookups | Expands user-visible factual retrieval without changing public chat routes or widening the medical-domain safety boundary |
| Keep the safe tool-expansion slice backend-only in this pass | Matches the frozen contract and avoids unnecessary FE churn before QA validates the new tool behavior |
| Freeze `ocr_summary.v1` and `risk_snapshot.v1` before writing a shared normalizer | Gives BE one explicit target for write-path alignment, scan tooling, and future repair work instead of normalizing against drifting legacy assumptions |
| Centralize canonical health-payload handling in one shared backend normalizer | Prevents OCR, profile writes, chat context, and tool projections from drifting into separate legacy-compatibility implementations |
| Treat the legacy scan as reporting-only in this slice | Surfaces real non-canonical rows without mixing repair/backfill risk into the backend normalization implementation stage |
| Pick `expanded audit detail` as the next unfinished backlog slice | It is the highest-priority remaining item that improves runtime observability without reopening contracts or frontend scope |
| Keep the expanded audit detail slice backend-only | The new fields are internal audit metadata, so they should strengthen observability without widening the public API surface |

## Proposed Target Roles
- `orchestrator`: owns blackboard updates, gate transitions, and handoff routing
- `pm`: owns product scope, acceptance criteria, and feature-level priorities
- `architect`: owns architecture, schema boundaries, API contracts, and cross-module technical decisions
- `fe`: owns Vue UI implementation and any UI consistency or token guidance that would otherwise sit with `designer`
- `be`: owns FastAPI APIs, service-layer behavior, persistence, and integration boundaries
- `ai-data`: owns model training flows, ETL/data contracts, feature pipelines, and AI asset readiness
- `qa`: owns validation and release-readiness checks
- `general`: owns repo-facing docs, deployment notes, and handoff packaging

## Review Outcomes
- `docs/PRD.md`: moved conceptually from `existing_unreviewed` to `approved`
- `docs/FEATURE_MAP.md`: moved conceptually from `existing_unreviewed` to `approved`
- `prd_ready`: now `true`
- `docs/architecture.md`: now `drafted_pending_review`
- `docs/api-contract.md`: now `drafted_pending_review`
- `docs/data-model-contract.md`: now `drafted_pending_review`
- `docs/architecture.md`: now `approved`
- `docs/api-contract.md`: now `approved`
- `docs/data-model-contract.md`: now `approved`
- `architecture_ready`: now `true`
- `api_contract_ready`: now `true`
- `data_model_contract_ready`: now `true`
- `implementation_ready`: now `true`
- Next owner recommended by the orchestrator: `orchestrator` until a concrete implementation slice is assigned
- Agent-architecture design spec written for user review: `docs/superpowers/specs/2026-03-24-health-ai-agent-architecture-design.md`
- Agent-architecture implementation plan written: `docs/superpowers/plans/2026-03-24-health-ai-agent-architecture-implementation.md`
- C3 evidence-panel contract refresh approved in `docs/architecture.md`, `docs/api-contract.md`, and `docs/data-model-contract.md`; BE and FE must implement the additive shape without silent contract redesign.
- BE and FE implementation handoffs both stayed within the frozen contract: backend added additive `evidence_panel` persistence/emission, and frontend rendered it without replacing `sources`, `evidence_tags`, `decision_summary`, or `suggestion_card`.
- QA found no blocking findings in the C3 evidence-panel slice, and fresh parent-thread verification matched the QA results (`51 passed` focused, `93 passed` full, frontend build green).
- Architect approved the next safe read-only tool contract refresh in `docs/architecture.md`, `docs/api-contract.md`, and `docs/data-model-contract.md`; backend implementation is the next active stage and must preserve the frozen tool names, scopes, and bounded result shapes.
- Backend implemented the three frozen read-only tools without contract escalation, and fresh parent-thread verification confirmed the focused/backend and full test suites remain green (`24 passed` focused, `102 passed` full).
- Architect approved canonical health-payload envelopes for `MedicalDocument.ocr_summary`, `HealthRecord.risk_snapshot`, and `UserProfile.risk_history`; backend normalization and scan work is the next active stage.
- Backend implemented canonical health-payload normalization without contract drift; fresh parent-thread verification confirmed the focused/backend suite (`45 passed, 2 warnings`), the full repository suite (`107 passed, 2 warnings`), and a working legacy scan script that reports `legacy_count: 3`.
- QA validated the canonical health-payload normalization slice with no blocking findings; the only residual risk remains the three known legacy rows intentionally left for a later repair/backfill slice.
- Backend implemented the expanded Agent audit detail slice without contract drift; fresh parent-thread verification confirmed focused audit/chat coverage (`18 passed, 2 warnings`) and full repository regression (`110 passed, 2 warnings`).
- QA validated the expanded Agent audit detail slice with no blocking findings; the remaining limitation is that audit evidence is still log-only and not persisted in a dedicated store.
- The next unfinished backlog slice, re-synced against the current blackboard rather than older phase notes, is `legacy-title repair`.
- `legacy-title repair` does not require a contract refresh because it only changes backend-owned conversation-title repair behavior and optional repair tooling, not route shapes or payload fields.
- Backend implemented `legacy-title repair` without contract drift; exact-match legacy placeholders are now repaired conservatively on read, and a one-off script reuses the same repair helper for local cleanup.
- Fresh parent-thread verification confirmed the slice is regression-safe in the current repository: focused conversation-title tests passed at `20 passed, 2 warnings`, and full repository regression passed at `114 passed, 2 warnings`.
- QA validated the legacy-title repair slice with no blocking defects; the remaining concerns are limited to unrepaired historical placeholder variants, stdout-only script reporting, and the lack of a live-database rehearsal for the one-off script.
- The next unfinished backlog slice after legacy-title repair is `batch archive/delete preparation hooks`.
- `batch archive/delete preparation hooks` requires an architecture change request before implementation because it expands conversation-management contract surface rather than staying purely internal.
- Architect has now frozen the conservative batch-archive contract: a read-only `prepare` step plus a non-destructive batch archive action, while batch delete and message purge stay explicitly out of scope.
- Fresh parent-thread doc verification confirmed the contract landed cleanly in `docs/architecture.md`, `docs/api-contract.md`, and `docs/data-model-contract.md` with no whitespace or merge issues.
- BE and FE have now implemented the frozen batch-archive slice without contract drift: backend owns prepare/archive semantics for owned conversation ids, and the frontend keeps selection state local while calling the prepare endpoint before mutation.
- Fresh parent-thread verification confirmed the implementation slice is QA-ready in the current repository: focused backend/API regression passed at `36 passed, 2 warnings`, full repository regression passed at `118 passed, 2 warnings`, and the frontend build succeeded.
- QA validated the batch archive hooks slice with no blocking defects; the remaining concerns are limited to the missing browser-driven sidebar smoke test, local-only selection-state assumptions, and the explicit need for a new architect review if batch delete is ever proposed.
- The next requested conversation-management optimization is `batch restore hooks`.
- `batch restore hooks` requires an architecture change request before implementation because the current frozen contract covers only single-item restore plus batch archive; FE/BE may not silently add new batch restore route semantics.
- The orchestrator has now routed the slice to `architect` first; no FE/BE implementation work is authorized until the additive batch-restore contract is frozen.
- Architect has now frozen the conservative additive batch-restore contract in `docs/architecture.md`, `docs/api-contract.md`, and `docs/data-model-contract.md`.
- The approved batch-restore slice includes both a read-only prepare hook and a non-destructive batch restore hook over flat `conversation_id` lists, while still excluding batch delete, hard delete, message purge, and archive-folder mutation semantics.
- Fresh parent-thread doc verification confirmed the contract landed cleanly and `git diff --check` is clean for the three architect-owned docs.
- BE and FE have now implemented the frozen batch-restore slice without contract drift: backend owns prepare/restore semantics for owned archived conversation ids, and the frontend keeps restore selection state local to the archived view while calling the prepare endpoint before mutation.
- Fresh parent-thread verification confirmed the implementation slice is QA-ready in the current repository: focused backend/API regression passed at `41 passed, 2 warnings`, full repository regression passed at `123 passed, 2 warnings`, and the frontend build succeeded.
- QA validated the batch restore hooks slice with no blocking or non-blocking findings; the only remaining concern is the lack of a browser-driven smoke test for the archived-sidebar multi-select restore flow.
- Fresh parent-thread verification matched the QA result on 2026-03-28: focused backend/API/sidebar regression passed at `46 passed, 2 warnings`, full repository regression passed at `123 passed, 2 warnings`, and the frontend build succeeded.
- The next unfinished residual-risk slice is browser-driven smoke / E2E validation for Dr. AI conversation management and evidence interactions.
- This browser-smoke slice does not require an architecture change request because it adds validation infrastructure and frontend-side test coverage without changing API contracts or backend semantics.
- FE has now implemented the browser-smoke slice entirely inside frontend-owned files: Playwright is the chosen runner, Dr. AI exposes minimal `data-testid` hooks, and the smoke suite covers conversation selection, manual rename, batch archive, batch restore, and evidence-panel expand/collapse.
- Fresh parent-thread verification confirms the FE handoff is regression-safe enough to route to QA: `npm.cmd run test:e2e -- tests/dr-ai-smoke.spec.js` passed with `5 passed`, and `npm.cmd run build` in `frontend` also passed.
- QA validated the browser-smoke / E2E slice with no blocking or non-blocking findings and re-scoped `docs/qa-report.md` to the requested Dr. AI interaction coverage only.
- Fresh parent-thread verification matched the QA result on 2026-03-28: `npm.cmd run test:e2e -- tests/dr-ai-smoke.spec.js` passed with `5 passed`, `npm.cmd run build` in `frontend` passed, and `git diff --check -- docs/qa-report.md` was clean.
- The next unfinished backend remediation slice is `legacy health payload repair/backfill`.
- This slice does not require a new architecture change request because it repairs persisted rows and optional backfill tooling under the already-frozen canonical envelopes `ocr_summary.v1` and `risk_snapshot.v1`.
- BE has now implemented the repair/backfill slice entirely inside backend-owned files: a session-based repair helper reuses the canonical normalizers, a CLI wrapper exposes one-off repair execution, and focused regression covers both scan and repair behavior.
- Fresh parent-thread verification confirms the BE handoff is regression-safe enough to route to QA: `python -m pytest tests/test_repair_legacy_payload_shapes.py -q` passed with `2 passed, 2 warnings`, `python -m pytest tests/test_legacy_payload_scan.py tests/test_repair_legacy_payload_shapes.py -q` passed with `3 passed, 2 warnings`, and `git diff --check` for the touched backend files was clean.
- QA validated the repair/backfill slice with no blocking defects; the current workspace database was repaired from `legacy_count_before=3` to `legacy_count_after=0`, and full repository regression stayed green at `125 passed`.
- The remaining non-blocking risk is operational rather than functional: the repair CLI prints config debug noise, including a masked API-key prefix, before the JSON report and should be cleaned up in a later observability pass.
- The next highest-value residual-risk slice is `live backend integrated E2E`, which strengthens real frontend-backend-database linkage verification without introducing new product capabilities.
- This slice does not require an architecture change request because the goal is to exercise existing login, chat, conversation-history, archive/restore, and evidence-display flows against the real backend rather than to add or change public contracts.
- FE has now implemented the live-backend integrated E2E slice without contract drift; Playwright starts a real `uvicorn` backend plus the Vite frontend and validates live registration, live chat/conversation creation, evidence-panel interaction, and batch archive/restore against the actual backend.
- Fresh parent-thread verification confirms the FE handoff is strong enough to route to QA: `npm.cmd run test:e2e -- tests/dr-ai-smoke.spec.js` passed with `2 passed`, and `npm.cmd run build` in `frontend` also passed.
- The remaining non-blocking risks are operational: backend boot still emits `PharmService` lifespan noise plus missing-Redis/missing-OPENAI_API_KEY warnings during the E2E run, and the FE-owned Python shim layer may need maintenance if optional backend imports continue to grow.
- QA validated the live-backend integrated E2E slice with no blocking or non-blocking defects in the browser flow itself; the real-backend Playwright run, source review, and frontend build all support a pass recommendation.
- The residual risks remain operational rather than contractual: backend startup noise still needs cleanup, FE-owned Python shims may need maintenance as optional backend imports evolve, and Playwright coverage is still Chromium-only.
- The next highest-value backend remediation slice is `backend startup hygiene for live E2E`, focused on cleaning `PharmService` startup handling and optional-service degradation noise exposed by the validated live E2E run.
- This slice does not require an architecture change request because it should preserve current public contracts and only improve backend startup resilience and log hygiene.
- The current `backend startup hygiene for live E2E` slice is blocked and may not continue automatically: the BE agent exceeded its retry limit and left `backend/main.py` and `backend/core/cache.py` in a syntactically broken state.
- Fresh parent-thread verification confirms the damage is real, not just reported: `py_compile` fails for both backend files, so manual intervention is required before re-dispatching BE.
- The next safe action is operational, not implementation: restore the two backend files from a known-good commit or backup, then restart this slice with the original narrow goal of fixing `PharmService` startup handling and optional-service noise without changing contracts.
- Manual intervention has now completed safely: the damaged backend files were backed up and restored from `HEAD`, and fresh `py_compile` verification confirms both files are syntactically valid again.
- The startup-hygiene slice can therefore resume, but it should be treated as a fresh narrow BE attempt from a clean baseline rather than a continuation of the broken repair session.
- Fresh parent-thread verification of the new BE handoff shows the slice is close but not yet QA-ready: startup now degrades cleanly and `/health` responds, but `backend/api/api_v1/endpoints/analysis.py` contains `except pdf_error as e:` even though `pdf_error` is undefined.
- This is a backend-only implementation defect rather than contract pressure, so the slice should be returned to `be` for a narrow revision instead of being escalated back to `architect`.
- The narrow BE revision is now in place and parent-thread verification cleared it: `analysis.py` no longer has an undefined PDF export exception path, a focused regression test covers the handler path, and the startup-hygiene slice can move to QA.
- Residual startup output is now limited to non-blocking warning noise and one `nutrition_service` import-time print; these are backend hygiene follow-ups rather than blockers for the current slice.
- QA validated the backend startup-hygiene slice with no blocking defects; focused regression, compile checks, and a live `/health` probe all support a pass recommendation.
- The remaining warnings are operational runtime-noise debt rather than gate blockers: optional dependency warnings, Redis warning, and the nutrition-service import-time print still appear during boot.
- The next user-visible enhancement slice is `evidence source drill-down`, which additively extends the already-frozen `evidence_panel` contract rather than introducing a new top-level chat payload.
- This slice required an architecture change request because it adds replay-visible assistant metadata across `/chat/send`, `/chat/stream` final payloads, and historical replay.
- Architect has now frozen the additive contract: each `evidence_panel.sections[*]` may carry bounded `source_items` with `source_type`, `title`, `snippet`, `timestamp`, and optional `confidence` or `relevance`.
- The initial `source_type` set is intentionally narrow and user-facing: `profile`, `trend`, `report`, and `guideline`.
- The contract explicitly keeps `source_refs` intact and forbids raw large JSON payload exposure; the new drill-down layer must remain safe-summary only.
- The contract is now implementation-ready, and the safest execution pattern is BE/FE parallelism with disjoint write scopes.
- BE should own runtime assembly, persistence, replay, and backend tests for `source_items`; FE should own only the Dr. AI evidence-panel drill-down rendering on top of the frozen contract.
- BE has now implemented the backend half of the slice without contract drift: `source_items` are additive, bounded, replay-safe, and still preserve `source_refs` plus the narrow `source_type` set.
- FE has now implemented the frontend half of the slice without contract drift: Dr. AI renders source-detail drill-down only inside the active evidence section and stays null-safe when `source_items` are absent.
- Fresh parent-thread verification confirms the implementation slice is QA-ready in the current repository: focused backend regression passed at `57 passed, 2 warnings`, Playwright smoke passed at `3 passed`, and the frontend build succeeded.
- QA validated the evidence source drill-down slice with no blocking or non-blocking defects; the additive `source_items` contract is now confirmed across send, stream-final, and historical replay.
- The only remaining caution is contractual rather than functional: any future widening of `source_type` or section shape must route back through `architect` instead of being inferred in FE/BE locally.
- The next unfinished backlog slice is `audit persistence`.
- This slice requires an architecture change request because it introduces a persisted audit store and new repository-level boundaries for redaction, retention, internal accessibility, and durable audit-event shape even if the public chat API remains unchanged.
- The orchestrator has therefore routed the slice to `architect` first; `be` may not implement audit persistence until the storage model, field set, and retention/redaction rules are frozen in architect-owned docs.
- Architect has now frozen the audit-persistence boundary: persisted audit rows are internal-only, append-only, metadata-only records for one completed chat turn or one short-circuited safety response.
- The frozen persisted payload keeps the current runtime audit fields from `build_audit_record` (`timestamp`, `user_id`, `conversation_id`, `intent`, `tool_used`, `safety_level`, `evidence_tags`, `context_budget_summary`, `tool_latency_ms`, `tool_count`, `response_latency_ms`, and `fallback_used`) while allowing backend-owned storage keys such as row ids or schema versions.
- Runtime logger-based audit remains in place alongside durable persisted rows, and any future request to expose audit search/export/filtering through public chat routes is now explicitly frozen as contract pressure that must return through `architect`.
- The slice is now implementation-ready, and `be` may proceed only within the frozen internal-persistence boundary.
- BE has now implemented the audit-persistence slice without contract drift: backend-owned `AgentAuditEvent` rows persist the frozen audit metadata while keeping public chat APIs unchanged.
- Persistence is wired into the existing finalize branches for normal chat completion, cache-hit completion, and urgent safety short-circuit responses, so durable audit rows follow the same backend-owned runtime decision points as the current logger-based audit trail.
- The implementation keeps persisted payloads bounded and metadata-only by sanitizing `context_budget_summary` and by excluding raw query text, assistant text, prompt text, and raw RAG/medical payloads from storage.
- Fresh parent-thread verification confirms the backend slice is QA-ready: focused audit/chat regression passed at `22 passed, 2 warnings`, and full repository regression passed at `132 passed, 2 warnings`.
- QA validated the audit-persistence slice with no blocking defects; the internal-only durable audit store, bounded persisted payload, and unchanged public chat contract all support a pass recommendation.
- Fresh parent-thread verification matched the QA result on 2026-03-29: focused audit/chat regression stayed green at `22 passed, 2 warnings`, full repository regression stayed green at `132 passed, 2 warnings`, and `git diff --check -- docs/qa-report.md` was clean.
- The remaining governance boundary is explicit rather than risky: any future audit search, export, filtering, or frontend visibility request must route back through `architect` as a new contract-affecting slice.
- The next highest-value remaining optimization slice is `startup noise cleanup`.
- This slice should stay backend-only and does not require an architecture change request as long as it only reduces import-time prints and optional-service warning noise without changing routes, payloads, or internal audit contracts.
- The slice is now routed to `be`; if startup-noise cleanup reveals contract pressure or reaches the retry ceiling, the work must stop and return to the orchestrator.
- BE has now implemented the startup-noise cleanup slice without contract drift: nutrition startup no longer eagerly initializes at router import time, nutrition-service `print()` calls are now structured logs, and Redis cache unavailability is reduced to one concise warning.
- Fresh parent-thread verification confirms the backend slice is QA-ready: focused backend startup/nutrition regression passed at `13 passed, 2 warnings`, the targeted noise-cleanup assertions passed at `2 passed`, and `py_compile` passed for the touched backend files.
- QA validated the startup-noise cleanup slice with no blocking defects; the backend-only runtime-hygiene changes, unchanged public contract surface, and focused regression evidence support a pass recommendation.
- Fresh parent-thread verification matched the QA result on 2026-03-30: focused backend startup/nutrition regression stayed green at `13 passed, 2 warnings`, the targeted noise-cleanup assertions stayed green at `2 passed`, `py_compile` passed for the touched backend files, and `git diff --check -- docs/qa-report.md` was clean.
- The remaining risk is intentionally bounded: broader logging-policy cleanup and unrelated legacy `print()` calls remain future backend hygiene work rather than part of this slice.
- The next highest-value remaining backend hygiene slice is `broader logging-policy cleanup`.
- This slice should stay backend-only and does not require an architecture change request as long as it only normalizes legacy `print()` usage, warning emission, and logger consistency without changing routes, payloads, or internal audit boundaries.
- The slice is now routed to `be`; if broader logging cleanup reveals contract pressure or reaches the retry ceiling, the work must stop and return to the orchestrator.
- BE has now completed the broader logging-policy cleanup slice without contract drift: several runtime-critical backend modules moved from direct `print()` noise or ad hoc exception chatter to logger-based handling and bounded warnings.
- Fresh parent-thread verification confirms the backend slice is QA-ready: focused backend regression passed at `19 passed, 2 warnings`, full repository regression passed at `134 passed, 2 warnings`, and `py_compile` passed for the touched backend files.
- The cleanup is intentionally partial rather than exhaustive: many legacy `print()` sites remain in standalone scripts, ETL utilities, and non-runtime service code, so future logging-policy work should continue as additional backend hygiene slices rather than being treated as a missed blocker here.
- QA has now validated the broader logging-policy cleanup slice with no blocking defects and with a pass recommendation recorded in `docs/qa-report.md`.
- Fresh parent-thread verification after the QA handoff confirms the slice is fully validated: the QA report is in place, the cleanup remains contract-safe, and the already-run focused/full regression evidence stands.
- The next requested slice is QA-only: author a complete detailed functional test-case matrix based on the current platform and execute browser-driven verification.
- This slice should not modify FE/BE code or any contract docs; QA may only update `docs/qa-report.md` and report defects or browser-test outcomes back to the orchestrator.
- QA has now completed the requested QA-only slice: `docs/qa-report.md` includes a comprehensive test-case matrix for the current platform plus browser-validation evidence.
- Fresh parent-thread verification confirms the browser validation is complete and green: headed Playwright against `tests/dr-ai-smoke.spec.js` passed at `3 passed`, and the QA-report update landed cleanly without contract changes.
- The next remaining validation gap is `cross-browser E2E`: current Playwright configuration still covers only Chromium/MS Edge.
- This slice should remain validation/infrastructure-only and does not require an architecture change request as long as FE only extends Playwright project/browser coverage without changing app contracts or product behavior.
- FE has now completed the minimal cross-browser expansion without contract drift: Playwright is configured for Chromium, Firefox, and WebKit while preserving the existing Dr. AI smoke semantics.
- Fresh parent-thread verification confirms the slice is QA-ready but environment-limited: Chromium passes, while Firefox/WebKit fail only because the local Playwright browser binaries are not installed on this machine.
- QA has now validated the cross-browser E2E slice with a pass recommendation and an explicit environment-limited caveat recorded in `docs/qa-report.md`.
- Fresh parent-thread verification confirms the QA conclusion: the remaining Firefox/WebKit failures are launch-environment issues, not product-behavior or API-contract defects.
- The next capability-expansion slice is `additional safe read-only tools`.
- This slice must start with `architect` because implementation agents may not silently define new tool names, scopes, bounded payloads, or safe evidence-source exposure rules.
- The intended scope remains additive and read-only: enrich Agent fact access without reopening public chat routes or introducing write-capable behavior.
- Architect has now frozen the three tool names and safe boundaries: `medication_summary_lookup`, `recent_metric_anomaly_lookup`, and `report_comparison_lookup`.
- The contract keeps these tools backend-internal and provider-function-call-only; no new public REST exposure or direct FE-owned tool surface was approved.
- The next stage is backend implementation only, and BE must stay inside the frozen names, scopes, bounded result shapes, and evidence-mapping rules.
- BE has now implemented the frozen tool slice without widening contracts: the three new read-only tools are wired into the internal registry, function-calling path, fallback planner, and bounded evidence mapping.
- Fresh parent-thread verification is green for the backend slice: focused tool and chat-service regression passed, and full `pytest -q` is now green at `139 passed, 2 warnings`.
- Residual risk is limited to bounded data-shape assumptions and a non-blocking CRLF normalization warning on `backend/services/chat_service.py`; neither is a blocker for QA.
- QA has now validated the additional safe read-only tools slice with no blocking or non-blocking defects and recorded the result in `docs/qa-report.md`.
- Fresh parent-thread verification after the QA handoff stayed green: focused regression passed at `36 passed, 2 warnings`, full repository regression stayed green at `139 passed, 2 warnings`, and `git diff --check -- docs/qa-report.md` was clean.
- Residual risk remains intentionally bounded: direct cross-user denial is still covered through the shared `enforce_tool_policy` path rather than one dedicated regression per new tool name.
- The next backlog slice is a bounded RAG chunking optimization for Chinese medical PDFs.
- This slice must start with `architect` because implementation agents may not silently redefine internal knowledge-base chunking boundaries, chunk metadata expectations, or retrieval assumptions without an approved design freeze.
- The intended scope is deliberately conservative: keep the existing recursive-splitting build pipeline, improve separators / chunk size / overlap / basic metadata, and avoid semantic chunking or LLM-assisted chunking in this pass.
- Architect has now frozen the chunking contract: keep `RecursiveCharacterTextSplitter`, adopt Chinese-aware separators, set default `chunk_size=800`, set default `chunk_overlap=120`, and require internal metadata `source`, `page`, and `chunk_index`.
- The contract keeps KB chunk metadata internal-only; it does not expand public chat response fields or add any new chat/KB management HTTP route.
- The next stage is backend implementation only, and BE must stay inside the frozen chunking profile, metadata floor, and explicit non-goals.
- BE has now implemented the frozen chunking slice without widening contracts: `backend/rag/build_kb.py` now uses the approved Chinese-aware recursive splitter profile and stamps internal chunk metadata with `source`, `page`, and `chunk_index`.
- Fresh parent-thread verification is green for the backend slice: focused RAG build/startup regression passed, and full `pytest tests -q` is now green at `140 passed, 2 warnings`.
- Residual risk is limited to optional metadata enrichment: `section_title` and `page_range` depend on what the PDF loader already exposes, and `backend/rag/build_kb.py` still has a non-blocking CRLF normalization warning.
- QA has now validated the RAG chunking optimization slice with no blocking defects and recorded the result in `docs/qa-report.md`.
- Fresh parent-thread verification after the QA handoff stayed green: focused regression passed at `3 passed, 2 warnings`, full repository regression stayed green at `140 passed, 2 warnings`, and `git diff --check -- docs/qa-report.md` was clean.
- Residual risk remains intentionally bounded: current coverage proves the frozen chunking profile and metadata floor, but not a live rebuild benchmark against a broader Chinese medical-PDF corpus.
- The next residual RAG-quality slice is now `section_title / page_range` stabilization inside the already-frozen chunking contract.
- This slice does not require a new architecture change request because it keeps the internal metadata floor unchanged and only makes optional metadata safer and more deterministic.
- `page` remains the minimum required chunk provenance field; `section_title` must come only from loader metadata or stable lightweight heading rules, and `page_range` must appear only for real cross-page chunks.
- The backend metadata-stabilization slice is now in place: `section_title` is resolved only from explicit loader metadata or conservative heading heuristics, and `page_range` is suppressed for same-page chunks such as `7-7`.
- Fresh parent-thread verification is green for this backend slice: focused RAG build/startup regression passed at `8 passed, 2 warnings`, and full `pytest tests -q` is now green at `145 passed, 2 warnings`.
- Residual risk is now narrower and more explicit: optional `section_title` still depends on either loader-supplied titles or a small safe heading pattern set, not on full PDF structural understanding.
- QA has now validated the RAG chunk metadata stabilization slice with no blocking defects and recorded the result in `docs/qa-report.md`.
- Fresh parent-thread verification after the QA handoff stayed green: focused regression passed at `8 passed, 2 warnings`, full repository regression stayed green at `145 passed, 2 warnings`, and documentation hygiene checks were clean.
- The next residual RAG-quality slice is now a live rebuild benchmark over the repository-local Chinese medical PDF corpus.
- This slice does not require a new architecture change request because it keeps the frozen chunking contract intact and only adds benchmark tooling plus QA evidence.
- The repository already contains multiple suitable benchmark PDFs under `backend/rag/docs`, so the benchmark can be executed against real in-repo medical-guideline documents instead of synthetic fixtures.
- The first attempt at this slice only benchmarked the checked-in vector-store index and was deliberately rejected by the orchestrator because it did not satisfy the user-requested live rebuild benchmark requirement.
- The revised backend slice is now correct: `backend/rag/benchmark.py` runs a real live-corpus benchmark over the repository-local PDFs using loader-plus-split behavior, while still avoiding embeddings and vector-store writes.
- Fresh parent-thread benchmark evidence shows the current frozen chunking profile over 9 PDFs / 668 pages / 1127 chunks with `metadata_floor_coverage=1.0`, `section_title_coverage=0.1411`, and `page_range_coverage=0.0`.
- The live benchmark also surfaced a real corpus-quality issue rather than a harness failure: `中国居民膳食指南_2022.pdf` currently contributes pages with near-zero extracted text, so some corpus-level stats reflect PDF extraction quality as well as chunking behavior.
- QA has now validated the live-corpus benchmark slice with no blocking defects and recorded the result in `docs/qa-report.md`.
- Fresh parent-thread verification after the QA handoff stayed green: focused benchmark regression passed at `11 passed, 2 warnings`, full repository regression stayed green at `148 passed, 2 warnings`, and the benchmark output stayed stable across reruns.

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `rg` is unavailable due to an execution permission error in this environment | Use PowerShell `Get-ChildItem` and `Get-Content` instead |
| Recursive search for local instruction files timed out | Narrow future scans to specific directories or patterns |
| Local Python environment was missing `sqlmodel`, `pydantic-settings`, `openai`, `python-jose`, `bcrypt`, `redis`, and `python-multipart` | Installed the missing packages needed to execute the targeted verification slice |
| Test import setup pulled in heavy modules such as RAG, OCR, PDF, and KB build code unrelated to the conversation layer | Expanded `tests/conftest.py` mocks so Phase 1 verification can run without those optional runtime dependencies |
| PowerShell execution policy blocked the standard `npm` entrypoint during frontend verification | Used `npm.cmd` to run the frontend production build successfully |
| Docker Compose rebuilds became unreliable because Docker registry/auth resolution and TLS handshakes timed out during image build | Validated runtime fixes through Compose recreation and host-level smoke checks, but treated rebuilt-image validation as an explicit release blocker |
| Subagent handoff claimed doc edits for the architect stage before the parent thread had verified them locally | Re-checked the actual contract files in the parent workspace before updating blackboard and advancing the stage |
| The first full `pytest -q` run for the normalization slice hit the default timeout | Re-ran the same command with a longer timeout and recorded the successful `107 passed, 2 warnings` result before making any completion claims |

## Resources
- `E:\MutiData-Nexus\AGENTS.md`
- `E:\MutiData-Nexus\.codex`
- `E:\MutiData-Nexus\.agents`
- `E:\MutiData-Nexus\docs\blackboard`
- `E:\MutiData-Nexus\.codex\config.toml`
- `E:\MutiData-Nexus\.codex\agents\pm.toml`
- `E:\MutiData-Nexus\.codex\agents\architect.toml`
- `E:\MutiData-Nexus\.codex\agents\fe.toml`
- `E:\MutiData-Nexus\.codex\agents\be.toml`
- `E:\MutiData-Nexus\.agents\skills\shared-policy.md`
- `E:\MutiData-Nexus\docs\blackboard\state.yaml`
- `E:\health_ai_platform_2.0\README.md`
- `E:\health_ai_platform_2.0\PROJECT_CONTEXT.md`
- `E:\health_ai_platform_2.0\AGENTS.md`
- `E:\health_ai_platform_2.0\.codex\config.toml`
- `E:\health_ai_platform_2.0\docs\blackboard\state.yaml`
- `E:\health_ai_platform_2.0\docs\superpowers\specs\2026-03-24-health-ai-multi-agent-workflow-design.md`
- `E:\health_ai_platform_2.0\docs\superpowers\plans\2026-03-24-health-ai-multi-agent-workflow.md`

## Visual/Browser Findings
- No browser or image review performed in this task.

## Live Backend E2E Findings
- `frontend/playwright.config.js` now launches a real backend and frontend together, with an isolated sqlite database for the backend live E2E run.
- The FE-only shim set had to cover `langchain_chroma`, `langchain_huggingface`, `xgboost`, `reportlab`, `fitz`, `filetype`, `aip`, `tenacity`, and `langchain_community` so backend startup could complete without changing backend code or contracts.
- The live E2E happy path passed against the real backend for conversation creation, evidence panel interaction, replay, archive, and restore flows.

## RAG PDF Extraction Quality Remediation
- The live-corpus benchmark exposed a real PDF extraction weakness rather than a chunking-contract failure.
- The remediation stays inside the already-frozen RAG chunking contract because it improves loader fallback behavior and bounded extraction quality without changing public chat routes, chunking defaults, or metadata-floor guarantees.
- `backend/rag/pdf_extraction.py` now provides a bounded OCR fallback for image-only PDF pages.
- The fallback renders pages with `pdftoppm`, uses the existing Baidu OCR credential path, and limits OCR attempts to the first 10 pages of image-only PDFs to keep build/benchmark cost bounded.
- `backend/rag/build_kb.py` and `backend/rag/benchmark.py` now share the same remediation path, so benchmark evidence reflects the actual build-time extraction path instead of a benchmark-only workaround.
- Fresh parent-thread verification confirms the problematic corpus document no longer behaves like an almost-empty PDF in the benchmark: the current live report shows `page_count: 363`, `chunk_count: 365`, and `average_chunk_size: 10.4959`.
- QA has now validated the remediation slice with no contract drift and with a pass recommendation recorded in `docs/qa-report.md`.
- Fresh parent-thread verification after the QA handoff stayed green: focused regression passed at `5 passed, 2 warnings`, syntax checks passed for the touched files, and the live benchmark remained stable at `document_count: 9`, `page_count: 668`, `chunk_count: 1129`, and `metadata_floor_coverage: 1.0`.

## Current RAG Findings
- The validated live-corpus benchmark surfaced a real PDF extraction quality issue rather than a chunking-contract failure.
- The most visible corpus outlier is `E:\health_ai_platform_2.0\backend\rag\docs\中国居民膳食指南_2022.pdf`, which currently yields near-zero extracted text through the existing loader path.
- The next slice is therefore `RAG PDF extraction quality remediation`.
- This slice stays inside the already-frozen RAG chunking contract as long as it improves loader fallback behavior, text extraction quality, or bounded preprocessing without changing public chat routes, chunking defaults, or metadata-floor guarantees.

## Residual Risk Backlog
- The current non-blocking residual risks are now formalized in `E:\health_ai_platform_2.0\docs\superpowers\plans\2026-03-31-rag-runtime-risk-backlog.md`.
- The recommended next wave starts with:
  - PDF low-text-density diagnostics
  - OCR fallback capability signaling
  - loader fallback warning cleanup
- Later waves cover:
  - `section_title` stabilization enhancement
  - `page_range` capability evaluation
  - Pydantic deprecation cleanup
  - cross-browser local completion
- The active residual-risk slice is now `PDF low-text-density diagnostics`, chosen because the live-corpus benchmark already proved the harness and exposed real document-level extraction-quality variance.
- This slice stays inside the frozen RAG contract as long as it only adds bounded benchmark diagnostics such as low-density flags, blank-page ratios, OCR-touched-page counts, or extremely short-chunk counts.
- Fresh backend evidence now shows the benchmark can explicitly identify low-density outliers instead of only surfacing corpus averages: `low_density_document_count` is reported at the corpus level and `中国居民膳食指南_2022.pdf` is flagged with bounded reasons (`blank_page_ratio>=0.5`, `extremely_short_chunk_ratio>=0.5`).
- QA has now validated the slice and confirmed the benchmark remains read-only (`vector_store_writes: 0`) while still flagging the known outlier document correctly.
- The remaining risk is no longer that low-density PDFs are invisible; it is now that threshold tuning and OCR-fallback capability signaling may need their own follow-up slices if the corpus or environment changes.
- The active residual-risk slice is now `OCR fallback capability signaling`, chosen because the current PDF extraction remediation still depends on local OCR prerequisites that are not yet surfaced clearly enough in build/benchmark flows.
- This slice stays inside the frozen RAG contract as long as it only adds bounded capability summaries, concise warnings, and deployment/runtime documentation updates without changing public chat routes or chunking behavior.
- Fresh backend evidence now makes OCR fallback capability explicit: the benchmark report includes `ocr_fallback_capability` and the build/benchmark path emits one concise preflight capability line instead of leaving OCR readiness implicit.
- QA has now validated the slice and confirmed the capability summary is explicit, benchmark/build remain read-only, and deployment docs now state `pdftoppm`, Baidu OCR credentials, and outbound OCR network assumptions clearly.
- The remaining risk is no longer that OCR fallback state is hidden; it is now that loader fallback warning noise and OCR-environment dependence still merit their own follow-up slices.
- The active residual-risk slice is now `Loader fallback warning cleanup`, chosen because benchmark/build output still repeats per-document fallback warnings that obscure the now-valid capability summary.
- This slice stays inside the frozen RAG contract as long as it only reduces warning noise and clarifies loader-selection behavior without changing public chat routes, chunking defaults, or metadata-floor guarantees.
- Fresh backend evidence now shows the warning cleanup worked as intended: benchmark/build still fall back safely, but the repeated per-document `PyPDFLoader unavailable` noise has been reduced to a single process-level fallback notice.
- QA has now validated the slice and confirmed the benchmark remains read-only while emitting exactly one process-level loader fallback warning rather than one warning per document.
- The remaining risk is no longer the warning spam itself; it is now the still-separate follow-up work around `section_title`, `page_range`, and later hygiene slices such as Pydantic cleanup.
- The active residual-risk slice is now `section_title stabilization enhancement`, chosen because optional title coverage is still conservative even after chunk metadata stabilization and loader cleanup.
- This slice stays inside the frozen RAG contract as long as it only expands safe heading rules for eligible documents, keeps `section_title` optional, and does not fabricate titles or alter the metadata floor.
- Fresh backend evidence now shows build and benchmark share the same metadata-first `section_title` resolver, with deterministic lightweight heading rules improving coverage while plain body text still resolves to `None`.
- A non-blocking cleanup note remains: `build_kb.py` and `benchmark.py` still contain old local title-helper codepaths that are no longer on the live path after the shared resolver landed.
- QA has now validated the slice and confirmed `section_title` remains optional, the shared resolver is the live source of truth, and there was no contract drift.
- The remaining risk is no longer missing `section_title` stabilization itself; it is the later cleanup of dead local helper blocks and the next provenance-oriented slice around `page_range`.
- The active residual-risk slice is now `page_range capability evaluation`, chosen because cross-page provenance is still absent even after chunking, title, and warning improvements.
- This slice stays inside the frozen RAG contract as long as it only proves whether real cross-page ranges are safely derivable, keeps `page_range` optional, and does not fabricate provenance.
- Fresh backend evidence now shows the current loader-plus-split path is still page-local for this corpus: shared provenance helpers reject invalid or same-page pseudo-ranges, while the live benchmark continues to report `page_range_coverage: 0.0`.
- The current validated outcome for this slice is therefore not “add cross-page ranges,” but “prove that real cross-page provenance is not safely derivable under the existing extraction/splitting path.”
- A follow-up observation emerged during parent-thread verification: `section_title_coverage` on the current live benchmark output is only `0.031`, so title coverage may merit a later corpus-quality tuning pass even though the `section_title` stabilization slice itself remains validated.
- QA has now validated the `page_range` slice and confirmed there is no contract drift: `page_range` remains optional, fake ranges are not emitted, and the benchmark stays read-only with `vector_store_writes: 0`.
- With the residual-risk backlog's fifth slice now closed, the next recommended slice is `Pydantic deprecation cleanup`.
- The user has now asked to resolve the two remaining non-blocking residual risks directly rather than only backlog them.
- The first active follow-up slice is `section_title coverage uplift`, chosen because live benchmark coverage is still low (`0.031`) even though the existing stabilization work is validated.
- This slice stays inside the frozen RAG contract as long as it only improves conservative title-recognition coverage, keeps `section_title` optional, and never fabricates headings.
- Fresh backend evidence now shows the uplift worked in a bounded way: live benchmark `section_title_coverage` improved from `0.031` to `0.0425` by reusing page-level resolved titles across same-page chunks instead of inventing new headings.
- The second planned follow-up slice is `Pydantic deprecation cleanup`, which remains backend/runtime hygiene work and should start only after the current title-coverage slice is validated.
- QA has now validated the `section_title` coverage-uplift slice and confirmed the uplift is real, bounded, and contract-safe: no fake headings were introduced, `page_range_coverage` stayed `0.0`, and `metadata_floor_coverage` stayed `1.0`.
- The final remaining residual-risk slice is now `Pydantic deprecation cleanup`.
- Parent-thread inspection before dispatch isolated two current warning candidates in repository-owned code: class-based config on `backend/main.py:CheckupData` and a class-based `Config` block in `backend/models.py`.
- This final slice stays inside backend/runtime hygiene boundaries as long as it only replaces class-based config with `ConfigDict`-style equivalents or removes obsolete config blocks without changing public response semantics.
- Fresh backend evidence now shows the cleanup succeeded without contract drift: `backend/main.py` now uses `ConfigDict(extra="allow")` for `CheckupData`, the obsolete `class Config` block in `backend/models.py` is gone, and importing both modules with warnings promoted to errors now passes.
- The test suite is now warning-clean for the targeted slice: `python -m pytest tests/test_pydantic_deprecation_cleanup.py -q` passed at `2 passed`, and the full repository regression completed at `166 passed` with no Pydantic deprecation warnings in the output.
- QA has now validated the `Pydantic deprecation cleanup` slice and confirmed there is no contract drift: repository-owned class-based Pydantic config is gone from the live path, targeted imports succeed under `-W error`, and the focused cleanup test remains green.
- The two residual risks the user asked to resolve are now both closed under the repository workflow: `section_title_coverage` has been lifted from `0.031` to `0.0425`, and repository-owned Pydantic deprecation warnings have been eliminated from the live path.
- A fresh whole-repository optimization scan on 2026-04-02 shows that the highest-value next work is no longer raw feature expansion but baseline recovery: `python -m pytest tests -q` currently reports `6 failed, 204 passed`, and the failures cluster around Agent behavior evaluation, human takeover semantics, and RAG-quality-aware chat behavior.
- The frontend production build still succeeds, but current bundle output remains heavy enough that frontend performance work should stay on the medium-priority roadmap.
- RAG quality has improved meaningfully, but there is still room to improve low-density PDF handling, section-title coverage, and the mapping between benchmark outputs and runtime answer quality.
- Runtime hygiene is better than before, but import-time side effects and degraded-mode signaling are still not fully cleaned up.
- These findings are now formalized in `E:\health_ai_platform_2.0\docs\superpowers\plans\2026-04-02-repository-optimization-plan.md`, which recommends starting the next execution wave with baseline recovery before further feature work.
