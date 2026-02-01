"""
USDA SR Legacy Data ETL Script (Purified)
=========================================
将 USDA SR Legacy 营养数据清洗并转换为 JSON 格式用于营养规划模块。
v2.0 Update: 引入严格的黑名单过滤和名称美化逻辑。

数据源: FoodData_Central_sr_legacy_food_csv_2018-04
输出: backend/data/nutrition_db.json
"""

import pandas as pd
import json
import os
import re
from pathlib import Path

# ================= 配置 =================
# Task 107: 使用统一配置路径
from backend.config import DATA_WAREHOUSE_DIR, BACKEND_DIR

# 数据源路径
DATA_DIR = Path(DATA_WAREHOUSE_DIR) / "raw_data" / "USDA" / "FoodData_Central_sr_legacy_food_csv_2018-04"

# 输出路径
OUTPUT_DIR = Path(BACKEND_DIR) / "data"
OUTPUT_FILE = OUTPUT_DIR / "nutrition_db.json"

# 1. Category 黑名单 (排除不适合做健康食谱的类别)
EXCLUDED_CATEGORIES = {
    2,   # Spices and Herbs
    3,   # Baby Foods
    6,   # Soups, Sauces, and Gravies
    7,   # Sausages and Luncheon Meats
    14,  # Beverages
    19,  # Sweets
    21,  # Fast Foods
    22,  # Meals, Entrees, and Side Dishes
    25,  # Snacks
    28,  # Alcoholic Beverages (if exists)
    36,  # Restaurant Foods (if exists)
}

# 2. Keyword 黑名单 (不区分大小写)
KEYWORD_BLACKLIST = [
    "Pizza",
    "McDonald's", 
    "Burger King", 
    "Wendy's", 
    "KFC", 
    "Taco Bell", 
    "Pizza Hut",
    "Domino's",
    "Industrial",
    "Formula",      # Baby formula
    "Alcohol",
    "Beverage",
    "Carbonated",
    "Cookie",
    "Candy",
    "Chocolate",
    "Supplement",
    "Ensure",
    "Silk",
    "Brand",
    "Energy Drink"
]

# 3. 目标营养素 ID
NUTRIENT_MAP = {
    1008: "calories",    # Energy (KCAL)
    1003: "protein",     # Protein (g)
    1004: "fat",         # Total lipid/fat (g)
    1005: "carbs",       # Carbohydrate, by difference (g)
    1079: "fiber",       # Fiber, total dietary (g)
    1093: "sodium",      # Sodium, Na (mg)
}

def clean_name(original_name: str) -> str:
    """
    清洗 USDA 数据名称，使其更适合 C 端展示。
    Example: 
      "Chicken, broilers or fryers, breast, meat only, raw" -> "Chicken Breast (Raw)"
      "Broccoli, raw" -> "Broccoli (Raw)"
    """
    # 1. 基础清理
    parts = [p.strip() for p in original_name.split(',')]
    if not parts:
        return original_name

    base_name = parts[0]
    extras = []
    state = []

    # 2. 关键词提取 (从剩余部分中提取有价值的信息)
    important_keywords = {
        # 部位
        'breast', 'thigh', 'wing', 'drumstick', 'filet', 'sirloin', 'loin', 'steak', 'chop',
        # 状态
        'raw', 'cooked', 'boiled', 'roasted', 'grilled', 'fried', 'baked', 'dried', 'fresh', 'frozen', 'canned'
    }

    # 总是保留的部分后缀（如果很短）
    for p in parts[1:]:
        p_lower = p.lower()
        
        # 提取状态 (Raw/Cooked...)
        if p_lower in {'raw', 'cooked', 'boiled', 'roasted', 'grilled', 'fried', 'baked', 'dried', 'dry heat'}:
            state.append(p.capitalize().replace("Dry heat", "").strip())
            continue
            
        # 提取重要部位或修饰词
        if any(k in p_lower for k in important_keywords):
            # 简化 some phrasing
            clean_p = p.replace("meat only", "").replace("skin only", "").strip()
            if clean_p:
                extras.append(clean_p.title())
            continue

    # 3. 组装
    final_name = base_name
    if extras:
        final_name += f" {' '.join(extras)}"
    
    # 将状态放在括号里
    if state:
        # 去重
        state = list(set(state))
        final_name += f" ({'/'.join(state)})"

    return final_name


def load_foods() -> pd.DataFrame:
    """加载并过滤食物数据 (Strict Purification)"""
    print("📂 加载 food.csv...")
    food_df = pd.read_csv(DATA_DIR / "food.csv")
    
    print("📂 加载 food_category.csv...")
    category_df = pd.read_csv(DATA_DIR / "food_category.csv")
    
    # 合并获取类别描述
    food_df = food_df.merge(
        category_df[['id', 'description']].rename(columns={'id': 'food_category_id', 'description': 'category'}),
        on='food_category_id',
        how='left'
    )
    
    before_count = len(food_df)
    
    # ------------------ Filtering Logic ------------------
    
    # 1. Filter Category Blacklist
    food_df = food_df[~food_df['food_category_id'].isin(EXCLUDED_CATEGORIES)]
    
    # 2. Filter Keyword Blacklist (Description)
    # create regex pattern
    pattern = '|'.join(map(re.escape, KEYWORD_BLACKLIST))
    food_df = food_df[~food_df['description'].str.contains(pattern, case=False, na=False)]
    
    # 3. Specific Exclusions (Water)
    food_df = food_df[~food_df['description'].isin(["Water, tap", "Water, bottled", "Water, generic"])]

    # -----------------------------------------------------

    after_count = len(food_df)
    print(f"   ✅ 过滤完成: {before_count} -> {after_count} 条记录 (剔除 {before_count - after_count} 条垃圾数据)")
    
    # Apply Name Cleaning
    print("   ✨ 执行名称美化 (Name Cleaning)...")
    food_df['clean_name'] = food_df['description'].apply(clean_name)
    
    return food_df[['fdc_id', 'clean_name', 'category']].rename(columns={'clean_name': 'name'})


def load_nutrients(fdc_ids: set) -> pd.DataFrame:
    """加载并透视营养素数据"""
    print("📂 加载 food_nutrient.csv (大文件，请稍候)...")
    nutrient_df = pd.read_csv(DATA_DIR / "food_nutrient.csv")
    
    # 筛选目标营养素和目标食物
    target_nutrient_ids = set(NUTRIENT_MAP.keys())
    nutrient_df = nutrient_df[
        (nutrient_df['nutrient_id'].isin(target_nutrient_ids)) &
        (nutrient_df['fdc_id'].isin(fdc_ids))
    ]
    
    # 映射营养素名称
    nutrient_df['nutrient_name'] = nutrient_df['nutrient_id'].map(NUTRIENT_MAP)
    
    # 透视表
    pivot_df = nutrient_df.pivot_table(
        index='fdc_id',
        columns='nutrient_name',
        values='amount',
        aggfunc='first'
    ).reset_index()
    
    # 确保所有营养素列存在
    for col in NUTRIENT_MAP.values():
        if col not in pivot_df.columns:
            pivot_df[col] = 0.0
    
    # 丢弃缺失热量的记录
    pivot_df = pivot_df.dropna(subset=['calories'])
    
    return pivot_df


def load_portions(fdc_ids: set) -> pd.DataFrame:
    """加载份量数据"""
    print("📂 加载 food_portion.csv...")
    portion_df = pd.read_csv(DATA_DIR / "food_portion.csv")
    measure_df = pd.read_csv(DATA_DIR / "measure_unit.csv")
    
    portion_df = portion_df[portion_df['fdc_id'].isin(fdc_ids)]
    
    portion_df = portion_df.merge(
        measure_df[['id', 'name']].rename(columns={'id': 'measure_unit_id', 'name': 'unit_name'}),
        on='measure_unit_id',
        how='left'
    )
    
    # 排序取最优
    portion_df = portion_df.sort_values(['fdc_id', 'seq_num'])
    portion_df = portion_df.groupby('fdc_id').first().reset_index()
    
    def format_portion(row):
        parts = []
        if pd.notna(row.get('amount')) and row['amount'] > 0:
            val = row['amount']
            parts.append(f"{int(val)}" if val == int(val) else f"{val}")
        if pd.notna(row.get('modifier')) and row['modifier']:
            parts.append(str(row['modifier']))
        if pd.notna(row.get('unit_name')) and row['unit_name']:
            parts.append(str(row['unit_name']))
        
        desc = " ".join(parts) if parts else "1 serving"
        grams = row.get('gram_weight', 100) if pd.notna(row.get('gram_weight')) else 100
        return desc, grams
    
    portion_df[['portion_desc', 'portion_grams']] = portion_df.apply(
        lambda row: pd.Series(format_portion(row)), axis=1
    )
    
    return portion_df[['fdc_id', 'portion_desc', 'portion_grams']]


def build_nutrition_db():
    """主 ETL 流程"""
    print("\n" + "="*60)
    print("🚀 SR Legacy Nutrition ETL Pipeline (Purified)")
    print("="*60 + "\n")
    
    # 1. 加载食物 (带过滤)
    foods_df = load_foods()
    fdc_ids = set(foods_df['fdc_id'])
    
    if not fdc_ids:
        print("❌ 错误: 过滤后没有剩余食物数据！请检查过滤条件。")
        return

    # 2. 加载营养素
    nutrients_df = load_nutrients(fdc_ids)
    
    # 3. 加载份量
    portions_df = load_portions(fdc_ids)
    
    # 4. 合并数据
    print("\n🔗 合并数据...")
    merged_df = foods_df.merge(nutrients_df, on='fdc_id', how='inner')
    merged_df = merged_df.merge(portions_df, on='fdc_id', how='left')
    
    # 填充缺失
    merged_df['portion_desc'] = merged_df['portion_desc'].fillna("1 serving")
    merged_df['portion_grams'] = merged_df['portion_grams'].fillna(100)
    merged_df = merged_df.fillna(0) # 填充其余数值

    # 5. 构造 JSON
    print("\n📝 构造 JSON...")
    result = []
    for _, row in merged_df.iterrows():
        item = {
            "id": int(row['fdc_id']),
            "name": row['name'], # 已经是 Clean Name
            "category": row['category'],
            "nutrients": {
                "calories": round(row['calories'], 1),
                "protein": round(row['protein'], 1),
                "carbs": round(row['carbs'], 1),
                "fat": round(row['fat'], 1),
                "fiber": round(row['fiber'], 1),
                "sodium": round(row['sodium'], 1),
            },
            "portion": {
                "desc": row['portion_desc'],
                "grams": round(row['portion_grams'], 1)
            }
        }
        result.append(item)
    
    # 6. 保存
    print(f"\n💾 保存到 {OUTPUT_FILE}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ 成功保存 {len(result)} 条精选食物记录")
    
    # 7. 统计
    print(f"   最终数据库大小: {len(result)} items")
    return result


if __name__ == "__main__":
    build_nutrition_db()
