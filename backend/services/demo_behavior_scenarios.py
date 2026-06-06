import json
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT


class DemoScenarioArtifactError(ValueError):
    """Raised when the static demo scenario artifact violates the frozen contract."""


class BehaviorScenarioRepository:
    EVENT_TYPES = {
        "sleep",
        "activity",
        "sedentary",
        "diet_vision",
        "vitals",
        "hydration",
        "medication_context",
        "symptom_note",
        "analysis_marker",
        "daily_summary",
    }

    def __init__(self, artifact_path: Path | str | None = None):
        self.artifact_path = Path(artifact_path or Path(PROJECT_ROOT) / "data/demo/behavior_day_scenarios.json")

    def list_scenarios(self) -> list[dict[str, Any]]:
        artifact = self._load_valid_artifact()
        return [self._scenario_metadata(scenario) for scenario in artifact["scenarios"]]

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        artifact = self._load_valid_artifact()
        for scenario in artifact["scenarios"]:
            if scenario["scenario_id"] == scenario_id:
                return scenario
        return None

    def _load_valid_artifact(self) -> dict[str, Any]:
        try:
            artifact = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise DemoScenarioArtifactError(f"Scenario artifact not found: {self.artifact_path}") from exc
        except json.JSONDecodeError as exc:
            raise DemoScenarioArtifactError(f"Scenario artifact is not valid JSON: {exc}") from exc

        self._validate_collection(artifact)
        return artifact

    def _validate_collection(self, artifact: Any) -> None:
        if not isinstance(artifact, dict):
            raise DemoScenarioArtifactError("Scenario artifact must be a JSON object")
        if artifact.get("schema_version") != "behavior_day_scenarios.v1":
            raise DemoScenarioArtifactError("Invalid collection schema_version")
        if artifact.get("data_mode") != "simulated_demo":
            raise DemoScenarioArtifactError("Scenario collection data_mode must be simulated_demo")
        self._validate_source_provenance(artifact.get("source_provenance"), "behavior_day_scenarios.v1")

        scenarios = artifact.get("scenarios")
        if not isinstance(scenarios, list):
            raise DemoScenarioArtifactError("Scenario collection must contain a scenarios list")
        seen_ids = set()
        for scenario in scenarios:
            self._validate_scenario(scenario)
            scenario_id = scenario["scenario_id"]
            if scenario_id in seen_ids:
                raise DemoScenarioArtifactError(f"Duplicate scenario_id: {scenario_id}")
            seen_ids.add(scenario_id)

    def _validate_scenario(self, scenario: Any) -> None:
        if not isinstance(scenario, dict):
            raise DemoScenarioArtifactError("Scenario must be an object")
        for field in ("schema_version", "scenario_id", "demo_patient_id", "data_mode", "timeline", "source_provenance"):
            if field not in scenario:
                raise DemoScenarioArtifactError(f"Scenario missing required field: {field}")
        if scenario["schema_version"] != "behavior_day_scenario.v1":
            raise DemoScenarioArtifactError(f"Invalid scenario schema_version for {scenario.get('scenario_id')}")
        if scenario["data_mode"] != "simulated_demo":
            raise DemoScenarioArtifactError(f"Scenario data_mode must be simulated_demo: {scenario.get('scenario_id')}")
        self._validate_source_provenance(scenario.get("source_provenance"), "behavior_day_scenario.v1")
        self.validate_lifestyle_context(scenario.get("lifestyle_context"), expected_scenario_id=scenario["scenario_id"])

        timeline = scenario.get("timeline")
        if not isinstance(timeline, list):
            raise DemoScenarioArtifactError(f"Scenario timeline must be a list: {scenario['scenario_id']}")
        for event in timeline:
            self._validate_event(event)

    def _validate_event(self, event: Any) -> None:
        if not isinstance(event, dict):
            raise DemoScenarioArtifactError("Timeline event must be an object")
        for field in ("schema_version", "event_id", "time", "event_type", "label", "data_mode", "payload", "source_provenance"):
            if field not in event:
                raise DemoScenarioArtifactError(f"Timeline event missing required field: {field}")
        if event["schema_version"] != "behavior_timeline_event.v1":
            raise DemoScenarioArtifactError(f"Invalid timeline event schema_version: {event.get('event_id')}")
        if event["data_mode"] != "simulated_demo":
            raise DemoScenarioArtifactError(f"Timeline event data_mode must be simulated_demo: {event.get('event_id')}")
        event_type = event.get("event_type")
        if event_type not in self.EVENT_TYPES:
            raise DemoScenarioArtifactError(f"Invalid event_type: {event_type}")
        self._validate_source_provenance(event.get("source_provenance"), "behavior_timeline_event.v1", strict_schema=False)
        if event_type == "diet_vision":
            self._validate_diet_vision_payload(event.get("payload"), event.get("event_id"))

    def _validate_diet_vision_payload(self, payload: Any, event_id: str | None = None) -> None:
        if not isinstance(payload, dict):
            raise DemoScenarioArtifactError(f"diet_vision payload must be an object: {event_id}")
        if payload.get("schema_version") != "diet_vision_event.v1":
            raise DemoScenarioArtifactError(f"Invalid diet_vision payload schema_version: {event_id}")
        for field in ("meal_type", "food_items", "nutrition", "vision_provenance"):
            if field not in payload:
                raise DemoScenarioArtifactError(f"diet_vision payload missing required field {field}: {event_id}")
        nutrition = payload["nutrition"]
        if not isinstance(nutrition, dict):
            raise DemoScenarioArtifactError(f"diet_vision nutrition must be an object: {event_id}")
        for field in ("calories", "carbs", "protein", "fat"):
            if field not in nutrition:
                raise DemoScenarioArtifactError(f"diet_vision nutrition missing required field {field}: {event_id}")
        provenance = payload["vision_provenance"]
        if not isinstance(provenance, dict) or provenance.get("source_type") != "simulated_demo":
            raise DemoScenarioArtifactError(f"diet_vision vision_provenance.source_type must be simulated_demo: {event_id}")

    @classmethod
    def validate_lifestyle_context(cls, context: Any, expected_scenario_id: str | None = None) -> dict[str, Any]:
        if not isinstance(context, dict):
            raise DemoScenarioArtifactError("lifestyle_context must be an object")
        for field in ("schema_version", "data_mode", "scenario_id", "summary", "modifier_inputs", "source_provenance"):
            if field not in context:
                raise DemoScenarioArtifactError(f"lifestyle_context missing required field: {field}")
        if context["schema_version"] != "lifestyle_context.v1":
            raise DemoScenarioArtifactError("Invalid lifestyle_context schema_version")
        data_mode = context["data_mode"]
        if data_mode not in {"simulated_demo", "user_uploaded"}:
            raise DemoScenarioArtifactError("lifestyle_context data_mode must be simulated_demo or user_uploaded")
        if expected_scenario_id and context["scenario_id"] != expected_scenario_id:
            raise DemoScenarioArtifactError("lifestyle_context scenario_id must match scenario")
        if not isinstance(context.get("summary"), dict):
            raise DemoScenarioArtifactError("lifestyle_context summary must be an object")
        if not isinstance(context.get("modifier_inputs"), dict):
            raise DemoScenarioArtifactError("lifestyle_context modifier_inputs must be an object")
        provenance = context.get("source_provenance")
        if data_mode == "simulated_demo":
            cls._validate_source_provenance(provenance, "behavior_day_scenario.v1")
        elif not isinstance(provenance, dict):
            raise DemoScenarioArtifactError("source_provenance must be an object")

        source_type = provenance.get("source_type")
        if data_mode == "simulated_demo" and source_type != "demo_scenario":
            raise DemoScenarioArtifactError("simulated_demo lifestyle_context source_type must be demo_scenario")
        if data_mode == "user_uploaded" and source_type != "user_uploaded":
            raise DemoScenarioArtifactError("user_uploaded lifestyle_context source_type must be user_uploaded")
        if data_mode == "user_uploaded":
            artifact_schema = provenance.get("artifact_schema")
            if artifact_schema not in {"platform_behavior_day_csv.v1", "platform_behavior_day_json.v1"}:
                raise DemoScenarioArtifactError(
                    "user_uploaded lifestyle_context artifact_schema must be platform behavior day CSV or JSON"
                )
        return context

    @staticmethod
    def _validate_source_provenance(
        provenance: Any,
        expected_artifact_schema: str,
        *,
        strict_schema: bool = True,
    ) -> None:
        if not isinstance(provenance, dict):
            raise DemoScenarioArtifactError("source_provenance must be an object")
        if not provenance.get("source_type"):
            raise DemoScenarioArtifactError("source_provenance.source_type is required")
        generated_from = provenance.get("generated_from")
        if not isinstance(generated_from, list) or not generated_from:
            raise DemoScenarioArtifactError("source_provenance.generated_from is required")
        artifact_schema = provenance.get("artifact_schema")
        if strict_schema and artifact_schema != expected_artifact_schema:
            raise DemoScenarioArtifactError(
                f"source_provenance.artifact_schema must be {expected_artifact_schema}"
            )

    @staticmethod
    def _scenario_metadata(scenario: dict[str, Any]) -> dict[str, Any]:
        return {
            "scenario_id": scenario["scenario_id"],
            "schema_version": scenario["schema_version"],
            "title": scenario.get("title"),
            "demo_patient_id": scenario["demo_patient_id"],
            "data_mode": scenario["data_mode"],
            "summary": scenario.get("summary", {}),
            "source_provenance": scenario["source_provenance"],
        }
