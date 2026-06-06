import copy
import json

from backend.models import UserProfile
from backend.services.fusion_service import FusionRiskEngine


class ProjectionService:
    def __init__(self, fusion_engine=None):
        self.fusion_engine = fusion_engine or FusionRiskEngine()

    def set_fusion_engine(self, fusion_engine):
        if fusion_engine is not None:
            self.fusion_engine = fusion_engine

    def _profile_data(self, profile: UserProfile) -> dict:
        return profile.model_dump()

    def _parse_user_snps(self, profile: UserProfile) -> dict:
        if not profile.genomic_data:
            return {}
        try:
            return json.loads(profile.genomic_data)
        except Exception:
            return {}

    def _apply_natural_progression(self, data: dict, years: int) -> dict:
        future_data = copy.deepcopy(data)
        current_age = future_data.get("Age") or 45
        future_data["Age"] = current_age + years

        if future_data.get("SBP"):
            future_data["SBP"] += 0.5 * years
        if future_data.get("Glucose_Fasting"):
            future_data["Glucose_Fasting"] += 0.05 * years
        if future_data.get("BMI"):
            future_data["BMI"] += 0.1 * years

        return future_data

    def _apply_interventions(self, data: dict, intervention: dict) -> list[str]:
        changes = []

        weight_change_kg = intervention.get("weight_change_kg")
        if weight_change_kg is not None and data.get("Weight"):
            change_kg = float(weight_change_kg)
            original_weight = data["Weight"]
            data["Weight"] = max(30.0, original_weight + change_kg)
            if data.get("Height"):
                h_m = data["Height"] / 100.0
                data["BMI"] = data["Weight"] / (h_m * h_m)
            changes.append(f"weight_change_kg={change_kg:+.1f}")
            if change_kg < 0:
                if data.get("SBP"):
                    data["SBP"] -= min(8.0, abs(change_kg) * 1.2)
                if data.get("Glucose_Fasting"):
                    data["Glucose_Fasting"] -= min(0.6, abs(change_kg) * 0.08)

        elif "weight_loss_percent" in intervention and data.get("Weight"):
            loss_pct = float(intervention["weight_loss_percent"])
            original_weight = data["Weight"]
            data["Weight"] = max(30.0, original_weight * (1 - loss_pct))
            if data.get("Height"):
                h_m = data["Height"] / 100.0
                data["BMI"] = data["Weight"] / (h_m * h_m)
            changes.append(f"weight_loss_percent={loss_pct:.3f}")
            if data.get("SBP"):
                data["SBP"] -= 5
            if data.get("Glucose_Fasting"):
                data["Glucose_Fasting"] -= 0.5

        exercise_days = intervention.get("exercise_days_per_week")
        if exercise_days is not None:
            days = max(0.0, min(7.0, float(exercise_days)))
            changes.append(f"exercise_days_per_week={days:g}")
            if data.get("SBP"):
                data["SBP"] -= min(4.0, days * 0.4)
            if data.get("Glucose_Fasting"):
                data["Glucose_Fasting"] -= min(0.4, days * 0.04)

        return changes

    def _profile_summary(self, data: dict) -> dict:
        return {
            "Age": data.get("Age"),
            "BMI": round(data.get("BMI") or 0, 1),
            "SBP": round(data.get("SBP") or 0, 1),
            "Glucose_Fasting": round(data.get("Glucose_Fasting") or 0, 1),
            "Weight": round(data.get("Weight") or 0, 1),
        }

    def _calculate_risk(self, profile_data: dict, user_snps: dict) -> dict:
        from backend.config import DEFAULT_DEVICE_STATE

        return self.fusion_engine.calculate_composite_risk(
            clinical_profile=profile_data,
            user_snps=user_snps,
            iot_data=DEFAULT_DEVICE_STATE,
        )

    def simulate_future_risk(self, profile: UserProfile, years: int = 5) -> dict:
        future_data = self._apply_natural_progression(self._profile_data(profile), years)
        risk_result = self._calculate_risk(future_data, self._parse_user_snps(profile))

        return {
            "years_later": years,
            "simulated_profile_summary": self._profile_summary(future_data),
            "risk_result": risk_result,
        }

    def simulate_intervention(self, profile: UserProfile, intervention: dict) -> dict:
        years = int(intervention.get("years") or 0)
        base_data = (
            self._apply_natural_progression(self._profile_data(profile), years)
            if years
            else self._profile_data(profile)
        )
        sim_data = copy.deepcopy(base_data)
        changes = self._apply_interventions(sim_data, intervention)
        user_snps = self._parse_user_snps(profile)

        base_risk = self._calculate_risk(base_data, user_snps)
        new_risk = self._calculate_risk(sim_data, user_snps)

        def get_max_prob(report):
            if not isinstance(report, dict) or report.get("error"):
                return 0
            probs = [
                d.get("final_risk", d.get("probability", 0))
                for d in report.values()
                if isinstance(d, dict)
            ]
            return max(probs) if probs else 0

        old_max = get_max_prob(base_risk)
        new_max = get_max_prob(new_risk)
        reduction = (old_max - new_max) / old_max if old_max > 0 else 0

        return {
            "intervention": intervention,
            "changes_applied": changes,
            "base_risk_max": old_max,
            "new_risk_max": new_max,
            "risk_reduction_percent": round(reduction * 100, 1),
            "base_profile_summary": self._profile_summary(base_data),
            "simulated_profile_summary": self._profile_summary(sim_data),
            "base_risk_report": base_risk,
            "new_risk_report": new_risk,
        }


projection_service = ProjectionService()
