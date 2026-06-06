# 资产 Manifest 与外部化策略 Phase 6

生成时间：2026-04-24

## 当前阶段

阶段 6：资产 manifest、外部化策略与完整验收。

## 验收目标

本阶段的目标不是删除大文件，而是把“哪些资产有用、为什么保留、未来如何外部化、答辩时如何展示”说清楚，并用自动化测试和全量回归证明治理动作没有影响功能。

## 总体策略

- 直接删除：不允许。
- 归档或外部化：必须先完成 owner 复核、重建路径、校验和、隐私检查和最小可展示样例。
- Git 中保留：只保留必要源码、文档、manifest、小样例和可复现脚本。
- 答辩展示：优先展示来源、指标、流程和边界，不现场打开超大原始文件。

## 资产清单快照

| 资产类别 | 路径 | 文件数 | 大小 MB | Git 跟踪数 | 保留决策 | Owner |
| --- | --- | ---: | ---: | ---: | --- | --- |
| raw_data | `data_warehouse/raw_data` | 285736 | 148691.12 | 0 | keep_with_manifest | ai-data |
| processed_data | `data_warehouse/processed_data` | 24 | 38.88 | 0 | review_before_externalize | ai-data |
| model_artifacts | `models` | 8 | 76.50 | 0 | keep_with_manifest | ai-data |
| rag_documents | `backend/rag/docs` | 9 | 107.20 | 0 | keep_with_manifest | ai-data |
| vector_store | `backend/rag/vector_store` | 6 | 22.68 | 0 | review_before_externalize | ai-data |
| upload_samples | `temp_uploads` | 7 | 7616.68 | 0 | review_before_externalize | orchestrator |
| runtime_databases | `backend/health_ai_v2.db` | 1 | 0.18 | 0 | review_before_externalize | be |
| thesis_artifacts | `thesis_latex` | 91 | 10.40 | 102 | keep | general |

机器可读版本见：`docs/maintenance/asset-manifest-phase6.json`。

## 分类别验收结论

### raw_data

- 结论：保留 manifest，不直接删除。
- 原因：`data_warehouse/raw_data` 约 148.7GB，是 NHANES、GWAS、USDA、Nutrition5k 等训练和评估资产来源。
- 外部化策略：后续可迁移到网盘、对象存储或数据盘，并在仓库保留下载来源、checksum、目录结构说明和小样例。
- 展示边界：答辩时只展示数据来源表、处理流程和评估结果，不打开大体积原始文件。

### processed_data

- 结论：owner 复核后再外部化。
- 原因：处理后表格可能支撑评估复现、模型训练或论文指标。
- 外部化策略：区分“可由 ETL 重建的中间产物”和“当前唯一评估基线”，前者保留生成命令，后者保留 checksum 与小样例。

### model_artifacts

- 结论：保留 manifest，不直接删除。
- 原因：模型权重和 joblib/pkl 资产用于兼容性检查、风险评估、营养视觉模型或答辩复现。
- 外部化策略：模型进入 release asset 或模型存储，记录依赖版本、训练/导出脚本、checksum 和模型卡。

### rag_documents

- 结论：保留 manifest。
- 原因：医学指南 PDF 是 RAG 知识库来源和证据可解释性的基础。
- 外部化策略：保留文档来源、版本、checksum、知识库构建命令和检索 smoke 测试。

### vector_store

- 结论：先 review，再决定是否外部化。
- 原因：向量库可重建，但只有在 RAG 构建脚本、embedding 版本和 smoke 检索通过后才能删除现有索引。
- 外部化策略：优先把向量库视为 generated asset，仓库保留构建命令和验证用例。

### upload_samples

- 结论：必须隐私复核。
- 原因：`temp_uploads` 体积大且可能混有历史上传/演示输入，不能作为普通垃圾处理。
- 外部化策略：保留合成 demo 样例，真实或不确定来源样例需脱敏、归档或删除前人工确认。

### runtime_databases

- 结论：owner 复核后替换为 migration/seed。
- 原因：本地 SQLite 可能保存 demo 状态，也可能保存临时用户数据。
- 外部化策略：使用 Alembic migration、seed 脚本或 sanitized demo DB 替代不可解释的本地数据库。

### thesis_artifacts

- 结论：保留。
- 原因：论文源码、图表和检查产物与答辩材料直接相关；当前工作区已有一些历史删除标记，本阶段不接管、不扩大处理。
- 外部化策略：仅在论文 owner 确认后清理可重建 LaTeX 中间产物，不删除源文件和正式图片。

## 下一步外部化路线

1. ai-data 为 `data_warehouse/raw_data` 和 `models` 补充来源、版本、checksum 和下载/导出命令。
2. be 为 `backend/health_ai_v2.db` 明确 migration + seed 的可重建路径。
3. ai-data 为 `backend/rag/vector_store` 固化 RAG build 命令和 smoke retrieval 验收。
4. orchestrator 对 `temp_uploads` 做隐私和演示价值复核，只保留合成或公开安全样例。
5. general 对 `thesis_latex` 建立 LaTeX 构建产物与正式论文资产的边界。

## 契约边界

- 本阶段无 API 路由、请求/响应 envelope、数据库 schema、模型 I/O 或前端 API 契约变更。
- 本阶段未删除数据、模型、PDF、向量库、数据库、上传资产或论文文件。
- 任何外部化执行阶段都必须重新跑对应功能验证，不能只凭 manifest 删除文件。
