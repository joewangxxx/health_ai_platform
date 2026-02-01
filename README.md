# 🏥 Health AI Platform 2.0 (Dr. AI)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js)
![License](https://img.shields.io/badge/License-MIT-green)

**全周期慢病管理 AI 平台** | 集成 OCR 体检单识别 · RAG 智能问答 · 多模态风险预测

[English](#english) | [中文](#中文)

</div>

---

## 📖 项目简介

Health AI Platform 是一个面向慢病管理的智能健康平台，融合多项前沿 AI 技术，为用户提供从体检数据录入、健康风险评估到个性化干预建议的全链路服务。

### 🎯 核心价值

- **降低门槛**：OCR + LLM 自动解析体检单，告别手动录入
- **精准预测**：基于 NHANES 人群数据训练的多疾病风险模型
- **个性化建议**：结合用户画像的 RAG 智能问答系统
- **全周期管理**：健康时光机追踪趋势，预警异常

---

## ✨ 核心功能

### 🩺 临床体检 OCR 智能录入
- 支持 JPG/PNG/PDF 格式体检报告
- Baidu OCR + LLM 结构化解析
- 自动提取 50+ 项生化指标

### 🤖 Dr. AI 健康顾问
- RAG 检索增强生成技术
- 接入 Kimi / Ollama / OpenAI 多模型
- 基于循证医学指南的专业回答
- 结合用户健康档案的个性化建议

### 🍎 AI 营养师
- 基于 NHANES 数据的膳食分析
- 个性化热量目标计算 (TDEE)
- 智能食谱生成 + 米其林级菜品推荐
- 疾病饮食禁忌自动过滤

### 📉 全周期健康时光机
- 可视化健康指标趋势
- 异常指标智能预警
- 多维度风险评分追踪
- CKM 心肾代谢分期评估

### 🧬 基因风险分析 (进阶)
- SNP 位点风险解读
- 药物基因组学推荐
- 多基因风险评分 (PRS)

---

## 🛠️ 技术栈

### Backend
| 技术 | 用途 |
|------|------|
| **FastAPI** | 高性能异步 Web 框架 |
| **Python 3.11+** | 核心开发语言 |
| **SQLModel** | ORM + Pydantic 数据验证 |
| **Redis** | 缓存层 (LLM 响应优化) |

### Frontend
| 技术 | 用途 |
|------|------|
| **Vue 3** | 渐进式前端框架 |
| **Element Plus** | UI 组件库 |
| **ECharts** | 数据可视化 |
| **TailwindCSS** | 原子化 CSS |
| **Pinia** | 状态管理 |

### AI / Data Science
| 技术 | 用途 |
|------|------|
| **XGBoost / LightGBM** | 疾病风险预测模型 |
| **Scikit-learn** | 特征工程 & 模型评估 |
| **ChromaDB** | 向量数据库 (RAG) |
| **LangChain** | LLM 应用框架 |
| **PaddleOCR** | 体检单文字识别 |

---

## 🚀 快速开始

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
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys
```

### 3. 启动后端
```bash
python run.py
# 服务运行于 http://127.0.0.1:8000
# API 文档: http://127.0.0.1:8000/docs
```

### 4. 前端配置
```bash
cd frontend
npm install
```

### 5. 启动前端
```bash
npm run dev
# 访问 http://localhost:5173
```

---

## ⚙️ 环境变量配置

创建 `.env` 文件并配置以下变量：

```env
# LLM API (选择一个)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.moonshot.cn/v1  # Kimi
OPENAI_MODEL=moonshot-v1-8k

# Baidu OCR (可选)
BAIDU_OCR_API_KEY=xxx
BAIDU_OCR_SECRET_KEY=xxx

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=sqlite:///./health_ai.db
```

---

## 📁 项目结构

```
health_ai_platform_2.0/
├── backend/                 # 后端服务
│   ├── api/                 # API 路由
│   ├── core/                # 核心配置
│   ├── models/              # 数据模型
│   ├── services/            # 业务逻辑
│   └── rag/                 # RAG 知识库
├── frontend/                # Vue 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── stores/          # Pinia 状态
│   │   └── components/      # UI 组件
├── ai_core/                 # AI 模型训练
│   ├── train_risk_models.py
│   └── train_diet_model.py
├── data_warehouse/          # 数据仓库
│   ├── raw_data/            # 原始数据 (gitignore)
│   └── processed_data/      # 处理后数据
├── run.py                   # 启动入口
└── requirements.txt         # Python 依赖
```

---

## 📊 数据来源

- **NHANES** (National Health and Nutrition Examination Survey)
- **USDA FoodData Central** (营养成分数据库)
- **中国慢性病指南** (高血压、糖尿病、痛风)

---

## 🔒 安全说明

- 所有用户数据本地存储，不上传第三方服务器
- API Keys 通过环境变量管理，不硬编码
- 敏感文件已添加至 `.gitignore`

---

## 📄 License

MIT License © 2024 Health AI Platform

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<div align="center">

**Built with ❤️ for Better Health**

</div>
