# Health AI Platform Multi-Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install a repository-local multi-agent governance scaffold for the Health AI Platform without modifying existing business logic.

**Architecture:** Add an orchestration layer made of governance docs, role configs, shared policy, and a blackboard file. Keep the scaffold additive, conservative, and aligned to the existing Vue, FastAPI, and AI/data repository layout.

**Tech Stack:** Markdown, TOML, YAML

---

## Chunk 1: Governance Skeleton

### Task 1: Create top-level governance files

**Files:**
- Create: `AGENTS.md`
- Create: `.codex/config.toml`
- Test: manual file-existence check

- [ ] **Step 1: Write the file contents**
- [ ] **Step 2: Verify the files exist**
Run: `Get-ChildItem AGENTS.md,.codex\config.toml`
Expected: both files are listed

### Task 2: Add role configs and shared policy

**Files:**
- Create: `.codex/agents/pm.toml`
- Create: `.codex/agents/architect.toml`
- Create: `.codex/agents/fe.toml`
- Create: `.codex/agents/be.toml`
- Create: `.codex/agents/ai-data.toml`
- Create: `.codex/agents/qa.toml`
- Create: `.codex/agents/general.toml`
- Create: `.agents/skills/shared-policy.md`
- Create: `.agents/skills/pm.md`
- Create: `.agents/skills/architect.md`
- Create: `.agents/skills/fe.md`
- Create: `.agents/skills/be.md`
- Create: `.agents/skills/ai-data.md`
- Create: `.agents/skills/qa.md`
- Create: `.agents/skills/general.md`
- Test: manual file-existence check

- [ ] **Step 1: Write the config and skill files**
- [ ] **Step 2: Verify the files exist**
Run: `Get-ChildItem .codex\agents,.agents\skills -File`
Expected: all config and skill files are listed

## Chunk 2: Blackboard And Workflow Docs

### Task 3: Add blackboard and contract templates

**Files:**
- Create: `docs/blackboard/state.yaml`
- Create: `docs/architecture.md`
- Create: `docs/api-contract.md`
- Create: `docs/data-model-contract.md`
- Create: `docs/qa-report.md`
- Create: `docs/deployment.md`
- Create: `docs/release.md`
- Create: `docs/handoff.md`
- Test: manual file-existence check

- [ ] **Step 1: Write the blackboard and template docs**
- [ ] **Step 2: Verify the files exist**
Run: `Get-ChildItem docs\blackboard\state.yaml,docs\architecture.md,docs\api-contract.md,docs\data-model-contract.md,docs\qa-report.md,docs\deployment.md,docs\release.md,docs\handoff.md`
Expected: all files are listed

### Task 4: Save workflow design and execution references

**Files:**
- Create: `docs/superpowers/specs/2026-03-24-health-ai-multi-agent-workflow-design.md`
- Create: `docs/superpowers/plans/2026-03-24-health-ai-multi-agent-workflow.md`
- Test: manual file-existence check

- [ ] **Step 1: Write the design and plan references**
- [ ] **Step 2: Verify the files exist**
Run: `Get-ChildItem docs\superpowers\specs,docs\superpowers\plans -File`
Expected: both workflow reference docs are listed

## Chunk 3: Final Verification

### Task 5: Verify the scaffold is coherent

**Files:**
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`
- Test: repository status and targeted file reads

- [ ] **Step 1: Update planning records**
- [ ] **Step 2: Verify repository status**
Run: `git status --short`
Expected: only additive governance and planning files plus any pre-existing unrelated dirty files
- [ ] **Step 3: Read key scaffold files**
Run: `Get-Content AGENTS.md; Get-Content .codex\config.toml; Get-Content docs\blackboard\state.yaml`
Expected: files describe the approved no-designer workflow and the conservative initial blackboard state
