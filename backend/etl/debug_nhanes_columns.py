import pandas as pd
import os

# ================= ⚙️ 配置区域 =================
# Task 107: 使用统一配置路径
from backend.config import DATA_WAREHOUSE_DIR

RAW_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "NHANES")

def check_all_files():
    print(f"=== 🔍 开始对 {RAW_DIR} 进行全量体检 ===")
    
    # 1. 获取目录下所有文件
    all_files = [f for f in os.listdir(RAW_DIR) if f.upper().endswith(".XPT")]
    
    print(f"📂 共发现 {len(all_files)} 个 XPT 文件\n")
    
    success_count = 0
    fail_count = 0
    
    # 2. 逐个检查
    for filename in all_files:
        filepath = os.path.join(RAW_DIR, filename)
        
        try:
            # 读取
            df = pd.read_sas(filepath, format='xport')
            
            # 检查关键指标
            has_seqn = 'SEQN' in df.columns
            row_count = len(df)
            col_count = len(df.columns)
            
            # 检查 SEQN 类型 (关键！合并失败的罪魁祸首通常在这里)
            seqn_type = "❌ 无"
            if has_seqn:
                seqn_type = df['SEQN'].dtype
            
            # 打印报告
            status = "✅" if has_seqn and row_count > 0 else "❌"
            print(f"{status} [{filename:<15}] 行数: {row_count:<6} | 列数: {col_count:<4} | SEQN类型: {seqn_type}")
            
            if has_seqn: success_count += 1
            else: fail_count += 1
            
        except Exception as e:
            print(f"❌ [{filename:<15}] 读取崩溃: {e}")
            fail_count += 1

    print("-" * 50)
    print(f"📊 总结: 成功 {success_count} 个 / 失败 {fail_count} 个")
    print("👉 重点观察：所有文件的 SEQN 类型是否一致？(全是 float64 或全是 int64)")

if __name__ == "__main__":
    check_all_files()