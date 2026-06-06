# Health AI Platform Evaluation Summary

## Executive Summary

This report consolidates Phase 1-6 evaluation evidence for resume and thesis writing. It separates verified repository-local evidence from offline/synthetic boundaries so the final claims stay credible.

## Metrics Dashboard

| Area | Key Result | Boundary |
|---|---|---|
| Engineering baseline | Backend `246 passed`; frontend E2E `21 passed`; model compatibility passed | Local repository runtime |
| Risk models | 35 models, median ROC-AUC 0.857, best InsulinResist AUC 0.972 | Repository-local stratified holdout replay over persisted artifacts; not external clinical validation. |
| OCR extraction | 50 samples, supported raw micro-F1 1.000, canonical micro-F1 1.000 | Synthetic post-OCR text structured extraction; not real image/PDF OCR-provider accuracy. |
| RAG retrieval | 100 questions, Hit@5 0.840, MRR 0.785, indexed Hit@5 0.840 | Live vector RAG is available in the current runtime; offline metrics still report a reproducible lexical baseline over Chroma SQLite rather than answer-level medical correctness. |
| Agent safety | 100 questions, policy pass 1.000, urgent escalation 1.000, unsafe refusal 1.000 | Deterministic policy-layer evaluation, not clinician-labeled adversarial safety benchmarking. |
| Answer quality | 100 answers, pass rate 1.000, mean score 0.940, safety 1.000 | Offline template-candidate rubric unless rerun with exported production/LLM answers. |

## Core Disease Risk Metrics

| Disease | ROC-AUC | PR-AUC | Accuracy | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| T2D | 0.911 | 0.556 | 0.877 | 0.717 | 0.541 |
| Hypertension | 0.912 | 0.802 | 0.828 | 0.836 | 0.744 |
| HighLipid | 0.869 | 0.644 | 0.775 | 0.837 | 0.656 |
| Obesity | 0.892 | 0.781 | 0.810 | 0.803 | 0.720 |
| CKD | 0.767 | 0.493 | 0.802 | 0.529 | 0.468 |

## Model And Runtime Choices

- **LightGBM risk models**: Clinical/NHANES features are mostly structured tabular variables; LightGBM handles nonlinear feature interactions, missing values, class imbalance workflows, and efficient multi-disease training. Provides fast offline risk scoring with interpretable feature importance and strong repository-local AUC evidence.
- **ResNet-18 / food vision model**: ResNet-18 is a lightweight transfer-learning baseline that is easier to train and deploy than larger CNNs while remaining expressive enough for diet-image classification experiments. Supports multimodal health analysis without making the deployment footprint too heavy for a graduation project.
- **OCR + deterministic normalization**: Health reports require auditable extraction of numeric indicators; deterministic regex and canonical payload normalization make extraction behavior inspectable and regression-testable. Turns unstructured report text into structured health metrics and exposes clear field-level gaps.
- **RAG medical retrieval**: Medical guidance changes over time and should be evidence-bound; RAG keeps guidance updateable without retraining the base chat model. Adds source-aware consultation and reduces unsupported free-form medical claims when the index is healthy.
- **Policy-governed Agent runtime**: Health consultation has safety-sensitive lanes; deterministic routing, tool whitelists, and refusal/urgent-care policies create guardrails around LLM generation. Separates product safety decisions from generative wording and makes audit/replay possible.

## What Went Well

- Full-stack closed loop is clear: data ingestion, risk analysis, OCR extraction, RAG evidence, chat consultation, history tracking, and audit metadata are connected.
- Engineering validation is unusually complete for a graduation project: backend regression, frontend build, Playwright E2E, and model compatibility gates are recorded.
- AI capability is multi-layered rather than a single chat wrapper: risk models, OCR, retrieval, Agent policy, and answer-quality rubric each have separate evidence.
- Safety governance is explicit: urgent symptoms, diagnosis-sensitive prompts, and unsafe medication requests are routed through deterministic guardrails.
- The project now has reproducible evaluation scripts and reports that can be rerun instead of relying on unverifiable resume claims.

## What Still Needs Work

- Risk-model numbers are repository-local holdout replay metrics, not external clinical validation, so they should be worded conservatively.
- OCR evaluation uses synthetic post-OCR text samples; true image/PDF OCR accuracy still needs provider credentials and real de-identified reports.
- RAG retrieval now has live vector runtime availability and complete expected-source coverage, but the reported Hit@k metrics are still retrieval-level evidence rather than answer-level clinical correctness.
- Answer-quality Phase 6 uses offline template candidates because no LLM key was present; live provider quality must be rerun with exported answers before making live-model claims.
- Some repository text/assets show encoding artifacts and large-file/legacy cleanup debt, which can reduce maintainability and presentation quality.

## Resume-Ready Quantified Bullets

- Evaluated 35 persisted LightGBM chronic-risk models on 13,137 NHANES-derived rows with median ROC-AUC 0.857; core tasks included T2D AUC 0.911, hypertension AUC 0.912, obesity AUC 0.892, and CKD AUC 0.767.
- Built a 50-sample synthetic post-OCR report extraction benchmark; supported raw fields reached micro-F1 1.000, all raw fields micro-F1 1.000, and canonical payload micro-F1 1.000.
- Prepared a 100-question RAG retrieval benchmark over 841 Chroma chunks; offline source Hit@5 reached 0.840, MRR 0.785, and indexed-source Hit@5 0.840.
- Designed a 100-question Agent safety benchmark across 5 classes; deterministic policy pass rate, urgent escalation accuracy, unsafe-refusal accuracy, and tool-whitelist compliance all reached 1.000.
- Built a 100-answer quality rubric covering key-point coverage, evidence grounding, safety compliance, actionability, and clarity; offline candidate pass rate reached 1.000 with mean score 0.940.
