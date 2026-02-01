# 🏥 HealthAI Platform v2.0

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js)
![License](https://img.shields.io/badge/License-MIT-green)

### 全周期慢病精准管理平台

**Multi-Modal AI Health Management System**

*融合基因组学 · 临床表型 · 生活行为数据的智能医疗平台*

</div>

---

## 🎯 核心理念

HealthAI Platform 是一个基于**多模态数据融合**的智能医疗平台。区别于传统单一指标评估，本平台通过融合三大数据维度，实现对慢性疾病的**精准风险评估**与**全生命周期管理**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Fusion Risk Engine                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│  🧬 Genomics    │  🩺 Clinical    │  ⌚ Lifestyle           │
│  基因风险因子   │  体检生化指标    │  IoT 行为数据           │
│  (SNP/PRS)      │  (NHANES)       │  (MobileWell)           │
└─────────────────┴─────────────────┴─────────────────────────┘
                           ↓
              个性化风险评估 + 精准干预建议
```

---

## ✨ 核心功能

### � 多模态风险融合引擎 (Fusion Engine)
- 结合 **LightGBM** 临床模型 + **贝叶斯网络** 基因模型
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
├── backend/                    # 后端服务
│   ├── api/                    # API 路由层
│   │   └── api_v1/endpoints/   # RESTful 端点
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 环境配置
│   │   ├── constants.py        # 业务常量
│   │   └── cache.py            # Redis 缓存管理
│   ├── models/                 # SQLModel 数据模型
│   ├── services/               # 业务逻辑层
│   │   ├── risk_engine.py      # 疾病风险引擎
│   │   ├── gene_risk_engine.py # 基因风险引擎
│   │   ├── fusion_engine.py    # 多模态融合引擎
│   │   ├── chat_service.py     # Dr. AI 问答
│   │   └── nutrition_service.py# 营养规划
│   └── rag/                    # RAG 知识库
│       ├── vector_store/       # ChromaDB 向量库
│       └── guidelines/         # 医学指南文档
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── views/              # 页面组件
│       ├── stores/             # Pinia 状态
│       └── components/         # UI 组件
├── ai_core/                    # AI 模型训练脚本
│   ├── train_risk_models.py    # 风险模型训练
│   └── train_diet_model.py     # 膳食模型训练
├── data_warehouse/             # 数据仓库
│   ├── raw_data/               # 原始数据 (gitignore)
│   └── processed_data/         # ETL 处理后数据
├── run.py                      # 启动入口
├── requirements.txt            # Python 依赖
└── .env.example                # 环境变量模板
```

---

## 🔒 安全与隐私

- ✅ 所有用户数据**本地存储**，不上传第三方服务器
- ✅ API Keys 通过环境变量管理，不硬编码
- ✅ 敏感文件已添加至 `.gitignore`
- ✅ 支持本地 LLM 部署 (Ollama) 实现完全离线运行

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
