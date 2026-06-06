# 模型依赖复现与兼容治理（AI-DATA，2026-04-23）

## 1. 目标与边界

- 目标：为 `xgboost`、`torch`、`torchvision`、`scikit-learn`、`joblib` 建立可复现基线和兼容检查流程。
- 边界：本阶段不改变任何 API 路由语义、`risk_report` 语义或模型输入输出契约。

## 2. 仓库内基线产物

- 依赖基线：`ai_core/requirements-ml-baseline.txt`
- 兼容检查脚本：`ai_core/check_model_compatibility.py`

推荐执行：

```powershell
pip install -r ai_core/requirements-ml-baseline.txt
python ai_core/check_model_compatibility.py --strict
```

## 3. 当前发现（基于 2026-04-23 实测）

### 3.1 已确认风险

- `models/risk_assessment_models.pkl` 与 `models/feature_scaler.pkl` 在当前运行环境下触发 `InconsistentVersionWarning`：
  - 工件训练/导出版本为 `scikit-learn 1.6.1`
  - 当前环境为 `scikit-learn 1.8.0`
- 这类告警不应作为长期发布状态，需通过模型重导出消除。

### 3.2 阻塞项（Blocker）

- 当前环境缺失关键包：
  - `xgboost`（未安装）
  - `torch`（未安装）
  - `torchvision`（未安装）
- 因此，无法在本轮完成以下验证：
  - `models/lifestyle_xgb_model.pkl` 的完整加载兼容性
  - `*.pth` 视觉/时序模型的可加载性校验

## 4. 治理策略

### 4.1 版本冻结策略

- 训练与重导出环境必须使用同一份 `ai_core/requirements-ml-baseline.txt`。
- 线上运行环境如采用不同版本，必须先通过 `check_model_compatibility.py --strict`。

### 4.2 工件重导出策略（sklearn/joblib）

- 对所有 `joblib/pkl` 模型，采用目标运行环境重新导出（至少覆盖 `risk_assessment_models.pkl`、`feature_scaler.pkl`）。
- 重导出后运行兼容检查脚本，确认不再出现 `InconsistentVersionWarning`。

### 4.3 PyTorch/XGBoost 工件策略

- 在安装 `xgboost`、`torch`、`torchvision` 后执行兼容脚本，确认模型可加载。
- 若加载失败，必须回到训练脚本重导出并更新模型说明文档中的“版本信息/限制”。

## 5. 发布门禁建议（与当前契约一致）

- 允许：可解释且一次性、已登记的降级告警。
- 不允许：长期存在的 sklearn 版本不一致告警，或关键模型依赖缺失导致的静默不可用。

