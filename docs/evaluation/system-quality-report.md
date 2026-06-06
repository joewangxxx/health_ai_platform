# System Quality Baseline Report

## Scope

- Stage: evaluation baseline, phase 1
- Date: 2026-04-24
- Purpose: establish a reproducible engineering baseline before adding model, OCR, RAG, and Agent evaluation metrics.

## Repository Governance Context

- Files read before validation:
  - `AGENTS.md`
  - `docs/blackboard/state.yaml`
- Current blackboard state observed:
  - `workflow.phase`: `stability_and_governance_remediation`
  - `workflow.status`: `stage14_orchestrator_final_closure_release_ready`
  - `qa_passed`: `true`
  - `release_ready`: `true`
- This phase did not modify `docs/blackboard/state.yaml`.

## Environment Baseline

| Item | Value |
|---|---|
| Python | `3.11.9` |
| Node.js | `v24.14.0` |
| npm | `11.9.0` |
| Python dependency snapshot | `docs/evaluation/python-freeze.txt` |
| Snapshot package count | `105` |

Note: `python -m pip freeze` failed in this environment because pip hit a Windows `NotADirectoryError` while resolving an editable/VCS-style package path. The baseline therefore uses `python -m pip list --format=freeze`, which completed successfully and is sufficient for reproducibility tracking.

## Validation Results

| Check | Command | Result |
|---|---|---|
| Backend regression | `python -m pytest tests -q` | Passed: `246 passed` in `60.96s` |
| Frontend production build | `npm.cmd run build` in `frontend` | Passed: Vite build completed successfully |
| Frontend E2E | `npx.cmd playwright test --reporter=line` in `frontend` | Passed: `21 passed` in about `1.2m` |
| Model compatibility gate | `python ai_core/check_model_compatibility.py --strict` | Passed: exit code `0`, no compatibility issues detected |

## Model Runtime Baseline

Strict compatibility check reported these runtime package versions:

| Package | Version |
|---|---|
| `xgboost` | `2.1.4` |
| `torch` | `2.5.1` |
| `torchvision` | `0.20.1` |
| `scikit-learn` | `1.6.1` |
| `joblib` | `1.5.3` |

## E2E Coverage Observed

Checked Playwright specs:

| Spec | Covered Area |
|---|---|
| `frontend/tests/dr-ai-takeover.spec.js` | Dr. AI takeover rendering and suppression behavior |
| `frontend/tests/ocr-guided-completion.spec.js` | OCR state rendering, guided completion, analysis-context refresh, major-page smoke |

Playwright ran across:

- `chromium`
- `firefox`
- `webkit`

## Non-Blocking Warnings

- Playwright backend startup reported Redis cache unavailable and continued without cache.
- `torch.load(..., weights_only=False)` FutureWarning appeared for food and glucose model loading paths.
- The model compatibility checker also surfaced the same future warning class while loading torch assets.

These warnings did not fail the current baseline, but they should be tracked in later model-governance hardening because they affect long-term dependency and model-loading safety.

## Phase Handoff

- Current stage: evaluation baseline, phase 1
- Updated artifacts:
  - `docs/evaluation/python-freeze.txt`
  - `docs/evaluation/system-quality-report.md`
- Blockers:
  - None for phase 1. All baseline validation checks passed.
- Next stage:
  - Phase 2: risk-model offline evaluation, including AUC, Accuracy, Precision, Recall, F1, and core-disease summary tables.
