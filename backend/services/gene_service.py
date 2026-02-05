import pandas as pd
import numpy as np
import os
import glob
from backend.config import GENE_KB_DIR

# 指向真实数据清洗后的文件夹
BASE_DIR = GENE_KB_DIR

class GeneRiskEngine:
    def __init__(self):
        # Lazy Loading: 只定义变量，不加载数据
        self.disease_models = {}
        self._loaded = False

    async def load_models(self):
        """异步加载基因库 (在 FastAPI lifespan 中调用)"""
        if self._loaded:
            return
        print("🧬 初始化全病种基因引擎 (Real GWAS Data)...")
        
        # 自动扫描所有 GWAS_*.csv
        files = glob.glob(os.path.join(BASE_DIR, "GWAS_*_weights.csv"))
        
        if not files:
            print(f"   ❌ 警告: 在 {BASE_DIR} 未找到基因库文件！")
        
        for path in files:
            filename = os.path.basename(path)
            # 文件名: GWAS_T2D_weights.csv -> 病种: T2D
            disease_name = filename.replace("GWAS_", "").replace("_weights.csv", "")
            
            try:
                df = pd.read_csv(path)
                # 建立哈希字典
                model_dict = df.set_index('rsid')[['weight', 'risk_allele']].to_dict('index')
                
                # 计算理论最大风险分 (Top 10% 强效位点总和作为分母，防止分母过大导致分数太小)
                # 这里优化一下算法：只取权重最大的前50个位点作为归一化基准
                top_weights = sorted([abs(v['weight']) for v in model_dict.values()], reverse=True)[:50]
                max_score = sum(top_weights) * 2
                
                self.disease_models[disease_name] = {
                    "data": model_dict,
                    "max_score": max_score
                }
            except Exception as e:
                print(f"   ⚠️ 加载失败 {disease_name}: {e}")
                
        print(f"   ✅ 共加载 {len(self.disease_models)} 个基因模型")
        self._loaded = True

    def reload(self):
        """重新加载基因库 (Hot Reload)"""
        print("🔄重新加载全病种基因引擎...")
        self.__init__()

    def parse_23andme_txt(self, content: str):
        """解析 23andMe 原始文本数据，返回字典用于计算 + 列表用于预览"""
        snps_dict = {}
        preview_list = []
        # 兼容 Windows/Linux 换行符
        lines = content.replace('\r\n', '\n').split('\n')
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'): continue
            
            # 支持 tab 或 空格 分隔
            parts = line.split('\t') if '\t' in line else line.split()
            
            # 23andMe 格式: rsid, chr, pos, genotype
            if len(parts) >= 4:
                rsid = parts[0].strip()
                chrom = parts[1].strip()
                pos = parts[2].strip()
                genotype = parts[3].strip()
                snps_dict[rsid] = genotype
                preview_list.append({
                    "rsid": rsid,
                    "chrom": chrom,
                    "pos": pos,
                    "genotype": genotype
                })
        return {"snps_dict": snps_dict, "preview_list": preview_list}

    def calculate_risk_from_file(self, user_genotypes):
        report = {}
        
        for disease, model in self.disease_models.items():
            kb_data = model["data"]
            max_score = model["max_score"]
            raw_score = 0.0
            
            # 遍历用户基因
            for rsid, user_geno in user_genotypes.items():
                if rsid in kb_data:
                    info = kb_data[rsid]
                    # 计算风险基因数量
                    dosage = str(user_geno).upper().count(str(info['risk_allele']))
                    if dosage > 0:
                        raw_score += info['weight'] * dosage
            
            # 归一化
            final_score = 0
            if max_score > 0:
                final_score = (raw_score / max_score) * 100
                final_score = min(100, max(0, final_score))
            
            report[disease] = {
                "score": round(final_score, 1)
            }
            
        return report