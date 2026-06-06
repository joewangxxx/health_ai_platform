# HealthAI Platform 展示检查清单

## 2026-05-13 Lifestyle behavior upload checks

- Prepare one platform-standard behavior-day `.csv` or `.json` file when the upload flow is part of the demo.
- Confirm the Lifestyle page upload control is visible and the existing demo scenarios are still available.
- Confirm a successful upload is described as `user_uploaded` preview data, not simulated demo data and not real-device data.
- Confirm optional `patient_id` / `local_date` selectors match the file when used; mismatch is expected to reject with structured `400` validation.
- Confirm error semantics before release/demo narration: structured `400` validation, `413` oversize, and `415` unsupported media.
- Confirm no persistence claim is made: uploaded behavior is parse-only and does not write profile, IoT, health-history, medical-document, or risk-snapshot state.
- Confirm the real-device API remains placeholder-only/not connected.
- Keep QA wording current: focused backend `18 passed`, focused frontend `15 passed`, full backend `269 passed`, frontend build passed, and live browser/contract artifacts are under `output/playwright`.

## 2026-05-07 Lifestyle demo checks

- Use only the committed `simulated_demo` scenarios for the Lifestyle simulator, and keep Demo-only labels visible while replaying.
- Place the Lifestyle simulator between Clinical/OCR and risk analysis; do not describe the replay as live wearable, IoT, food-camera, or device evidence.
- Explain that `lifestyle_context.v1` is optional analysis context for heuristic explanation, not a required clinical input floor and not a calibrated posterior probability.
- Confirm the demo path does not auto-save profile data, does not sync IoT records, does not upload documents or food images, and does not create health-history rows.
- If asked about QA depth, state the current PASS used focused backend/frontend tests, frontend build, and a mock-API browser check rather than full live authenticated FastAPI E2E across all three demo patients.

生成时间：2026-04-24

## 展示前检查

- 确认仓库路径为 `E:\health_ai_platform_2.0`。
- 运行 `python -m pytest tests -q`，记录通过数量和耗时。
- 运行 `npm.cmd run build`，确认 Vite production build 成功。
- 准备 `.env`，但不得在投屏时展示密钥。
- 确认 README 顶部展示入口、`docs/showcase/` 和 `docs/evaluation/` 可打开。
- 准备一份可公开展示的体检报告样例或合成样例，不展示真实个人隐私。

## 现场演示检查

- 浏览器缩放保持 100% 或 110%，避免表格和证据面板拥挤。
- 先展示产品闭环，再展示代码和指标，避免一开始陷入实现细节。
- Dr. AI 演示时优先选择安全、常见、可解释的问题。
- 展示指标时同步说明数据来源、样本规模和评估边界。
- 展示黑板时强调这是协作治理层，不是替代产品架构的额外复杂度。

## 观感风险清单

| 风险 | 处理策略 |
| --- | --- |
| README 信息过长 | 使用顶部展示入口快速跳转，不从头逐段滚动 |
| 工作区存在历史脏文件 | 说明阶段 1-5 已完成清单化、编码治理、源码拆分、历史清理和展示治理 |
| 大文件仍存在 | 说明数据/模型/RAG 资产不能盲删，下一步走 manifest 与外部化 |
| 指标被追问真实性 | 明确区分离线合成评估、仓库回归测试和真实世界临床验证 |
| 终端中文乱码 | 使用 UTF-8 文档和浏览器展示，避免直接依赖 PowerShell 默认编码显示中文 |

## 结束后归档

- 将最新 QA 证据写入 `docs/qa-report.md`。
- 将阶段结论写入 `docs/maintenance/presentation-polish-phase5.md`。
- 由 orchestrator 更新 `docs/blackboard/state.yaml`。
- 不把本地临时截图、录屏、缓存和构建产物纳入提交。
