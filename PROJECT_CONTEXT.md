# Project Context: Health AI Platform 2.0

## 1. 项目概况 (Project Overview)
本项目是一个 **多模态数字生命健康管理平台 (Advanced Multimodal Digital Health Platform)**。
它旨在通过融合 **临床体检数据 (Clinical)**、**基因组学数据 (Genomics)**、**行为生活方式数据 (Lifestyle/IoT)** 和 **环境数据**，构建用户的全息数字生命档案，并利用 AI/ML 模型进行疾病风险预测、个性化健康干预和智能问答。

核心理念是 **贝叶斯融合 (Bayesian Fusion)**，即综合多源数据以提高健康预测的准确性。

## 2. 技术栈清单 (Tech Stack)

### 前端 (Frontend)
- **核心框架**: Vue 3 (Composition API) + Vite 6
- **语言**: JavaScript (部分 TypeScript 支持，但在 `src` 中主要为 JS)
- **UI 组件库**: Element Plus + Shadcn Vue (Radix Vue)
- **样式**: Tailwind CSS v4 + PostCSS
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **可视化**: ECharts v6 + Motion
- **请求库**: Axios

### 后端 (Backend)
- **核心框架**: FastAPI (Python 3.10+)
- **ORM / 数据库交互**: SQLModel (结合 SQLAlchemy + Pydantic)
- **数据库**: SQLite (`health_ai_v2.db`)
- **机器学习 / 深度学习**:
    - **PyTorch**: 核心深度学习框架
    - **Scikit-learn / XGBoost / LightGBM**: 传统机器学习与树模型 (用于风险评分)
    - **PaddleOCR**: 医疗单据 OCR 识别
- **AI / LLM**:
    - **LangChain**: RAG (检索增强生成) 框架
    - **ChromaDB**: 向量数据库 (用于知识库检索)
    - **GPT4All / HuggingFace**: 本地 LLM 支持

## 3. 目录结构映射 (Directory Structure)

### Frontend (`/frontend/src`)
- **`views/`**: 页面级组件 (Page Views)。
    - `clinical/`: 临床数据录入与展示。
    - `genomics/`: 基因数据上传与分析。
    - `admin/`: 管理员后台 (数据中心, 训练流水线)。
    - `nutrition/`: AI 营养师模块。
- **`components/`**: 可复用 UI 组件。
    - `ui/`: 基础 UI 组件 (Button, Card, Input)，多采用 Glassmorphism (毛玻璃) 风格。
- **`stores/`**: Pinia 状态管理。
    - `authStore.js`: 用户认证与 Profile 同步。
    - `healthStore.js`: 核心健康数据 (User Profile + Genomic Data)。
    - `nutritionStore.js`: 营养方案生成状态。
- **`layout/`**: 布局组件 (MainLayout 包含侧边栏和顶部导航)。
- **`composables/`**: 公用逻辑 (Hooks)，如 `useToast.js`。
- **`router/`**: 路由定义与权限守卫 (Auth Guard, Admin Guard)。

### Backend (`/backend`)
- **`api/`**: API 路由定义 (Routers)，按模块划分 (auth, clinical, genomic, etc.)。
- **`services/`**: 核心业务逻辑层。负责调用模型、处理数据、执行训练任务。
    - `clinical_service.py`: 风险计算逻辑。
    - `pipeline_service.py`: 数据 ETL 和训练流水线。
- **`models.py`**: 数据库模型定义 (SQLModel)。
- **`rag/`**: AI 问答与知识库模块 (Vector Store, Retrieval)。
- **`core/`**: 核心配置与工具 (Config, Security)。

## 4. 核心业务逻辑 (Core Business Logic)

根据数据库 Schema 和 API 推断，系统包含以下核心模块：

1.  **用户与档案管理 (User Profile)**
    - 用户注册/登录 (JWT Auth)。
    - **UserProfile**: 存储极其详细的身体指标 (BMI, 血压, 血脂, 血糖, 肝肾功能, 血常规)。
    - 既然包含 `WBC`, `Platelet`, `GGT` 等指标，说明系统具备深度的临床分析能力。

2.  **多模态风险预测 (Risk Prediction)**
    - 系统基于 **NHANES** (美国国家健康营养调查) 数据训练模型。
    - 预测高风险疾病 (如糖尿病 T2D, 心血管疾病 CVD)。
    - 支持 **"平行宇宙模拟" (Simulation)**: 推演用户在不同生活方式干预下 (如减重 5kg) 未来 5-10 年的健康风险变化。

3.  **基因组学分析 (Genomics / GWAS)**
    - 处理 GWAS (全基因组关联分析) 数据。
    - 计算 **PRS (多基因风险评分)**，将基因风险与临床风险进行贝叶斯融合。
    - 后台支持上传 GWAS Catalog 原始数据进行 ETL 清洗。

4.  **智能药房与营养 (Pharmacy & Nutrition)**
    - **PharmGKB**: 基于基因的药物反应预测 (如华法林剂量)。
    - **AI Nutrition**: 根据用户的健康状况与疾病标签，自动生成个性化食谱。

5.  **视觉与 IoT (Vision & IoT)**
    - **Food Vision**: 使用 YOLOv8 识别食物照片并估算热量。
    - **IoT Monitoring**: 实时同步智能穿戴设备数据 (心率, 步数)。

6.  **RAG 智能问答 (Dr. AI)**
    - 基于本地医疗知识库 (PDF/Text) 的问答系统，允许用户上传体检报告进行解读。

## 5. 开发规范 (Development Standards)

1.  **Vue 风格**:
    - 统一使用 `<script setup>` 语法糖。
    - 必须使用 **Composition API**。
    - 样式优先使用 **Tailwind CSS**，复杂特效组件 (如玻璃卡片) 使用 scoped CSS 或专门的 UI 组件。

2.  **交互反馈**:
    - **禁止使用 `alert` 或 `ElMessage`**。
    - **必须使用全局封装的 `useToast`** (`showToast`) 进行所有用户通知，位置统一为 `top-center`。
    - UI 设计追求 **Premium Glassmorphism** (磨砂玻璃/极光背景)，保持视觉高端感。

3.  **语言规范**:
    - 所有 UI 文本、注释、Log 输出 **必须使用中文** (API 字段名除外)。
    - 代码变量名使用英文 (camelCase 仅前端, snake_case 仅后端)。

4.  **后端架构**:
    - **Service Layer Pattern**: API 层 (`routers`) 只负责请求解析，所有复杂逻辑必须下沉到 `services/` 目录。
    - **Async First**: 全面使用 `async/await` 处理 I/O 操作。

5.  **数据流**:
    - 前端通过 Axios 调用后端 -> 后端返回 JSON -> 前端 Pinia 更新 Store -> 组件响应式更新。
    - 耗时任务 (如训练模型) 采用 **异步任务 + 轮询 (Polling)** 机制，前端通过 `DataCenterView` 实时展示 Terminal Logs。
