"""
[V2 LEGACY COMPONENT]
This module is retained for backward compatibility with V3 routes.
Do not delete until a V3 replacement is fully implemented.
"""
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import io
import os
import traceback
from pathlib import Path

# ================= 🔧 1. 动态路径计算 (最稳健的方式) =================
# 获取当前文件所在位置: .../backend/services/food_service.py
CURRENT_DIR = Path(__file__).resolve().parent
# 回退两层找到 F:\health_ai_platform_2.0
PROJECT_ROOT = CURRENT_DIR.parent.parent
# 拼接模型路径
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "nutrition_efficientnet.pth")

class FoodPredictor:
    def __init__(self):
        self.device = torch.device("cpu") # 视觉推理用 CPU 足够快且稳定
        self.model = None
        print("\n📸 初始化全能营养视觉引擎 (EfficientNet-B0)...")
        print(f"   📂 目标模型路径: {MODEL_PATH}")
        
        # 1. 检查文件是否存在
        if not os.path.exists(MODEL_PATH):
            print(f"   ❌ 错误：模型文件未找到！请确认文件位于: {MODEL_PATH}")
            return
        
        try:
            # 2. 重建模型结构 (必须与训练时完全一致)
            # 使用新版 weights=None, 因为我们会从 .pth 文件加载自训练权重
            self.model = models.efficientnet_b0(weights=None)
            
            # 修改输出层为 4 维 (Cal, Carb, Prot, Fat)
            in_features = self.model.classifier[1].in_features
            self.model.classifier[1] = nn.Linear(in_features, 4)
            
            # 3. 加载权重
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            
            # 4. 预处理管线
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
            
            print("   ✅ 视觉引擎加载成功！(Ready)")
            
        except Exception as e:
            print(f"   ❌ 模型加载崩溃: {e}")
            traceback.print_exc()
            self.model = None

    def predict(self, image_bytes):
        """
        接收图片字节流 -> 返回详细营养字典
        即使出错，也返回全0数据，防止接口报错
        """
        # 默认安全返回值
        safe_result = {
            "calories": 0.0,
            "carbs": 0.0,
            "protein": 0.0,
            "fat": 0.0,
            "status": "fail"
        }

        if self.model is None:
            print("⚠️ 警告：视觉模型未初始化，返回空结果")
            return safe_result
            
        try:
            # 1. 图片预处理
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # 2. 推理
            with torch.no_grad():
                output = self.model(img_tensor)
                # output shape: [1, 4] -> [[cal, carb, prot, fat]]
                vals = output[0].tolist()
                
            # 3. 后处理 (ReLU: 去除负数)
            vals = [max(0.0, round(v, 1)) for v in vals]
            
            return {
                "calories": vals[0],
                "carbs": vals[1],
                "protein": vals[2],
                "fat": vals[3],
                "status": "success"
            }
            
        except Exception as e:
            print(f"❌ 图像推理过程出错: {e}")
            traceback.print_exc()
            return safe_result

# 简单测试
if __name__ == "__main__":
    predictor = FoodPredictor()