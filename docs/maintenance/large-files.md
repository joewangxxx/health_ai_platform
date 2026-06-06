# Large File And Oversized Module Inventory

Generated on: 2026-04-24

Scope: identify large binary/data assets, generated artifacts, oversized docs, and long source files. This is an inventory only; no file was deleted, moved, or split.

## Summary

- Large files above threshold: 145
- Long source/doc files above threshold: 14

Thresholds used:

- Text/source/doc large-file threshold: >= 512 KB
- Data/model/binary large-file threshold: >= 5 MB
- Long source/doc threshold: >= 800 lines or >= 256 KB

## Large Files

| Bucket | Path | Size MB | Suggested action |
| --- | --- | --- | --- |
| other | data_warehouse/raw_data/gene_source/SystolicBP/SystolicBP_GCST90474636.tsv | 10718.46 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Obesity/Obesity_GCST90473209.tsv | 10638.94 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/HeartFailure/HeartFailure_GCST90473575.tsv | 10604.40 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/KidneyStone/KidneyStone_GCST90474182.tsv | 10572.52 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Osteoporosis/Osteoporosis_GCST90474133.tsv | 10473.78 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Asthma/Asthma_GCST90473712.tsv | 4862.75 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Rheumatoid/Rheumatoid_GCST90474000.tsv | 4771.69 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Hemoglobin/Hemoglobin_GCST90474471.tsv | 4002.75 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Stroke/Stroke_GCST90473589.tsv | 3979.69 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/ALT/ALT_GCST90473869.tsv | 3962.56 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/CKD/CKD_GCST90474176.tsv | 3962.25 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/C-ReactiveProtein/C-ReactiveProtein_GCST90474349.tsv | 3938.38 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Coronary/Coronary_GCST010767.tsv | 3756.68 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Obesity/Obesity_GCST90473207.tsv | 3519.10 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/HighCholesterol/HighCholesterol_GCST90239649.tsv | 3183.77 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Coronary/Coronary_GCST90132314.tsv | 3099.86 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/UricAcid/UricAcid_GCST90444429.tsv | 2225.21 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/CKD/CKD_GCST90474177.tsv | 2220.42 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Rheumatoid/Rheumatoid_GCST90474003.tsv | 2211.58 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Glucose/Glucose_GCST90002232 | 1549.76 | keep_with_manifest_or_externalize_if_not_required |
| other | temp_uploads/57370b3d_InsulinResist_GCST90002238 | 1487.13 | keep_with_manifest_or_externalize_if_not_required |
| other | temp_uploads/33f46efd_InsulinResist_GCST90002238 | 1487.13 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/gene_source/HeavyDrinker/f30f333a_HeavyDrinker_GCST007461.txt | 1475.42 | split_or_summarize |
| source_or_doc | temp_uploads/f30f333a_HeavyDrinker_GCST007461.txt | 1475.42 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/Osteoporosis/Osteoporosis_GCST90018887.tsv | 1417.07 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Glucose/Glucose_GCST90002233 | 1263.96 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/C-ReactiveProtein/C-ReactiveProtein_GCST90474348.tsv | 1257.30 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Hemoglobin/Hemoglobin_GCST90474470.tsv | 1256.28 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Asthma/Asthma_GCST90473711.tsv | 1240.97 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/T2D/T2D_GCST90018706.tsv | 1207.49 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/KidneyStone/KidneyStone_GCST90018715.tsv | 1201.84 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Stroke/Stroke_GCST90038613.tsv | 1198.45 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/T2D/T2D_GCST90274723.tsv | 1122.50 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/gene_source/T2D/T2D_GCST007847.txt | 950.44 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/Glucose/Glucose_GCST90002234 | 915.57 | keep_with_manifest_or_externalize_if_not_required |
| other | temp_uploads/ee1b10ee_InsulinResist_GCST90002240 | 907.74 | keep_with_manifest_or_externalize_if_not_required |
| other | temp_uploads/2730f764_InsulinResist_GCST90002240 | 907.74 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/gene_source/T2D/T2D_GCST010118.txt | 887.16 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/UricAcid/UricAcid_GCST90278646.tsv | 845.70 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/gene_source/Coronary/Coronary_GCST006405.txt | 747.44 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/UricAcid/UricAcid_GCST90018757.tsv | 732.57 | keep_with_manifest_or_externalize_if_not_required |
| other | temp_uploads/0776eee7_InsulinResist_GCST90002237 | 675.76 | keep_with_manifest_or_externalize_if_not_required |
| other | temp_uploads/27e41396_InsulinResist_GCST90002237 | 675.76 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Depression/Depression_GCST90013959.tsv | 615.58 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Depression/Depression_GCST90013909.tsv | 615.58 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/MobileWell400/activity_recognition.csv | 598.04 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/gene_source/HeartFailure/HeartFailure_GCST009541.txt | 485.29 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/Obesity/Obesity_GCST90566414.tsv | 360.53 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Coronary/Coronary_GCST90000582.tsv | 214.62 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/MobileWell400/screen.csv | 129.41 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/Stroke/Stroke_GCST90432124.tsv | 109.34 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/MobileWell400/light.csv | 96.36 | split_or_summarize |
| other | data_warehouse/raw_data/gene_source/Osteoporosis/Osteoporosis_GCST90080556.tsv | 66.48 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/Obesity/Obesity_GCST90079763.tsv | 63.84 | keep_with_manifest_or_externalize_if_not_required |
| data_model_or_binary | backend/rag/docs/中国居民膳食指南_2022.pdf | 54.02 | keep_with_manifest_or_externalize_if_not_required |
| data_model_or_binary | models/food_resnet_model.pth | 42.96 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/gene_source/UricAcid/UricAcid_GCST90474653.tsv | 42.65 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/USDA/FoodData_Central_sr_legacy_food_csv_2018-04/food_nutrient.csv | 34.68 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/MobileWell400/noise.csv | 29.11 | split_or_summarize |
| data_model_or_binary | backend/rag/docs/慢性肾脏病早期筛查_诊断及防治指南_2022.pdf | 24.99 | keep_with_manifest_or_externalize_if_not_required |
| other | backend/rag/vector_store/chroma.sqlite3 | 18.75 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/NHANES/P_DR1TOT.xpt | 18.35 | keep_with_manifest_or_externalize_if_not_required |
| data_model_or_binary | models/risk_assessment_models.pkl | 17.31 | keep_with_manifest_or_externalize_if_not_required |
| data_model_or_binary | models/nutrition_efficientnet.pth | 15.60 | keep_with_manifest_or_externalize_if_not_required |
| data_model_or_binary | backend/rag/docs/成人高尿酸血症与痛风食养指南_2024.pdf | 15.16 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/NHANES/P_OHXDEN.xpt | 14.68 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/NHANES/P_DSQIDS.xpt | 14.18 | keep_with_manifest_or_externalize_if_not_required |
| other | data_warehouse/raw_data/NHANES/P_DR2TOT.xpt | 9.29 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/raw_data/USDA/FoodData_Central_foundation_food_csv_2025-12-18/food_nutrient.csv | 8.98 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/MobileWell400/connectivity.csv | 8.02 | split_or_summarize |
| other | data_warehouse/raw_data/NHANES/P_MCQ.xpt | 7.21 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_HighCholesterol_weights.csv | 7.21 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/MobileWell400/daily_survey.csv | 7.15 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/clinical_clean/nhanes_integrated_data_v2.csv | 6.52 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/USDA/FoodData_Central_foundation_food_csv_2025-12-18/food.csv | 6.16 | split_or_summarize |
| other | data_warehouse/raw_data/PharmGKB/clinicalAnnotations/clinical_ann_alleles.tsv | 5.30 | keep_with_manifest_or_externalize_if_not_required |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_SystolicBP_weights.csv | 5.23 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/MobileWell400/wifi.csv | 4.75 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/USDA/FoodData_Central_foundation_food_csv_2025-12-18/sub_sample_result.csv | 4.62 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/clinical_clean/nhanes_integrated_data.csv | 4.54 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/USDA/FoodData_Central_foundation_food_csv_2025-12-18/food_update_log_entry.csv | 4.48 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_Hemoglobin_weights.csv | 3.21 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/Nutrition5k/dish_ingredients.csv | 2.18 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_T2D_weights.csv | 2.15 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_C-ReactiveProtein_weights.csv | 2.13 | split_or_summarize |
| source_or_doc | backend/data/nutrition_db.json | 1.86 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_Coronary_weights.csv | 1.74 | split_or_summarize |
| source_or_doc | data_warehouse/processed_data/knowledge_base/GWAS_UricAcid_weights.csv | 1.45 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/USDA/FoodData_Central_foundation_food_csv_2025-12-18/sub_sample_food.csv | 1.23 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-036/CGMacros-036.csv | 1.21 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-039/CGMacros-039.csv | 1.14 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-029/CGMacros-029.csv | 1.14 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-048/CGMacros-048.csv | 1.13 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-049/CGMacros-049.csv | 1.13 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-002/CGMacros-002.csv | 1.12 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-028/CGMacros-028.csv | 1.11 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-001/CGMacros-001.csv | 1.08 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-005/CGMacros-005.csv | 1.08 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-022/CGMacros-022.csv | 1.07 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-006/CGMacros-006.csv | 1.06 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-014/CGMacros-014.csv | 1.06 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-047/CGMacros-047.csv | 1.05 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-045/CGMacros-045.csv | 1.05 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-020/CGMacros-020.csv | 1.03 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-030/CGMacros-030.csv | 1.03 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-013/CGMacros-013.csv | 1.02 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-023/CGMacros-023.csv | 1.02 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-010/CGMacros-010.csv | 1.01 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-016/CGMacros-016.csv | 1.01 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/MobileWell400/initial_survey.csv | 1.01 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-021/CGMacros-021.csv | 1.01 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-033/CGMacros-033.csv | 1.01 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-026/CGMacros-026.csv | 1.00 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-017/CGMacros-017.csv | 1.00 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-015/CGMacros-015.csv | 0.99 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-046/CGMacros-046.csv | 0.97 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-044/CGMacros-044.csv | 0.97 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-043/CGMacros-043.csv | 0.97 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-042/CGMacros-042.csv | 0.97 | split_or_summarize |
| source_or_doc | data_warehouse/raw_data/CGMacros/CGMacros-038/CGMacros-038.csv | 0.96 | split_or_summarize |

## Long Source Or Documentation Files

| Path | Lines | Size KB | Suggested action |
| --- | --- | --- | --- |
| backend/services/chat_service.py | 2362 | 102.4 | module_split_candidate |
| docs/qa-report.md | 2297 | 142.3 | summarize_or_archive_candidate |
| docs/api-contract.md | 1915 | 97.2 | summarize_or_archive_candidate |
| tests/test_chat_agent_service.py | 1785 | 70.4 | module_split_candidate |
| frontend/src/views/chat/DrAI.vue | 1763 | 88.1 | module_split_candidate |
| backend/services/agent_tools.py | 1612 | 51.2 | module_split_candidate |
| docs/data-model-contract.md | 1596 | 87.2 | summarize_or_archive_candidate |
| backend/main.py | 1199 | 46.6 | module_split_candidate |
| docs/architecture.md | 1176 | 102.1 | summarize_or_archive_candidate |
| tests/test_chat_endpoint_contract.py | 1063 | 39.9 | module_split_candidate |
| frontend/src/views/ClinicalView.vue | 981 | 44.5 | module_split_candidate |
| backend/services/agent_safety.py | 948 | 34.7 | module_split_candidate |
| backend/services/payload_normalization.py | 894 | 34.2 | module_split_candidate |
| tests/test_main.py | 870 | 29.2 | module_split_candidate |

## Safe Cleanup Guidance

- Business source files should be split only behind existing public contracts and with regression tests.
- Model/data assets should be kept if they are runtime inputs; consider manifest documentation or external storage only after reference checks.
- Generated reports should keep their generator scripts as the source of truth.
- Never delete a large file only because it is large.
