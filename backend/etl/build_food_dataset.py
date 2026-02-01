import pandas as pd
import os
import glob

# === 配置 ===
RAW_ROOT = r"C:\Users\王彬桥\Desktop\health_ai_platform\data_processing\raw_data\CGMacros_dateshifted365"
OUTPUT_INDEX = r"C:\Users\王彬桥\Desktop\health_ai_platform\data_processing\processed_data\food_image_labels.csv"

def build_image_index():
    print("📸 开始构建食物图像标签索引...")
    
    dataset = []
    
    # 1. 遍历所有用户的 CSV，提取饮食记录
    csv_files = glob.glob(os.path.join(RAW_ROOT, "CGMacros", "CGMacros-*", "CGMacros-*.csv"))
    
    for csv_path in csv_files:
        try:
            # 获取用户目录路径，照片就在这个 CSV 同级的 photos 文件夹里
            user_dir = os.path.dirname(csv_path)
            photos_dir = os.path.join(user_dir, "photos")
            
            if not os.path.exists(photos_dir):
                continue
                
            df = pd.read_csv(csv_path)
            
            # 筛选出有照片记录的行
            # 假设列名里有 'Image path' 或类似字段 (需要根据你之前的 check_columns 确认)
            # 根据你之前的反馈，列名是 'Image path' (注意空格)
            if 'Image path' not in df.columns:
                print(f"跳过 {os.path.basename(csv_path)}: 无 Image path 列")
                continue
                
            df_food = df.dropna(subset=['Image path'])
            
            for _, row in df_food.iterrows():
                img_name = row['Image path']
                carbs = row.get('Carbs', 0)
                calories = row.get('Calories', 0)
                
                # 这是一个坑：CSV 里的文件名可能带有路径，我们需要清洗
                # 比如 "photos/abc.jpg" -> "abc.jpg"
                img_name = os.path.basename(img_name)
                
                full_img_path = os.path.join(photos_dir, img_name)
                
                # 确认文件真的存在
                if os.path.exists(full_img_path):
                    dataset.append({
                        'image_path': full_img_path,
                        'carbs': carbs,
                        'calories': calories
                    })
                    
        except Exception as e:
            print(f"处理出错: {e}")

    # 2. 保存索引表
    df_result = pd.DataFrame(dataset)
    print(f"✅ 索引构建完成！共找到 {len(df_result)} 张有效训练图片。")
    
    if len(df_result) > 0:
        df_result.to_csv(OUTPUT_INDEX, index=False)
        print(f"📂 已保存至: {OUTPUT_INDEX}")
        print(df_result.head())
    else:
        print("❌ 未找到任何匹配的图片，请检查路径结构！")

if __name__ == "__main__":
    build_image_index()