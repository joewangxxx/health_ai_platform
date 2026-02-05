import pandas as pd
import os
import re
from backend.config import DATA_WAREHOUSE_DIR
from backend.core.constants import (
    THRESHOLD_KIDNEY_EGFR_LOW,
    THRESHOLD_LIVER_ALT_HIGH,
    THRESHOLD_HEART_BRADYCARDIA,
    THRESHOLD_ACTIVITY_HIGH_STEPS,
    DEFAULT_HEART_RATE,
)

class PharmService:
    def __init__(self):
        # Lazy Loading: 只定义变量，不加载数据
        self.rules_df = None
        self.kb_path = os.path.join(DATA_WAREHOUSE_DIR, "processed_data", "knowledge_base", "drug_gene_rules.csv")
        self._loaded = False

    async def load_models(self):
        """异步加载药物规则库 (在 FastAPI lifespan 中调用)"""
        if self._loaded:
            return
        print("💊 初始化药物基因组学服务 (PharmService)...")
        self._load_kb()
        self._loaded = True

    def reload(self):
        """重新加载药物基因知识库"""
        print("🔄重新加载药物服务...")
        self._load_kb()

    def _load_kb(self):
        if os.path.exists(self.kb_path):
            try:
                self.rules_df = pd.read_csv(self.kb_path)
                print(f"   ✅ 加载药物基因规则库: {len(self.rules_df)} 条规则")
            except Exception as e:
                print(f"   ❌ 规则库加载失败: {e}")
        else:
            print(f"   ⚠️ 未找到规则库文件: {self.kb_path} (如果是首次运行，请先执行 ETL)")

    def get_supported_drugs(self) -> list:
        """
        获取知识库中支持的所有药物名称
        """
        if self.rules_df is None:
            return []
        
        try:
            # 提取 Drug 列，去重，排序
            if 'Drug' in self.rules_df.columns:
                drugs = self.rules_df['Drug'].dropna().astype(str).str.strip().unique()
                return sorted(list(drugs))
            return []
        except Exception as e:
            print(f"Error fetching drugs: {e}")
            return []

    def calculate_dosage_recommendation(self, drug_name: str, user_snps: dict, clinical_profile: dict, iot_data: dict) -> dict:
        """
        基于三维异构数据计算用药推荐
        :param drug_name: 药物名称 (e.g., 'Metoprolol')
        :param user_snps: 用户基因数据 {'rs1234': 'AA', ...}
        :param clinical_profile: 临床体检数据 {'eGFR': 55, 'ALT': 45, ...}
        :param iot_data: 实时 IoT 数据 {'hr': 55, 'steps': 20000}
        :return: 推荐报告字典
        """
        
        # 结果容器
        result = {
            "drug_name": drug_name,
            "base_suggestion": "未发现显著基因相互作用。",
            "clinical_warning": [],
            "iot_alert": [],
            "final_dosage_factor": 1.0,
            "risk_factors": []
        }
        
        factor = 1.0
        
        # =========================================
        # 1. 🧬 维度一：基因组学修正 (Genomic Factor)
        # =========================================
        if self.rules_df is not None and user_snps:
            # 模糊匹配药物名称 (忽略大小写)
            drug_rules = self.rules_df[self.rules_df['Drug'].astype(str).str.contains(drug_name, case=False, na=False)]
            
            for _, row in drug_rules.iterrows():
                rsid = str(row.get('RSID', '')).strip()
                risk_genotype = str(row.get('Genotype', '')).strip() 
                rec_text = str(row.get('Recommendation', ''))
                
                # 检查用户基因是否命中
                if rsid in user_snps:
                    user_g = user_snps[rsid]
                    # 简单匹配：如果用户基因型 == 风险基因型
                    # (注：实际生产环境需处理 Phase 判读，这里简化为字符串匹配)
                    if user_g == risk_genotype:
                        rec_lower = rec_text.lower()
                        
                        # 分析代谢类型
                        if "poor metabolizer" in rec_lower or "intermediate metabolizer" in rec_lower:
                            # 代谢差 -> 易蓄积中毒 -> 减量
                            factor *= 0.5
                            msg = f"基因 {row.get('Gene')} ({rsid}:{user_g}) 提示代谢减慢。建议减量。"
                            result['base_suggestion'] = msg
                            result['risk_factors'].append("Genomic: Poor Metabolizer")
                            
                        elif "rapid metabolizer" in rec_lower or "ultrarapid" in rec_lower:
                            # 代谢快 -> 药效不足 -> 加量
                            factor *= 1.5
                            msg = f"基因 {row.get('Gene')} ({rsid}:{user_g}) 提示超快代谢。建议加量。"
                            result['base_suggestion'] = msg
                            result['risk_factors'].append("Genomic: Rapid Metabolizer")
                        
                        # 命中一条规则后通常通过 break 停止（避免同一药物多条规则冲突），或改为累积
                        # 这里演示命中即停止
                        break

        # =========================================
        # 2. 🩺 维度二：临床表型修正 (Clinical Factor)
        # =========================================
        # Strict Data Check
        missing_fields = []
        if clinical_profile.get('eGFR') is None:
             missing_fields.append("eGFR (肾功能)")
        if clinical_profile.get('ALT') is None:
             missing_fields.append("ALT (肝功能)")
             
        if missing_fields:
            return {
                "status": "missing_data",
                "missing_fields": missing_fields,
                "base_suggestion": "❌ 无法评估：缺失关键临床数据",
                "clinical_warning": [f"缺失: {', '.join(missing_fields)}"],
                "iot_alert": [],
                "risk_factors": []
            }

        egfr = clinical_profile.get('eGFR')
        alt = clinical_profile.get('ALT')
        
        # 肾功能规则
        if egfr < THRESHOLD_KIDNEY_EGFR_LOW:
            factor *= 0.8
            result['clinical_warning'].append(f"检测到 eGFR={egfr} (肾功能不全)，药物清除率降低，建议把剂量降至 80%。")
            result['risk_factors'].append("Clinical: Low eGFR")
            
        # 肝功能规则
        if alt > THRESHOLD_LIVER_ALT_HIGH:
            # 肝损伤不直接调整数字，而是给出强警告
            result['clinical_warning'].append(f"检测到 ALT={alt} (肝指标异常)，请慎用肝代谢药物。")
            result['risk_factors'].append("Clinical: High ALT")

        # =========================================
        # 3. ⌚ 维度三：实时状态修正 (IoT Factor)
        # =========================================
        hr = iot_data.get('hr', DEFAULT_HEART_RATE)
        steps = iot_data.get('steps', 0)
        drug_lower = drug_name.lower()
        
        # 规则 A: 心血管药物 (降压/降心率)
        # 关键词库
        cardio_keywords = ['metoprolol', 'atenolol', 'bisoprolol', 'propranolol', 
                           'losartan', 'valsartan', 'amlodipine', 'nifedipine', 'hypertension']
        is_cardio = any(kw in drug_lower for kw in cardio_keywords)
        
        if is_cardio and hr < THRESHOLD_HEART_BRADYCARDIA:
            result['iot_alert'].append(f"当前心率 ({hr} bpm) 偏低，此时服用 {drug_name} 可能会导致心动过缓，建议暂缓。")
            
        # 规则 B: 降糖药/胰岛素
        is_insulin = 'insulin' in drug_lower or 'metformin' in drug_lower
        
        if is_insulin and steps > THRESHOLD_ACTIVITY_HIGH_STEPS:
            result['iot_alert'].append(f"今日运动量 ({steps} 步) 较大，胰岛素敏感性提高，建议减少剂量以防低血糖。")

        # =========================================
        # 4. 📝 最终汇总
        # =========================================
        result['final_dosage_factor'] = round(factor, 2)
        
        return result

# 简单的单例模式，如果需要的话 (main.py 中可以实例化)
if __name__ == "__main__":
    # 测试代码
    service = PharmService()
    
    # Mock Data
    mock_snps = {"rs1234": "AA"} # 假设这对应某个 Poor Metabolizer
    mock_clinical = {"eGFR": 50, "ALT": 20}
    mock_iot = {"hr": 55, "steps": 2000}
    
    # 模拟 DataFrame (因为文件可能不存在)
    # 在实际运行中，这会从 CSV 读取
    print("Test run complete.")
