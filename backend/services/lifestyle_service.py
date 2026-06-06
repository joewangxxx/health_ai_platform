import logging
import os

import joblib
import pandas as pd

from backend.config import LIFESTYLE_MODEL_PATH
from backend.core.constants import (
    LIFESTYLE_COUNT_BASE,
    LIFESTYLE_MODIFIER_BASE,
    LIFESTYLE_MODIFIER_RANGE,
    LIFESTYLE_STEPS_NORMALIZE_BASE,
)

logger = logging.getLogger(__name__)
_warning_emitted = False

MODEL_PATH = LIFESTYLE_MODEL_PATH


def _emit_unavailable_warning():
    """中文说明：_emit_unavailable_warning 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    global _warning_emitted
    if _warning_emitted:
        return
    logger.warning("Lifestyle model unavailable; continuing without XGBoost modifier.")
    _warning_emitted = True


class LifestyleService:
    """中文说明：LifestyleService 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""

    def __init__(self):
        self.model = None
        if not os.path.exists(MODEL_PATH):
            _emit_unavailable_warning()
            return

        try:
            self.model = joblib.load(MODEL_PATH)
        except Exception:
            _emit_unavailable_warning()
            self.model = None

    def calculate_modifier(self, iot_data):
        """
        Convert coarse IoT activity data into the trained XGBoost input space.
        When the optional model is unavailable, return the neutral modifier.
        """
        if not self.model or not iot_data:
            return 1.0

        steps = iot_data.get("steps", 0)
        simulated_count = LIFESTYLE_COUNT_BASE
        simulated_sum = (steps / LIFESTYLE_STEPS_NORMALIZE_BASE) * LIFESTYLE_COUNT_BASE
        input_df = pd.DataFrame([{"sum": simulated_sum, "count": simulated_count}])

        try:
            risk_prob = self.model.predict_proba(input_df)[0][1]
            modifier = LIFESTYLE_MODIFIER_BASE + (risk_prob * LIFESTYLE_MODIFIER_RANGE)
            return round(modifier, 2)
        except Exception:
            return 1.0


class HydrationAdvisor:
    """中文说明：HydrationAdvisor 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""

    DEFAULT_SCHEDULE = [
        {"time": "07:00", "label": "Morning"},
        {"time": "09:00", "label": "Mid-morning"},
        {"time": "11:00", "label": "Noon"},
        {"time": "13:00", "label": "Early afternoon"},
        {"time": "15:00", "label": "Afternoon"},
        {"time": "17:00", "label": "Evening"},
        {"time": "19:00", "label": "Night"},
        {"time": "21:00", "label": "Before sleep"},
    ]

    def calculate_water_plan(self, profile: dict) -> dict:
        # 先计算基础饮水量，再按年龄/性别进行温和缩放，
        # 后续再叠加肾心功能与排尿风险约束，确保建议可执行且保守。
        weight = profile.get("Weight", 65)
        age = profile.get("Age", 45)
        gender = profile.get("Gender", 1)
        eGFR = profile.get("eGFR", 90)
        ckm_stage = profile.get("CKM_Stage", 0)
        heart_failure = profile.get("Heart_Failure", False)
        urine_peak_flow = profile.get("Urine_Peak_Flow")

        base_ml = weight * 30
        if age > 65:
            base_ml *= 0.9
        if gender == 2:
            base_ml *= 0.95

        restrictions = []
        warnings = []
        bladder_caution = False

        # CKM 分期较高、心衰或 eGFR 明显下降时，启用上限限水策略。
        if ckm_stage >= 3 or heart_failure or (eGFR is not None and eGFR < 30):
            base_ml = min(base_ml, 1500)
            restrictions.append("Fluid intake should stay within clinician-approved renal/cardiac limits.")
            warnings.append("Confirm the hydration plan with a clinician when cardiac or kidney function is impaired.")

        # 尿流率下降时采取“小量高频”分配，降低单次膀胱负担。
        if urine_peak_flow is not None:
            threshold = 15 if gender == 1 else 20
            if urine_peak_flow < threshold:
                bladder_caution = True
                restrictions.append("Prefer smaller, more frequent water intake because urinary flow is reduced.")

        nocturia_risk = age > 60 or bladder_caution
        if nocturia_risk:
            restrictions.append("Reduce evening fluid volume after 19:00 to limit nocturia risk.")

        daily_target = round(base_ml)
        remaining = daily_target
        schedule = []

        # 时段权重控制“白天多、夜间少”，并在高夜尿风险下进一步收缩晚间分配。
        for slot in self.DEFAULT_SCHEDULE:
            time = slot["time"]
            if time < "10:00":
                weight_factor = 1.3
            elif time < "18:00":
                weight_factor = 1.0
            elif time < "20:00":
                weight_factor = 0.6 if nocturia_risk else 0.8
            else:
                weight_factor = 0.3 if nocturia_risk else 0.5

            if bladder_caution:
                weight_factor *= 0.7

            amount = round((daily_target / len(self.DEFAULT_SCHEDULE)) * weight_factor / 50) * 50
            amount = min(amount, remaining, 400)
            if time >= "19:00" and nocturia_risk:
                amount = min(amount, 100)

            if amount <= 0:
                continue

            schedule.append(
                {
                    "time": time,
                    "amount": amount,
                    "label": slot["label"],
                    "reason": self._build_reason(time, nocturia_risk),
                }
            )
            remaining -= amount

        actual_total = sum(item["amount"] for item in schedule)
        return {
            "daily_target_ml": daily_target,
            "actual_total_ml": actual_total,
            "schedule": schedule,
            "restrictions": restrictions,
            "warnings": warnings,
            "summary": self._generate_summary(daily_target, restrictions, nocturia_risk),
        }

    def _build_reason(self, time: str, nocturia_risk: bool) -> str:
        """中文说明：_build_reason 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        if time == "07:00":
            return "Rehydrate after waking."
        if time == "19:00" and nocturia_risk:
            return "Keep evening hydration light to reduce nocturia."
        if time == "21:00":
            return "Small pre-sleep hydration only."
        return "Spread hydration evenly through the day."

    def _generate_summary(self, target: int, restrictions: list, nocturia_risk: bool) -> str:
        """中文说明：_generate_summary 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        if restrictions:
            return f"Recommended daily intake is about {target} mL with clinical restrictions applied."
        if nocturia_risk:
            return f"Recommended daily intake is about {target} mL with reduced evening fluids."
        return f"Recommended daily intake is about {target} mL spread across the full day."


hydration_advisor = HydrationAdvisor()
