<![CDATA[<div align="center">

# 🏥 Health AI Platform 2.0 (HAP v2.0)

### **基于多模态贝叶斯融合与AI推断的下一代数字生命管理平台**

*Next-Gen Digital Life Management Platform Powered by Multi-Modal Bayesian Fusion & Causal Inference*

---

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js)
![Status](https://img.shields.io/badge/Status-Beta-orange)
![PRs](https://img.shields.io/badge/PRs-Welcome-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## 📌 行业洞察与解决方案

### 🔴 The Problem (痛点)

当前健康管理领域面临三大核心挑战：

| 痛点 | 现状描述 |
|------|----------|
| **数据孤岛效应** | 体检数据沉睡在 PDF 报告中，基因数据锁在专业机构，IoT 数据散落在各个 App，三者无法打通 |
| **被动响应模式** | 绝大多数健康平台仅能"记录过去"，无法"预测未来"，用户不病不来 |
| **缺乏因果推断** | 市面产品止步于"相关性分析"，无法回答"如果我现在减重 5kg，10 年后 CVD 风险能降多少" |

### 🟢 The Solution (破局)

> **Bayesian Fusion (贝叶斯融合)** — 我们将 Clinical (临床表型)、Genomic (基因组学)、Lifestyle (生活方式) 三维异构数据在概率图模型中统一，实现从"被动记录"到"主动预测"的范式转换。

```
┌─────────────────────────────────────────────────────────────────┐
│                    🧠 Bayesian Fusion Engine                     │
├───────────────────┬───────────────────┬─────────────────────────┤
│    🧬 Genomics    │    🩺 Clinical     │    ⌚ Lifestyle         │
│   基因风险因子     │   体检生化指标      │   IoT 行为数据          │
│   GWAS / PRS      │   NHANES Model    │   MobileWell Sensor    │
├───────────────────┴───────────────────┴─────────────────────────┤
│                 P(Disease | Gene, Clinical, IoT)                 │
│               贝叶斯后验概率 → 精准风险评估 → 因果干预建议          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 产品矩阵与核心价值

### 🧬 多模态融合引擎 (Fusion Core)

超越传统的加权求和方法，采用 **LightGBM + Bayesian Network** 联合建模。即使部分数据缺失，系统仍能通过概率推断给出有意义的评估结果。

- ✅ 覆盖 **16+ 慢性疾病** 风险预测 (T2D, CVD, CKD, Gout...)
- ✅ **AHA CKM 2023** 心-肾-代谢综合征 0-4 期分层
- ✅ 中文风险归因解释 (Top 5 致病因子)

---

### 🔮 平行宇宙模拟器 (Causal Digital Twin)

基于 **因果推断 (Causal Inference)** 的健康推演引擎。让用户不仅看到风险，更能看到行动的价值。

- ✅ **What-If 模拟**："如果我坚持每天走 8000 步，1 年后血压会怎样？"
- ✅ **时光机推演**：模拟 5-10 年后的自然病程进展
- ✅ **干预效果量化**：用数字告诉你减重 5kg 能换来多少健康收益

---

### ⌚ 生命体征驾驶舱 (Vital Cockpit)

通过 **Web Bluetooth** 直连真实医疗设备 (血压计、心率带、血糖仪)，实现数据采集到风险计算的毫秒级闭环。

- ✅ 心率异常实时预警 (静息心率 > 100 bpm)
- ✅ 睡眠质量分析 & 压力指数评估
- ✅ 行为模式识别 (MobileWell400+ 模型)

---

### � 全能单据解析 (Universal OCR)

集成 **PaddleOCR + LLM 结构化提取** 双引擎，让沉睡在抽屉里的体检报告"活"起来。

- ✅ 支持 JPG / PNG / PDF 多格式上传
- ✅ 智能提取 **50+ 项生化指标**
- ✅ 自动映射至个人健康档案

> ⚠️ **部署提示**：如遇 MKL-DNN 错误，请在 PaddleOCR 初始化时设置 `enable_mkldnn=False`

---

### 🤖 Dr. AI (RAG Agent)

**检索增强生成 (RAG)** 驱动的循证医学问答，引用权威医学指南，拒绝无源闲聊。

**内置知识库**：
- 《中国高血压防治指南 2024》
- 《中国 2 型糖尿病防治指南》
- 《中国居民膳食指南 2022》
- 《中国高尿酸血症与痛风诊疗指南》
- ... 共 9 大权威指南

---

## 📊 数据资产与算法壁垒

### 训练数据集

| 数据集 | 来源 | 规模 | 用途 |
|--------|------|------|------|
| **NHANES 2017-2020** | CDC (美国疾控) | 10,000+ 样本 | 慢病 LightGBM 模型训练 |
| **GWAS Catalog** | EMBL-EBI | 10M+ SNPs | 多基因风险评分 (PRS) |
| **PharmGKB** | Stanford | 600+ 注释 | 药物基因组学规则库 |
| **Nutrition5k** | Google Research | 5,000+ 菜品 | EfficientNet 食物识别 |
| **USDA SR Legacy** | USDA | 8,000+ 食品 | 营养素查询 |

### 核心算法亮点

| 模块 | 技术 | 优化 |
|------|------|------|
| 临床风险模型 | **LightGBM / XGBoost** | 处理缺失值、自动特征交叉 |
| 食物视觉识别 | **EfficientNet-B0** | PyTorch + OneDNN 加速 |
| 模型加载 | **Lazy Loading** | Lifespan 阶段统一初始化，消除重复加载 |
| 响应缓存 | **Redis TTL** | 相同条件秒级响应 |

---

## 💰 商业化与增长路线图

```
┌─────────────────────────────────────────────────────────────────┐
│               Health AI Platform 商业化演进                      │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Phase 1 (MVP)  │  Phase 2 (Growth)│  Phase 3 (Ecosystem)       │
│    ✅ 当前       │    🔜 计划中      │    🎯 远景                 │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • 融合风险引擎   │ • Freemium 订阅  │ • 数字疗法 (DTx) 认证       │
│ • OCR 智能解析   │ • API Economy   │ • 家庭健康账户体系          │
│ • IoT 直连      │ • B2B 体检赋能   │ • 医院数据互通             │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

**北极星指标 (North Star Metric)**：
> 📈 **"有效健康闭环数"** — 用户完成 `数据录入 → 风险分析 → 干预建议` 完整流程的次数

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Layer 4: UI                               │
│    Vue 3  +  Element Plus  +  TailwindCSS  +  ECharts           │
│                    (Glassmorphism Design)                        │
├─────────────────────────────────────────────────────────────────┤
│                      Layer 3: AI/ML                              │
│   PyTorch  |  LangChain  |  PaddleOCR  |  ChromaDB (RAG)        │
├─────────────────────────────────────────────────────────────────┤
│                     Layer 2: Core Services                       │
│   FastAPI Async  |  FusionEngine  |  RiskEngine  |  OcrService  │
├─────────────────────────────────────────────────────────────────┤
│                       Layer 1: Data                              │
│          SQLite / PostgreSQL  |  Redis Cache  |  VectorDB       │
└─────────────────────────────────────────────────────────────────┘
```

### 技术栈明细

<details>
<summary><b>Backend</b></summary>

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.100+ | 高性能异步 Web 框架 |
| Python | 3.11+ | 核心开发语言 |
| SQLModel | 0.0.18+ | ORM + Pydantic 验证 |
| Redis | 4.5+ | LLM 响应缓存 |

</details>

<details>
<summary><b>Frontend</b></summary>

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.x | 渐进式前端框架 |
| Element Plus | 2.x | UI 组件库 |
| TailwindCSS | 3.x | 原子化 CSS |
| ECharts | 5.x | 数据可视化 |
| Pinia | 2.x | 状态管理 |

</details>

<details>
<summary><b>AI / LLM</b></summary>

| 技术 | 用途 |
|------|------|
| Kimi (Moonshot AI) | 云端 LLM 主力模型 |
| Ollama | 本地 LLM 部署 |
| LangChain | LLM 应用框架 |
| ChromaDB | 向量数据库 (RAG) |
| PaddleOCR / Baidu OCR | 体检单 OCR |

</details>

<details>
<summary><b>ML Core</b></summary>

| 技术 | 用途 |
|------|------|
| LightGBM | 轻量梯度提升 |
| XGBoost | 梯度提升模型 |
| Scikit-learn | 特征工程 |
| PyTorch | 深度学习 |

</details>

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- Redis (可选，用于缓存)
- Docker (可选，推荐)

---

### 🐳 Docker 一键部署 (推荐)

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
# 🌐 浏览器打开 http://localhost
# 📖 API 文档: http://localhost:8000/docs
```

**常用命令**：
```bash
docker-compose logs -f       # 查看日志
docker-compose down          # 停止服务
docker-compose up --build -d # 重建并启动
```

---

### 📦 手动部署

```bash
# 1. 克隆项目
git clone https://github.com/your-username/health-ai-platform.git
cd health-ai-platform

# 2. 后端配置
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys

# 4. 启动后端
python run.py
# ✅ http://127.0.0.1:8000
# 📖 http://127.0.0.1:8000/docs

# 5. 前端配置与启动
cd frontend
npm install
npm run dev
# ✅ http://localhost:5173
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
├── backend/                    # 后端服务
│   ├── api/api_v1/endpoints/   # RESTful 端点
│   ├── core/                   # 配置、常量、缓存
│   ├── services/               # 业务逻辑层
│   │   ├── risk_engine.py      # 疾病风险引擎
│   │   ├── gene_service.py     # 基因风险引擎
│   │   ├── fusion_service.py   # 多模态融合
│   │   └── chat_service.py     # Dr. AI 问答
│   └── rag/                    # RAG 知识库
├── frontend/                   # Vue 3 前端
├── ai_core/                    # AI 模型训练脚本
├── data_warehouse/             # 数据仓库
├── docs/                       # 商业文档
│   ├── COMPETITIVE_ANALYSIS.md # 竞品分析
│   ├── BUSINESS_AND_METRICS.md # 商业模型
│   └── PRD.md                  # 产品需求文档
├── run.py                      # 启动入口
└── requirements.txt            # Python 依赖
```

---

## 🔒 安全与隐私

- ✅ 所有用户数据**本地存储**，不上传第三方服务器
- ✅ 基因数据 **AES 加密存储**
- ✅ API Keys 通过环境变量管理，不硬编码
- ✅ 支持本地 LLM (Ollama) 实现**完全离线运行**

---

## 📄 License

MIT License © 2024-2026 Health AI Platform

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

**[📖 API Docs](http://localhost:8000/docs)** · **[🐛 Report Bug](https://github.com/your-username/health-ai-platform/issues)** · **[💡 Request Feature](https://github.com/your-username/health-ai-platform/issues)**

</div>
]]>
