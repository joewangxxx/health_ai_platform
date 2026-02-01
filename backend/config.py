import os

# ================= 🚀 Project Root Resolution =================
# Getting the directory of this file (backend/)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Going up one level to get the project root (f:/health_ai_platform_2.0)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# ================= 📂 Directory Paths =================
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DATA_WAREHOUSE_DIR = os.path.join(PROJECT_ROOT, "data_warehouse")
AI_CORE_DIR = os.path.join(PROJECT_ROOT, "ai_core")

# ================= 🧠 Model Paths =================
# Disease Risk Assessment (LightGBM)
RISK_MODEL_PATH = os.path.join(MODELS_DIR, "risk_assessment_models.pkl")

# Lifestyle Risk (XGBoost)
LIFESTYLE_MODEL_PATH = os.path.join(MODELS_DIR, "lifestyle_xgb_model.pkl")

# Food Vision (ResNet-18)
FOOD_MODEL_PATH = os.path.join(MODELS_DIR, "food_resnet_model.pth")

# Glucose Prediction (LSTM & Scaler)
GLUCOSE_MODEL_PATH = os.path.join(MODELS_DIR, "glucose_lstm_model.pth")
FEATURE_SCALER_PATH = os.path.join(MODELS_DIR, "feature_scaler.pkl")

# Gene Knowledge Base
GENE_KB_DIR = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "knowledge_base")

# ================= 🌍 Global Constants =================
# Default device state for IoT simulation
DEFAULT_DEVICE_STATE = {"hr": 70, "steps": 0, "glucose": 100.0}
