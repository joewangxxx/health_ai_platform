# Risk Model Offline Evaluation Report

- Generated at: 2026-05-05T09:17:28+00:00
- Model bundle: `E:\health_ai_platform_2.0\models\risk_assessment_models.pkl`
- Evaluation data: `E:\health_ai_platform_2.0\data_warehouse\processed_data\clinical_clean\nhanes_integrated_data_v2.csv`
- Evaluation mode: `persisted_artifact_stratified_holdout_replay`
- Split: `test_size=0.2`, `random_state=42`, stratified by target
- Decision threshold: `0.5`
- Evaluated models: `35`
- Skipped models: `0`
- Best ROC-AUC: `0.972`
- Median ROC-AUC: `0.857`
- Models with complete replay features: `35/35`

## Interpretation Boundary

These numbers are suitable as repository-local offline evaluation evidence, but they should not be described as external clinical validation.
The persisted model bundle does not store the exact original training indices, so this script replays a deterministic stratified split against the current data and evaluates the persisted artifacts on that split.
If the persisted artifacts were trained on the full dataset or an overlapping split, the metrics may be optimistic. For thesis-grade claims, follow this phase with a fresh train/validation/test rerun that saves split IDs.

## Data Assembly Notes

- Loaded 13137 rows and 115 columns from E:\health_ai_platform_2.0\data_warehouse\processed_data\clinical_clean\nhanes_integrated_data_v2.csv.
- DIET_DAY1: merged 10 new columns from P_DR1TOT.xpt
- DIET_DAY2: no usable feature columns in P_DR2TOT.xpt
- VITD: merged 1 new columns from P_VID.xpt
- FOLATE: no usable feature columns in P_FOLATE.xpt

## Core Resume-Relevant Models

| Disease | Test N | Positives | ROC-AUC | PR-AUC | Accuracy | Balanced Acc | Precision | Recall | F1 | Missing Features |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T2D | 2628 | 265 | 0.911 | 0.556 | 0.877 | 0.806 | 0.435 | 0.717 | 0.541 | 0 |
| Hypertension | 2628 | 784 | 0.912 | 0.802 | 0.828 | 0.830 | 0.670 | 0.835 | 0.743 | 0 |
| HighLipid | 2628 | 674 | 0.869 | 0.644 | 0.775 | 0.795 | 0.539 | 0.837 | 0.656 | 0 |
| Obesity | 2628 | 799 | 0.892 | 0.781 | 0.810 | 0.808 | 0.652 | 0.804 | 0.720 | 0 |
| CKD | 2628 | 431 | 0.767 | 0.493 | 0.803 | 0.693 | 0.419 | 0.529 | 0.468 | 0 |
| CVD | 2628 | 191 | 0.913 | 0.424 | 0.884 | 0.797 | 0.349 | 0.696 | 0.465 | 0 |
| Stroke | 2628 | 83 | 0.855 | 0.119 | 0.941 | 0.562 | 0.134 | 0.157 | 0.144 | 0 |
| CoronaryHeart | 2628 | 73 | 0.943 | 0.353 | 0.964 | 0.762 | 0.396 | 0.548 | 0.460 | 0 |
| Depression | 2628 | 173 | 0.824 | 0.238 | 0.880 | 0.675 | 0.259 | 0.439 | 0.325 | 0 |

## Top Models By ROC-AUC

| Disease | Test N | Positives | ROC-AUC | PR-AUC | Accuracy | Balanced Acc | Precision | Recall | F1 | Missing Features |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| InsulinResist | 2628 | 480 | 0.972 | 0.882 | 0.909 | 0.906 | 0.693 | 0.900 | 0.783 | 0 |
| HighTriglycerides | 2628 | 153 | 0.949 | 0.576 | 0.930 | 0.803 | 0.432 | 0.660 | 0.522 | 0 |
| HeartFailure | 2628 | 62 | 0.947 | 0.394 | 0.971 | 0.710 | 0.403 | 0.435 | 0.419 | 0 |
| CoronaryHeart | 2628 | 73 | 0.943 | 0.353 | 0.964 | 0.762 | 0.396 | 0.548 | 0.460 | 0 |
| HeartAttack | 2628 | 75 | 0.926 | 0.358 | 0.966 | 0.711 | 0.407 | 0.440 | 0.423 | 0 |
| MetabolicSyndrome | 2628 | 357 | 0.921 | 0.663 | 0.861 | 0.828 | 0.493 | 0.782 | 0.605 | 0 |
| CVD | 2628 | 191 | 0.913 | 0.424 | 0.884 | 0.797 | 0.349 | 0.696 | 0.465 | 0 |
| Hypertension | 2628 | 784 | 0.912 | 0.802 | 0.828 | 0.830 | 0.670 | 0.835 | 0.743 | 0 |
| T2D | 2628 | 265 | 0.911 | 0.556 | 0.877 | 0.806 | 0.435 | 0.717 | 0.541 | 0 |
| AbdominalObesity | 2628 | 1072 | 0.909 | 0.860 | 0.815 | 0.820 | 0.736 | 0.852 | 0.789 | 0 |
| Arthritis | 2628 | 505 | 0.896 | 0.609 | 0.809 | 0.817 | 0.502 | 0.830 | 0.625 | 0 |
| Obesity | 2628 | 799 | 0.892 | 0.781 | 0.810 | 0.808 | 0.652 | 0.804 | 0.720 | 0 |

## All Evaluated Models

| Disease | Test N | Positives | ROC-AUC | PR-AUC | Accuracy | Balanced Acc | Precision | Recall | F1 | Missing Features |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AbdominalObesity | 2628 | 1072 | 0.909 | 0.860 | 0.815 | 0.820 | 0.736 | 0.852 | 0.789 | 0 |
| Anemia | 2628 | 374 | 0.857 | 0.515 | 0.830 | 0.765 | 0.438 | 0.674 | 0.531 | 0 |
| Arthritis | 2628 | 505 | 0.896 | 0.609 | 0.809 | 0.817 | 0.502 | 0.830 | 0.625 | 0 |
| Asthma | 2628 | 423 | 0.610 | 0.239 | 0.706 | 0.563 | 0.230 | 0.352 | 0.278 | 0 |
| CKD | 2628 | 431 | 0.767 | 0.493 | 0.803 | 0.693 | 0.419 | 0.529 | 0.468 | 0 |
| CVD | 2628 | 191 | 0.913 | 0.424 | 0.884 | 0.797 | 0.349 | 0.696 | 0.465 | 0 |
| CoronaryHeart | 2628 | 73 | 0.943 | 0.353 | 0.964 | 0.762 | 0.396 | 0.548 | 0.460 | 0 |
| Depression | 2628 | 173 | 0.824 | 0.238 | 0.880 | 0.675 | 0.259 | 0.439 | 0.325 | 0 |
| Gout | 2628 | 317 | 0.857 | 0.421 | 0.822 | 0.745 | 0.364 | 0.644 | 0.465 | 0 |
| GumDisease | 2628 | 483 | 0.774 | 0.465 | 0.777 | 0.715 | 0.427 | 0.617 | 0.505 | 0 |
| HeartAttack | 2628 | 75 | 0.926 | 0.358 | 0.966 | 0.711 | 0.407 | 0.440 | 0.423 | 0 |
| HeartFailure | 2628 | 62 | 0.947 | 0.394 | 0.971 | 0.710 | 0.403 | 0.435 | 0.419 | 0 |
| HeavyDrinker | 2628 | 387 | 0.871 | 0.545 | 0.796 | 0.772 | 0.397 | 0.739 | 0.516 | 0 |
| HighLead | 2628 | 24 | 0.667 | 0.025 | 0.990 | 0.500 | 0.000 | 0.000 | 0.000 | 0 |
| HighLipid | 2628 | 674 | 0.869 | 0.644 | 0.775 | 0.795 | 0.539 | 0.837 | 0.656 | 0 |
| HighPulsePressure | 2628 | 319 | 0.879 | 0.505 | 0.841 | 0.773 | 0.407 | 0.683 | 0.511 | 0 |
| HighTriglycerides | 2628 | 153 | 0.949 | 0.576 | 0.930 | 0.803 | 0.432 | 0.660 | 0.522 | 0 |
| Hypertension | 2628 | 784 | 0.912 | 0.802 | 0.828 | 0.830 | 0.670 | 0.835 | 0.743 | 0 |
| Hyperuricemia | 2628 | 317 | 0.857 | 0.421 | 0.822 | 0.745 | 0.364 | 0.644 | 0.465 | 0 |
| Inflammation | 2628 | 671 | 0.852 | 0.668 | 0.778 | 0.762 | 0.549 | 0.729 | 0.627 | 0 |
| InsulinResist | 2628 | 480 | 0.972 | 0.882 | 0.909 | 0.906 | 0.693 | 0.900 | 0.783 | 0 |
| IronDef | 2628 | 377 | 0.889 | 0.594 | 0.837 | 0.795 | 0.457 | 0.737 | 0.564 | 0 |
| IronOverload | 2628 | 195 | 0.882 | 0.384 | 0.865 | 0.729 | 0.290 | 0.569 | 0.384 | 0 |
| KidneyStones | 2628 | 159 | 0.728 | 0.120 | 0.860 | 0.569 | 0.133 | 0.239 | 0.171 | 0 |
| LiverDisease | 2628 | 162 | 0.824 | 0.266 | 0.885 | 0.650 | 0.235 | 0.383 | 0.291 | 0 |
| LowHDL | 2628 | 605 | 0.846 | 0.610 | 0.760 | 0.755 | 0.486 | 0.745 | 0.588 | 0 |
| MetabolicSyndrome | 2628 | 357 | 0.921 | 0.663 | 0.861 | 0.828 | 0.493 | 0.782 | 0.605 | 0 |
| Obesity | 2628 | 799 | 0.892 | 0.781 | 0.810 | 0.808 | 0.652 | 0.804 | 0.720 | 0 |
| Osteoporosis | 2628 | 11 | 0.667 | 0.079 | 0.994 | 0.544 | 0.143 | 0.091 | 0.111 | 0 |
| PoorHealth | 2628 | 467 | 0.820 | 0.491 | 0.760 | 0.727 | 0.397 | 0.675 | 0.500 | 0 |
| PreDiabetes | 2628 | 512 | 0.840 | 0.496 | 0.750 | 0.764 | 0.424 | 0.787 | 0.551 | 0 |
| Psoriasis | 2628 | 57 | 0.834 | 0.117 | 0.968 | 0.555 | 0.171 | 0.123 | 0.143 | 0 |
| Stroke | 2628 | 83 | 0.855 | 0.119 | 0.941 | 0.562 | 0.134 | 0.157 | 0.144 | 0 |
| T2D | 2628 | 265 | 0.911 | 0.556 | 0.877 | 0.806 | 0.435 | 0.717 | 0.541 | 0 |
| ToothLoss | 2628 | 85 | 0.799 | 0.159 | 0.941 | 0.634 | 0.213 | 0.306 | 0.251 | 0 |

## Output Files

- CSV metrics: `E:\health_ai_platform_2.0\docs\evaluation\risk-model-metrics.csv`
- JSON metrics: `E:\health_ai_platform_2.0\docs\evaluation\risk-model-metrics.json`
- Markdown report: `E:\health_ai_platform_2.0\docs\evaluation\model-evaluation-report.md`

## Suggested Resume Wording

- 可表述为：`完成 LightGBM 慢病风险模型离线评估，覆盖 35 个疾病/风险标签，固定分层回放测试集 ROC-AUC 中位数 0.857，核心标签如 T2D/高血压/血脂异常/肥胖等形成可复现实验记录。`
- 不建议表述为：`达到临床诊断准确率`、`已完成真实世界临床验证` 或 `外部验证集准确率`，除非后续补充独立外部数据集。

## Phase Handoff

- Current stage: Phase 2 - risk-model offline evaluation
- Updated artifacts: `ai_core/evaluate_risk_models.py`, `docs/evaluation/risk-model-metrics.csv`, `docs/evaluation/risk-model-metrics.json`, `docs/evaluation/model-evaluation-report.md`
- Blockers: none for repository-local offline evaluation; external clinical validation remains out of scope.
- Next stage: Phase 3 - OCR structured extraction evaluation.
