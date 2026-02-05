"""
[V2 LEGACY COMPONENT]
This module is retained for backward compatibility with V3 routes.
Do not delete until a V3 replacement is fully implemented.
"""
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import joblib
import os

import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import joblib
import os
from backend.config import GLUCOSE_MODEL_PATH, FEATURE_SCALER_PATH
from backend.core.constants import THRESHOLD_HEART_STRESS

# 指向 models 文件夹
MODEL_PATH = GLUCOSE_MODEL_PATH
SCALER_PATH = FEATURE_SCALER_PATH

# ================= 模型参数 =================
# 必须与训练时保持一致 (10个生理特征 + 1个心理特征 = 11)
INPUT_SIZE = 11 
HIDDEN_SIZE = 64
NUM_LAYERS = 2

# 定义模型结构
class GlucoseLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size=1):
        super(GlucoseLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = out[:, -1, :]
        out = self.fc(out)
        return out

class Predictor:
    def __init__(self):
        # Lazy Loading: 只定义变量，不加载模型
        self.device = torch.device("cpu")
        self.scaler = None
        self.model = None
        self._loaded = False

    async def load_models(self):
        """异步加载 LSTM 模型 (在 FastAPI lifespan 中调用)"""
        if self._loaded:
            return
        print(f"🔍 正在加载 LSTM 模型...\n   路径: {MODEL_PATH}")
        
        try:
            if not os.path.exists(SCALER_PATH) or not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"找不到模型文件！请检查 F:/health_ai_platform_2.0/models/ 下是否有 .pth 和 .pkl 文件")

            # 1. 加载归一化器
            self.scaler = joblib.load(SCALER_PATH)
            
            # 2. 加载模型
            self.model = GlucoseLSTM(INPUT_SIZE, HIDDEN_SIZE, NUM_LAYERS)
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            print("✅ LSTM 血糖预测模型加载成功！")
            
        except Exception as e:
            print(f"❌ LSTM 模型加载失败: {e}")
            # 这里不抛出异常，允许主程序继续运行，但预测功能将不可用
        
        self._loaded = True

    def predict_scenario(self, current_glucose, carbs, hr, prs_score):
        """
        返回字典：{'glucose': float, 'stress_is_high': bool}
        """
        # 🔥 安全检查：如果模型没加载成功，直接返回默认值，防止崩坏
        if self.scaler is None or self.model is None:
            print("⚠️ 预测中止：模型未正确加载")
            return {"glucose": current_glucose, "stress_is_high": False}

        try:
            # 1. 准备前10个特征进行归一化
            # 这里的 Key 必须和 feature_scaler.pkl 训练时的列名完全一致
            features_to_scale = {
                'Glucose': current_glucose,
                'HR': hr,
                'Carbs': carbs,
                'Protein': carbs * 0.15, # 简单估算
                'Fat': carbs * 0.1,     
                'Calories': carbs * 4,  
                'BMI': 24.0,            # 默认值
                'HbA1c': 5.5,           
                'Age': 30,              
                'PRS_Score': prs_score  
            }
            
            df_scale = pd.DataFrame([features_to_scale])
            scaled_part = self.scaler.transform(df_scale) 
            
            # 2. 准备第11个特征 (Stress)
            stress_val = 1 if hr > THRESHOLD_HEART_STRESS else 0 
            stress_part = np.array([[stress_val]])
            
            # 3. 拼接
            final_input_vector = np.hstack((scaled_part, stress_part))
            
            # 4. 构造序列 (模拟过去12个时间步)
            seq_input = np.tile(final_input_vector, (12, 1))
            tensor_input = torch.FloatTensor(seq_input).unsqueeze(0).to(self.device)
            
            # 5. 预测
            with torch.no_grad():
                pred_scaled = self.model(tensor_input).item()
                
            # 6. 反归一化
            # 构造一个 1x10 的全0矩阵，只填入 Glucose 位置
            # 注意：feature_scaler 只管 10 个特征，Glucose 通常是第 0 列（取决于训练时的列顺序）
            # 为了保险，我们需要知道 Glucose 在 scaler 中的位置。通常是第一个。
            
            dummy = np.zeros((1, 10))
            dummy[0, 0] = pred_scaled 
            
            real_pred = self.scaler.inverse_transform(dummy)[0, 0]
            
            return {
                "glucose": round(real_pred, 2),
                "stress_is_high": bool(stress_val)
            }
        except Exception as e:
            print(f"❌ 预测计算过程出错: {e}")
            return {"glucose": current_glucose, "stress_is_high": False}

if __name__ == "__main__":
    p = Predictor()
    # 测试一下
    print(p.predict_scenario(100, 50, 75, 0.9))