# RAG Retrieval Evaluation Report

- Generated at: 2026-04-28T05:52:22+00:00
- Question count: `100`
- Indexed chunks read from Chroma SQLite: `841`
- Expected sources: `9`
- Unique indexed sources: `9`
- Missing expected sources: `none`
- Evaluation mode: `runtime_probe_plus_chroma_sqlite_lexical_baseline`

## Runtime RAG Service Probe

- LangChain/embedding dependencies available: `True`
- Runtime retrieval status: `ok`
- Runtime hit count: `3`
- Runtime chunk quality: `mixed`

## Offline Retrieval Metrics

- Source Hit@1: `0.740`
- Source Hit@3: `0.820`
- Source Hit@5: `0.840`
- Source Hit@10: `0.870`
- MRR: `0.785`
- Indexed-source subset questions: `100`
- Indexed-source subset Hit@5: `0.840`
- Indexed-source subset MRR: `0.785`
- Mean keyword coverage@5: `0.517`
- Top5 keyword pass rate: `0.550`

## Topic Breakdown

| Topic | Questions | Hit@1 | Hit@3 | Hit@5 | MRR | Keyword Coverage@5 |
|---|---:|---:|---:|---:|---:|---:|
| ckd | 11 | 0.727 | 0.909 | 0.909 | 0.803 | 0.714 |
| diabetes | 11 | 0.909 | 1.000 | 1.000 | 0.955 | 0.403 |
| dietary_guideline | 11 | 0.545 | 0.545 | 0.545 | 0.545 | 0.468 |
| fatty_liver | 11 | 0.909 | 0.909 | 0.909 | 0.924 | 0.506 |
| gout | 12 | 0.833 | 0.917 | 0.917 | 0.875 | 0.571 |
| hypertension | 11 | 1.000 | 1.000 | 1.000 | 1.000 | 0.532 |
| lipid | 11 | 0.545 | 0.636 | 0.818 | 0.638 | 0.597 |
| obesity | 11 | 0.727 | 1.000 | 1.000 | 0.864 | 0.455 |
| physical_activity | 11 | 0.455 | 0.455 | 0.455 | 0.455 | 0.403 |

## Interpretation Boundary

The runtime RAG service is recorded exactly as observed. In this environment the optional LangChain/embedding packages are available and live vector retrieval returned `ok`.
The offline metrics are a reproducible lexical retrieval baseline over the existing Chroma SQLite text/index content. They measure knowledge-base source coverage for 100 synthetic medical questions, not live embedding semantic retrieval quality.
All expected sources are present in the current Chroma index.
Live vector retrieval was available during this run; the reported Hit@k/MRR values still describe retrieval-source matching, not final LLM answer correctness.

## Output Files

- Question set: `E:\health_ai_platform_2.0\docs\evaluation\rag-questions.json`
- Per-query metrics: `E:\health_ai_platform_2.0\docs\evaluation\rag-retrieval-metrics.csv`
- Summary JSON: `E:\health_ai_platform_2.0\docs\evaluation\rag-retrieval-summary.json`
- Markdown report: `E:\health_ai_platform_2.0\docs\evaluation\rag-evaluation-report.md`

## Suggested Resume Wording

- Suggested: `Built a 100-question medical RAG retrieval benchmark over 841 Chroma chunks from 9 indexed guideline sources; live vector retrieval returned ok, offline source Hit@5 reached 0.840, and MRR reached 0.785.`
- Avoid: `LLM medical-answer correctness` or `clinical-grade RAG`, unless answer-level human/expert annotation is added.

## Phase Handoff

- Current stage: Phase 4 - RAG retrieval evaluation
- Updated artifacts: `ai_core/evaluate_rag_retrieval.py`, `docs/evaluation/rag-questions.json`, `docs/evaluation/rag-retrieval-metrics.csv`, `docs/evaluation/rag-retrieval-summary.json`, `docs/evaluation/rag-evaluation-report.md`
- Blockers: none for live vector RAG startup and expected-source index coverage in this run.
- Next stage: Phase 5 - Agent behavior and safety evaluation.
