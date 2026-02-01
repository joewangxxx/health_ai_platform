import pandas as pd
import os
import re

# ================= ⚙️ 配置区域 =================
# Task 107: 使用统一配置路径
from backend.config import DATA_WAREHOUSE_DIR

RAW_DIR = os.path.join(DATA_WAREHOUSE_DIR, "raw_data", "PharmGKB", "CLINICALANNOTATIONS")
OUTPUT_DIR = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "knowledge_base")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_ANNOTATIONS = os.path.join(RAW_DIR, "clinical_annotations.tsv")
FILE_ALLELES = os.path.join(RAW_DIR, "clinical_ann_alleles.tsv")

def process_pharmgkb_v3():
    print("=== 💊 PharmGKB ===")
    
    if not os.path.exists(FILE_ANNOTATIONS):
        print(f"❌ 找不到文件: {FILE_ANNOTATIONS}")
        return

    # 1. 读取主表
    print("   📖 读取 Annotations...")
    try:
        df_ann = pd.read_csv(FILE_ANNOTATIONS, sep='\t')
        # 🔥 修正列名：打印出来的列名里有 's'
        if 'Variant/Haplotypes' in df_ann.columns:
            df_ann = df_ann.rename(columns={'Variant/Haplotypes': 'Variant'})
        else:
            # 防御性编程：如果还是找不到，尝试模糊匹配
            col = [c for c in df_ann.columns if 'Variant' in c][0]
            df_ann = df_ann.rename(columns={col: 'Variant'})
            
        print(f"      原始记录: {len(df_ann)}")
    except Exception as e:
        print(f"      ❌ 读取失败: {e}")
        return

    # 2. 筛选高等级证据
    # 只要包含 1 或 2 (例如 "Level 1A", "1A", "2B")
    df_high = df_ann[df_ann['Level of Evidence'].astype(str).apply(lambda x: '1' in x or '2' in x)]
    print(f"      ✅ 高等级证据: {len(df_high)}")

    # 3. 读取 Alleles 表
    print("   📖 读取 Alleles...")
    try:
        df_alleles = pd.read_csv(FILE_ALLELES, sep='\t')
    except:
        print("      ❌ Alleles 表读取失败")
        return

    # 4. 合并
    print("   🔗 合并表...")
    merged = pd.merge(df_high, df_alleles, on='Clinical Annotation ID', how='inner')
    print(f"      合并后记录: {len(merged)}")

    # 5. 清洗规则
    print("   🧹 提取 rsID 和规则...")
    rules = []
    
    for _, row in merged.iterrows():
        try:
            # 提取 rsID (使用正则查找 rs+数字)
            variant_raw = str(row.get('Variant', ''))
            rs_match = re.search(r'(rs\d+)', variant_raw)
            
            # 如果不是 rsID (可能是 *2 这种星号等位基因)，暂时跳过
            # V4.0 Pro 阶段可以处理星号，但目前为了跑通流程，先只抓 rsID
            if not rs_match:
                continue
            
            rsid = rs_match.group(1)
            
            # 提取其他字段
            drugs = str(row.get('Drug(s)', '')).split(';')
            gene = str(row.get('Gene', 'Unknown'))
            genotype = str(row.get('Genotype/Allele', ''))
            annotation = str(row.get('Annotation Text', ''))
            level = str(row.get('Level of Evidence', ''))
            
            # 风险评级逻辑
            risk_level = "Info"
            text_lower = annotation.lower()
            if any(x in text_lower for x in ['toxicity', 'adverse', 'risk', 'poor', 'decreased']):
                risk_level = "Warning"
            if any(x in text_lower for x in ['avoid', 'contraindication', 'severe', 'do not']):
                risk_level = "Danger"

            for drug in drugs:
                d = drug.strip()
                if not d: continue
                
                rules.append({
                    "Drug": d,
                    "Gene": gene,
                    "RSID": rsid,
                    "Genotype": genotype,
                    "Risk_Level": risk_level,
                    "Recommendation": annotation[:300]
                })
        except:
            continue

    # 6. 保存
    if rules:
        df_rules = pd.DataFrame(rules).drop_duplicates()
        output_file = os.path.join(OUTPUT_DIR, "drug_gene_rules.csv")
        df_rules.to_csv(output_file, index=False)
        
        print("\n" + "="*60)
        print(f"🎉 成功生成药物基因库！")
        print(f"📂 保存至: {output_file}")
        print(f"💊 包含药物: {df_rules['Drug'].nunique()} 种")
        print(f"🧬 包含位点: {df_rules['RSID'].nunique()} 个")
        print(f"📜 总规则数: {len(df_rules)} 条")
        print("="*60)
    else:
        print("❌ 提取结果为空，请检查是否所有 rsID 都被过滤了。")

if __name__ == "__main__":
    process_pharmgkb_v3()