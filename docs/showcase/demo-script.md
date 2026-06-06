# HealthAI Platform 答辩演示脚本

## 2026-05-13 Lifestyle behavior upload update

- New demo option: on the Lifestyle page, upload a platform-standard behavior-day `.csv` or `.json` file to preview a user-provided day timeline.
- Backend boundary: the upload calls authenticated multipart `POST /api/v1/lifestyle/import-behavior-day`; it parses and validates only, with no persistence.
- What to say on success: the response returns import metadata plus `behavior_day.lifestyle_context`; all uploaded timeline/context data is `data_mode="user_uploaded"` and provenance-labeled.
- Selector note: optional `patient_id` and `local_date` fields are assertions. If they do not match the file, the platform rejects the upload instead of silently switching patients or dates.
- Error note: validation failures use structured `400`; files over 1 MB use `413`; unsupported extension/content type uses `415`.
- Demo continuity: the existing `simulated_demo` scenarios remain available, so presenters can show either prepared examples or a user-uploaded behavior day.
- Device boundary: the real-device API remains a visible placeholder only and is not connected to wearable, vendor, or background-sync data.
- QA status: PASS with focused backend `18 passed`, focused frontend `15 passed`, full backend `269 passed`, frontend build success, live contract probes, and headed browser upload artifacts under `output/playwright`.

## 2026-05-07 Lifestyle Digital Twin demo update

- Recommended placement: show the Lifestyle behavior simulator immediately after Clinical/OCR data entry and before the main risk-analysis explanation, so the audience sees how clinical profile evidence and optional behavior context meet at the analysis boundary.
- What to show: load/select one of the three demo patients, replay the `simulated_demo` day timeline, inspect an event, show summary metrics, point out diet_vision nutrition sync, then run the demo-aware comprehensive analysis.
- Boundary to say out loud: this is `simulated_demo` / Demo-only behavior replay, not real wearable, IoT, food-camera, or device evidence.
- Fusion wording: `/analyze/comprehensive` receives optional `lifestyle_context.v1`; it supports a provenance-labeled heuristic explanation, not a clinically calibrated posterior probability.
- Persistence boundary: replay and demo analysis do not auto-save profile data, do not call IoT batch sync, do not upload documents or food images, and do not create health-history rows.
- QA caveat: current QA PASS includes focused backend tests, frontend node tests, frontend build, and a browser check with mocked demo APIs; it is not a full live authenticated FastAPI E2E run across all three demo patients.

生成时间：2026-04-24

## 演示目标

用 8 到 10 分钟说明平台的产品价值、技术闭环、模型证据、工程治理和交付稳定性，让评审先理解“为什么做”，再看到“如何做”和“做到什么程度”。

## 演示动线

| 时间 | 页面/材料 | 讲解重点 |
| --- | --- | --- |
| 0:00-1:00 | README 展示入口 | 项目定位、慢病管理痛点、多模态闭环 |
| 1:00-2:30 | 前端主界面 | Vue3 + Vite 前端、健康模块导航、数据入口 |
| 2:30-4:00 | 体检 OCR / Clinical | OCR 到 canonical metrics，说明 AST/HGB/UA 已纳入 report-level 指标 |
| 4:00-5:30 | 风险分析 / Dashboard | LightGBM 风险模型、启发式融合语义、趋势追踪 |
| 5:30-7:00 | Dr. AI | RAG、证据面板、建议卡片、只读工具调用、安全分流 |
| 7:00-8:30 | 工程治理 | 多 Agent 黑板、架构契约、QA 报告、阶段 1-5 维护记录 |
| 8:30-10:00 | 指标与边界 | 量化结果、离线评估边界、下一步优化路线 |

## 讲解话术

- 开场：这个项目不是单点模型 demo，而是一套围绕慢病管理闭环设计的 HealthAI Platform。
- 价值：用户上传体检报告后，系统把非结构化报告转为结构化健康画像，再结合模型、知识库和对话式建议形成干预闭环。
- 技术：前端负责清晰交互，后端负责契约化服务链路，AI/data 负责训练与评估资产，QA 负责回归证据。
- 可信：回答不是裸 LLM 输出，而是有证据标签、证据面板、工具状态、建议卡片和审计记录支撑。
- 边界：当前指标主要是仓库内离线评估证据，不夸大为临床诊断性能。

## 应急方案

| 风险 | 应对 |
| --- | --- |
| 本地服务启动慢 | 先展示 README、project-one-page、QA 报告和截图/录屏证据 |
| OCR 凭证不可用 | 说明 manual-entry fallback 和 synthetic post-OCR 评估边界 |
| Redis 不可用 | 说明缓存为可降级依赖，不影响核心 API 可用性 |
| LLM API 不可用 | 使用离线 answer-quality rubric 和已记录 QA 证据说明链路设计 |
| 前端网络异常 | 切换到后端 `/docs`、QA 报告、黑板状态和测试输出证据 |

## 结束话术

总结时强调三点：第一，项目完成了多模态健康管理闭环；第二，模型指标和系统行为都有可追溯证据；第三，多 Agent 治理让开发过程具备契约、QA 和交付闭环。
