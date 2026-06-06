# 阶段 6 完整验收报告

生成时间：2026-04-24

## 当前阶段

阶段 6：资产 manifest 与外部化策略完整验收。

## 验收范围

- 建立机器可读资产 manifest：`docs/maintenance/asset-manifest-phase6.json`。
- 建立人类可读资产策略文档：`docs/maintenance/asset-manifest-phase6.md`。
- 建立本验收报告：`docs/maintenance/phase6-acceptance-report.md`。
- 将阶段 6 入口补充到 README 展示入口。
- 新增自动化验收测试：`tests/test_asset_manifest_phase6.py`。

## 验收结论

阶段 6 验收通过。当前仓库的大体积资产不再被笼统称为“历史垃圾”，而是按 raw data、processed data、model artifacts、RAG documents、vector store、upload samples、runtime databases、thesis artifacts 八类进行归档治理。

## 关键验收项

| 验收项 | 结果 |
| --- | --- |
| 资产类别覆盖 | 通过，8 类关键资产均已纳入 JSON manifest |
| 直接删除策略 | 通过，`direct_delete_allowed=false` |
| owner 复核策略 | 通过，归档/外部化前必须 owner review |
| 展示边界 | 通过，每类资产都有 demo_boundary |
| 外部化策略 | 通过，每类资产都有 externalization_strategy |
| README 入口 | 通过，README 已链接 manifest 与验收报告 |
| 自动化守卫 | 通过，新增 Phase 6 验收测试 |

## 验证命令

- `python -m pytest tests/test_asset_manifest_phase6.py tests/test_showcase_hygiene.py -q`
  - 结果：通过，`6 passed in 0.03s`。
- `python -m pytest tests -q`
  - 结果：通过，`246 passed in 58.35s`。
- `npm.cmd run build`
  - 结果：通过，`built in 7.43s`。

## 保护边界

- 未删除数据、模型、PDF、向量库、数据库、上传资产或论文文件。
- 无 API 路由、请求/响应 envelope、数据库 schema、模型 I/O 或前端 API 契约变更。
- 未修改前端 UI 行为、后端业务服务、模型训练脚本或 ETL 数据处理逻辑。
- 未接管既有 thesis_latex 删除标记，后续需由论文 owner 单独确认。

## 剩余风险

- `data_warehouse/raw_data` 约 148.7GB，长期仍建议迁移到外部数据盘或对象存储。
- `temp_uploads` 约 7.6GB，可能包含历史上传或演示输入，必须先做隐私复核。
- `backend/rag/vector_store` 可重建性需要由 RAG build 命令和 smoke retrieval 测试进一步固化。
- `backend/health_ai_v2.db` 应用 migration + seed 方案替代不可解释的本地状态。

## 最终建议

阶段 6 已经完成“能不能验收”的闭环。下一阶段如果继续推进，应进入 owner 分派和外部化执行，而不是继续扩大清理范围：先为数据、模型、RAG、上传样例和论文产物分别指定 owner，再逐项补 checksum、重建命令、最小 demo 样例和回归验证。
