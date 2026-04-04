from backend.services.lifestyle_service import LifestyleService
import re
from backend.core.constants import (
    FUSION_RISK_VERY_HIGH,
    FUSION_RISK_HIGH,
    FUSION_RISK_MEDIUM,
    GENE_MODIFIER_POTENTIAL_RISK,
    GENE_MODIFIER_BASE,
    GENE_MODIFIER_RANGE,
)

class FusionRiskEngine:
    def __init__(self, risk_engine=None, gene_engine=None):
        """
        初始化融合引擎
        :param risk_engine: 已加载的 LightGBM 临床风险引擎 (Optional)
        :param gene_engine: 已加载的 GWAS 基因引擎 (Optional)
        """
        print("🔗 初始化多模态融合引擎 (Fusion Engine)...")
        
        # Lazy Loading to avoid circular dependency
        if risk_engine is None:
            from backend.services.risk_engine import DiseaseRiskEngine
            self.risk_engine = DiseaseRiskEngine()
        else:
            self.risk_engine = risk_engine

        if gene_engine is None:
            from backend.services.gene_service import GeneRiskEngine
            self.gene_engine = GeneRiskEngine()
        else:
            self.gene_engine = gene_engine
        self.lifestyle_service = LifestyleService() # 内部实例化生活方式引擎
        
        # 疾病名称映射表 (NHANES 简称 -> GWAS 文件关键词)
        # 作用：让两个不同来源的数据库能对话
        self.name_mapping = {
            "T2D": ["T2D", "Diabetes"],
            "Hypertension": ["Hypertension", "SystolicBP", "BloodPressure"],
            "HighLipid": ["HighCholesterol", "HighLipid", "Lipid"],
            "Obesity": ["Obesity", "BMI"],
            "Gout": ["Gout", "UricAcid"],
            "CKD": ["CKD", "Kidney"],
            "CoronaryHeart": ["Coronary"],
            "Stroke": ["Stroke"],
            "Osteoporosis": ["Osteoporosis", "BoneDensity"],
            "Depression": ["Depression"],
            "Asthma": ["Asthma"],
            "Arthritis": ["Rheumatoid", "Arthritis"],
            "Anemia": ["Hemoglobin", "Anemia"],
            "HeartFailure": ["HeartFailure"],
            "LiverDisease": ["Liver", "ALT"],
            "KidneyStones": ["KidneyStone", "Urolithiasis"]
        }

    def _get_gene_modifier(self, disease_name, gene_report):
        """
        内部函数：计算基因风险修正系数
        输入：病名, 基因报告
        输出：系数 (0.8 - 1.5)
        """
        if not gene_report:
            return 1.0
            
        target_score = None
        
        # 1. 尝试直接匹配
        if disease_name in gene_report:
            target_score = gene_report[disease_name]['score']
            
        # 2. 尝试模糊映射匹配
        else:
            keywords = self.name_mapping.get(disease_name, [])
            for key_in_report in gene_report.keys():
                for kw in keywords:
                    if kw.lower() in key_in_report.lower():
                        target_score = gene_report[key_in_report]['score']
                        break
                if target_score is not None: break
        
        # 3. 如果没找到对应的基因数据，系数为 1.0 (不影响)
        if target_score is None:
            return 1.0
            
        # 4. 将分数 (0-100) 转换为系数 (Odds Ratio 模拟)
        # 0分 -> 0.8倍 (基因保护)
        # 20分 -> 1.0倍 (平均水平)
        # 50分 -> 1.2倍
        # 100分 -> 1.5倍 (高危遗传)
        modifier = GENE_MODIFIER_BASE + (target_score / 100.0) * GENE_MODIFIER_RANGE
        return round(modifier, 2)

    def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
        """
        🔥 核心融合逻辑
        1. 临床模型 -> 基准概率
        2. 基因引擎 -> 遗传系数
        3. IoT引擎 -> 行为系数
        4. 结果 = 基准 * 遗传 * 行为
        """
        # 1. 获取临床基准风险 (Base Risk)
        # 返回格式: {'T2D': {'probability': 20.5, 'level': 'Low'}, ...}
        clinical_report = self.risk_engine.assess_health(clinical_profile)
        
        if "error" in clinical_report:
            return clinical_report

        # 2. 获取全量基因报告 (如果提供了 SNP)
        gene_report = {}
        if user_snps:
            gene_report = self.gene_engine.calculate_risk_from_file(user_snps)
            
        final_report = {}
        
        # 3. 遍历每一种病进行融合
        for disease, info in clinical_report.items():
            # 获取基准概率 (0-100)
            base_prob = info.get('probability', 0)
            
            # 获取基因系数
            gene_mod = self._get_gene_modifier(disease, gene_report)
            
            # 获取生活方式系数
            # (IoT 引擎会自动根据病种类别判断敏感度)
            # 例如：心血管病对步数非常敏感，骨质疏松对运动也敏感
            life_mod = self.lifestyle_service.calculate_modifier(iot_data)
            
            # 🔥 贝叶斯融合公式
            final_prob = base_prob * gene_mod * life_mod
            
            # 边界截断 (0.1% - 99.9%)
            final_prob = min(99.9, max(0.1, final_prob))
            
            # 重新评级 (根据融合后的分数)
            # 🔥 优化：引入“潜在遗传风险”兜底逻辑
            # 如果基因风险显著 (>=1.2) 但最终得分依然不高 (<=20)，强制标记为 Potential
            if gene_mod >= GENE_MODIFIER_POTENTIAL_RISK and final_prob <= FUSION_RISK_MEDIUM:
                level = "潜在遗传风险 (Potential)"
            elif final_prob > FUSION_RISK_VERY_HIGH: level = "极高 (Very High)"
            elif final_prob > FUSION_RISK_HIGH: level = "高 (High)"
            elif final_prob > FUSION_RISK_MEDIUM: level = "中 (Medium)"
            else: level = "低 (Low)"
            
            # 构造输出
            final_report[disease] = {
                "final_risk": round(final_prob, 1),
                "level": level,
                "breakdown": {
                    "base_clinical": f"{base_prob}%",
                    "gene_modifier": f"x{gene_mod}",
                    "lifestyle_modifier": f"x{life_mod}"
                }
            }
            
        return final_report

    async def update_realtime_risk(self, user_profile, latest_hr: float):
        """
        实时贝叶斯风险更新 (IoT Triggered)
        P(Risk|Data) ∝ γ · P(Risk)

        流程：
        1. 根据心率 + BMI 确定贝叶斯因子 γ
        2. 调用 calculate_composite_risk 获取当前静态先验 P_t
        3. 对每种疾病施加 P_{t+1} = clip(γ · P_t) 并重新分级
        """
        print(f"⚡ [Fusion] Triggered Real-time Update for HR: {latest_hr} bpm")

        # 1. 基础参数
        bmi = user_profile.BMI if user_profile and user_profile.BMI else 24.0

        # 2. 事件分级 → 贝叶斯因子 γ
        gamma = 1.0
        risk_event = "Normal"

        if latest_hr > 100:
            if bmi > 28:
                gamma = 1.8
                risk_event = "High HR + Obesity"
            else:
                gamma = 1.3
                risk_event = "High HR"
        elif latest_hr < 50:
            gamma = 1.2
            risk_event = "Bradycardia"

        # 若心率正常，无需更新，直接返回
        if gamma == 1.0:
            return {
                "event": risk_event,
                "hr_read": latest_hr,
                "bayes_factor": gamma,
                "updated": False,
                "message": "心率正常，无需实时更新"
            }

        # 3. 获取当前静态先验 P_t (调用 calculate_composite_risk)
        import json
        from backend.config import DEFAULT_DEVICE_STATE

        clinical_data = user_profile.model_dump() if user_profile else {}
        user_snps = {}
        if user_profile and user_profile.genomic_data:
            try:
                user_snps = json.loads(user_profile.genomic_data)
            except Exception:
                pass

        prior_report = self.calculate_composite_risk(
            clinical_profile=clinical_data,
            user_snps=user_snps,
            iot_data=DEFAULT_DEVICE_STATE
        )

        if not prior_report or "error" in prior_report:
            return {
                "event": risk_event,
                "hr_read": latest_hr,
                "bayes_factor": gamma,
                "updated": False,
                "message": "无法获取先验风险，跳过实时更新"
            }

        # 4. 施加贝叶斯更新：P_{t+1} = clip(γ · P_t, 0.1, 99.9)
        updated_report = {}
        for disease, info in prior_report.items():
            prior_risk = info.get("final_risk", 0)
            posterior_risk = min(99.9, max(0.1, prior_risk * gamma))

            # 重新分级
            if posterior_risk > FUSION_RISK_VERY_HIGH:
                level = "极高 (Very High)"
            elif posterior_risk > FUSION_RISK_HIGH:
                level = "高 (High)"
            elif posterior_risk > FUSION_RISK_MEDIUM:
                level = "中 (Medium)"
            else:
                level = "低 (Low)"

            updated_report[disease] = {
                "prior_risk": round(prior_risk, 1),
                "posterior_risk": round(posterior_risk, 1),
                "level": level,
                "gamma_applied": gamma,
            }

        return {
            "event": risk_event,
            "hr_read": latest_hr,
            "bmi": bmi,
            "bayes_factor": gamma,
            "updated": True,
            "updated_report": updated_report,
            "message": f"实时贝叶斯更新完成：γ={gamma}，触发事件={risk_event}"
        }