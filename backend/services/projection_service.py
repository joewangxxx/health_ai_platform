import copy
from backend.models import UserProfile
from backend.services.fusion_service import FusionRiskEngine
# Note: projection_service uses FusionRiskEngine to ensure consistent risk logic 
# (which internally calls risk_engine, gene_engine, etc.)

class ProjectionService:
    def __init__(self):
        self.fusion_engine = FusionRiskEngine()

    def simulate_future_risk(self, profile: UserProfile, years: int = 5) -> dict:
        """
        Simulate future risk by aging the user and applying natural progression trends.
        """
        # 1. Clone profile metrics
        # We convert to dict first to avoid attaching to DB session
        future_data = profile.model_dump()
        
        # 2. Apply Aging
        current_age = future_data.get("Age") or 45
        future_data["Age"] = current_age + years
        
        # 3. Apply Natural Progression (Worst case scenario: No intervention)
        # SBP: +0.5 mmHg/year
        if future_data.get("SBP"):
            future_data["SBP"] += (0.5 * years)
            
        # Glucose: +0.05 mmol/L/year approx
        if future_data.get("Glucose_Fasting"):
            future_data["Glucose_Fasting"] += (0.05 * years)
            
        # BMI: Assume slight increase (+0.1/year) due to metabolism slow down
        if future_data.get("BMI"):
            future_data["BMI"] += (0.1 * years)
            
        # 4. Calculate Risk
        # Note: We need to mock IoT data or pass defaults
        from backend.config import DEFAULT_DEVICE_STATE
        
        # Since fusion_engine expects `user_snps` and profile dict
        # We'll use the genomic data stored in profile
        
        # Parse genomic data if exists
        user_snps = {}
        if profile.genomic_data:
            import json
            try:
                user_snps = json.loads(profile.genomic_data)
            except:
                pass

        # Call Fusion Engine
        risk_result = self.fusion_engine.calculate_composite_risk(
            clinical_profile=future_data,
            user_snps=user_snps,
            iot_data=DEFAULT_DEVICE_STATE
        )
        
        return {
            "years_later": years,
            "simulated_profile_summary": {
                "Age": future_data["Age"],
                "BMI": round(future_data.get("BMI", 0), 1),
                "SBP": round(future_data.get("SBP", 0), 1)
            },
            "risk_result": risk_result
        }

    def simulate_intervention(self, profile: UserProfile, intervention: dict) -> dict:
        """
        Simulate risk after lifestyle interventions.
        Intervention Target Example: {"weight_loss_percent": 0.05}
        """
        sim_data = profile.model_dump()
        
        # Apply Interventions
        changes = []
        
        # 1. Weight Loss
        if "weight_loss_percent" in intervention:
            loss_pct = intervention["weight_loss_percent"] # e.g. 0.05
            if sim_data.get("Weight"):
                orig = sim_data["Weight"]
                sim_data["Weight"] = orig * (1 - loss_pct)
                # Recalculate BMI
                if sim_data.get("Height"):
                    h_m = sim_data["Height"] / 100.0
                    sim_data["BMI"] = sim_data["Weight"] / (h_m * h_m)
                changes.append(f"体重降低 {loss_pct*100}%")
                
                # Weight loss often improves BP and Glucose
                if sim_data.get("SBP"): sim_data["SBP"] -= 5 # Rough estimate
                if sim_data.get("Glucose_Fasting"): sim_data["Glucose_Fasting"] -= 0.5

        # 2. Quit Smoking (Hypothetically affects risk engine if it had smoking feature)
        # Currently our model might not explicitly have smoking, 
        # but we can simulate effect by improving general vitals
        
        # Calculate Base Risk
        from backend.config import DEFAULT_DEVICE_STATE
        import json
        
        user_snps = {}
        if profile.genomic_data:
            try: user_snps = json.loads(profile.genomic_data)
            except: pass
            
        # Get Original Risk
        base_risk = self.fusion_engine.calculate_composite_risk(
            clinical_profile=profile.model_dump(),
            user_snps=user_snps,
            iot_data=DEFAULT_DEVICE_STATE
        )
        
        # Get New Risk
        new_risk = self.fusion_engine.calculate_composite_risk(
            clinical_profile=sim_data,
            user_snps=user_snps,
            iot_data=DEFAULT_DEVICE_STATE
        )
        
        # Calculate Benefit (e.g. Max risk reduction across diseases)
        # Simplified: Compare highest probability
        
        def get_max_prob(report):
            if not report: return 0
            # FusionRiskEngine returns `final_risk`; keep backward compatibility
            # for report shapes that may still expose `probability`.
            probs = [
                d.get('final_risk', d.get('probability', 0))
                for d in report.values()
                if isinstance(d, dict)
            ]
            return max(probs) if probs else 0
            
        old_max = get_max_prob(base_risk)
        new_max = get_max_prob(new_risk)
        
        reduction = 0
        if old_max > 0:
            reduction = (old_max - new_max) / old_max
            
        return {
            "intervention": intervention,
            "changes_applied": changes,
            "base_risk_max": old_max,
            "new_risk_max": new_max,
            "risk_reduction_percent": round(reduction * 100, 1),
            "new_risk_report": new_risk
        }

projection_service = ProjectionService()
