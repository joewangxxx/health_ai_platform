import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import os
import re
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

# ================= ⚙️ Task 105: 使用统一配置路径 =================
from backend.config import PROJECT_ROOT, DATA_WAREHOUSE_DIR, MODELS_DIR

# 数据路径 (Task 105: 直接读取 ETL 清洗后的 CSV，无需再读 .xpt)
DATA_FILE = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "clinical_clean", "nhanes_integrated_data_v2.csv")
# NHANES 原始营养数据目录（用于补充加载 DR1/DR2/VID/FOLATE）
RAW_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "NHANES")

# 模型输出路径
os.makedirs(MODELS_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODELS_DIR, "risk_assessment_models.pkl")
IMPORTANCE_PLOT_PATH = os.path.join(MODELS_DIR, "feature_importance_top30.png")

# ================= 🍎 Task 91: 营养数据配置 =================
NUTRITION_FILES = {
    "DIET_DAY1": "P_DR1TOT.xpt",   # 膳食总摄入 Day1
    "DIET_DAY2": "P_DR2TOT.xpt",   # 膳食总摄入 Day2
    "VITD": "P_VID.xpt",           # 维生素D
    "FOLATE": "P_FOLATE.xpt",      # 叶酸
}

# 🍎 从膳食表提取的关键特征 (来自 P_DR1TOT / P_DR2TOT)
DIET_FEATURES = [
    "DR1TKCAL",   # 能量 kcal
    "DR1TPROT",   # 蛋白质 g
    "DR1TCARB",   # 碳水化合物 g
    "DR1TSUGR",   # 总糖 g
    "DR1TFIBE",   # 膳食纤维 g
    "DR1TSODI",   # 钠 mg
    "DR1TFAT",    # 总脂肪 g
    "DR1TSFAT",   # 饱和脂肪 g
    "DR1TCHOL",   # 胆固醇 mg
    "DR1TCAFF",   # 咖啡因 mg
    "DR1TALCO",   # 酒精 g
]

# 🧪 从实验室表提取的微量元素
MICRONUTRIENT_FEATURES = [
    "LBXVIDMS",   # 血清25-羟基维生素D (nmol/L)
    "LBXRBCF",    # 红细胞叶酸 (ng/mL)
    "LBXB12",     # 血清维生素B12 (pg/mL)
]

# ================= 🌐 Task 92: 语义化映射字典 =================
# 第一层：SAS 原始代码 -> 代码语义名 (用于 DataFrame 列名，保持英文)
SAS_TO_ENGLISH = {
    # --- 人口学 ---
    "RIAGENDR": "Gender",
    "RIDAGEYR": "Age",
    "BMXBMI":   "BMI",
    "BMXWT":    "Weight",
    "BMXHT":    "Height",
    "BMXWAIST": "WaistCircum",
    
    # --- 膳食 (P_DR1TOT) ---
    "DR1TKCAL": "Diet_Energy",
    "DR1TPROT": "Diet_Protein",
    "DR1TCARB": "Diet_Carbs",
    "DR1TSUGR": "Diet_Sugar",
    "DR1TFIBE": "Diet_Fiber",
    "DR1TSODI": "Diet_Sodium",
    "DR1TFAT":  "Diet_Fat",
    "DR1TSFAT": "Diet_SatFat",
    "DR1TCHOL": "Diet_Cholesterol",
    "DR1TCAFF": "Diet_Caffeine",
    "DR1TALCO": "Diet_Alcohol",
    
    # --- 实验室 (血液/生化) ---
    "LBXVIDMS": "Lab_VitD",
    "LBXRBCF":  "Lab_Folate_RBC",
    "LBXB12":   "Lab_VitB12",
    "LBXGH":    "Lab_HbA1c",
    "LBXGLU":   "Lab_Glucose",
    "LBXTC":    "Lab_Cholesterol_Total",
    "LBXTR":    "Lab_Triglycerides",
    "LBDHDD":   "Lab_HDL",
    "LBDLDL":   "Lab_LDL",
    "LBXSUA":   "Lab_UricAcid",
    "LBXSCR":   "Lab_Creatinine",
    "LBXSATSI": "Lab_ALT",
    "LBXSASSI": "Lab_AST",
    "LBXWBCSI": "Lab_WBC",
    "LBXHGB":   "Lab_Hemoglobin",
    "LBXPLTSI": "Lab_Platelet",
    
    # --- 血压 ---
    "BPXSY1":   "SBP",
    "BPXDI1":   "DBP",
    
    # --- Task 98: 尿流率 (P_UCFLOW) ---
    "URXPMAX":  "Urine_Peak_Flow",    # 最大尿流率 (mL/s)
    "URXVOL":   "Urine_Vol",          # 排尿量 (mL)
    "URXTIME":  "Urine_Time",         # 排尿时间 (s)
    
    # --- 尿液检查 (P_ALB_CR) ---
    "URXUMA":   "Urine_Albumin",      # 尿微量白蛋白 (mg/L)
    "URXUCR":   "Urine_Creatinine",   # 尿肌酐 (mg/dL)
    "URDACT":   "UACR",               # 尿白蛋白肌酐比 (mg/g)
}

# 第二层：代码语义名 -> 中文业务名 (用于 AI 报告和前端展示)
ENGLISH_TO_CHINESE = {
    # --- 人口学 ---
    "Gender": "性别",
    "Age": "年龄 (岁)",
    "BMI": "体重指数 (BMI)",
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
    
    # --- 实验室 ---
    "Lab_VitD": "维生素D (nmol/L)",
    "Lab_Folate_RBC": "红细胞叶酸 (ng/mL)",
    "Lab_VitB12": "维生素B12 (pg/mL)",
    "Lab_HbA1c": "糖化血红蛋白 (%)",
    "Lab_Glucose": "空腹血糖 (mmol/L)",
    "Lab_Cholesterol_Total": "总胆固醇 (mmol/L)",
    "Lab_Triglycerides": "甘油三酯 (mmol/L)",
    "Lab_HDL": "高密度脂蛋白 (mmol/L)",
    "Lab_LDL": "低密度脂蛋白 (mmol/L)",
    "Lab_UricAcid": "尿酸 (μmol/L)",
    "Lab_Creatinine": "肌酐 (μmol/L)",
    "Lab_ALT": "谷丙转氨酶 (U/L)",
    "Lab_AST": "谷草转氨酶 (U/L)",
    "Lab_WBC": "白细胞计数 (10^9/L)",
    "Lab_Hemoglobin": "血红蛋白 (g/L)",
    "Lab_Platelet": "血小板 (10^9/L)",
    
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

# 辅助函数：获取中文名称
def get_chinese_name(col_name: str) -> str:
    """
    将列名转换为中文显示名称。
    优先查找 ENGLISH_TO_CHINESE，若无则返回原名。
    """
    # 如果是 SAS 代码，先转为英文语义名
    english_name = SAS_TO_ENGLISH.get(col_name, col_name)
    # 再转为中文
    return ENGLISH_TO_CHINESE.get(english_name, english_name)


LEAKAGE_MAPPING = {
    # --- 代谢 ---
    "T2D": ["HbA1c", "Glucose_Fasting", "Insulin", "HOMA_IR", "Target_PreDiabetes"],
    "PreDiabetes": ["HbA1c", "Glucose_Fasting", "Target_T2D"],
    "InsulinResist": ["Insulin", "HOMA_IR", "Glucose_Fasting", "HbA1c"],
    "Obesity": ["BMI", "WaistCircum", "Target_AbdominalObesity", "Weight", "Height"],
    "AbdominalObesity": ["WaistCircum", "BMI", "Target_Obesity", "Weight", "Height"],
    "MetabolicSyndrome": ["WaistCircum", "Triglycerides", "Cholesterol_HDL", "SBP", "DBP", "Glucose_Fasting"],
    "Gout": ["Uric_Acid", "Target_Hyperuricemia"],
    "Hyperuricemia": ["Uric_Acid", "Target_Gout"],
    
    # 🔥 [新增] 脂肪肝 (必须剔除 CAP 指数)
    "FattyLiver": ["Liver_Fat_CAP", "ALT", "AST"], 
    
    # --- 心血管 ---
    "Hypertension": ["SBP", "DBP", "Target_HighPulsePressure"],
    "HighPulsePressure": ["SBP", "DBP", "Target_Hypertension"],
    "HighLipid": ["Cholesterol_Total", "Cholesterol_HDL", "Triglycerides", "Target_HighTriglycerides", "Target_LowHDL"],
    "HighTriglycerides": ["Triglycerides"],
    "LowHDL": ["Cholesterol_HDL"],
    
    # 问卷类互斥
    "HeartFailure": ["Target_CVD", "Heart_Failure"],
    "CoronaryHeart": ["Target_CVD", "Coronary_Heart"],
    "HeartAttack": ["Target_CVD", "Heart_Attack"],
    "Stroke": ["Target_CVD", "Stroke"],
    "CVD": ["Target_Stroke", "Target_HeartAttack", "Target_CoronaryHeart", "Target_HeartFailure", "Stroke", "Heart_Attack", "Coronary_Heart", "Heart_Failure"], 
    
    # --- 脏器 ---
    "CKD": ["Creatinine", "eGFR", "UACR", "Urine_Albumin", "Urine_Creatinine"],
    "KidneyStones": ["Kidney_Stones"],
    "LiverDisease": ["ALT", "AST", "GGT"], # 加入 GGT 防止泄露
    
    # --- 血液/免疫 ---
    "Anemia": ["Hemoglobin", "Ferritin", "MCV"], # 加入 MCV
    "IronDef": ["Ferritin", "Hemoglobin", "Target_IronOverload"],
    "IronOverload": ["Ferritin", "Target_IronDef"],
    "Inflammation": ["HS_CRP", "WBC"], # 加入 WBC
    
    # --- 毒理与骨骼 ---
    "HighLead": ["Blood_Lead"],
    "HighCadmium": ["Blood_Cadmium"],
    "Osteoporosis": ["Bone_Density"],
    
    # --- 其他 ---
    "Arthritis": ["Arthritis", "Arthritis_History"],
    "Asthma": ["Asthma"],
    "COPD": ["COPD"],
    "Psoriasis": ["Psoriasis"],
    "GumDisease": ["Gum_Disease", "Gum_Disease_History"],
    "CognitiveDecline": ["Cognitive_Score"],
    "Glaucoma": ["Glaucoma"], # 问卷题，必须踢出
    "ToothLoss": ["Dentition_Status", "Gum_Disease"], 
    "Depression": [],
    "Hypertension": ["SBP", "DBP", "Target_HighPulsePressure", "BP_Meds"],
    "HighLipid": ["Cholesterol_Total", "Cholesterol_HDL", "Triglycerides", "Target_HighTriglycerides", "Target_LowHDL", "Cholesterol_Meds"],
    "HeavyDrinker": ["Alcohol_Days"],
    "PoorHealth": ["General_Health"],
    "Smoker": ["Smoked_100_Cigs", "Thiocyanate"], 
}

def clean_column_name(col_name):
    return re.sub(r'[^A-Za-z0-9_]+', '_', str(col_name))


# ================= 🍎 Task 91: 营养数据加载器 =================
def load_nhanes_nutrition_data(main_df: pd.DataFrame) -> pd.DataFrame:
    """
    从 NHANES XPT 文件中加载营养数据并合并到主数据框。
    使用 SEQN 作为 Join Key。
    """
    print("\n=== 🍎 加载 NHANES 营养与微量元素数据 ===")
    
    # 确保主表有 SEQN
    if 'SEQN' not in main_df.columns:
        print("⚠️ 主表无 SEQN 列，跳过营养数据合并")
        return main_df
    
    merged_df = main_df.copy()
    
    for name, filename in NUTRITION_FILES.items():
        filepath = os.path.join(RAW_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"  ⚠️ [{name}] 文件不存在: {filename}")
            continue
        
        try:
            # 使用 pandas.read_sas 读取 SAS XPT 格式
            xpt_df = pd.read_sas(filepath, format='xport', encoding='utf-8')
            xpt_df.columns = [clean_column_name(c) for c in xpt_df.columns]
            
            # 确定要提取的特征列
            if name.startswith("DIET"):
                target_cols = ['SEQN'] + [c for c in DIET_FEATURES if c in xpt_df.columns]
            else:
                target_cols = ['SEQN'] + [c for c in MICRONUTRIENT_FEATURES if c in xpt_df.columns]
            
            # 只保留存在的列
            available_cols = [c for c in target_cols if c in xpt_df.columns]
            if len(available_cols) <= 1:  # 只有 SEQN
                print(f"  ⚠️ [{name}] 无可用特征列")
                continue
            
            subset = xpt_df[available_cols].copy()
            
            # Left Merge
            before_cols = len(merged_df.columns)
            merged_df = merged_df.merge(subset, on='SEQN', how='left', suffixes=('', f'_{name}'))
            new_cols = len(merged_df.columns) - before_cols
            
            print(f"  ✅ [{name}] 合并成功: +{new_cols} 列 | 原始样本: {len(xpt_df)}")
            
        except Exception as e:
            print(f"  ❌ [{name}] 加载失败: {e}")
    
    # 显示营养特征统计
    nutrition_cols = [c for c in merged_df.columns if c in DIET_FEATURES + MICRONUTRIENT_FEATURES]
    print(f"\n📊 营养特征总数: {len(nutrition_cols)}")
    for col in nutrition_cols[:5]:  # 只显示前5个
        non_null = merged_df[col].notna().sum()
        print(f"   - {col}: {non_null} 有效值 ({100*non_null/len(merged_df):.1f}%)")
    
    return merged_df


def plot_feature_importance(model_bundle: dict, top_n: int = 30, save_path: str = None):
    """
    绘制所有模型的平均特征重要性 Top N。
    Task 93: Y轴使用中文标签
    """
    print("\n=== 📊 生成特征重要性图表 (中文标签) ===")
    
    all_importance = {}
    
    for disease, model in model_bundle["models"].items():
        features = model_bundle["features_map"].get(disease, [])
        importances = model.feature_importances_
        
        for feat, imp in zip(features, importances):
            if feat not in all_importance:
                all_importance[feat] = []
            all_importance[feat].append(imp)
    
    # 计算平均重要性
    avg_importance = {feat: np.mean(imps) for feat, imps in all_importance.items()}
    
    # 排序并取 Top N
    sorted_items = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
    features_top = [x[0] for x in sorted_items]
    values_top = [x[1] for x in sorted_items]
    
    # Task 93: 转换为中文标签
    features_chinese = [get_chinese_name(f) for f in features_top]
    
    # 绘图 (设置中文字体)
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.figure(figsize=(14, 10))
    bars = plt.barh(range(len(features_chinese)), values_top[::-1], color='steelblue')
    plt.yticks(range(len(features_chinese)), features_chinese[::-1], fontsize=10)
    plt.xlabel('平均特征重要性 (LightGBM)', fontsize=12)
    plt.title(f'Top {top_n} 特征重要性排名 (跨所有疾病模型)', fontsize=14)
    
    # 标注营养相关特征 (绿色高亮)
    nutrition_feats = set(DIET_FEATURES + MICRONUTRIENT_FEATURES)
    nutrition_english = set([SAS_TO_ENGLISH.get(f, f) for f in nutrition_feats])
    
    for i, feat in enumerate(features_top[::-1]):
        # 检查是否是营养特征
        if feat in nutrition_feats or feat in nutrition_english or feat.startswith("Diet_") or feat.startswith("Lab_Vit"):
            plt.gca().get_yticklabels()[i].set_color('green')
            plt.gca().get_yticklabels()[i].set_fontweight('bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"💾 特征重要性图表已保存: {save_path}")
    else:
        plt.show()
    
    plt.close()
    
    # 输出营养相关特征的排名 (中文)
    print("\n🍎 营养特征在 Top30 中的表现:")
    for i, (feat, val) in enumerate(sorted_items):
        if feat in nutrition_feats or feat.startswith("Diet_") or feat.startswith("Lab_Vit"):
            chinese_name = get_chinese_name(feat)
            print(f"   #{i+1}: {chinese_name} = {val:.2f}")


def train_all_diseases_v12():
    print("=== 🚀 开始训练 V13 全科模型 (含营养与微量元素) ===")
    
    if not os.path.exists(DATA_FILE):
        print(f"❌ 找不到: {DATA_FILE}")
        return
    
    df = pd.read_csv(DATA_FILE)
    df = df.rename(columns=lambda x: clean_column_name(x))
    print(f"📊 基础数据就绪: {len(df)} 行 x {len(df.columns)} 列")
    
    # 🍎 Task 91: 合并 NHANES 营养数据
    df = load_nhanes_nutrition_data(df)
    print(f"📊 合并后总维度: {len(df)} 行 x {len(df.columns)} 列")

    targets = [c for c in df.columns if c.startswith('Target_')]
    base_exclude = targets + ['SEQN']
    base_features = [c for c in df.columns if c not in base_exclude]
    
    print(f"\n🎯 目标病种: {len(targets)} 个 | 特征维度: {len(base_features)} 个")
    print("-" * 60)

    model_bundle = {"models": {}, "features_map": {}}
    success_count = 0

    for target in targets:
        disease_name = target.replace("Target_", "")
        print(f"🔥 [{disease_name:<20}] ", end="")
        
        y = df[target].fillna(0).astype(int)
        
        if len(y.unique()) < 2:
            print("⚠️ 跳过 (单一标签)")
            continue

        # 动态特征筛选
        drop_list = LEAKAGE_MAPPING.get(disease_name, [])
        cleaned_drop_list = [clean_column_name(d) for d in drop_list]
        current_features = [f for f in base_features if f not in cleaned_drop_list and f != disease_name]
        
        # 样本量检查 (放宽以容纳罕见病)
        if y.sum() < 20:
            print(f"⚠️ 跳过 (阳性 {y.sum()} < 20)")
            continue

        try:
            X = df[current_features]
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
            
            clf = lgb.LGBMClassifier(
                n_estimators=150, learning_rate=0.05, num_leaves=31, random_state=42, 
                verbosity=-1, is_unbalance=True
            )
            clf.fit(X_train, y_train)
            
            auc = roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
            acc = accuracy_score(y_test, clf.predict(X_test))
            
            mark = "★" if auc > 0.8 else " "
            print(f"✅ AUC: {mark} {auc:.3f} | Acc: {acc:.3f}")
            
            model_bundle["models"][disease_name] = clf
            model_bundle["features_map"][disease_name] = current_features
            success_count += 1
            
        except Exception as e:
            print(f"❌ 失败: {e}")

    print("-" * 60)
    joblib.dump(model_bundle, MODEL_PATH)
    print(f"💾 模型更新完毕: {MODEL_PATH}")
    print(f"🎉 集成模型: {success_count} 个")
    
    # 🍎 Task 91: 生成特征重要性图表
    if success_count > 0:
        plot_feature_importance(model_bundle, top_n=30, save_path=IMPORTANCE_PLOT_PATH)

if __name__ == "__main__":
    train_all_diseases_v12()
