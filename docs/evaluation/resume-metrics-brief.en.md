# Resume Metrics Brief

## STAR Rewrite Direction

**S/T**: Built a full-stack HealthAI platform for chronic-disease risk assessment and personalized health intervention, addressing fragmented health data, non-explainable model outputs, and weak safety governance in AI health consultation.

**A**: Owned data/model assets, FastAPI Agent runtime, Vue3 interaction flows, RAG/OCR integration boundaries, regression/E2E validation, and multi-agent delivery governance.

**R**: Use the quantified bullets below, keeping the validation boundary wording intact.

## Quantified Bullets

- Evaluated 35 persisted LightGBM chronic-risk models on 13,137 NHANES-derived rows with median ROC-AUC 0.857; core tasks included T2D AUC 0.911, hypertension AUC 0.912, obesity AUC 0.892, and CKD AUC 0.767.
- Built a 50-sample synthetic post-OCR report extraction benchmark; supported raw fields reached micro-F1 1.000, all raw fields micro-F1 1.000, and canonical payload micro-F1 1.000.
- Prepared a 100-question RAG retrieval benchmark over 841 Chroma chunks; offline source Hit@5 reached 0.840, MRR 0.785, and indexed-source Hit@5 0.840.
- Designed a 100-question Agent safety benchmark across 5 classes; deterministic policy pass rate, urgent escalation accuracy, unsafe-refusal accuracy, and tool-whitelist compliance all reached 1.000.
- Built a 100-answer quality rubric covering key-point coverage, evidence grounding, safety compliance, actionability, and clarity; offline candidate pass rate reached 1.000 with mean score 0.940.

## Safe Wording

- Prefer: `repository-local offline evaluation`, `synthetic post-OCR extraction benchmark`, `offline RAG lexical baseline`, `deterministic Agent policy benchmark`.
- Avoid: `clinical-grade`, `doctor-level`, `externally validated`, `live LLM quality`, unless future experiments provide that evidence.
