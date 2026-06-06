# 历史遗留清理 Phase 4

生成时间：2026-04-24

## 当前阶段

阶段 4：历史遗留清理与可重建产物治理。

## 范围

本阶段只清理确认可重建、未被 Git 跟踪、不会影响业务运行的本地缓存、临时目录、构建产物和测试输出。阶段 1 清单中的数据集、模型权重、RAG PDF、向量库、上传资产、论文图片和已跟踪临时样例均未删除。

## 已执行清理

| 类型 | 路径 | 处理 |
| --- | --- | --- |
| Python 缓存 | `backend/**/__pycache__`, `tests/__pycache__`, `ai_core/__pycache__`, `frontend/tests/python-shims/**/__pycache__` | 删除，可由 Python 运行自动重建 |
| Pytest 缓存 | `.pytest_cache/` | 删除，可由 pytest 自动重建 |
| 前端构建产物 | `frontend/dist/` | 删除，已用 `npm.cmd run build` 验证可重建 |
| 前端临时验证产物 | `frontend/.tmp/` | 删除，属于本地 E2E/验证输出 |
| 根级临时目录 | `.tmp/` | 删除，属于本地 OCR、浏览器、论文渲染与检查产物 |
| 文档抽取临时目录 | `tmp_doc_extract/` | 删除，属于本地 Word/规格抽取中间产物 |
| Playwright 输出 | `output/` | 删除，属于可重建截图/视频/JSON 验证输出 |

首轮清理约释放 `21.8 MB` 本地临时/缓存/构建产物。后续验证命令重新生成的 `.pytest_cache/`、`__pycache__/`、`frontend/dist/` 已在验证后再次清理。

## 已更新治理规则

- 修复 `.gitignore` 中历史乱码注释，使敏感信息、Python、前端、数据仓库、模型、数据库、日志缓存、IDE、系统文件和项目特定产物分类可读。
- 新增或明确忽略规则：`frontend/.tmp/`、`.tmp/`、`tmp_doc_extract/`、`output/`。
- 保留既有数据、模型、向量库、上传目录和生成 PDF 的忽略策略，避免后续把大体积运行资产误纳入普通代码提交。

## 明确未清理项

| 路径/类别 | 原因 |
| --- | --- |
| `data_warehouse/` | 原始与处理后健康数据可能用于训练、评估或答辩复现，需要资产清单或外部化方案后再处理 |
| `models/`、`*.pkl`、`*.pth` 等 | 模型资产可能是运行和实验复现输入，不能只因体积大删除 |
| `backend/rag/docs/`、`backend/rag/vector_store/` | RAG 知识库与向量库属于功能资产，需单独制定重建脚本和保留策略 |
| `temp_uploads/` | 体积很大但可能包含历史上传/演示输入，需 owner 确认后处理 |
| `tmp/pdfs/*.png` | 当前为 Git 已跟踪文件，本阶段不删除已跟踪资产 |
| `test-results/.last-run.json` | 当前为 Git 已跟踪文件，本阶段不删除已跟踪测试状态文件 |
| `thesis_latex/*.png` 删除标记 | 工作区既有状态，本阶段不恢复、不扩大、不接管 |

## 验证证据

- `python -m pytest tests -q`：通过，`240 passed in 66.52s`。
- `npm.cmd run build`：通过，`vite build` 成功，`built in 8.93s`。
- 清理脚本在删除前校验目标绝对路径位于 `E:\health_ai_platform_2.0` 内，并跳过 Git 已跟踪路径。

## 契约与风险控制

- 无 API 路由、请求/响应 envelope、数据库 schema、OCR/RAG/Agent 工具契约、前端 API 契约变更。
- 无业务源代码删除。
- 无模型、数据、PDF、SQLite/向量库等功能资产删除。
- 剩余大文件和历史资产不再视为“可直接删除垃圾”，后续必须走资产 owner 复核、重建脚本确认或外部化方案。

## 下一阶段建议

如果继续做仓库维护，下一阶段建议进入“资产保留与外部化策略”：为 `data_warehouse/`、`models/`、`backend/rag/docs/`、`backend/rag/vector_store/`、`temp_uploads/` 建立 manifest、重建说明和答辩展示保留边界，而不是直接删除。
