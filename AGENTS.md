# Health AI Platform Agent Workflow

This repository uses a parent-thread orchestration model to coordinate product, architecture, implementation, AI/data, QA, and release work for the Health AI Platform.

## Orchestrator

- The parent thread is the `orchestrator`.
- Only the `orchestrator` may write `docs/blackboard/state.yaml`.
- All project agents treat the blackboard as read-only context.
- The `orchestrator` opens and closes workflow gates, approves status changes, and routes handoffs to the next owner.

## Role Ownership

| Role | Primary Ownership | Required Deliverables | Hard Limits |
|------|-------------------|-----------------------|-------------|
| `pm` | Product scope, user value, acceptance criteria | `docs/PRD.md`, `docs/FEATURE_MAP.md` | Must not finalize API, schema, or model I/O contracts |
| `architect` | Cross-module design, API contract, data/model contract | `docs/architecture.md`, `docs/api-contract.md`, `docs/data-model-contract.md` | Must not silently change product scope |
| `fe` | Vue frontend implementation and UI consistency | `frontend/src` | Blocked until implementation gates open; cannot change contracts directly |
| `be` | FastAPI routes, service-layer behavior, backend persistence | `backend/api`, `backend/services`, `backend/core`, `backend/schemas` | Blocked until implementation gates open; cannot change contracts directly |
| `ai-data` | Model training, ETL, data readiness, AI asset integration boundaries | `ai_core`, `data_warehouse`, `backend/etl` | Must not redefine frontend UX or public API contracts directly |
| `qa` | Validation, regression checks, release readiness evidence | `docs/qa-report.md` | Runs after integration evidence exists |
| `general` | Repository-facing docs, deployment, release, handoff packaging | `README.md`, `docs/deployment.md`, `docs/release.md`, `docs/handoff.md` | Must not redefine scope or technical contracts |

## Workflow Gates

1. `pm` confirms product scope and acceptance criteria in `docs/PRD.md` and `docs/FEATURE_MAP.md`.
2. `architect` defines the repository-level architecture, API contract, and data/model contract.
3. The `orchestrator` opens `implementation_ready` only after `architecture_ready`, `api_contract_ready`, and `data_model_contract_ready` are all true.
4. `fe`, `be`, and `ai-data` may work in parallel only after `implementation_ready` is open.
5. `fe`, `be`, and `ai-data` cannot silently change contracts. They must escalate contract pressure to the `orchestrator`, which routes the issue back through `architect`.
6. `qa` validates when implementation evidence exists and records findings in `docs/qa-report.md`.
7. `general` finalizes repository-facing documentation after QA passes or the `orchestrator` explicitly approves a documentation-only handoff.

## Retry Policy

- `fe` max retries: `3`
- `be` max retries: `3`
- `ai-data` max retries: `3`
- On the third failed attempt, the owning agent must stop, summarize evidence, propose the next-best alternative, and escalate to the `orchestrator`.

## Required Read Order

Every agent must read these items before working:

1. `AGENTS.md`
2. `.codex/config.toml`
3. Its own `.codex/agents/<role>.toml`
4. `docs/blackboard/state.yaml`
5. The docs and code areas it owns or depends on

## Handoff Protocol

Each handoff must include:

- Files read and files changed
- Decisions made
- Assumptions, risks, or open questions
- Evidence for requested gate changes
- Requested next owner

Child agents do not update workflow state directly. The `orchestrator` reviews the handoff first and then updates the blackboard if appropriate.

## Current Repository Intent

- This repository is a working Health AI Platform with a Vue frontend, FastAPI backend, AI/ML training assets, ETL/data-warehouse assets, and product documentation already present.
- The multi-agent workflow in this repository is a governance layer. It should organize work without rewriting the existing product architecture.
- Existing product documents such as `docs/PRD.md` and `docs/FEATURE_MAP.md` remain valid inputs, but their approval status must now be recorded through the blackboard.
