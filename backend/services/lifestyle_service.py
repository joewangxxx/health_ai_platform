import joblib
import pandas as pd
import numpy as np
import os
from backend.config import LIFESTYLE_MODEL_PATH
from backend.core.constants import (
    LIFESTYLE_STEPS_NORMALIZE_BASE,
    LIFESTYLE_COUNT_BASE,
    LIFESTYLE_MODIFIER_BASE,
    LIFESTYLE_MODIFIER_RANGE,
)

# 指向你刚才训练好的 XGBoost 模型
MODEL_PATH = LIFESTYLE_MODEL_PATH

class LifestyleService:
    def __init__(self):
        print("⌚ 初始化生活方式 AI 引擎 (XGBoost)...")
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            print("   ✅ 加载成功")
        else:
            print("   ❌ 警告: 未找到生活方式模型文件！")
            self.model = None

    def calculate_modifier(self, iot_data):
        """
        输入: {"steps": 5000, "hr": 70, ...}
        输出: 风险修正系数 (例如 1.2 = 风险增加20%)
        """
        if not self.model or not iot_data:
            return 1.0
            
        steps = iot_data.get('steps', 0)
        
        # --- 特征工程 (Feature Engineering) ---
        # 我们的模型训练时用了 ['sum', 'count'] (活跃记录数, 总记录数)
        # 我们需要把 'steps' 映射回去
        
        # 假设逻辑：
        # 1. 'count' 代表一天的时间窗，固定设为 LIFESTYLE_COUNT_BASE (归一化基准)
        # 2. 'sum' 代表活跃程度。假设 10000 步 = 100% 活跃(即sum=count)
        #    那么 sum = (steps / LIFESTYLE_STEPS_NORMALIZE_BASE) * LIFESTYLE_COUNT_BASE
        
        simulated_count = LIFESTYLE_COUNT_BASE
        simulated_sum = (steps / LIFESTYLE_STEPS_NORMALIZE_BASE) * LIFESTYLE_COUNT_BASE
        
        # 构造输入 DataFrame (列名必须与训练时一致)
        input_df = pd.DataFrame([{
            'sum': simulated_sum,
            'count': simulated_count
        }])
        
        try:
            # 预测 "生活方式风险" (1=高风险, 0=低风险)
            # 获取属于类别 1 (高风险) 的概率
            risk_prob = self.model.predict_proba(input_df)[0][1]
            
            # 将概率转换为修正系数 (Modifier)
            # 概率 0.0 (非常健康) -> 系数 0.8 (降低风险)
            # 概率 0.5 (普通)     -> 系数 1.0
            # 概率 1.0 (极不健康) -> 系数 1.3 (增加风险)
            
            modifier = LIFESTYLE_MODIFIER_BASE + (risk_prob * LIFESTYLE_MODIFIER_RANGE)
            
            return round(modifier, 2)
            
        except Exception as e:
            print(f"Lifestyle inference error: {e}")
            return 1.0


class HydrationAdvisor:
    """
    Task 100: 精准水合建议算法 (Precision Hydration)
    
    根据用户的生理参数、CKM分期和排尿情况，推荐最佳喝水计划。
    """
    
    # 默认喝水时间点
    DEFAULT_SCHEDULE = [
        {"time": "07:00", "label": "晨起"},
        {"time": "09:00", "label": "上午"},
        {"time": "11:00", "label": "午前"},
        {"time": "13:00", "label": "午后"},
        {"time": "15:00", "label": "下午"},
        {"time": "17:00", "label": "傍晚"},
        {"time": "19:00", "label": "晚间"},
        {"time": "21:00", "label": "睡前"},
    ]
    
    def calculate_water_plan(self, profile: dict) -> dict:
        """
        计算个性化喝水计划。
        
        Args:
            profile: 用户画像，包含:
                - Weight: 体重 (kg)
                - Age: 年龄
                - Gender: 性别 (1=男, 2=女)
                - CKM_Stage: CKM分期 (0-4)
                - Urine_Peak_Flow: 最大尿流率 (mL/s)
                - eGFR: 肾小球滤过率
                - Heart_Failure: 是否心衰
        
        Returns:
            dict: 水合计划
        """
        # ============= 1. 基础需求计算 =============
        weight = profile.get("Weight", 65)
        age = profile.get("Age", 45)
        gender = profile.get("Gender", 1)
        
        # 基础公式: 30 mL/kg
        base_ml = weight * 30
        
        # 年龄调整 (老年人代谢减慢)
        if age > 65:
            base_ml *= 0.9
        
        # 性别调整
        if gender == 2:  # 女性
            base_ml *= 0.95
        
        # ============= 2. 病理调整 =============
        ckm_stage = profile.get("CKM_Stage", 0)
        egfr = profile.get("eGFR", 90)
        heart_failure = profile.get("Heart_Failure", False)
        urine_peak_flow = profile.get("Urine_Peak_Flow")
        
        restrictions = []
        warnings = []
        
        # CKM Stage 3-4 或心肾功能不全: 限制液体摄入
        if ckm_stage >= 3 or heart_failure or (egfr is not None and egfr < 30):
            max_allowed = 1500
            if base_ml > max_allowed:
                base_ml = max_allowed
                restrictions.append(f"⚠️ 心肾功能受限，每日液体摄入限制为 {max_allowed}mL")
                warnings.append("请遵医嘱调整饮水量")
        
        # 尿流率过低: 提示少量多次
        bladder_caution = False
        if urine_peak_flow is not None:
            threshold = 15 if gender == 1 else 20
            if urine_peak_flow < threshold:
                bladder_caution = True
                restrictions.append("🚾 尿流率偏低，建议少量多次饮水，避免膀胱过度充盈")
        
        # ============= 3. 夜间策略 (Nocturia Prevention) =============
        evening_cutoff = "19:00"
        evening_limit = 200  # 晚间最大饮水量
        
        # 高风险人群: 老年 或 尿流率低
        nocturia_risk = age > 60 or bladder_caution
        if nocturia_risk:
            restrictions.append(f"🌙 夜尿防控: {evening_cutoff} 后限制液体 < {evening_limit}mL")
        
        # ============= 4. 生成饮水计划 =============
        daily_target = round(base_ml)
        
        # 计算每次饮水量
        # 早晨多喝，晚间少喝
        schedule = []
        remaining = daily_target
        
        for i, slot in enumerate(self.DEFAULT_SCHEDULE):
            time = slot["time"]
            label = slot["label"]
            
            # 时间权重 (早晨多，晚间少)
            if time < "10:00":
                weight_factor = 1.3  # 晨起多喝
            elif time < "18:00":
                weight_factor = 1.0  # 日间正常
            elif time < "20:00":
                weight_factor = 0.6 if nocturia_risk else 0.8
            else:
                weight_factor = 0.3 if nocturia_risk else 0.5
            
            # 膀胱问题: 减少单次量
            if bladder_caution:
                weight_factor *= 0.7
            
            # 计算本次饮水量
            base_per_slot = daily_target / len(self.DEFAULT_SCHEDULE)
            amount = round(base_per_slot * weight_factor / 50) * 50  # 四舍五入到50mL
            amount = min(amount, remaining, 400)  # 单次最多400mL
            
            if time >= evening_cutoff and nocturia_risk:
                amount = min(amount, 100)
            
            # 生成建议理由
            if time == "07:00":
                reason = "晨起空腹补水，激活代谢"
            elif time == "19:00" and nocturia_risk:
                reason = "夜尿防控截止点，减少液体"
            elif time == "21:00":
                reason = "睡前适量，避免夜间起夜"
            else:
                reason = f"{label}补水"
            
            if amount > 0:
                schedule.append({
                    "time": time,
                    "amount": amount,
                    "label": label,
                    "reason": reason
                })
                remaining -= amount
        
        # 实际总量
        actual_total = sum(s["amount"] for s in schedule)
        
        return {
            "daily_target_ml": daily_target,
            "actual_total_ml": actual_total,
            "schedule": schedule,
            "restrictions": restrictions,
            "warnings": warnings,
            "summary": self._generate_summary(daily_target, restrictions, nocturia_risk)
        }
    
    def _generate_summary(self, target: int, restrictions: list, nocturia_risk: bool) -> str:
        """生成中文摘要"""
        if restrictions:
            return f"💧 建议每日饮水 {target}mL，需注意以下限制条件"
        elif nocturia_risk:
            return f"💧 建议每日饮水 {target}mL，晚间适当控制以减少夜尿"
        else:
            return f"💧 建议每日饮水 {target}mL，均匀分布于全天"


# 单例实例
hydration_advisor = HydrationAdvisor()
