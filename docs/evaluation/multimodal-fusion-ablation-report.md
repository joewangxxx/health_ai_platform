# Multimodal Fusion Ablation Report

- Generated at: `2026-05-05T10:00:25+00:00`
- Data file: `E:\health_ai_platform_2.0\data_warehouse\processed_data\clinical_clean\nhanes_integrated_data_v2.csv`
- Evaluation mode: `clinical_vs_clinical_plus_behavior_ablation`
- Split: `test_size=0.2`, `random_state=42`, stratified by target
- Decision threshold: `0.5`
- Evaluated tasks: `6`
- Tasks with positive ROC-AUC delta: `5/6`
- Mean ROC-AUC delta: `0.0030`

## Interpretation Boundary

This is a repository-local ablation over available NHANES-derived features. It compares clinical-only features with clinical plus behavior/lifestyle features.
It does not include genotype-level supervised fusion because no same-subject SNP/genotype table is paired with the NHANES rows in this repository.
Therefore, the result should be described as behavior-augmented multimodal ablation evidence, not as full clinical-genetic-behavior external validation.

## Core Results

| Disease | Test N | Positives | Clinical AUC | Clinical+Behavior AUC | Delta AUC | Clinical Acc | Clinical+Behavior Acc | Delta Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2型糖尿病 | 2628 | 265 | 0.909 | 0.911 | 0.0022 | 0.874 | 0.869 | -0.0042 |
| 高血压 | 2628 | 784 | 0.912 | 0.912 | 0.0001 | 0.830 | 0.832 | 0.0027 |
| 高脂血症 | 2628 | 674 | 0.868 | 0.871 | 0.0027 | 0.771 | 0.778 | 0.0065 |
| 肥胖 | 2628 | 799 | 0.888 | 0.893 | 0.0051 | 0.803 | 0.810 | 0.0068 |
| 慢性肾病 | 2628 | 431 | 0.764 | 0.763 | -0.0007 | 0.795 | 0.795 | 0.0000 |
| 心血管疾病 | 2628 | 191 | 0.905 | 0.914 | 0.0089 | 0.873 | 0.882 | 0.0088 |

## Thesis-Safe Summary

在当前可复现实验中，行为/生活方式特征对不同病种的增益并不完全一致。T2D、高脂血症、肥胖和心血管疾病任务的 ROC-AUC 出现小幅提升，高血压基本持平，CKD 略有下降。
这说明现有融合链路能够接入额外模态并形成可量化对比，但当前行为特征的增益幅度有限，且缺少同主体遗传数据支持完整三模态监督评估。
