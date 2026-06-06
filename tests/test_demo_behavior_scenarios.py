import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import select

import backend.main as backend_main
from backend.config import PROJECT_ROOT
from backend.auth import get_current_user
from backend.main import app
from backend.models import HealthRecord, IoTHealthData, MedicalDocument, User, UserProfile


def _create_user(session, username="behavior_demo_user"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1, Age=52, Gender=1, BMI=27.5)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)
    return user


def _auth_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _side_effect_counts(session, user_id):
    return {
        "iot": len(session.exec(select(IoTHealthData).where(IoTHealthData.user_id == user_id)).all()),
        "records": len(session.exec(select(HealthRecord).where(HealthRecord.user_id == user_id)).all()),
        "documents": len(session.exec(select(MedicalDocument).where(MedicalDocument.user_id == user_id)).all()),
        "profiles": len(session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).all()),
    }


def test_behavior_scenario_list_returns_metadata_without_persistence(client: TestClient, session):
    user = _create_user(session)
    _auth_as(user)
    before_counts = _side_effect_counts(session, user.id)

    response = client.get("/api/v1/demo/behavior-scenarios")

    body = response.json()
    after_counts = _side_effect_counts(session, user.id)
    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert len(body["scenarios"]) == 3
    first = body["scenarios"][0]
    assert first["schema_version"] == "behavior_day_scenario.v1"
    assert first["scenario_id"] == "metabolic_day_001"
    assert first["data_mode"] == "simulated_demo"
    assert first["source_provenance"]["artifact_schema"] == "behavior_day_scenario.v1"
    assert "timeline" not in first
    assert after_counts == before_counts
    assert stored_profile.risk_history is None

    app.dependency_overrides.clear()


def test_behavior_scenario_detail_returns_frozen_event_types_and_lifestyle_context(client: TestClient, session):
    user = _create_user(session, "behavior_demo_detail_user")
    _auth_as(user)
    before_counts = _side_effect_counts(session, user.id)

    response = client.get("/api/v1/demo/behavior-scenarios/metabolic_day_001")

    body = response.json()
    scenario = body["scenario"]
    event_types = {event["event_type"] for event in scenario["timeline"]}
    diet_events = [event for event in scenario["timeline"] if event["event_type"] == "diet_vision"]
    after_counts = _side_effect_counts(session, user.id)
    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert scenario["schema_version"] == "behavior_day_scenario.v1"
    assert scenario["data_mode"] == "simulated_demo"
    assert {"vitals", "daily_summary", "diet_vision"}.issubset(event_types)
    assert all(event["schema_version"] == "behavior_timeline_event.v1" for event in scenario["timeline"])
    assert all(event["data_mode"] == "simulated_demo" for event in scenario["timeline"])
    assert diet_events[0]["payload"]["schema_version"] == "diet_vision_event.v1"
    assert diet_events[0]["payload"]["vision_provenance"]["source_type"] == "simulated_demo"
    assert scenario["lifestyle_context"]["schema_version"] == "lifestyle_context.v1"
    assert scenario["lifestyle_context"]["data_mode"] == "simulated_demo"
    assert scenario["lifestyle_context"]["source_provenance"]["artifact_schema"] == "behavior_day_scenario.v1"
    assert after_counts == before_counts
    assert stored_profile.risk_history is None

    app.dependency_overrides.clear()


def test_behavior_scenario_detail_returns_404_for_unknown_scenario(client: TestClient, session):
    user = _create_user(session, "behavior_demo_unknown_user")
    _auth_as(user)

    response = client.get("/api/v1/demo/behavior-scenarios/not_a_scenario")

    assert response.status_code == 404
    assert "scenario" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_behavior_scenario_repository_rejects_invalid_artifact(tmp_path):
    from backend.services.demo_behavior_scenarios import (
        BehaviorScenarioRepository,
        DemoScenarioArtifactError,
    )

    artifact_path = Path(PROJECT_ROOT) / "data/demo/behavior_day_scenarios.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    invalid_artifact = copy.deepcopy(artifact)
    invalid_artifact["scenarios"][0]["timeline"][0]["event_type"] = "unsupported_event"
    invalid_path = tmp_path / "invalid_behavior_day_scenarios.json"
    invalid_path.write_text(json.dumps(invalid_artifact), encoding="utf-8")

    repository = BehaviorScenarioRepository(artifact_path=invalid_path)

    try:
        repository.list_scenarios()
    except DemoScenarioArtifactError as exc:
        assert "event_type" in str(exc)
    else:
        raise AssertionError("Invalid behavior scenario artifact should be rejected")


def test_analyze_comprehensive_accepts_valid_lifestyle_context_without_persistence(client, session, monkeypatch):
    user = _create_user(session, "lifestyle_context_valid_user")
    _auth_as(user)
    before_counts = _side_effect_counts(session, user.id)

    class DummyFusionEngine:
        def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
            return {
                "Hypertension": {
                    "final_risk": 18.5,
                    "level": "Medium",
                    "breakdown": {
                        "base_clinical": "18.5%",
                        "gene_modifier": "x1.0",
                        "lifestyle_modifier": "x0.9",
                    },
                }
            }

    monkeypatch.setattr(backend_main, "fusion_engine", DummyFusionEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {"Age": 52, "Gender": 1, "BMI": 27.5},
            "user_snps": {},
            "lifestyle_context": {
                "schema_version": "lifestyle_context.v1",
                "data_mode": "simulated_demo",
                "scenario_id": "metabolic_day_001",
                "summary": {"steps": 4100, "sleep_hours": 5.7},
                "modifier_inputs": {"sleep_quality": "short_fragmented"},
                "source_provenance": {
                    "source_type": "demo_scenario",
                    "artifact_schema": "behavior_day_scenario.v1",
                    "generated_from": ["platform_demo_profiles.v1"],
                },
            },
        },
    )

    after_counts = _side_effect_counts(session, user.id)
    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert after_counts == before_counts
    assert stored_profile.risk_history is None

    app.dependency_overrides.clear()


def test_analyze_comprehensive_rejects_malformed_lifestyle_context(client, session, monkeypatch):
    user = _create_user(session, "lifestyle_context_invalid_user")
    _auth_as(user)

    class FailingFusionEngine:
        def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
            raise AssertionError("invalid lifestyle_context should fail before analysis")

    monkeypatch.setattr(backend_main, "fusion_engine", FailingFusionEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {"Age": 52, "Gender": 1, "BMI": 27.5},
            "user_snps": {},
            "lifestyle_context": {
                "schema_version": "lifestyle_context.v1",
                "data_mode": "simulated_demo",
                "scenario_id": "metabolic_day_001",
                "summary": {"steps": 4100},
                "modifier_inputs": {},
            },
        },
    )

    assert response.status_code == 422

    app.dependency_overrides.clear()
