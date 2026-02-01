import pandas as pd
import numpy as np
import os
import glob
import warnings

warnings.filterwarnings("ignore")

# Task 107: 使用统一配置路径
from backend.config import DATA_WAREHOUSE_DIR

INPUT_ROOT = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "gene_source")
OUTPUT_DIR = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "knowledge_base")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COL_VARIANTS = {
    'rsid': ['rsid', 'variant_id', 'snp', 'markername', 'marker', 'snpid', 'variant', 'hm_rsid', 'id'],
    'p_value': ['p_value', 'pval', 'p', 'p-value', 'p.value', 'p_val', 'frequentist_add_pvalue', 'scan_p_value_clean'],
    'weight': ['beta', 'log_odds', 'effect_weight', 'or', 'odds_ratio', 'effect_size', 'b', 'hm_beta', 'frequentist_add_beta_1'],
    'risk_allele': ['effect_allele', 'risk_allele', 'a1', 'ea', 'alt', 'allele1', 'allele2', 'a_1', 'hm_effect_allele'],
    # 🔥 新增坐标列识别
    'chr': ['chromosome', 'chr', 'chrom'],
    'pos': ['base_pair_location', 'pos', 'bp', 'position']
}

def guess_column(df_cols, target_key):
    df_cols_lower = [str(c).lower().strip().replace(' ', '_') for c in df_cols]
    for cand in COL_VARIANTS[target_key]:
        if cand in df_cols_lower:
            return df_cols[df_cols_lower.index(cand)]
    return None

def process_single_file(filepath):
    filename = os.path.basename(filepath)
    print(f"      📄 扫描: {filename} ...", end="")
    
    try:
        if filename.endswith('.csv'): sep = ','
        else: sep = '\t'

        chunk_size = 100000
        reader = pd.read_csv(filepath, sep=sep, chunksize=chunk_size, engine='python')
        
        try:
            first_chunk = next(reader)
        except StopIteration:
            print(" ❌ 空文件")
            return None

        col_map = {}
        missing = []
        
        # 1. 尝试找 rsid
        rsid_col = guess_column(first_chunk.columns, 'rsid')
        if rsid_col:
            col_map[rsid_col] = 'rsid'
        else:
            # 🔥 如果没 rsid，尝试找 chr 和 pos
            chr_col = guess_column(first_chunk.columns, 'chr')
            pos_col = guess_column(first_chunk.columns, 'pos')
            if chr_col and pos_col:
                col_map[chr_col] = 'chr'
                col_map[pos_col] = 'pos'
            else:
                missing.append('rsid/chr+pos')

        # 2. 找其他列
        for key in ['p_value', 'weight', 'risk_allele']:
            found = guess_column(first_chunk.columns, key)
            if found:
                col_map[found] = key
            else:
                missing.append(key)
        
        if missing:
            print(f" ⚠️ 缺关键列: {missing}")
            return None
            
        is_or = False
        for original_col in col_map.keys():
            if 'or' in str(original_col).lower() or 'odds' in str(original_col).lower():
                is_or = True

        # --- 处理函数 ---
        valid_chunks = []
        
        def process(chunk):
            chunk = chunk.rename(columns=col_map)
            
            # 🔥 核心修复：如果没有 rsid，用 chr:pos 填充
            if 'rsid' not in chunk.columns:
                if 'chr' in chunk.columns and 'pos' in chunk.columns:
                    chunk['rsid'] = chunk['chr'].astype(str) + ':' + chunk['pos'].astype(str)
                else:
                    return pd.DataFrame() # 没救了
            
            chunk['p_value'] = pd.to_numeric(chunk['p_value'], errors='coerce')
            chunk['weight'] = pd.to_numeric(chunk['weight'], errors='coerce')
            
            sig = chunk[chunk['p_value'] < 1e-5].copy()
            
            if is_or and not sig.empty:
                sig = sig[sig['weight'] > 0]
                sig['weight'] = np.log(sig['weight'])
            
            # 必须要有 rsid, p, weight, allele
            if 'rsid' in sig.columns and 'risk_allele' in sig.columns:
                return sig[['rsid', 'p_value', 'weight', 'risk_allele']]
            return pd.DataFrame()

        # 处理第一块
        processed_first = process(first_chunk)
        if not processed_first.empty: valid_chunks.append(processed_first)
        
        # 处理后续
        for chunk in reader:
            processed = process(chunk)
            if not processed.empty: valid_chunks.append(processed)
            
        if valid_chunks:
            df = pd.concat(valid_chunks)
            print(f" ✅ 提取 {len(df)} 行 (ID修复模式)" if not rsid_col else f" ✅ 提取 {len(df)} 行")
            return df
        else:
            print(" ⚠️ 无显著位点")
            return None

    except Exception as e:
        print(f" ❌ 错误: {str(e)[:50]}")
        return None

def process_folders():
    print("=== 🚀 GWAS 终极清洗脚本 V3.0 (ID Fix) ===")
    subfolders = [f.path for f in os.scandir(INPUT_ROOT) if f.is_dir()]
    success_count = 0
    
    for folder in subfolders:
        disease_name = os.path.basename(folder)
        print(f"\n🌊 处理病种: [{disease_name}]")
        files = glob.glob(os.path.join(folder, "*"))
        disease_dfs = []
        
        for f in files:
            df = process_single_file(f)
            if df is not None:
                disease_dfs.append(df)
        
        if disease_dfs:
            print(f"   🔗 正在融合...", end="")
            merged_df = pd.concat(disease_dfs)
            merged_df = merged_df.sort_values(by='p_value', ascending=True)
            unique_df = merged_df.drop_duplicates(subset=['rsid'], keep='first')
            
            out_name = f"GWAS_{disease_name}_weights.csv"
            out_path = os.path.join(OUTPUT_DIR, out_name)
            unique_df.to_csv(out_path, index=False)
            
            print(f" ✅ 保存: {out_name} ({len(unique_df)} 位点)")
            success_count += 1
        else:
            print(f"   ❌ {disease_name} 暂无数据")

    print(f"\n🎉 处理完毕！成功: {success_count}/{len(subfolders)}")

if __name__ == "__main__":
    process_folders()