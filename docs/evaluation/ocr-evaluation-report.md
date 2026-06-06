# OCR Structured Extraction Evaluation Report

- Generated at: 2026-04-24T10:31:19+00:00
- Sample type: `synthetic_post_ocr_text_reports`
- Sample count: `50`
- Evaluation path: `MedicalOCRService._extract_by_regex -> normalize_ocr_summary_payload`
- Field tolerance: `+/-0.011`

## Interpretation Boundary

This phase uses 50 synthetic text reports as OCR-after-text fixtures. It measures deterministic structured extraction quality after OCR text is available.
It does not measure Baidu OCR image/PDF recognition accuracy, scanner quality, layout recovery, or external clinical validity.
The result is still useful for resume/thesis evidence because it quantifies the platform's report-to-structured-fields step with reproducible samples and ground truth.

## Summary Metrics

- Raw regex supported-field micro precision: `1.000`
- Raw regex supported-field micro recall: `1.000`
- Raw regex supported-field micro F1: `1.000`
- Raw regex all-field micro precision: `1.000`
- Raw regex all-field micro recall: `1.000`
- Raw regex all-field micro F1: `1.000`
- Canonical `ocr_summary.v1` micro precision: `1.000`
- Canonical `ocr_summary.v1` micro recall: `1.000`
- Canonical `ocr_summary.v1` micro F1: `1.000`
- Documents with all supported raw fields matched: `50/50`
- Average document supported-field recall: `1.000`
- Average document all-field recall: `1.000`

## Raw Regex Field Metrics

| Field | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALT | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| AST | 45 | 45 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| BMI | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Creatinine | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| DBP | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| GGT | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Glu | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| HDL | 46 | 46 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| HGB | 43 | 43 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| HbA1c | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| LDL | 46 | 46 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| PLT | 43 | 43 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SBP | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| TC | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| TG | 45 | 45 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UA | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| WBC | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| eGFR | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Canonical OCR Summary Metrics

| Field | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALT | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| AST | 45 | 45 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| BMI | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Cholesterol_HDL | 46 | 46 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Cholesterol_LDL | 46 | 46 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Cholesterol_Total | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Creatinine | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| DBP | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| GGT | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Glucose_Fasting | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| HGB | 43 | 43 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| HbA1c | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Platelet | 43 | 43 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SBP | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Triglycerides | 45 | 45 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UA | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| WBC | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| eGFR | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Known Gaps Found By This Phase

- AST, HGB, and UA are now included in canonical `ocr_summary.v1.metrics` after the approved report-level biomarker contract extension.
- Real image/PDF OCR recognition quality still needs a provider-backed, de-identified report benchmark; this phase only measures post-OCR text extraction.

## Output Files

- Synthetic samples: `E:\health_ai_platform_2.0\docs\evaluation\ocr-samples`
- Ground truth: `E:\health_ai_platform_2.0\docs\evaluation\ocr-samples\ground_truth.json`
- Raw field metrics: `E:\health_ai_platform_2.0\docs\evaluation\ocr-raw-field-metrics.csv`
- Canonical field metrics: `E:\health_ai_platform_2.0\docs\evaluation\ocr-canonical-field-metrics.csv`
- Per-sample metrics: `E:\health_ai_platform_2.0\docs\evaluation\ocr-sample-metrics.csv`
- JSON summary: `E:\health_ai_platform_2.0\docs\evaluation\ocr-extraction-summary.json`
- Markdown report: `E:\health_ai_platform_2.0\docs\evaluation\ocr-evaluation-report.md`

## Suggested Resume Wording

- 可表述为：`构建 50 份合成体检报告样本及标准答案，完成 OCR 后文本结构化抽取评估；当前规则抽取链路在已覆盖字段上的 micro-F1 为 1.000，并形成字段级误差分析，为后续 OCR/LLM 抽取优化提供依据。`
- 不建议表述为：`真实 OCR 图片识别准确率` 或 `医院真实报告识别率`，除非后续补充真实脱敏报告和 OCR Provider 识别评测。

## Phase Handoff

- Current stage: Phase 3 - OCR structured extraction evaluation
- Updated artifacts: `ai_core/evaluate_ocr_extraction.py`, `docs/evaluation/ocr-samples/*`, `docs/evaluation/ocr-*.csv`, `docs/evaluation/ocr-extraction-summary.json`, `docs/evaluation/ocr-evaluation-report.md`
- Blockers: none for synthetic post-OCR extraction evaluation; real image/PDF OCR accuracy remains blocked on provider credentials and real de-identified reports.
- Next stage: Phase 4 - RAG retrieval evaluation.
