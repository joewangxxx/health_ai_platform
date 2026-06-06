import pandas as pd
import numpy as np
import os

# ================= ⚙️ 配置区域 =================
# Task 107: 使用统一配置路径
from backend.config import PROJECT_ROOT, DATA_WAREHOUSE_DIR
# Task 103: 使用集中式变量映射
from backend.core.constants import NHANES_MAPPING

RAW_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "NHANES")
PROCESSED_DIR = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "clinical_clean")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 全量文件列表 (Task 104 升级版: 含膳食/维生素/尿流率)
FILES_MAP = {
    # === 基础 ===
    "DEMO": "P_DEMO.xpt", "BMX": "P_BMX.xpt", "BPX": "P_BPXO.xpt", 
    
    # === 化验 ===
    "GLU": "P_GLU.xpt", "GHB": "P_GHB.xpt", "INS": "P_INS.xpt",
    "TCHOL": "P_TCHOL.xpt", "HDL": "P_HDL.xpt", "TRIGLY": "P_TRIGLY.xpt",
    "BIOPRO": "P_BIOPRO.xpt", "ALB_CR": "P_ALB_CR.xpt",
    "CBC": "P_CBC.xpt", "HSCRP": "P_HSCRP.xpt",
    "FERTIN": "P_FERTIN.xpt", "HEPC": "P_HEPC.xpt",
    "PBCD": "P_PBCD.xpt", 
    
    # === 问卷 & 检查 ===
    "DIQ": "P_DIQ.xpt", "MCQ": "P_MCQ.xpt", "DPQ": "P_DPQ.xpt", 
    "SLQ": "P_SLQ.xpt", "PAQ": "P_PAQ.xpt", "OHQ": "P_OHQ.xpt",
    "KIQ": "P_KIQ_U.xpt", "DEQ": "P_DEQ.xpt", "DXXFEM": "P_DXXFEM.xpt",
    "OHXDEN": "P_OHXDEN.xpt",   # 牙齿检查
    "SMQ": "P_SMQ.xpt",         # 吸烟
    "ALQ": "P_ALQ.xpt",         # 饮酒
    "HUQ": "P_HUQ.xpt",         # 整体健康
    "BPQ": "P_BPQ.xpt",         # 药物
    
    # === 🍎 Task 104 新增: 膳食数据 ===
    "DR1TOT": "P_DR1TOT.xpt",   # 膳食总摄入 Day1
    "DR2TOT": "P_DR2TOT.xpt",   # 膳食总摄入 Day2
    
    # === 🧪 Task 104 新增: 微量元素 ===
    "VID": "P_VID.xpt",         # 维生素D
    "FOLATE": "P_FOLATE.xpt",   # 叶酸
    "VITAEC": "P_VITAEC.xpt",   # 维生素A/C/E (如有)
    
    # === 💧 Task 104 新增: 尿流率 ===
    "UCFLOW": "P_UCFLOW.xpt",   # 尿流率
    
    # === 💊 Task 104 新增: 补充剂 ===
    "DSQTOT": "P_DSQTOT.xpt",   # 膳食补充剂总量
}

def clean_seqn(col):
    """强力清洗 SEQN：转为纯整数"""
    return pd.to_numeric(col, errors='coerce').fillna(-1).astype(int)

def calculate_egfr(row):
    """Calculate eGFR with the 2021 CKD-EPI creatinine equation."""
    scr = row.get('Creatinine', np.nan)
    age = row.get('Age', np.nan)
    gender = row.get('Gender', np.nan)
    if pd.isna(scr) or pd.isna(age) or pd.isna(gender):
        return np.nan

    # 2021 CKD-EPI creatinine equation is race-free; Scr is expected in mg/dL.
    kappa = 0.7 if gender == 2 else 0.9
    alpha = -0.241 if gender == 2 else -0.302
    female_factor = 1.012 if gender == 2 else 1.0
    scr_ratio = scr / kappa
    return (
        142
        * (min(scr_ratio, 1) ** alpha)
        * (max(scr_ratio, 1) ** -1.200)
        * (0.9938 ** age)
        * female_factor
    )

def process_nhanes_final_fix():
    print("=== 🚀 NHANES  (修复SEQN丢失 & 含牙齿数据) ===")
    
    dfs = {}
    
    # 1. 读取并标准化
    print("\n[Step 1] 读取文件...")
    for key, filename in FILES_MAP.items():
        path = os.path.join(RAW_DIR, filename)
        if not os.path.exists(path): path = path.replace(".xpt", ".XPT")
        
        if os.path.exists(path):
            try:
                df = pd.read_sas(path, format='xport')
                # 强转大写
                df.columns = [c.upper() for c in df.columns]
                
                if 'SEQN' in df.columns:
                    # 强转 Int
                    df['SEQN'] = clean_seqn(df['SEQN'])
                    # 去重
                    df = df.drop_duplicates(subset=['SEQN'])
                    
                    # 🔥 关键修改：不要 set_index，保持 SEQN 为普通列
                    # 这样后续 merge 时不容易丢
                    dfs[key] = df
                    print(f"   📦 {key:<8}: {len(df)} 行")
                else:
                    print(f"   ⚠️ 跳过 {key}: 无 SEQN")
            except: pass
        else:
            print(f"   ⚠️ 缺失: {filename}")

    if 'DEMO' not in dfs: 
        print("❌ 核心 DEMO 缺失")
        return

    # 2. 合并 (Merge on Column)
    print("\n[Step 2] 融合数据...")
    final_df = dfs['DEMO']
    
    for key in dfs:
        if key != 'DEMO':
            # 使用 merge，明确指定 on='SEQN'
            final_df = pd.merge(final_df, dfs[key], on='SEQN', how='left', suffixes=('', f'_{key}'))

    print(f"   合并后维度: {final_df.shape}")

    # 3. 特征映射 (Task 104: 使用集中式 NHANES_MAPPING)
    print("\n[Step 3] 提取特征 (使用 NHANES_MAPPING)...")
    
    # 补充 NHANES_MAPPING 中没有的特殊字段
    col_map = NHANES_MAPPING.copy()
    col_map.update({
        'LBXHCV': 'HCV_Ab',
        'LBXBPB': 'Blood_Lead',
        'LBXBCD': 'Blood_Cadmium',
    })
    
    clean_df = pd.DataFrame()
    # 🔥 修复 KeyError 的核心：直接从 final_df 拿 SEQN
    if 'SEQN' in final_df.columns:
        clean_df['SEQN'] = final_df['SEQN']
    else:
        # 如果万一 SEQN 在索引里，重置索引
        clean_df['SEQN'] = final_df.index
    
    for original, new_name in col_map.items():
        if original in final_df.columns:
            clean_df[new_name] = final_df[original]
        else:
            clean_df[new_name] = np.nan

    # 4. 病种判定
    def q_to_bin(col): return (clean_df[col] == 1).astype(int) if col in clean_df.columns else 0

    # 1. 代谢
    clean_df['Target_T2D'] = ((clean_df.get('HbA1c', 0) >= 6.5) | (clean_df.get('Glucose_Fasting', 0) >= 126)).fillna(0).astype(int)
    clean_df['Target_Obesity'] = (clean_df.get('BMI', 0) >= 30).fillna(0).astype(int)
    clean_df['Target_PreDiabetes'] = ((clean_df.get('HbA1c', 0) >= 5.7) & (clean_df.get('HbA1c', 0) < 6.5)).fillna(0).astype(int)
    
    is_male = clean_df['Gender'] == 1
    ua = clean_df.get('Uric_Acid', 0)
    clean_df['Target_Gout'] = (((is_male) & (ua > 7)) | ((~is_male) & (ua > 6))).fillna(0).astype(int)
    clean_df['Target_Hyperuricemia'] = clean_df['Target_Gout']
    
    clean_df['HOMA_IR'] = (clean_df.get('Glucose_Fasting', 0) * clean_df.get('Insulin', 0)) / 405
    clean_df['Target_InsulinResist'] = (clean_df.get('HOMA_IR', 0) > 2.5).fillna(0).astype(int)
    
    ms_waist = ((is_male & (clean_df.get('WaistCircum',0)>=102)) | (~is_male & (clean_df.get('WaistCircum',0)>=88))).fillna(0).astype(int)
    ms_trig = (clean_df.get('Triglycerides', 0) >= 150).fillna(0).astype(int)
    ms_hdl = ((is_male & (clean_df.get('Cholesterol_HDL', 100)<40)) | (~is_male & (clean_df.get('Cholesterol_HDL', 100)<50))).fillna(0).astype(int)
    clean_df['Target_AbdominalObesity'] = ms_waist

    # 2. 心血管 (药物修正)
    bp_high = ((clean_df.get('SBP', 0) >= 140) | (clean_df.get('DBP', 0) >= 90))
    bp_meds = q_to_bin('BP_Meds')
    clean_df['Target_Hypertension'] = (bp_high | bp_meds).astype(int)
    
    lipid_high = (clean_df.get('Cholesterol_Total', 0) >= 240)
    lipid_meds = q_to_bin('Cholesterol_Meds')
    clean_df['Target_HighLipid'] = (lipid_high | lipid_meds).astype(int)

    clean_df['Target_HighPulsePressure'] = ((clean_df.get('SBP', 0) - clean_df.get('DBP', 0)) > 60).fillna(0).astype(int)
    clean_df['Target_HighTriglycerides'] = ms_trig
    clean_df['Target_LowHDL'] = ms_hdl
    
    ms_bp = ((clean_df.get('SBP', 0) >= 130) | (clean_df.get('DBP', 0) >= 85)).fillna(0).astype(int)
    ms_glu = (clean_df.get('Glucose_Fasting', 0) >= 100).fillna(0).astype(int)
    clean_df['Target_MetabolicSyndrome'] = ((ms_waist + ms_trig + ms_hdl + ms_bp + ms_glu) >= 3).astype(int)

    # 3. 脏器
    if 'Creatinine' in clean_df.columns:
        clean_df['eGFR'] = clean_df.apply(calculate_egfr, axis=1)
        clean_df['UACR'] = (clean_df.get('Urine_Albumin', 0) / clean_df.get('Urine_Creatinine', 1)) * 100
        clean_df['Target_CKD'] = ((clean_df['eGFR'] < 60) | (clean_df['UACR'] > 30)).fillna(0).astype(int)
    else: clean_df['Target_CKD'] = 0
    
    clean_df['Target_LiverDisease'] = ((clean_df.get('ALT', 0) > 40) | (clean_df.get('AST', 0) > 40)).fillna(0).astype(int)
    clean_df['Target_KidneyStones'] = q_to_bin('Kidney_Stones')

    # 4. 血液/免疫/生活
    hb = clean_df.get('Hemoglobin', 99)
    clean_df['Target_Anemia'] = (((is_male) & (hb < 13)) | ((~is_male) & (hb < 12))).fillna(0).astype(int)
    clean_df['Target_Inflammation'] = (clean_df.get('HS_CRP', 0) > 3.0).fillna(0).astype(int)
    clean_df['Target_HepC'] = q_to_bin('HCV_Ab')
    clean_df['Target_IronDef'] = (clean_df.get('Ferritin', 100) < 30).fillna(0).astype(int)
    clean_df['Target_IronOverload'] = (clean_df.get('Ferritin', 0) > 300).fillna(0).astype(int)
    clean_df['Target_HighLead'] = (clean_df.get('Blood_Lead', 0) > 5).fillna(0).astype(int)
    clean_df['Target_HighCadmium'] = (clean_df.get('Blood_Cadmium', 0) > 5).fillna(0).astype(int)
    
    # 问卷类
    clean_df['Target_HeartFailure'] = q_to_bin('Heart_Failure')
    clean_df['Target_CoronaryHeart'] = q_to_bin('Coronary_Heart')
    clean_df['Target_HeartAttack'] = q_to_bin('Heart_Attack')
    clean_df['Target_Stroke'] = q_to_bin('Stroke')
    clean_df['Target_CVD'] = (clean_df['Target_HeartFailure'] | clean_df['Target_CoronaryHeart'] | 
                              clean_df['Target_HeartAttack'] | clean_df['Target_Stroke'])
    
    clean_df['Target_Osteoporosis'] = (clean_df.get('Bone_Density', 1.0) < 0.6).fillna(0).astype(int)
    clean_df['Target_Arthritis'] = q_to_bin('Arthritis')
    clean_df['Target_Asthma'] = q_to_bin('Asthma')
    clean_df['Target_COPD'] = q_to_bin('COPD')
    clean_df['Target_Psoriasis'] = q_to_bin('Psoriasis')
    clean_df['Target_GumDisease'] = q_to_bin('Gum_Disease')
    
    # 🔥 新增：严重牙齿脱落
    # Dentition_Status: 1=Full, 2=Partial, 3=No teeth
    clean_df['Target_ToothLoss'] = (clean_df.get('Dentition_Status', 1) >= 2).astype(int)
    
    # 新增：生活方式风险
    clean_df['Target_HeavyDrinker'] = (clean_df.get('Alcohol_Days', 0).replace({999:0}) >= 3).astype(int)
    clean_df['Target_PoorHealth'] = (clean_df.get('General_Health', 0) >= 4).astype(int)

    # 抑郁
    dpq_cols = [c for c in final_df.columns if c.startswith('DPQ') and len(c)==6]
    if dpq_cols: clean_df['Target_Depression'] = (final_df[dpq_cols].replace({7:0, 9:0}).fillna(0).sum(axis=1) >= 10).astype(int)
    else: clean_df['Target_Depression'] = 0

    # 6. 保存
    clean_df = clean_df.dropna(subset=['Age', 'BMI'])
    for col in clean_df.columns:
        if clean_df[col].dtype in ['float64', 'float32'] and not col.startswith('Target_'):
            clean_df[col] = clean_df[col].fillna(clean_df[col].median())

    # 🔥 Task 104: 输出新版本数据
    output_path = os.path.join(PROCESSED_DIR, "nhanes_integrated_data_v2.csv")
    clean_df.to_csv(output_path, index=False)
    
    print("\n" + "="*60)
    print(f"🎉 Task 104 完成！(全量数据 V2.0)")
    print(f"📂 结果保存: {output_path}")
    print(f"   总记录数: {len(clean_df)}")
    print(f"   总特征数: {len(clean_df.columns)}")
    print(f"   牙齿脱落阳性: {clean_df['Target_ToothLoss'].sum()}")
    print("="*60)

if __name__ == "__main__":
    process_nhanes_final_fix()
