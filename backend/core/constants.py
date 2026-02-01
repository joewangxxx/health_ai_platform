"""
Business Constants and Thresholds

This module centralizes all magic numbers and thresholds used across the backend services.
Modifying values here will affect all dependent services.
"""

# ================= 临床阈值 (Clinical Thresholds) =================
# 肾功能
THRESHOLD_KIDNEY_EGFR_LOW = 60          # eGFR < 60 indicates kidney impairment

# 肝功能  
THRESHOLD_LIVER_ALT_HIGH = 40           # ALT > 40 indicates liver abnormality

# 心率
THRESHOLD_HEART_BRADYCARDIA = 60        # HR < 60 indicates bradycardia
THRESHOLD_HEART_STRESS = 85             # HR > 85 indicates stress/elevated state

# 运动量
THRESHOLD_ACTIVITY_HIGH_STEPS = 15000   # Steps > 15000 indicates high activity

# 密码
MIN_PASSWORD_LENGTH = 6                 # Minimum password length for registration


# ================= 风险等级阈值 (Risk Level Thresholds) =================
# risk_engine.py 使用的概率阈值 (0-1)
RISK_PROB_VERY_HIGH = 0.7               # probability > 0.7 -> Very High
RISK_PROB_HIGH = 0.5                    # probability > 0.5 -> High
RISK_PROB_MEDIUM = 0.3                  # probability > 0.3 -> Medium

# fusion_service.py 使用的百分比阈值 (0-100)
FUSION_RISK_VERY_HIGH = 70              # final_prob > 70 -> Very High
FUSION_RISK_HIGH = 40                   # final_prob > 40 -> High
FUSION_RISK_MEDIUM = 20                 # final_prob > 20 -> Medium

# 基因系数阈值
GENE_MODIFIER_POTENTIAL_RISK = 1.2      # gene_mod >= 1.2 triggers potential risk flag


# ================= 模型参数 (Model Parameters) =================
# lifestyle_service.py 步数归一化
LIFESTYLE_STEPS_NORMALIZE_BASE = 10000  # 10000 steps = 100% activity level
LIFESTYLE_COUNT_BASE = 1000             # Normalization constant

# 基因系数公式参数: modifier = BASE + (score/100) * RANGE
GENE_MODIFIER_BASE = 0.8                # Minimum modifier (protective)
GENE_MODIFIER_RANGE = 0.7               # Range: 0.8 to 1.5

# 生活方式系数公式参数: modifier = BASE + (prob * RANGE)
LIFESTYLE_MODIFIER_BASE = 0.8           # Minimum modifier
LIFESTYLE_MODIFIER_RANGE = 0.5          # Range: 0.8 to 1.3


# ================= 默认值 (Default Values) =================
DEFAULT_AGE_FALLBACK = 45               # Default age when not provided
DEFAULT_HEART_RATE = 70                 # Default HR for calculations


# ================= 🌐 Task 92: NHANES 语义化映射 =================
# 代码语义名 -> 中文业务名 (用于 AI 报告和前端展示)
FIELD_CHINESE_NAMES = {
    # --- 人口学 ---
    "Gender": "性别",
    "Age": "年龄 (岁)",
    "BMI": "体重指数",
    "Weight": "体重 (kg)",
    "Height": "身高 (cm)",
    "WaistCircum": "腰围 (cm)",
    
    # --- 膳食 ---
    "Diet_Energy": "日均热量摄入 (kcal)",
    "Diet_Protein": "蛋白质摄入 (g)",
    "Diet_Carbs": "碳水化合物 (g)",
    "Diet_Sugar": "糖分摄入 (g)",
    "Diet_Fiber": "膳食纤维 (g)",
    "Diet_Sodium": "钠摄入 (mg)",
    "Diet_Fat": "脂肪摄入 (g)",
    "Diet_SatFat": "饱和脂肪 (g)",
    "Diet_Cholesterol": "膳食胆固醇 (mg)",
    "Diet_Caffeine": "咖啡因 (mg)",
    "Diet_Alcohol": "酒精摄入 (g)",
    
    # --- 实验室/临床 ---
    "Lab_VitD": "维生素D",
    "Lab_Folate_RBC": "红细胞叶酸",
    "Lab_VitB12": "维生素B12",
    "Lab_HbA1c": "糖化血红蛋白",
    "Lab_Glucose": "空腹血糖",
    "Glucose_Fasting": "空腹血糖 (mmol/L)",
    "HbA1c": "糖化血红蛋白 (%)",
    "Cholesterol_Total": "总胆固醇 (mmol/L)",
    "Cholesterol_HDL": "高密度脂蛋白 (mmol/L)",
    "Cholesterol_LDL": "低密度脂蛋白 (mmol/L)",
    "Triglycerides": "甘油三酯 (mmol/L)",
    "ALT": "谷丙转氨酶 (U/L)",
    "AST": "谷草转氨酶 (U/L)",
    "GGT": "谷氨酰转肽酶 (U/L)",
    "ALP": "碱性磷酸酶 (U/L)",
    "eGFR": "肾小球滤过率",
    "Creatinine": "肌酐 (μmol/L)",
    "WBC": "白细胞 (10^9/L)",
    "Platelet": "血小板 (10^9/L)",
    "HGB": "血红蛋白 (g/L)",
    
    # --- 血压 ---
    "SBP": "收缩压 (mmHg)",
    "DBP": "舒张压 (mmHg)",
    
    # --- Task 98: 泌尿系统 ---
    "Urine_Peak_Flow": "最大尿流率 (mL/s)",
    "Urine_Vol": "单次排尿量 (mL)",
    "Urine_Time": "排尿耗时 (s)",
    "Urine_Albumin": "尿微量白蛋白 (mg/L)",
    "Urine_Creatinine": "尿肌酐 (mg/dL)",
    "UACR": "尿白蛋白肌酐比 (mg/g)",
}

# 疾病中英对照 (用于风险报告)
DISEASE_CHINESE_NAMES = {
    "T2D": "2型糖尿病",
    "PreDiabetes": "糖尿病前期",
    "Hypertension": "高血压",
    "CVD": "心血管疾病",
    "Obesity": "肥胖症",
    "MetabolicSyndrome": "代谢综合征",
    "CKD": "慢性肾病",
    "FattyLiver": "脂肪肝",
    "Gout": "痛风",
    "Anemia": "贫血",
    "Osteoporosis": "骨质疏松",
    "Depression": "抑郁倾向",
    # Task 99: 糖尿病泌尿并发症
    "DKD": "糖尿病肾病",
    "DCP": "糖尿病膀胱病变",
}

def get_field_chinese_name(field_name: str) -> str:
    """获取字段的中文名称，未找到则返回原名"""
    return FIELD_CHINESE_NAMES.get(field_name, field_name)

def get_disease_chinese_name(disease_name: str) -> str:
    """获取疾病的中文名称，未找到则返回原名"""
    return DISEASE_CHINESE_NAMES.get(disease_name, disease_name)


# ================= ⚙️ Task 103: NHANES 变量全量映射 =================
# SAS 原始代码 -> 英文业务名 (用于 ETL 和模型训练)
NHANES_MAPPING = {
    # --- 人口学 (DEMO) ---
    "RIAGENDR": "Gender",
    "RIDAGEYR": "Age",
    
    # --- 体测 (BMX) ---
    "BMXBMI": "BMI",
    "BMXWT": "Weight",
    "BMXHT": "Height",
    "BMXWAIST": "WaistCircum",
    
    # --- 血压 (BPX) ---
    "BPXOSY1": "SBP",
    "BPXODI1": "DBP",
    
    # --- 血糖 (GLU / GHB / INS) ---
    "LBXGLU": "Glucose_Fasting",
    "LBXGH": "HbA1c",
    "LBXIN": "Insulin",
    
    # --- 血脂 (TCHOL / HDL / TRIGLY) ---
    "LBXTC": "Cholesterol_Total",
    "LBDHDD": "Cholesterol_HDL",
    "LBXTR": "Triglycerides",
    
    # --- 肝肾功能 (BIOPRO) ---
    "LBXSCR": "Creatinine",
    "LBXSUA": "Uric_Acid",
    "LBXSATSI": "ALT",
    "LBXSASSI": "AST",
    "LBXALP": "ALP",
    "LBXSGTSI": "GGT",
    
    # --- 血常规 (CBC) ---
    "LBXHGB": "Hemoglobin",
    "LBXWBCSI": "WBC",
    "LBXPLTSI": "Platelet",
    "LBXMCVSI": "MCV",
    "LBXLYPCT": "Lymph_Percent",
    
    # --- 炎症/微量元素 (HSCRP / FERTIN) ---
    "LBXHSCRP": "HS_CRP",
    "LBXFER": "Ferritin",
    
    # --- 膳食数据 Day1 (P_DR1TOT) ---
    "DR1TKCAL": "Diet_Energy_Kcal",
    "DR1TPROT": "Diet_Protein_g",
    "DR1TCARB": "Diet_Carbs_g",
    "DR1TSUGR": "Diet_Sugar_g",
    "DR1TFIBE": "Diet_Fiber_g",
    "DR1TCHOL": "Diet_Cholesterol_mg",
    "DR1TSODI": "Diet_Sodium_mg",
    "DR1TFAT": "Diet_Fat_g",
    "DR1TSFAT": "Diet_SatFat_g",
    "DR1TCAFF": "Diet_Caffeine_mg",
    "DR1TALCO": "Diet_Alcohol_g",
    
    # --- 膳食数据 Day2 (P_DR2TOT) ---
    "DR2TKCAL": "Diet_Energy_Kcal_D2",
    "DR2TPROT": "Diet_Protein_g_D2",
    "DR2TCARB": "Diet_Carbs_g_D2",
    
    # --- 实验室微量元素 (P_VID / P_FOLATE / P_VITAEC) ---
    "LBXVIDMS": "Lab_VitaminD",
    "LBXVIC": "Lab_VitaminC",
    "LBXRBF": "Lab_Folate_RBC",
    "LBXATC": "Lab_VitaminE",
    "LBXB12": "Lab_VitaminB12",
    
    # --- 尿流率 (P_UCFLOW) ---
    "URXPMAX": "Urine_Flow_Max",
    "URXVOL": "Urine_Vol_Voided",
    "URXTIME": "Urine_Time_Voiding",
    
    # --- 尿白蛋白 (P_ALB_CR) ---
    "URXUMA": "Urine_Albumin",
    "URXUCR": "Urine_Creatinine",
    
    # --- 补充剂 (P_DSQTOT) ---
    "DSDCOUNT": "Supp_Count",
    
    # --- 问卷/检查 ---
    "SLD012": "Sleep_Hours",
    "KIQ026": "Kidney_Stones",
    "MCQ160A": "Arthritis",
    "MCQ160B": "Heart_Failure",
    "MCQ160C": "Coronary_Heart",
    "MCQ160E": "Heart_Attack",
    "MCQ160F": "Stroke",
    "MCQ010": "Asthma",
    "MCQ160O": "COPD",
    "DEQ034C": "Psoriasis",
    "DXXOFBMD": "Bone_Density",
    "OHQ845": "Gum_Disease",
    "OHDDESTS": "Dentition_Status",
    "SMQ020": "Smoked_100_Cigs",
    "ALQ130": "Alcohol_Days",
    "HUQ010": "General_Health",
    "BPQ020": "BP_Meds",
    "BPQ080": "Cholesterol_Meds",
}

def get_nhanes_mapping() -> dict:
    """获取 NHANES 变量映射副本"""
    return NHANES_MAPPING.copy()
