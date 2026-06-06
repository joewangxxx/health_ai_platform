import json

from backend.services.projection_service import ProjectionService


class DummyProfile:
    genomic_data = json.dumps({"rs7903146": "CT"})

    def model_dump(self):
        return {
            "Age": 45,
            "Height": 170,
            "Weight": 82,
            "BMI": 28.4,
            "SBP": 132,
            "Glucose_Fasting": 6.3,
        }


class DummyFusionEngine:
    def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
        bmi = float(clinical_profile["BMI"])
        glucose = float(clinical_profile["Glucose_Fasting"])
        risk = round(min(95, bmi * 1.6 + glucose * 5), 1)
        return {
            "T2D": {
                "final_risk": risk,
                "level": "Medium",
            }
        }


def test_intervention_applies_future_years_and_controls():
    service = ProjectionService(fusion_engine=DummyFusionEngine())

    result = service.simulate_intervention(
        DummyProfile(),
        {
            "years": 10,
            "weight_change_kg": -6,
            "exercise_days_per_week": 5,
        },
    )

    assert result["base_profile_summary"]["Age"] == 55
    assert result["simulated_profile_summary"]["Age"] == 55
    assert result["simulated_profile_summary"]["Weight"] == 76
    assert result["simulated_profile_summary"]["BMI"] < result["base_profile_summary"]["BMI"]
    assert result["new_risk_report"]["T2D"]["final_risk"] < result["base_risk_report"]["T2D"]["final_risk"]
    assert result["risk_reduction_percent"] > 0
