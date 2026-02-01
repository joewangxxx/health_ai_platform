import pandas as pd
import os
import glob

# ================= ⚙️ 配置区域 =================
# Task 107: 使用统一配置路径
from backend.config import DATA_WAREHOUSE_DIR

RAW_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "Nutrition5k")

# 图片根目录
IMG_DIR = os.path.join(RAW_DIR, "imagery", "realsense_overhead")
# 标签文件
LABEL_FILE = os.path.join(RAW_DIR, "dish_nutrition_values.csv")

OUTPUT_FILE = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "food_nutrition_labels.csv")

def process_nutrition5k_nested():
    print("=== 🥗 Nutrition5k 数据清洗：嵌套文件夹适配版 ===\n")
    
    if not os.path.exists(LABEL_FILE):
        print(f"❌ 找不到标签文件: {LABEL_FILE}")
        return
    if not os.path.exists(IMG_DIR):
        print(f"❌ 找不到图片目录: {IMG_DIR}")
        return

    # 1. 扫描图片 (寻找所有 rgb.png)
    print(f"1. 正在递归扫描 '{IMG_DIR}' 下的所有 rgb.png ...")
    
    # 递归查找所有 rgb.png
    pattern = os.path.join(IMG_DIR, "**", "rgb.png")
    # 🔥 修正变量名
    all_rgb_files = glob.glob(pattern, recursive=True)
    
    img_map = {}
    
    for f_path in all_rgb_files: # 🔥以此修正为 all_rgb_files
        # 获取父文件夹的名字作为 ID
        # 例如: .../dish_1556572657/rgb.png -> 父文件夹是 dish_1556572657
        parent_folder = os.path.basename(os.path.dirname(f_path))
        
        # 存入字典: "dish_1556572657" -> "路径"
        img_map[parent_folder] = f_path

    print(f"   ✅ 索引到 {len(img_map)} 个菜品文件夹")
    
    if len(img_map) == 0:
        print("   ⚠️ 警告：未找到任何 RGB 图片！请检查文件夹结构是否为 dish_xxx/rgb.png")
        return
        
    example_id = list(img_map.keys())[0]
    print(f"   📝 ID 示例: {example_id} -> .../{os.path.basename(os.path.dirname(img_map[example_id]))}/rgb.png")

    # 2. 读取 CSV
    print("\n2. 读取营养素 CSV...")
    df = pd.read_csv(LABEL_FILE)
    print(f"   CSV 总行数: {len(df)}")

    # 3. 匹配
    print("\n3. 正在匹配 ID...")
    valid_data = []
    
    for _, row in df.iterrows():
        raw_id = str(row['dish_id'])
        
        # CSV 里的 ID 可能是 "1556572657"，也可能是 "dish_1556572657"
        possible_ids = [raw_id, f"dish_{raw_id}"]
        
        matched_path = None
        for pid in possible_ids:
            if pid in img_map:
                matched_path = img_map[pid]
                break
        
        if matched_path:
            valid_data.append({
                "image_path": matched_path,
                "calories": float(row['calories']),
                "carbs": float(row.get('total_carb') or row.get('carb') or 0),
                "protein": float(row.get('total_protein') or row.get('protein') or 0),
                "fat": float(row.get('total_fat') or row.get('fat') or 0)
            })

    # 4. 保存
    if valid_data:
        df_final = pd.DataFrame(valid_data)
        # 过滤异常值
        df_final = df_final[df_final['calories'] > 0]
        
        df_final.to_csv(OUTPUT_FILE, index=False)
        print("\n" + "="*60)
        print(f"🎉 清洗完成！")
        print(f"📂 结果保存: {OUTPUT_FILE}")
        print(f"✅ 成功匹配: {len(df_final)} / {len(df)}")
        print("="*60)
    else:
        print("❌ 匹配失败！")
        print("   调试建议：请检查 CSV 里的 dish_id 和文件夹名是否对应。")

if __name__ == "__main__":
    process_nutrition5k_nested()