# Health AI Platform Multi-Agent Workflow Design

## Goal

Adapt the orchestrated multi-agent workflow from the reference repository into the Health AI Platform repository without copying stack-specific assumptions that do not fit this codebase.

## Why This Repository Needs An Adapted Version

The source workflow uses useful governance primitives: a parent-thread orchestrator, a shared blackboard, explicit role ownership, contract gates, retry limits, and structured handoffs. Those ideas transfer well. The source role map does not transfer one-to-one because this repository is organized around Vue, FastAPI, AI training assets, ETL/data-warehouse assets, and existing product documentation rather than a dedicated design-token or Figma lane.

## Design Principles

1. Keep governance separate from business code.
2. Adapt roles to the repository, not the other way around.
3. Freeze API and data/model contracts before parallel implementation begins.
4. Let only the orchestrator write workflow state.
5. Start with a conservative blackboard that marks most artifacts as existing but unapproved.

## Target Roles

- `orchestrator`
- `pm`
- `architect`
- `fe`
- `be`
- `ai-data`
- `qa`
- `general`

`designer` is intentionally removed. Any lightweight UI consistency concerns stay with `fe`.

## Gate Model

- `orchestrator_initialized`
- `prd_ready`
- `architecture_ready`
- `api_contract_ready`
- `data_model_contract_ready`
- `implementation_ready`
- `frontend_delivery_ready`
- `backend_delivery_ready`
- `ai_data_delivery_ready`
- `integration_ready`
- `qa_passed`
- `release_ready`

Parallel implementation is allowed only after `implementation_ready` is true.

## Repository Artifacts

### Governance Files

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/*.toml`
- `.agents/skills/*.md`
- `docs/blackboard/state.yaml`

### Contract And Verification Docs

- `docs/architecture.md`
- `docs/api-contract.md`
- `docs/data-model-contract.md`
- `docs/qa-report.md`
- `docs/deployment.md`
- `docs/release.md`
- `docs/handoff.md`

## Blackboard Shape

The blackboard must track project metadata, workflow phase and gates, role status and retries, document ownership and status, and control rules for contract changes and retries.

## Intended Rollout

1. Install governance scaffold only.
2. Review and approve existing product docs under the new workflow.
3. Pilot one cross-stack feature slice through the new gate system.
4. Expand the workflow as the default project operating model.
