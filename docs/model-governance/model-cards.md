# 主要模型资产说明（AI-DATA，2026-04-23）

> 本文档用于模型治理与合规说明，不变更 API 契约，不改变模型 I/O 语义。

## 1) LightGBM 临床风险模型（Risk Engine）

- 资产路径：`models/risk_assessment_models.pkl`
- 训练脚本：`ai_core/train_risk_models.py`
- 服务入口：`backend/services/risk_engine.py`
- 任务：多疾病风险概率估计（例如 T2D、CKD 等），并输出风险等级与解释字段。
- 训练数据：`data_warehouse/processed_data/clinical_clean/nhanes_integrated_data_v2.csv`，并合并 NHANES 相关 XPT 特征。
- 输入：用户结构化临床指标（如 BMI、血压、血脂、血糖、肾功能等）。
- 输出：疾病维度风险结果（概率/等级/解释字段）；供融合引擎与综合分析使用。
- 适用范围：健康风险分层与趋势提示。
- 不适用范围：诊断结论、处方建议、紧急医疗决策。
- 已知限制/风险：
  - 当前工件存在 sklearn 版本兼容告警（见依赖治理文档）。
  - 结果为风险评估，不是医学诊断结论。

## 2) XGBoost 生活方式风险模型（Lifestyle Modifier）

- 资产路径：`models/lifestyle_xgb_model.pkl`
- 训练脚本：`ai_core/train_lifestyle_model.py`
- 服务入口：`backend/services/lifestyle_service.py`
- 任务：根据活动相关特征计算生活方式修正系数（modifier）。
- 训练数据：`data_warehouse/processed_data/lifestyle_training_data.csv`
- 输入：训练时为 `sum`/`count` 特征；在线由 IoT 步数等粗粒度行为数据映射得到。
- 输出：`lifestyle_modifier`（用于融合阶段的乘法修正）。
- 适用范围：行为风险的相对修正。
- 不适用范围：单独作为疾病风险最终结论。
- 已知限制/风险：
  - 当前环境缺失 `xgboost` 时会降级，不应静默当作正常模型可用态。
  - 特征维度较粗，受设备采样质量影响明显。

## 3) EfficientNet / ResNet 营养视觉模型

### 3.1 EfficientNet（营养多目标回归）

- 资产路径：`models/nutrition_efficientnet.pth`
- 训练脚本：`ai_core/train_nutri_net.py`
- 服务入口：`backend/services/food_service.py`
- 任务：从食物图像回归估计 `calories/carbs/protein/fat`。
- 数据：`data_warehouse/processed_data/food_nutrition_labels.csv`
- 输入：食物图片（RGB，预处理到 224x224）。
- 输出：四项营养值估计。

### 3.2 ResNet（历史/备用视觉模型）

- 资产路径：`models/food_resnet_model.pth`
- 训练脚本：`ai_core/train_food_cv.py`
- 任务：历史版本中用于食物图像回归（以碳水估计为主）。

共同限制：

- 当前环境缺失 `torch/torchvision` 时无法完成完整可加载性验证。
- 视觉模型输出为估计值，受图像质量、菜品遮挡、份量尺度影响。
- 不能替代营养师或临床营养评估。

## 4) LSTM 血糖预测模型

- 资产路径：`models/glucose_lstm_model.pth`、`models/feature_scaler.pkl`
- 服务入口：`backend/services/inference_service.py`
- 任务：基于时序特征推断血糖变化趋势（场景预测）。
- 输入：由当前血糖、摄入、心率、PRS 等派生的序列特征。
- 输出：预测血糖值与压力状态标记（`stress_is_high`）。
- 适用范围：健康管理辅助提示。
- 不适用范围：临床诊断、用药调整决策。
- 已知限制/风险：
  - 依赖 `torch` 运行时；缺失时应显式降级。
  - scaler 工件同样受 sklearn 版本兼容约束。

## 5) GWAS / PRS 基因风险评分

- 数据资产：`data_warehouse/processed_data/knowledge_base/GWAS_*_weights.csv`
- 服务入口：`backend/services/gene_service.py`
- 任务：基于 SNP 基因型与 GWAS 权重计算疾病相关 PRS 风险分数。
- 输入：用户基因型（如 23andMe 文本解析后的 rsid -> genotype）。
- 输出：疾病维度分数（0-100 标准化区间）。
- 适用范围：遗传易感风险分层。
- 不适用范围：单基因病诊断、个体化治疗建议。
- 已知限制/风险：
  - 受人群偏差、样本代表性和 GWAS 来源质量影响。
  - PRS 仅描述统计相关风险，不等于发病必然性。

## 6) RAG / LLM / OCR 边界模型说明

- OCR：`backend/services/ocr_service.py`（Baidu OCR + 结构化解析）
- LLM：后端中转调用（Moonshot/Kimi 兼容接口），不允许前端直连提供商。
- RAG：`backend/services/rag_service.py`（检索与证据构建在后端内部完成）。

边界约束（治理要求）：

- 仅输出契约允许的结构化结果与证据元数据，不暴露原始 OCR/LLM/RAG provider payload。
- 用户健康数据、报告文本、审计数据遵循最小化原则，不应在日志中落地原始敏感内容。
- 本平台输出为健康管理建议，不承诺替代临床诊断与治疗。

## 7) 融合语义声明（重要）

- 当前综合风险融合采用：`base × gene_modifier × lifestyle_modifier`。
- 该语义是**启发式乘法缩放**，不是严格贝叶斯后验推断。
- 若要变更 `risk_report` 对外可见语义，必须先发起 architecture change request。

