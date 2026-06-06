# HealthAI Platform 展示一页纸

生成时间：2026-04-24

## 一句话定位

HealthAI Platform 是一个面向慢病风险评估与个性化健康干预的全栈 AI 健康管理平台，核心闭环是“多模态数据采集 - 风险分析 - 证据问答 - 历史追踪”。

## 展示亮点

- 多模态融合：体检指标、基因风险、生活方式、营养与医学知识库共同进入健康画像。
- 智能决策链路：后端通过 FastAPI 串联 OCR、RAG、风险模型、只读工具调用、审计与可解释输出。
- 可解释问答：Dr. AI 不只给答案，还展示 evidence_tags、evidence_panel、suggestion_card 与安全分流状态。
- 工程治理：多 Agent 黑板机制记录 PM、架构、BE、FE、AI/data、QA 与交付状态，避免静默契约漂移。
- 可交付验证：后端 pytest、前端 Vite build、Playwright E2E、Docker Compose 健康检查共同支撑交付可信度。

## 可量化证据

| 能力 | 当前证据 | 说明 |
| --- | --- | --- |
| OCR canonical 抽取 | micro-F1 1.000 | 50 份合成 post-OCR 体检报告样本，AST/HGB/UA 已按契约纳入 report-level canonical metrics |
| RAG 检索 | Hit@5 0.770 | 离线词法基线，用于答辩说明检索链路，不等同线上向量库最终效果 |
| Agent 策略层 | pass rate 1.000 | 100 条分类型策略问题，覆盖安全分流、工具白名单与拒答边界 |
| 回答质量 | mean score 0.940 | 离线 rubric/reference-template 评估，需与真实 LLM 输出区分 |
| 后端回归 | 243 passed | 阶段 5 使用 `python -m pytest tests -q` 验证 |
| 前端构建 | build success | 阶段 5 使用 `npm.cmd run build` 验证 |

## 推荐演示顺序

1. README 展示入口：先说明项目目标、闭环和治理边界。
2. 前端首页/登录后主流程：展示健康数据入口与核心模块导航。
3. 体检 OCR：上传或说明样例报告如何进入 canonical metrics。
4. 风险分析：展示风险卡片、趋势追踪和个性化建议。
5. Dr. AI：展示证据面板、建议卡片、工具状态和安全分流。
6. 工程证据：展示测试、QA 报告、黑板状态和维护阶段记录。

## 边界声明

- 本项目用于毕业设计、工程展示与研究验证，不替代医生诊断。
- 指标来自仓库内离线评估与合成/半合成样本，不能直接宣称临床真实世界泛化能力。
- API、数据模型、OCR/RAG/Agent 契约变更必须走架构变更流程，FE/BE 不允许静默改契约。
- 大体积数据、模型权重、RAG PDF、向量库与上传资产属于功能资产，不能只因体积大删除。
