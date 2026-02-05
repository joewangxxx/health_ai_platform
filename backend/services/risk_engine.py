"""
Disease Risk Engine (疾病风险评估引擎)
======================================

基于 LightGBM 模型集群的全科疾病风险评估引擎。

功能:
- 30+ 种慢性病的风险概率评估 (assess_health)
- AHA 2023 CKM 综合征分期评估 (assess_ckm_stage)
- 糖尿病泌尿系统并发症评估 (assess_diabetic_urology)

依赖:
- 预训练的 LightGBM 模型 (models/risk_models.joblib)
- 特征映射表 (features_map)

Author: Health AI Platform Team
"""
import joblib
import pandas as pd
import numpy as np
import os
import re
from backend.config import RISK_MODEL_PATH
from backend.core.constants import (
    RISK_PROB_VERY_HIGH,
    RISK_PROB_HIGH,
    RISK_PROB_MEDIUM,
    get_field_chinese_name,
    get_disease_chinese_name,
)

# TODO: Update AI Model to use V10 features (WBC, GGT, ALP, Platelet, Creatinine)
# Currently, these fields are passed through to assess_health() but only used
# if present in features_map (determined by model training configuration).
# To enable V10 features: retrain models in ai_core/train_risk_models.py with new features.


class DiseaseRiskEngine:
    """
    全科疾病风险评估引擎
    
    基于机器学习模型的多疾病风险评估系统，支持：
    - 加载和热重载预训练模型
    - 多疾病并行预测
    - 中文风险因子归因分析 (Task 94)
    - CKM 综合征分期 (Task 95)
    
    Attributes:
        models (dict): 疾病名 -> LightGBM 模型的映射
        features_map (dict): 疾病名 -> 所需特征列表的映射
        
    Example:
        >>> engine = DiseaseRiskEngine()
        >>> await engine.load_models()
        >>> result = engine.assess_health({"BMI": 28, "Age": 45, "SBP": 140})
        >>> print(result["T2D"]["probability"])  # 糖尿病风险概率
    """
    def __init__(self):
        # Lazy Loading: 只定义变量，不加载模型
        self.models = {}
        self.features_map = {}
        self.bundle = None
        self._loaded = False

    async def load_models(self):
        """异步加载模型 (在 FastAPI lifespan 中调用)"""
        if self._loaded:
            return
        print("🏥 初始化全科疾病风险引擎 (LightGBM Cluster)...")
        if os.path.exists(RISK_MODEL_PATH):
            self.bundle = joblib.load(RISK_MODEL_PATH)
            self.models = self.bundle["models"]
            self.features_map = self.bundle.get("features_map", {})
            print(f"   ✅ 加载成功: 支持 {len(self.models)} 种疾病评估")
        else:
            print("   ❌ 警告: 未找到模型文件！")
        self._loaded = True

    def reload(self):
        """重新加载模型文件 (Hot Reload)"""
        print("🔄重新加载全科疾病风险引擎...")
        self.__init__()

    def _clean_keys(self, data_dict):
        """清洗输入字典的 Key,使其与训练时的特征名一致"""
        new_dict = {}
        for k, v in data_dict.items():
            # 替换非字母数字下划线为 _
            clean_k = re.sub(r'[^A-Za-z0-9_]+', '_', str(k))
            new_dict[clean_k] = v
        return new_dict

    def _get_top_risk_factors(self, model, features: list, input_df: pd.DataFrame, top_n: int = 5) -> list:
        """
        Task 94: 获取对预测贡献最大的 Top N 风险因子 (中文)
        基于特征重要性 * 特征值的归一化分数。
        """
        try:
            importances = model.feature_importances_
            input_values = input_df.iloc[0].values
            
            # 计算每个特征的贡献分数 (重要性 * 归一化值)
            contributions = []
            for i, (feat, imp) in enumerate(zip(features, importances)):
                val = input_values[i]
                if pd.isna(val):
                    continue
                # 简化贡献计算：使用特征重要性作为基础
                contributions.append({
                    "feature": feat,
                    "importance": float(imp),
                    "value": float(val) if not pd.isna(val) else None
                })
            
            # 按重要性排序，取 Top N
            contributions.sort(key=lambda x: x["importance"], reverse=True)
            top_factors = contributions[:top_n]
            
            # 转换为中文输出格式
            result = []
            for item in top_factors:
                chinese_name = get_field_chinese_name(item["feature"])
                # 根据重要性判断影响等级
                if item["importance"] > 100:
                    impact = "高 (High)"
                elif item["importance"] > 50:
                    impact = "中 (Medium)"
                else:
                    impact = "低 (Low)"
                
                result.append({
                    "factor": chinese_name,
                    "impact": impact,
                    "contribution": round(item["importance"] / 100, 3),  # 归一化到 0-1
                    "value": item["value"]
                })
            
            return result
        except Exception as e:
            print(f"⚠️ 风险因子分析失败: {e}")
            return []

    def assess_health(self, user_profile: dict, include_breakdown: bool = True):
        """
        评估用户健康风险。
        Task 94: 支持中文归因解释。
        
        Args:
            user_profile: 用户健康数据字典
            include_breakdown: 是否包含风险因子分解
        
        Returns:
            dict: 包含每种疾病的风险概率、等级和中文归因
        """
        if not self.models: 
            return {"error": "模型未加载"}

        report = {}
        
        # 🔥 关键步骤：清洗用户输入的 Key
        clean_profile = self._clean_keys(user_profile)
        
        # 转换为 DataFrame
        input_df_raw = pd.DataFrame([clean_profile])

        for disease, model in self.models.items():
            try:
                # 获取该模型需要的特征
                required_feats = self.features_map.get(disease, [])
                
                # 构造输入，缺失补NaN
                input_df = pd.DataFrame()
                for feat in required_feats:
                    input_df[feat] = input_df_raw.get(feat, np.nan)
                
                # 预测
                prob = model.predict_proba(input_df)[0][1]
                prob_percent = round(prob * 100, 1)
                
                if prob > RISK_PROB_VERY_HIGH: level = "极高 (Very High)"
                elif prob > RISK_PROB_HIGH: level = "高 (High)"
                elif prob > RISK_PROB_MEDIUM: level = "中 (Medium)"
                else: level = "低 (Low)"
                
                # 构建结果
                result = {
                    "probability": prob_percent,
                    "level": level,
                    "disease_cn": get_disease_chinese_name(disease),  # 中文疾病名
                }
                
                # Task 94: 添加中文风险因子归因
                if include_breakdown and prob > 0.2:  # 只对有意义的风险进行分解
                    top_risks = self._get_top_risk_factors(model, required_feats, input_df)
                    result["top_risks"] = top_risks
                
                report[disease] = result
                
            except Exception as e:
                report[disease] = {
                    "probability": 0, 
                    "level": "Unknown", 
                    "disease_cn": get_disease_chinese_name(disease),
                    "error": str(e)
                }
            
        return report

    def assess_ckm_stage(self, user_profile: dict) -> dict:
        """
        Task 95: AHA 2023 CKM (Cardiovascular-Kidney-Metabolic) 综合征分期评估。
        基于规则的判定，不需要 ML 模型。
        
        Args:
            user_profile: 用户健康数据字典，包含 BMI, HbA1c, Glucose_Fasting, SBP, DBP, 
                         Triglycerides, Cholesterol_HDL, eGFR, UACR, Gender 等
        
        Returns:
            dict: 包含分期、分期名称、命中条件和建议
        """
        # ============= 1. 数据提取与预处理 =============
        bmi = user_profile.get("BMI")
        waist = user_profile.get("WaistCircum")
        hba1c = user_profile.get("HbA1c")
        glucose = user_profile.get("Glucose_Fasting")
        sbp = user_profile.get("SBP")
        dbp = user_profile.get("DBP")
        tg = user_profile.get("Triglycerides")
        hdl = user_profile.get("Cholesterol_HDL")
        egfr = user_profile.get("eGFR", 90)  # 默认正常
        uacr = user_profile.get("UACR", 0)    # 默认正常
        gender = user_profile.get("Gender", 1)  # 1=男, 2=女
        
        # CVD 病史 (从 risk_history 或直接字段获取)
        cvd_history = user_profile.get("CVD_History", False)
        if not cvd_history:
            # 尝试从其他字段推断
            cvd_history = any([
                user_profile.get("Stroke", False),
                user_profile.get("Heart_Attack", False),
                user_profile.get("Heart_Failure", False),
                user_profile.get("Coronary_Heart", False),
            ])
        
        # ============= 2. 状态判定 =============
        criteria_met = []
        
        # 糖尿病状态
        is_diabetic = False
        is_prediabetic = False
        if hba1c is not None:
            if hba1c >= 6.5:
                is_diabetic = True
                criteria_met.append("糖尿病 (HbA1c ≥ 6.5%)")
            elif hba1c >= 5.7:
                is_prediabetic = True
                criteria_met.append("糖耐量受损 (5.7% ≤ HbA1c < 6.5%)")
        elif glucose is not None:
            if glucose >= 7.0:
                is_diabetic = True
                criteria_met.append("糖尿病 (空腹血糖 ≥ 7.0 mmol/L)")
            elif glucose >= 5.6:
                is_prediabetic = True
                criteria_met.append("糖耐量受损 (空腹血糖 5.6-6.9 mmol/L)")
        
        # 高血压状态
        is_hypertensive = False
        if sbp is not None and dbp is not None:
            if sbp >= 130 or dbp >= 80:
                is_hypertensive = True
                criteria_met.append(f"高血压 (血压 {sbp}/{dbp} mmHg)")
        
        # 血脂异常状态
        is_dyslipidemic = False
        if tg is not None and tg > 1.7:
            is_dyslipidemic = True
            criteria_met.append(f"高甘油三酯 (TG = {tg} mmol/L)")
        if hdl is not None:
            hdl_threshold = 1.0 if gender == 1 else 1.3  # 男性 < 1.0, 女性 < 1.3
            if hdl < hdl_threshold:
                is_dyslipidemic = True
                criteria_met.append(f"低HDL胆固醇 (HDL = {hdl} mmol/L)")
        
        # 肥胖状态
        is_overweight = False
        is_abdominal_obesity = False
        if bmi is not None and bmi >= 25:
            is_overweight = True
            if bmi >= 30:
                criteria_met.append(f"肥胖 (BMI = {bmi})")
            else:
                criteria_met.append(f"超重 (BMI = {bmi})")
        if waist is not None:
            waist_threshold = 90 if gender == 1 else 85  # 中国标准
            if waist >= waist_threshold:
                is_abdominal_obesity = True
                criteria_met.append(f"腹型肥胖 (腰围 = {waist} cm)")
        
        # 肾脏损伤状态
        has_kidney_damage = False
        if egfr is not None and egfr < 60:
            has_kidney_damage = True
            criteria_met.append(f"肾功能下降 (eGFR = {egfr})")
        if uacr is not None and uacr >= 30:
            has_kidney_damage = True
            criteria_met.append(f"蛋白尿 (UACR = {uacr} mg/g)")
        
        # ============= 3. 分期判定 (AHA 2023 标准) =============
        stage = 0
        stage_name = ""
        recommendation = ""
        
        if cvd_history:
            # Stage 4: 临床期 (已有心血管疾病史)
            stage = 4
            stage_name = "Stage 4 (临床期 - 已确诊CVD)"
            recommendation = (
                "🚨 严格二级预防，多学科联合治疗。\n"
                "• 强化他汀治疗 (LDL-C < 1.4 mmol/L)\n"
                "• 血压控制 < 130/80 mmHg\n"
                "• 考虑 SGLT2i 减少心血管事件\n"
                "• 定期心脏康复评估"
            )
            criteria_met.insert(0, "心血管疾病病史")
            
        elif has_kidney_damage:
            # Stage 3: 亚临床期 (早期肾脏损伤)
            stage = 3
            stage_name = "Stage 3 (亚临床期 - 早期器官损伤)"
            recommendation = (
                "⚠️ 早期肾损伤预警，强化药物治疗。\n"
                "• 首选 SGLT2 抑制剂 (如达格列净)\n"
                "• 考虑 GLP-1 RA (如司美格鲁肽)\n"
                "• ACEI/ARB 保护肾脏\n"
                "• 限盐 < 5g/天，控制蛋白质摄入"
            )
            
        elif is_diabetic or is_hypertensive or is_dyslipidemic:
            # Stage 2: 代谢风险期
            stage = 2
            stage_name = "Stage 2 (代谢风险期)"
            recommendation = (
                "📋 针对性治疗代谢风险因素：\n"
                "• 血压目标 < 130/80 mmHg\n"
                "• HbA1c 目标 < 7.0%\n"
                "• 他汀类药物降低 LDL-C\n"
                "• 定期筛查微量白蛋白尿"
            )
            
        elif is_overweight or is_abdominal_obesity or is_prediabetic:
            # Stage 1: 多余能量期
            stage = 1
            stage_name = "Stage 1 (超重/糖耐量受损期)"
            recommendation = (
                "🏃 重点在于生活方式干预：\n"
                "• 目标减重 ≥ 5% 体重\n"
                "• 地中海饮食或 DASH 饮食\n"
                "• 每周 ≥ 150 分钟中等强度运动\n"
                "• 每年复查血糖、血脂"
            )
            
        else:
            # Stage 0: 健康期
            stage = 0
            stage_name = "Stage 0 (健康期)"
            recommendation = (
                "✅ 保持当前健康的生活方式：\n"
                "• 维持 BMI 在 18.5-24.9\n"
                "• 均衡饮食，限制加工食品\n"
                "• 规律运动，每周 ≥ 150 分钟\n"
                "• 每年体检监测代谢指标"
            )
            criteria_met = ["各项指标正常"]
        
        return {
            "stage": stage,
            "stage_name": stage_name,
            "criteria_met": criteria_met,
            "recommendation": recommendation,
            "source": "AHA 2023 CKM Syndrome Advisory"
        }

    def assess_diabetic_urology(self, user_profile: dict) -> dict:
        """
        Task 99: 糖尿病-膀胱-肾脏共病风险评估。
        
        评估糖尿病患者的泌尿系统并发症风险：
        1. DKD (糖尿病肾病) - 基于 UACR
        2. DCP (糖尿病膀胱病变) - 基于尿流率
        
        Args:
            user_profile: 用户画像 (包含 HbA1c, UACR, Urine_Peak_Flow, Gender 等)
        
        Returns:
            dict: 泌尿系统风险评估结果
        """
        # ============= 1. 数据提取 =============
        hba1c = user_profile.get("HbA1c")
        glucose = user_profile.get("Glucose_Fasting")
        uacr = user_profile.get("UACR")
        urine_peak_flow = user_profile.get("Urine_Peak_Flow")
        gender = user_profile.get("Gender", 1)  # 1=男, 2=女
        diabetes_duration = user_profile.get("Diabetes_Duration", 0)  # 糖尿病病程(年)
        egfr = user_profile.get("eGFR", 90)
        
        # 判断是否有糖尿病
        is_diabetic = False
        if hba1c is not None and hba1c >= 6.5:
            is_diabetic = True
        elif glucose is not None and glucose >= 7.0:
            is_diabetic = True
        elif diabetes_duration > 0:
            is_diabetic = True
        
        findings = []
        
        # ============= 2. DKD (糖尿病肾病) 评估 =============
        dkd_stage = None
        dkd_risk = "低"
        
        if uacr is not None:
            if uacr >= 300:
                dkd_stage = "A3 (大量白蛋白尿/临床肾病)"
                dkd_risk = "极高"
                findings.append(f"UACR = {uacr} mg/g: 大量白蛋白尿，提示临床糖尿病肾病")
            elif uacr >= 30:
                dkd_stage = "A2 (微量白蛋白尿/早期肾损伤)"
                dkd_risk = "高"
                findings.append(f"UACR = {uacr} mg/g: 微量白蛋白尿，提示早期糖尿病肾病")
            else:
                dkd_stage = "A1 (正常)"
                findings.append(f"UACR = {uacr} mg/g: 正常范围")
        
        # eGFR 辅助判断
        if egfr is not None and egfr < 60:
            dkd_risk = "极高" if dkd_risk != "极高" else dkd_risk
            findings.append(f"eGFR = {egfr}: 肾功能下降 (< 60)")
        
        # ============= 3. DCP (糖尿病膀胱病变) 评估 =============
        dcp_risk = False
        dcp_description = "正常"
        bladder_advice = ""
        
        if is_diabetic and urine_peak_flow is not None:
            # 性别特异性阈值
            if gender == 1:  # 男性
                flow_threshold = 15
            else:  # 女性
                flow_threshold = 20
            
            if urine_peak_flow < flow_threshold:
                dcp_risk = True
                dcp_description = "疑似神经源性膀胱 (膀胱收缩无力)"
                findings.append(
                    f"最大尿流率 = {urine_peak_flow} mL/s (< {flow_threshold}): "
                    f"糖尿病自主神经病变可能导致膀胱逼尿肌收缩功能减退"
                )
                bladder_advice = (
                    "建议进行尿动力学检查 (Urodynamic Study)，\n"
                    "评估膀胱残余尿量，必要时定时排尿训练。"
                )
            else:
                findings.append(f"最大尿流率 = {urine_peak_flow} mL/s: 正常范围")
        
        # ============= 4. 综合建议 =============
        overall_risk = "Low"
        suggestions = []
        
        if dkd_risk in ["高", "极高"]:
            overall_risk = "High" if dkd_risk == "高" else "Very High"
            suggestions.extend([
                "🩺 建议肾内科就诊，定期监测尿蛋白和肾功能",
                "💊 考虑 ACEI/ARB 降低蛋白尿",
                "💊 SGLT2 抑制剂 (如达格列净) 有肾脏保护作用",
            ])
        
        if dcp_risk:
            overall_risk = "High" if overall_risk == "Low" else overall_risk
            suggestions.extend([
                "🚾 建议尿动力学检查排除神经源性膀胱",
                "⏰ 定时排尿 (每3-4小时) 避免膀胱过度充盈",
                "🍷 睡前限制液体摄入以减少夜尿次数",
            ])
        
        if not suggestions:
            suggestions.append("✅ 目前泌尿系统功能正常，建议定期复查")
        
        return {
            "urology_risk": overall_risk,
            "is_diabetic": is_diabetic,
            "details": {
                "kidney": {
                    "stage": dkd_stage,
                    "risk_level": dkd_risk,
                    "uacr": uacr,
                    "egfr": egfr
                },
                "bladder": {
                    "function": dcp_description,
                    "peak_flow": urine_peak_flow,
                    "dcp_risk": dcp_risk
                }
            },
            "findings": findings,
            "suggestions": suggestions
        }


# 注意: 不再在模块级创建单例，以避免 import 时加载模型
# 单例由 main.py lifespan 统一管理


if __name__ == "__main__":
    engine = DiseaseRiskEngine()
    
    # 测试 CKM 分期
    print("\n=== AHA CKM 综合征分期测试 ===")
    
    test_cases = [
        {"name": "健康人", "data": {"BMI": 22, "SBP": 120, "DBP": 75, "HbA1c": 5.2}},
        {"name": "超重前驱糖尿病", "data": {"BMI": 27, "SBP": 125, "DBP": 78, "HbA1c": 5.9}},
        {"name": "代谢综合征", "data": {"BMI": 30, "SBP": 145, "DBP": 92, "HbA1c": 6.8, "Triglycerides": 2.5}},
        {"name": "早期肾损伤", "data": {"BMI": 28, "SBP": 140, "DBP": 88, "eGFR": 55, "UACR": 45}},
        {"name": "CVD病史", "data": {"BMI": 26, "Heart_Attack": True, "SBP": 135, "DBP": 85}},
    ]
    
    for case in test_cases:
        result = engine.assess_ckm_stage(case["data"])
        print(f"\n【{case['name']}】")
        print(f"  分期: {result['stage_name']}")
        print(f"  命中条件: {', '.join(result['criteria_met'])}")
        print(f"  建议: {result['recommendation'].split(chr(10))[0]}...")

