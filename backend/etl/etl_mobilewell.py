import pandas as pd
import numpy as np
import os

# ================= ⚙️ 配置区域 =================
# Task 107: 使用统一配置路径
from backend.config import DATA_WAREHOUSE_DIR

RAW_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "MobileWell400")
OUTPUT_FILE = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "lifestyle_training_data.csv")

# ===============================================

def process_mobilewell():
    print("=== ⌚ 开始 MobileWell 行为数据清洗 ===")
    
    act_file = os.path.join(RAW_DIR, "activity_recognition.csv")
    if not os.path.exists(act_file):
        print(f"❌ 找不到文件: {act_file}")
        return

    # 分块读取，防止内存爆炸
    chunk_size = 500000
    reader = pd.read_csv(act_file, chunksize=chunk_size)
    
    daily_stats = []
    
    print("   ⏳ 正在聚合传感器数据 (可能需要几分钟)...")
    
    for i, chunk in enumerate(reader):
        if i % 10 == 0: print(f"      处理第 {i} 块...")
        
        # 转换时间
        chunk['timestamp'] = pd.to_datetime(chunk['timestamp'])
        chunk['date'] = chunk['timestamp'].dt.date
        
        # 标签清洗 (假设标签列叫 'label')
        # 常见的标签: 'STILL', 'WALKING', 'RUNNING', 'ON_BICYCLE', 'IN_VEHICLE'
        if 'label' in chunk.columns:
            # 统计每种状态的次数 (假设每次记录代表几秒钟)
            # 我们只关心: 动 (Active) vs 不动 (Sedentary)
            chunk['is_active'] = chunk['label'].astype(str).str.upper().apply(
                lambda x: 1 if any(s in x for s in ['WALK', 'RUN', 'BICYCLE', 'FOOT']) else 0
            )
            
            # 按人、天聚合
            # count = 总记录数 (代表佩戴时长)
            # sum = 活跃记录数
            grouped = chunk.groupby(['participant', 'date'])['is_active'].agg(['count', 'sum']).reset_index()
            daily_stats.append(grouped)
            
    # 合并所有块
    print("   🔗 合并结果...")
    full_df = pd.concat(daily_stats)
    
    # 再次聚合 (因为分块可能把同一天切开了)
    final_df = full_df.groupby(['participant', 'date']).sum().reset_index()
    
    # 计算特征
    # Active_Ratio: 活跃时间占比
    # Total_Logs: 数据量 (用来过滤佩戴时间太短的天)
    final_df['Active_Ratio'] = final_df['sum'] / final_df['count']
    
    # 过滤掉数据量太少的天 (比如一天只记录了10次)
    final_df = final_df[final_df['count'] > 100]
    
    # 打标签 (Mock Label)
    # 因为 MobileWell 没有“是否患病”的标签，我们需要基于医学常识生成一个“生活方式风险分”
    # 逻辑：活跃度 < 5% -> 高风险(1); 活跃度 > 15% -> 低风险(0)
    # 这将作为我们要训练的目标
    threshold_low = final_df['Active_Ratio'].quantile(0.3) # 后30%的人是不健康的
    final_df['Lifestyle_Risk'] = (final_df['Active_Ratio'] < threshold_low).astype(int)
    
    print(f"   📊 提取到 {len(final_df)} 天的有效行为数据")
    print(f"   🏃 平均活跃度: {final_df['Active_Ratio'].mean():.2%}")
    
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ 保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    process_mobilewell()