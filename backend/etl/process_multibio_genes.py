import pandas as pd
import numpy as np
import os

# ================= 🔧 配置区域 =================
# Task 107: 使用统一配置路径 (无需 sys.path 操作)
from backend.config import GENE_KB_DIR, DATA_WAREHOUSE_DIR

OUTPUT_DIR = GENE_KB_DIR

# T1D 文件 (注意: 这些路径指向外部原始数据目录)
# 如果数据已移动到 data_warehouse，请更新这些路径
RAW_DATA_ROOT = os.path.join(DATA_WAREHOUSE_DIR, "raw_data")
FILE_T1D = os.path.join(RAW_DATA_ROOT, "gene_source", "Type_1_Diabetes_Statistics", "GCST90018705_buildGRCh37.tsv")

# T2D 文件列表 (更新为 data_warehouse 路径)
FILES_T2D = [
    {
        "path": os.path.join(RAW_DATA_ROOT, "gene_source", "Type_2_Diabetes_Statistics", "GCST90018706_buildGRCh37.tsv"),
        "source_name": "Japan_GCST",
        "format": "std_tsv" 
    },
    {
        "path": os.path.join(RAW_DATA_ROOT, "gene_source", "Type_2_Diabetes_Statistics", "SpracklenCN_prePMID_T2D_ALL_Primary.txt"),
        "source_name": "China_Spracklen",
        "format": "china_txt"
    },
    {
        "path": os.path.join(RAW_DATA_ROOT, "gene_source", "Type_2_Diabetes_Statistics", "Type_2_Diabetes_Statistics_EastAsia.txt"),
        "source_name": "EastAsia_Meta",
        "format": "ea_txt"
    }
]

# ===============================================

def get_col_mapping(fmt_type):
    if fmt_type == "std_tsv":
        return {
            'variant_id': 'rsid',
            'p_value': 'p_value',
            'beta': 'weight',
            'effect_allele': 'risk_allele',
            'chromosome': 'chr',          # 新增：保留染色体
            'base_pair_location': 'pos'   # 新增：保留位置
        }
    elif fmt_type == "china_txt":
        return {
            'MarkerName': 'rsid',
            'P': 'p_value',
            'Beta': 'weight',
            'EA': 'risk_allele'
        }
    elif fmt_type == "ea_txt":
        return {
            'SNP': 'rsid',
            'P': 'p_value',
            'BETA': 'weight',
            'ALT': 'risk_allele'
        }
    return {}

def clean_gwas_data_chunked(file_config, disease_name):
    file_path = file_config if isinstance(file_config, str) else file_config['path']
    fmt = "std_tsv" if isinstance(file_config, str) else file_config.get('format', 'std_tsv')
    col_map = get_col_mapping(fmt)
    
    print(f"   🌊 开始处理: {os.path.basename(file_path)}")
    
    chunk_size = 100000 
    significant_rows = []
    
    try:
        sep = '\t' if file_path.endswith('.tsv') else None
        engine = 'c' if sep == '\t' else 'python'
        
        reader = pd.read_csv(
            file_path, 
            sep=sep, 
            engine=engine,
            usecols=col_map.keys(), 
            chunksize=chunk_size
        )
        
        for chunk in reader:
            # 1. 重命名
            chunk = chunk.rename(columns=col_map)
            
            # 2. 类型转换
            chunk['p_value'] = pd.to_numeric(chunk['p_value'], errors='coerce')
            chunk['weight'] = pd.to_numeric(chunk['weight'], errors='coerce')
            
            # --- 🔥 核心修复：处理缺失的 ID ---
            # 如果是标准格式文件，可能会有 chr 和 pos 列
            if 'rsid' in chunk.columns and 'chr' in chunk.columns and 'pos' in chunk.columns:
                # 填充逻辑：如果 rsid 是 NaN，用 "chr:pos" 填充
                # 例如: "1:751343"
                fallback_id = chunk['chr'].astype(str) + ':' + chunk['pos'].astype(str)
                chunk['rsid'] = chunk['rsid'].fillna(fallback_id)
            
            # 3. 筛选显著位点 (P < 5e-8)
            sig_chunk = chunk[chunk['p_value'] < 5e-8].copy()
            
            if not sig_chunk.empty:
                significant_rows.append(sig_chunk)
        
        # 合并结果
        if significant_rows:
            df_final = pd.concat(significant_rows)
            
            # 4. 只保留关键列 (现在 rsid 应该不为空了)
            # 注意：旧文件可能没有 risk_allele，如果报错需要检查
            cols_to_keep = ['rsid', 'p_value', 'weight', 'risk_allele']
            # 确保列都存在
            cols_to_keep = [c for c in cols_to_keep if c in df_final.columns]
            
            df_final = df_final[cols_to_keep]
            df_final['disease'] = disease_name
            
            # 🔥 最后的清洗：只删掉权重或P值为空的，不再删掉 rsid 为空的（因为我们填过了）
            df_final = df_final.dropna(subset=['p_value', 'weight'])
            
            print(f"      ✅ 提取成功: {len(df_final)} 个显著位点")
            return df_final
        else:
            print("      ⚠️ 未发现显著位点")
            return None
            
    except Exception as e:
        print(f"      ❌ 读取出错: {e}")
        return None

def process_all():
    print("=== 🚀 开始构建多病种基因知识库 (Fix: NaN ID) ===")
    
    # 1. T1D
    print("\n[1/2] 处理 T1D...")
    df_t1d = clean_gwas_data_chunked(FILE_T1D, "T1D")
    if df_t1d is not None:
        out_path = os.path.join(OUTPUT_DIR, "GWAS_T1D_weights.csv")
        df_t1d.to_csv(out_path, index=False)
        print(f"   💾 保存至: {out_path}")

    # 2. T2D
    print("\n[2/2] 处理 T2D (多源)...")
    t2d_dfs = []
    for file_config in FILES_T2D:
        df_temp = clean_gwas_data_chunked(file_config, "T2D")
        if df_temp is not None:
            t2d_dfs.append(df_temp)
    
    if t2d_dfs:
        print("   🔗 融合去重...")
        df_merged = pd.concat(t2d_dfs)
        df_merged = df_merged.sort_values(by='p_value', ascending=True)
        # 此时 rsid 可能是 "rs12345" 也可能是 "1:751343"
        df_unique = df_merged.drop_duplicates(subset=['rsid'], keep='first')
        
        out_path_t2d = os.path.join(OUTPUT_DIR, "GWAS_T2D_weights.csv")
        df_unique.to_csv(out_path_t2d, index=False)
        print(f"   💾 保存至: {out_path_t2d}")
        print(f"   📊 最终位点数: {len(df_unique)}")

if __name__ == "__main__":
    process_all()