# Repository Optimization Plan

**Date:** 2026-04-02  
**Scope:** Whole-repository optimization pass after a fresh scan of backend, frontend, RAG, runtime behavior, and regression status  
**Intent:** Turn the current repository scan into a formal, prioritized optimization backlog and a phased execution plan

## Executive Summary

The Health AI Platform is no longer primarily blocked by missing features. It is now rich enough that the highest-value work is to stabilize the engineering baseline across runtime semantics, regression tests, RAG quality, frontend performance, and repository hygiene.

The strongest signal from the fresh scan is that the repository's current behavior, tests, and governance records are not fully aligned:

- `python -m pytest tests -q` currently reports `6 failed, 204 passed`
- failures cluster around Agent behavior evaluation, human takeover semantics, and RAG-quality-aware chat behavior
- frontend build still succeeds, but bundle output remains heavy
- RAG quality is materially better than before, but section-title coverage and low-density PDF handling still have room to improve
- runtime noise is lower than before, but import-time and degraded-mode signaling are still not fully tidy

This plan therefore prioritizes restoring a stable repository baseline before opening another major user-visible feature wave.

## Current Repository Signals

### Regression Status

Fresh full-suite verification indicates that the most urgent optimization need is baseline recovery:

- [test_agent_behavior_eval_harness.py](/E:/health_ai_platform_2.0/tests/test_agent_behavior_eval_harness.py)
- [test_chat_agent_api.py](/E:/health_ai_platform_2.0/tests/test_chat_agent_api.py)
- [test_chat_agent_service.py](/E:/health_ai_platform_2.0/tests/test_chat_agent_service.py)

Representative failure themes:

- eval harness deterministic baseline mismatch
- conversation reuse flow now returns takeover metadata where older tests expect none
- medication-change and insufficient-evidence policies do not match older `suppressed` vs `required` expectations
- RAG-quality-aware service tests cannot cleanly patch the current integration path

### Runtime / Contract Signals

- [chat_service.py](/E:/health_ai_platform_2.0/backend/services/chat_service.py) has become the convergence point for:
  - response verdicts
  - takeover behavior
  - RAG quality handling
  - evidence generation
  - audit behavior
- [agent_safety.py](/E:/health_ai_platform_2.0/backend/services/agent_safety.py) likely no longer aligns cleanly with older harness expectations
- the current [state.yaml](/E:/health_ai_platform_2.0/docs/blackboard/state.yaml) is tracking newer human-takeover work, while some tests still encode older assumptions

### RAG / Knowledge Signals

Recent RAG improvements are real and should be preserved:

- chunking rules were upgraded
- PDF extraction diagnostics now exist
- low-text-density benchmark diagnostics exist
- OCR fallback capability signaling exists
- loader fallback warning cleanup has improved

Residual RAG concerns:

- `section_title_coverage` remains conservative
- low-density PDFs still exist in the real corpus
- benchmark quality is better described than before, but answer-quality mapping is still indirect

### Frontend / UX Signals

- [frontend](/E:/health_ai_platform_2.0/frontend) still builds successfully
- bundle output remains relatively heavy, especially around charts and vendor assets
- current user-facing features are rich enough that performance and regression stability now matter more than raw feature count

### Repository Hygiene Signals

- the worktree is heavily dirty
- governance records, runtime behavior, and regression baselines are not perfectly synchronized
- residual logging/import-time side effects still reduce debugging signal quality

## Optimization Goals

1. restore a fully green and trustworthy regression baseline
2. stabilize human-takeover and response-verdict semantics
3. make RAG-quality-aware behavior easier to verify and maintain
4. keep improving RAG quality without reopening product scope
5. reduce frontend load cost and runtime/logging noise
6. re-align repository hygiene and governance artifacts

## Prioritized Optimization Backlog

### P0. Baseline Recovery

**Why first**

Without a green baseline, every future slice becomes harder to trust.

**Primary targets**

- [test_agent_behavior_eval_harness.py](/E:/health_ai_platform_2.0/tests/test_agent_behavior_eval_harness.py)
- [test_chat_agent_api.py](/E:/health_ai_platform_2.0/tests/test_chat_agent_api.py)
- [test_chat_agent_service.py](/E:/health_ai_platform_2.0/tests/test_chat_agent_service.py)
- [chat_service.py](/E:/health_ai_platform_2.0/backend/services/chat_service.py)
- [agent_safety.py](/E:/health_ai_platform_2.0/backend/services/agent_safety.py)
- [rag_service.py](/E:/health_ai_platform_2.0/backend/services/rag_service.py)

**Specific needs**

- determine whether current runtime behavior is correct and tests are stale, or whether runtime drift is accidental
- reconcile takeover semantics across sync, stream, replay, and eval paths
- restore `python -m pytest tests -q` to all-green

**Definition of done**

- full repository pytest is green
- any changed expectations are intentional and documented

### P1. Human Takeover / Response Verdict Harmonization

**Why next**

Current failing tests indicate that escalation semantics are drifting.

**Specific needs**

- define stable rules for:
  - when takeover is `None`
  - when takeover is `suppressed`
  - when takeover is `required`
- define the relationship between:
  - `takeover`
  - `response_verdict`
  - `decision_summary.policy`
  - `human_escalation_required`
- ensure product behavior, regression tests, and evaluation harness all share the same policy matrix

**Definition of done**

- one stable escalation matrix is reflected in runtime code and tests

### P2. Agent Behavior Harness Re-Baselining

**Why after policy lock**

The harness should become a trusted regression tool again, not a drifting snapshot.

**Specific needs**

- separate true regressions from stale expectations
- re-lock deterministic baselines only after runtime policy is intentionally stabilized
- preserve useful failure samples when behavior changes

**Definition of done**

- behavior harness passes deterministically
- baseline updates are intentional and reviewable

### P3. RAG Quality Follow-Up

**Why after runtime stabilization**

RAG quality work matters, but it should not mask unresolved runtime-policy drift.

**Specific needs**

- continue conservative `section_title` improvements
- isolate low-density PDF strategies instead of globally over-tuning extraction
- strengthen the mapping from benchmark metrics to answer-quality outcomes

**Definition of done**

- benchmark remains reproducible and more actionable
- targeted RAG quality improves without metadata fabrication

### P4. Frontend Bundle and Performance Hygiene

**Specific needs**

- further reduce heavy chart/vendor chunks
- review ECharts imports for finer-grained loading
- increase lazy-loading where appropriate

**Definition of done**

- build remains green
- bundle profile improves without destabilizing the current UX

### P5. Runtime Logging and Import-Time Side-Effect Cleanup

**Specific needs**

- move non-essential logs away from import time
- keep degraded-mode information explicit but concise
- reduce startup noise while preserving operational clarity

**Definition of done**

- startup/import path is quieter and easier to debug

### P6. Repository Hygiene and Baseline Realignment

**Specific needs**

- re-align blackboard, test baseline, and effective runtime baseline
- identify obsolete helpers that are no longer on the live path
- reduce ambiguity about what belongs to the current approved baseline

**Definition of done**

- repository state is easier to reason about for the next slice

## Phased Execution Plan

### Phase A. Restore Regression Baseline

**Focus**

- get full `pytest tests -q` back to green
- isolate true drift vs stale expectations

**Suggested verification**

```powershell
python -m pytest tests/test_agent_behavior_eval_harness.py -q
python -m pytest tests/test_chat_agent_api.py tests/test_chat_agent_service.py -q
python -m pytest tests -q
```

### Phase B. Lock Takeover / Verdict Policy

**Focus**

- unify human-takeover and response-verdict semantics

**Suggested verification**

```powershell
python -m pytest tests/test_chat_agent_api.py tests/test_chat_agent_service.py -q
python -m pytest tests/test_agent_behavior_eval_harness.py -q
```

### Phase C. Re-Lock Harness Baseline

**Focus**

- make evaluation artifacts trustworthy again

**Suggested verification**

```powershell
python -m pytest tests/test_agent_behavior_eval_harness.py -q
python -m pytest tests -q
```

### Phase D. Continue RAG Quality Work

**Focus**

- improve section/title and low-density diagnostics without reopening scope

**Suggested verification**

```powershell
python -m pytest tests/test_rag_build_kb.py tests/test_rag_live_corpus_benchmark.py tests/test_rag_pdf_extraction.py -q
python -m backend.rag.benchmark
```

### Phase E. Frontend + Runtime Hygiene

**Focus**

- bundle slimming
- runtime/startup noise reduction

**Suggested verification**

```powershell
python -m pytest tests/test_main.py tests/test_health_endpoint.py -q
cmd /c npm run build
cmd /c npm run test:e2e -- tests/dr-ai-smoke.spec.js
```

### Phase F. Repository Hygiene Closeout

**Focus**

- baseline reconciliation
- stale-helper and drift cleanup

**Suggested verification**

```powershell
git status --short
python -m pytest tests -q
```

## Recommended Execution Order

1. Baseline Recovery
2. Human Takeover / Response Verdict Harmonization
3. Agent Behavior Harness Re-Baselining
4. RAG Quality Follow-Up
5. Frontend Bundle and Runtime Hygiene
6. Repository Hygiene Closeout

## Recommendation

The next actual execution slice should be **Phase A: Baseline Recovery**. Until the repository-wide regression baseline is green again, every later optimization carries avoidable uncertainty.
