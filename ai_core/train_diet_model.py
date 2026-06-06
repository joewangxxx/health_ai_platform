"""
Task 96: NHANES Diet Pattern Clustering Model
==============================================
训练 KMeans 聚类模型，识别典型的饮食模式。
例如：健康均衡、高糖高脂、高蛋白、低热量贫瘠、高盐等。
"""
import os
import sys
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from backend.config import DATA_WAREHOUSE_DIR, MODELS_DIR

# ================= 配置区域 =================
BASE_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "NHANES")
DATA_FILE = os.path.join(BASE_DIR, "P_DR1TOT.xpt")

MODEL_DIR = MODELS_DIR
os.makedirs(MODEL_DIR, exist_ok=True)

KMEANS_PATH = os.path.join(MODEL_DIR, "diet_kmeans.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "diet_scaler.pkl")
CLUSTER_DESC_PATH = os.path.join(MODEL_DIR, "cluster_descriptions.json")

# 关键营养特征
DIET_FEATURES = [
    "DR1TKCAL",   # 热量 kcal
    "DR1TPROT",   # 蛋白质 g
    "DR1TCARB",   # 碳水化合物 g
    "DR1TSUGR",   # 总糖 g
    "DR1TFIBE",   # 膳食纤维 g
    "DR1TSFAT",   # 饱和脂肪 g
    "DR1TSODI",   # 钠 mg
    "DR1TPOTA",   # 钾 mg
    "DR1TVC",     # 维生素C mg
    "DR1TFAT",    # 总脂肪 g
]

# 特征中文名映射
FEATURE_CHINESE = {
    "DR1TKCAL": "热量",
    "DR1TPROT": "蛋白质",
    "DR1TCARB": "碳水化合物",
    "DR1TSUGR": "糖分",
    "DR1TFIBE": "膳食纤维",
    "DR1TSFAT": "饱和脂肪",
    "DR1TSODI": "钠",
    "DR1TPOTA": "钾",
    "DR1TVC": "维生素C",
    "DR1TFAT": "脂肪",
}

# 聚类数目
N_CLUSTERS = 5


def load_and_clean_data():
    """加载并清洗 NHANES 膳食数据"""
    print("=== 📊 加载 NHANES 膳食数据 ===")
    
    if not os.path.exists(DATA_FILE):
        print(f"❌ 文件不存在: {DATA_FILE}")
        return None
    
    # 读取 XPT 文件
    df = pd.read_sas(DATA_FILE, format='xport', encoding='utf-8')
    print(f"原始数据: {len(df)} 行 x {len(df.columns)} 列")
    
    # 筛选需要的特征
    available_features = [f for f in DIET_FEATURES if f in df.columns]
    print(f"可用特征: {len(available_features)} / {len(DIET_FEATURES)}")
    
    if len(available_features) < 5:
        print("❌ 可用特征过少，无法训练聚类模型")
        return None
    
    # 提取特征子集
    df_diet = df[['SEQN'] + available_features].copy()
    
    # 去除 NaN
    df_clean = df_diet.dropna()
    print(f"清洗后数据: {len(df_clean)} 行")
    
    return df_clean, available_features


def train_kmeans(df, features):
    """训练 KMeans 聚类模型"""
    print("\n=== 🤖 训练 KMeans 聚类模型 ===")
    
    X = df[features].values
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    print(f"数据标准化完成: shape = {X_scaled.shape}")
    
    # 训练 KMeans
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    
    # 预测簇标签
    labels = kmeans.predict(X_scaled)
    df['cluster'] = labels
    
    # 统计每个簇的大小
    cluster_sizes = pd.Series(labels).value_counts().sort_index()
    print(f"\n簇大小分布:")
    for i, size in enumerate(cluster_sizes):
        print(f"  Cluster {i}: {size} 人 ({100*size/len(df):.1f}%)")
    
    return kmeans, scaler, df


def profile_clusters(df, features, kmeans):
    """分析每个簇的营养特征，自动打标签"""
    print("\n=== 🏷️ 聚类模式分析 ===")
    
    # 计算全局均值
    global_means = df[features].mean()
    
    cluster_descriptions = {}
    
    for cluster_id in range(N_CLUSTERS):
        cluster_df = df[df['cluster'] == cluster_id]
        cluster_means = cluster_df[features].mean()
        
        # 比较与全局均值的差异
        deviations = {}
        for feat in features:
            ratio = cluster_means[feat] / global_means[feat]
            if ratio > 1.2:
                deviations[feat] = "高"
            elif ratio < 0.8:
                deviations[feat] = "低"
            else:
                deviations[feat] = "正常"
        
        # 自动生成标签
        label, description = _auto_label(deviations, cluster_means)
        
        cluster_descriptions[str(cluster_id)] = {
            "label_en": label,
            "label_cn": description,
            "size": int(len(cluster_df)),
            "percentage": round(100 * len(cluster_df) / len(df), 1),
            "feature_profile": {
                FEATURE_CHINESE.get(f, f): {
                    "value": round(cluster_means[f], 1),
                    "deviation": deviations[f]
                }
                for f in features
            },
            "dietary_advice": _get_dietary_advice(label)
        }
        
        print(f"\nCluster {cluster_id}: {description}")
        for f in features[:5]:  # 只显示前5个特征
            cn_name = FEATURE_CHINESE.get(f, f)
            print(f"  - {cn_name}: {cluster_means[f]:.1f} ({deviations[f]})")
    
    return cluster_descriptions


def _auto_label(deviations, means):
    """根据特征偏差自动生成标签"""
    # 高糖高脂
    if deviations.get("DR1TSUGR") == "高" and deviations.get("DR1TSFAT") == "高":
        return "Western_Pattern", "西式饮食模式 (高糖高脂)"
    
    # 高盐低钾 (不健康)
    if deviations.get("DR1TSODI") == "高" and deviations.get("DR1TPOTA") == "低":
        return "High_Sodium", "高盐饮食模式"
    
    # 高蛋白高热量
    if deviations.get("DR1TPROT") == "高" and deviations.get("DR1TKCAL") == "高":
        return "High_Protein", "高蛋白高能量模式"
    
    # 低热量贫瘠
    if deviations.get("DR1TKCAL") == "低" and deviations.get("DR1TFIBE") == "低":
        return "Low_Nutrient", "低能量贫瘠模式"
    
    # 高纤维健康
    if deviations.get("DR1TFIBE") == "高" and deviations.get("DR1TSFAT") == "低":
        return "Mediterranean", "地中海健康模式"
    
    # 均衡饮食
    high_count = sum(1 for v in deviations.values() if v == "高")
    low_count = sum(1 for v in deviations.values() if v == "低")
    if high_count <= 2 and low_count <= 2:
        return "Balanced", "均衡饮食模式"
    
    return "Mixed", "混合饮食模式"


def _get_dietary_advice(label):
    """根据饮食模式生成建议"""
    advice_map = {
        "Western_Pattern": "建议减少精制糖和饱和脂肪摄入，增加蔬菜水果和全谷物。",
        "High_Sodium": "建议每日盐摄入控制在5g以下，多吃高钾食物如香蕉、菠菜。",
        "High_Protein": "蛋白质充足，注意平衡碳水化合物和蔬菜水果摄入。",
        "Low_Nutrient": "能量摄入不足，建议增加营养密度，补充优质蛋白和微量元素。",
        "Mediterranean": "饮食模式健康，建议保持当前饮食习惯。",
        "Balanced": "饮食相对均衡，可适当增加膳食纤维摄入。",
        "Mixed": "建议咨询营养师进行个性化饮食调整。",
    }
    return advice_map.get(label, "建议保持均衡饮食。")


def save_models(kmeans, scaler, cluster_descriptions, features):
    """保存模型和描述文件"""
    print("\n=== 💾 保存模型 ===")
    
    # 保存 KMeans 模型
    model_bundle = {
        "kmeans": kmeans,
        "features": features,
        "n_clusters": N_CLUSTERS
    }
    joblib.dump(model_bundle, KMEANS_PATH)
    print(f"✅ KMeans 模型已保存: {KMEANS_PATH}")
    
    # 保存 Scaler
    joblib.dump(scaler, SCALER_PATH)
    print(f"✅ Scaler 已保存: {SCALER_PATH}")
    
    # 保存簇描述
    with open(CLUSTER_DESC_PATH, 'w', encoding='utf-8') as f:
        json.dump(cluster_descriptions, f, ensure_ascii=False, indent=2)
    print(f"✅ 聚类描述已保存: {CLUSTER_DESC_PATH}")


def main():
    print("=" * 60)
    print("🍎 Task 96: NHANES 膳食模式聚类模型训练")
    print("=" * 60)
    
    # 1. 加载数据
    result = load_and_clean_data()
    if result is None:
        return
    df, features = result
    
    # 2. 训练模型
    kmeans, scaler, df_labeled = train_kmeans(df, features)
    
    # 3. 分析聚类
    cluster_descriptions = profile_clusters(df_labeled, features, kmeans)
    
    # 4. 保存模型
    save_models(kmeans, scaler, cluster_descriptions, features)
    
    print("\n" + "=" * 60)
    print("🎉 训练完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
