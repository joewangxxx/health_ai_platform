import pandas as pd
import xgboost as xgb
import joblib
import os
import sys

# ================= 🔧 路径修正 =================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from backend.config import DATA_WAREHOUSE_DIR, LIFESTYLE_MODEL_PATH

# 配置
DATA_FILE = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "lifestyle_training_data.csv")
MODEL_PATH = LIFESTYLE_MODEL_PATH

def train_lifestyle():
    print("=== ⌚ 训练生活方式风险模型 (XGBoost) ===")
    
    if not os.path.exists(DATA_FILE):
        print("❌ 没找到数据，请先运行 etl_mobilewell.py")
        return

    df = pd.read_csv(DATA_FILE)
    
    # 特征 X: ['sum', 'count'] (即：活跃次数，总次数)
    # 真实场景中，手环传来的就是 steps (类似 sum) 和 佩戴时长
    X = df[['sum', 'count']]
    y = df['Lifestyle_Risk']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
    model.fit(X_train, y_train)
    
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"✅ 模型训练完成！准确率: {acc:.2f}")
    
    joblib.dump(model, MODEL_PATH)
    print(f"💾 保存至: {MODEL_PATH}")

if __name__ == "__main__":
    train_lifestyle()