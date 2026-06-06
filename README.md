# 🏥 HealthAI Platform v2.0

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js)
![License](https://img.shields.io/badge/License-MIT-green)

### 基于多模态数据融合与AI决策的个性化健康管理平台

**Multi-Modal AI Health Management System**

*融合基因组学 · 临床表型 · 生活行为数据的智能医疗平台*

</div>

---

## 答辩展示入口

如果用于项目答辩或代码展示，建议先从下面 5 个入口进入，避免直接在长文档和历史治理记录中迷路：

| 展示材料 | 用途 |
| :--- | :--- |
| [项目展示一页纸](./docs/showcase/project-one-page.md) | 用 1-2 分钟讲清楚项目定位、亮点、指标和边界 |
| [答辩演示脚本](./docs/showcase/demo-script.md) | 按 8-10 分钟动线串起前端、OCR、风险分析、Dr. AI 和工程治理 |
| [展示检查清单](./docs/showcase/presentation-checklist.md) | 演示前确认环境、隐私、指标口径和应急方案 |
| [展示观感治理记录](./docs/maintenance/presentation-polish-phase5.md) | 说明阶段 5 做了哪些展示入口、文档观感和编码卫生治理 |
| [资产 Manifest 与外部化策略](./docs/maintenance/asset-manifest-phase6.md) | 说明大体积数据、模型、RAG、上传和论文资产如何保留、外部化和验收 |
| [阶段 6 完整验收报告](./docs/maintenance/phase6-acceptance-report.md) | 汇总资产治理验收结论、保护边界、验证命令和剩余风险 |
| [项目评估汇总](./docs/evaluation/project-evaluation-summary.zh.md) | 展示 OCR、RAG、Agent、回答质量和风险模型的量化证据 |

当前推荐讲述主线：项目价值 -> 多模态闭环 -> 核心功能演示 -> 模型/Agent 指标证据 -> 多 Agent 工程治理 -> 风险边界与后续优化。

### Lifestyle Digital Twin demo handoff note

For the defense demo, place the Lifestyle behavior simulator after Clinical/OCR import and before the main risk-analysis explanation. It shows a `simulated_demo` / Demo-only day timeline for three prepared demo patients, including behavior events, diet-vision nutrition sync, summary metrics, and optional `lifestyle_context.v1` fusion explanation.

Boundary to state out loud: the timeline is not real wearable/device evidence, does not auto-save profile data, does not write IoT records, and does not create health-history rows. `/analyze/comprehensive` can use the selected scenario's optional `lifestyle_context` as provenance-labeled heuristic context only; it is not a clinically calibrated posterior probability or live device proof.

Latest QA status for this slice: PASS with focused backend tests (`6 passed`), frontend node tests (`13 passed`), frontend build success, and a real Vite browser check using mocked demo APIs. Residual risk remains that QA did not run a full live authenticated FastAPI login/API/browser end-to-end path across all three demo patients.

### Lifestyle behavior upload readiness note

The Lifestyle page now also supports platform-standard behavior-day `.csv` and `.json` uploads. The frontend submits an authenticated multipart request to `POST /api/v1/lifestyle/import-behavior-day`; the backend parses and validates the file only, with no raw upload storage, IoT sync, profile save, health-history write, medical-document write, or risk-snapshot persistence.

Successful imports return import metadata plus a generated `behavior_day` containing nested `lifestyle_context.v1`. The generated behavior day, timeline events, diet-vision provenance, and lifestyle context remain labeled `data_mode="user_uploaded"` with `source_provenance.source_type="user_uploaded"`. Optional `patient_id` and `local_date` multipart selectors are assertions; mismatches are rejected.

Error semantics are release-ready for the approved contract: structured `400` validation errors, `413` for uploads over 1 MB, and `415` for unsupported media. Existing demo scenarios remain available as examples/fallbacks, and the real-device API remains a visible placeholder only; it is not connected to wearable, vendor, or background-sync data.

Latest QA status for this slice: PASS with focused backend regression (`18 passed`), focused frontend node regression (`15 passed`), full backend regression (`269 passed`), frontend production build success, live contract probes, and headed browser upload artifacts under `output/playwright/`.

---

## Governance Update

### 2026-04-23 Stability & Governance Remediation Snapshot

- Current QA evidence:
  - `python -m pytest tests -q` passed (`235 passed`)
  - `python -m pytest tests/test_cors_config.py -q` passed (`3 passed`)
  - `npm.cmd run build` in `frontend` passed
  - targeted Playwright smoke passed:
    - `tests/dr-ai-takeover.spec.js` (`3 passed`)
    - `tests/ocr-guided-completion.spec.js` (`4 passed`)
- Strict model compatibility status:
  - `python ai_core/check_model_compatibility.py --strict` passed (`exit code 0`) with baseline versions:
    - `xgboost==2.1.4`
    - `torch==2.5.1`
    - `torchvision==0.20.1`
    - `scikit-learn==1.6.1`
    - `joblib==1.5.3`
- Residual non-blocking warnings:
  - `torch.load(..., weights_only=False)` `FutureWarning` still appears in compatibility/smoke logs.
  - local Playwright webserver logs may still show optional Redis degraded warning in environments without Redis.
- Contract-aligned wording and boundaries (architect-frozen):
  - fusion formula semantics are **heuristic multiplicative scaling** (`base x gene_modifier x lifestyle_modifier`), not a strict Bayesian posterior claim.
  - Baidu OCR, Moonshot/Kimi-compatible LLM calls, and RAG retrieval are backend-mediated; raw provider payloads/raw RAG passages are not public API output.
  - logs and audit/replay records stay bounded metadata only and must not store raw health payload text.

- 审计责任记录新写入 schema：`agent_audit_responsibility.v2`
- 当前运行时治理基线：`agent_runtime_governance.v1`
- 当前写入审计的策略版本基线：`explicit_policy.v1`
- `AgentAuditEvent` 现在是 backend internal-only 的责任记录，不会通过 `/chat/send`、`/chat/stream`、SSE status 或历史回放对外暴露
- rollout 前需要先执行迁移：[20260401_add_agent_audit_responsibility_fields.py](./backend/alembic/versions/20260401_add_agent_audit_responsibility_fields.py)
- 审计仍保持 metadata-only：不得持久化原始 query、原始 reply、原始 prompt、大段 RAG 文本、原始工具结果或未脱敏医疗 payload

---

## 📂 Product Strategy & Management Artifacts

> 本项目不仅是代码的实现，更是一个**完整产品生命周期**的推演。
> 从市场洞察到商业闭环，每一个决策都基于数据与逻辑。

## 📌 核心价值主张
> **🛑 行业痛点**:
> 当前健康管理市场面临严重的**数据孤岛效应**。基因数据锁在实验室，体检报告沉睡在 PDF 中，IoT 数据散落在各个 App 里。更致命的是，市面产品止步于"相关性分析"，无法回答用户最关心的因果问题（*"如果我现在减重 5kg，未来 10 年心血管风险能降多少？"*）。

> **🟢 我们的破局**:
> **Health AI Platform (HAP)** 采用多模态风险融合范式。当前线上融合语义为 **启发式乘法缩放**（`base x gene_modifier x lifestyle_modifier`），将 **Clinical (临床表型)**、**Genomic (基因组学)**、**Lifestyle (生活方式)** 三维异构数据用于风险评估与分层建议。

### 📄 产品工件集 (Documentation Matrix)

以下文档完整展示了 HAP v2.0 从 0 到 1 的孵化过程，点击 **View** 可查看详细报告：

| Document Type | Key Focus | Core Competencies | Link |
| :--- | :--- | :--- | :---: |
| **📊 竞品分析与行业洞察**<br>*(Market Analysis)* | 市场规模测算 (TAM/SAM/SOM)、SWOT分析、差异化定位 | `Market Research` `Competitive Analysis` `Blue Ocean Strategy` | [👉 View](./docs/COMPETITIVE_ANALYSIS.md) |
| **💼 商业模型与数据指标**<br>*(Business Logic)* | 商业画布 (BMC)、北极星指标、CLV/CAC 经济模型 | `Business Model Canvas` `North Star Metric` `Unit Economics` | [👉 View](./docs/BUSINESS_AND_METRICS.md) |
| **🚀 商业化验证与增长实验**<br>*(GTM Strategy)* | MVP 冷启动策略、A/B Test 实验设计、会员分层体系 | `Growth Hacking` `GTM Strategy` `Monetization` | [👉 View](./docs/COMMERCIAL_VALIDATION.md) |
| **📝 产品需求文档 (PRD)**<br>*(Execution)* | 功能详细定义、用户故事 (User Stories)、非功能性需求 | `Requirement Definition` `Product Roadmap` `System Design` | [👉 View](./docs/PRD.md) |

---

## 🎯 核心理念

HealthAI Platform 是一个基于**多模态数据融合**的智能医疗平台。区别于传统单一指标评估，本平台通过融合三大数据维度，实现对慢性疾病的**精准风险评估**与**全生命周期管理**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Fusion Risk Engine                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│  🧬 Genomics    │  🩺 Clinical   │  ⌚ Lifestyle          │
│  基因风险因子    │  体检生化指标    │   IoT 行为数据           │
│  (SNP/PRS)      │  (NHANES)       │  (MobileWell)           │
└─────────────────┴─────────────────┴─────────────────────────┘
                           ↓
              个性化风险评估 + 精准干预建议
```

---

## ✨ 核心功能

### Multimodal Risk Fusion Engine
- 结合 **LightGBM** 临床模型与基因/生活方式修饰因子进行启发式融合
- 综合分析先天遗传风险与后天表型数据
- 支持 12+ 慢性疾病风险预测（糖尿病、高血压、冠心病、CKD 等）
- **AHA CKM 分期评估**：心-肾-代谢综合征 0-4 期分层

### 🩺 智能病历录入 (Medical OCR)
- 集成 **百度高精度 OCR** + **LLM 结构化解析** (Kimi/Qwen)
- 支持 JPG/PNG/PDF 体检单自动识别
- 提取 **50+ 项生化指标**，自动映射至健康档案
- 智能缓存失效：数据更新后自动刷新 AI 建议

### 🤖 Dr. AI 健康顾问 (RAG)
- **检索增强生成 (RAG)** 技术，基于 ChromaDB 向量检索
- 当回答需要人工接管时，会额外显示后端 owned 的结构化接管提示，帮助用户理解下一步该做什么
- 内置 9 大权威医学指南知识库：
  - 《中国居民膳食指南 2022》
  - 《中国高血压防治指南 2024》
  - 《中国 2 型糖尿病防治指南》
  - 《中国高尿酸血症与痛风诊疗指南》
  - 更多...
- 结合用户健康画像的**个性化问答**

### 💊 药物基因组学 (Pharmacogenomics)
- 基于 **PharmGKB** 临床注释数据库
- 分析 CYP450 等药物代谢酶基因多态性
- 提供个性化**用药安全建议**与剂量调整参考
- 支持 100+ 常见药物的基因-药物相互作用查询

### 🍎 AI 视觉营养师
- **计算机视觉**食物识别（基于 Nutrition5k 训练）
- 结合 **USDA 营养数据库** 热量估算
- 基于 NHANES 膳食模型的**个性化食谱生成**
- 疾病饮食禁忌自动过滤（高血压低钠、糖尿病低 GI）
- **Redis 智能缓存**：相同条件秒级响应

### ⌚ IoT 实时监控
- 连接可穿戴设备（心率、血压、血糖、睡眠）
- 基于 **MobileWell400+** 行为识别模型
- 久坐提醒、睡眠质量分析、压力指数评估
- 异常指标实时预警

### 📉 全周期健康时光机
- 可视化健康指标趋势（ECharts）
- 多维度风险评分追踪
- 历史体检报告对比分析
- PDF 健康报告导出

---

## 📊 数据资产与模型来源

本平台的 AI 能力由以下权威数据集支撑：

| 数据集 | 来源 | 用途 |
|--------|------|------|
| **NHANES 2017-2020** | CDC (美国疾控中心) | 核心慢病风险模型训练（糖尿病、高血压、CKD），涵盖生化指标、人口学、膳食数据 (P_DR1TOT, P_VID 等) |
| **GWAS Catalog** | EMBL-EBI | 全基因组关联研究，计算多基因风险评分 (PRS) |
| **PharmGKB** | Stanford | 药物-基因相互作用临床注释，支撑智能药房模块 |
| **Nutrition5k** | Google Research | 5000+ 道菜品深度视觉数据，食物识别与热量估算模型 |
| **MobileWell400+** | MIT | 传感器数据行为识别，睡眠/压力分析模型 |
| **USDA SR Legacy** | USDA | 美国农业部标准参考食品数据库，营养素查询 |
| **MIMIC-IV** | MIT *(计划中)* | 重症监护数据，急性异常检测模型 |

### 模型文件

| 模型 | 算法 | 任务 |
|------|------|------|
| `diabetes_risk_model.pkl` | LightGBM | 糖尿病风险预测 |
| `hypertension_risk_model.pkl` | XGBoost | 高血压风险预测 |
| `ckd_risk_model.pkl` | LightGBM | 慢性肾病风险预测 |
| `diet_cluster_model.pkl` | KMeans | 膳食模式聚类 |
| `food_classifier.pth` | ResNet | 食物图像分类 |

---

## 🛠️ 技术栈

### Backend
| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.100+ | 高性能异步 Web 框架 |
| Python | 3.11+ | 核心开发语言 |
| SQLModel | 0.0.18+ | ORM + Pydantic 数据验证 |
| Redis | 4.5+ | LLM 响应缓存 & 会话管理 |
| Celery | - | 异步任务队列 *(预留)* |

### Frontend
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.x | 渐进式前端框架 |
| Element Plus | 2.x | UI 组件库 |
| TailwindCSS | 3.x | 原子化 CSS |
| ECharts | 5.x | 数据可视化 |
| Pinia | 2.x | 状态管理 |

### AI / LLM
| 技术 | 用途 |
|------|------|
| Kimi (Moonshot AI) | 云端 LLM 主力模型 |
| Ollama | 本地 LLM 部署 |
| LangChain | LLM 应用框架 |
| ChromaDB | 向量数据库 (RAG) |
| PaddleOCR / Baidu OCR | 体检单 OCR 识别 |

### ML Core
| 技术 | 用途 |
|------|------|
| XGBoost | 梯度提升模型 |
| LightGBM | 轻量梯度提升模型 |
| Scikit-learn | 特征工程 & 评估 |
| PyTorch | 深度学习模型 |

---

## 🚀 快速启动

### 环境要求
- Python 3.11+
- Node.js 18+
- Redis (可选，用于缓存)
- Docker (可选，推荐)

---

### 🐳 Docker 一键部署 (推荐)

如果你本地安装了 Docker，无需配置 Python 和 Node 环境，只需一行命令即可启动整个平台：

```bash
# 1. 克隆项目
git clone https://github.com/your-username/health-ai-platform.git
cd health-ai-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys

# 3. 启动服务 (后端 + 前端 + Redis)
docker-compose up --build -d

# 4. 访问平台
# 🌐 浏览器打开 http://localhost (无需端口号)
# 📖 API 文档: http://localhost:8000/docs
```

**常用命令**：
```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重建并启动
docker-compose up --build -d
```

---

### 📦 手动部署

如果你不使用 Docker，可以按以下步骤手动配置：

### 1. 克隆项目
```bash
git clone https://github.com/your-username/health-ai-platform.git
cd health-ai-platform
```

### 2. 后端配置
```bash
# 创建虚拟环境
python -m venv venv

# 激活环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys
```

### 3. 启动后端
```bash
python run.py

# ✅ 服务运行于 http://127.0.0.1:8000
# 📖 API 文档: http://127.0.0.1:8000/docs
```

### 4. 前端配置与启动
```bash
cd frontend
npm install
npm run dev

# ✅ 访问 http://localhost:5173
```

---

## ⚙️ 环境变量配置

创建 `.env` 文件：

```env
# ===== LLM API (选择一个) =====
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-8k

# ===== Baidu OCR (可选) =====
BAIDU_OCR_API_KEY=xxx
BAIDU_OCR_SECRET_KEY=xxx

# ===== Redis Cache (可选) =====
REDIS_URL=redis://localhost:6379/0

# ===== Database =====
DATABASE_URL=sqlite:///./health_ai.db
```

---

## 📁 项目结构

```
health_ai_platform_2.0/
├── backend/                      # 后端服务
│   ├── api/                      # API 路由层
│   │   └── api_v1/endpoints/     # RESTful 端点
│   ├── core/                     # 核心配置
│   │   ├── config.py             # 环境配置
│   │   ├── constants.py          # 业务常量
│   │   └── cache.py              # Redis 缓存管理
│   ├── models/                   # SQLModel 数据模型
│   ├── services/                 # 业务逻辑层
│   │   ├── risk_engine.py        # 疾病风险引擎
│   │   ├── gene_risk_engine.py   # 基因风险引擎
│   │   ├── fusion_engine.py      # 多模态融合引擎
│   │   ├── chat_service.py       # Dr. AI 问答
│   │   └── nutrition_service.py# 营养规划
│   └── rag/                      # RAG 知识库
│       ├── vector_store/         # ChromaDB 向量库
│       └── guidelines/           # 医学指南文档
├── frontend/                     # Vue 3 前端
│   └── src/
│       ├── views/                # 页面组件
│       ├── stores/               # Pinia 状态
│       └── components/           # UI 组件
├── ai_core/                      # AI 模型训练脚本
│   ├── train_risk_models.py      # 风险模型训练
│   └── train_diet_model.py       # 膳食模型训练
├── data_warehouse/               # 数据仓库
│   ├── raw_data/                 # 原始数据 (gitignore)
│   └── processed_data/           # ETL 处理后数据
│── docs/                         # 产品经理报告输出
│   ├── BUSINESS_AND_METRICS.md/  # 商业模型与数据指标体系
│   └── COMMERCIAL_VALIDATION.md/ # 商业化验证与增长实验计划
│   └── COMPETITIVE_ANALYSIS.md/  # 竞品分析与行业洞察报告
│   └── PRD.md/                   # 产品需求文档
├── run.py                        # 启动入口
├── requirements.txt              # Python 依赖
└── .env.example                  # 环境变量模板
```

---

## 🔒 安全与隐私

- ✅ API Keys 通过环境变量管理，不硬编码
- ✅ 敏感文件已添加至 `.gitignore`
- ✅ 支持本地 LLM 部署 (Ollama) 以实现离线运行方案
- ✅ 第三方能力边界明确：Baidu OCR 与 Moonshot/Kimi 调用均由后端代理，前端不直接调用供应商接口
- ✅ RAG 检索、OCR 解析与模型调用的原始供应商 payload 不作为公共 API 输出
- ✅ 日志/审计/回放仅保留有界元数据，不持久化原始健康文本与完整提示词/回答转录

---

## 📄 License

MIT License © 2024 HealthAI Platform

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 发起 Pull Request

---

<div align="center">

### 🏥 Built with ❤️ for Precision Health

*让每个人都能享受精准医疗的力量*

</div>
