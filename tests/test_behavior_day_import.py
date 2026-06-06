import json

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.auth import get_current_user
import backend.main as backend_main
from backend.main import app
from backend.models import HealthRecord, IoTHealthData, MedicalDocument, User, UserProfile


def _create_user(session, username="behavior_import_user"):
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


def _upload_file(content: bytes | str, filename: str, content_type: str):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return {"file": (filename, content, content_type)}


def _assert_error(response, status_code: int, error_code: str, detail_path: str | None = None):
    body = response.json()
    assert response.status_code == status_code
    assert body["status"] == "error"
    assert body["error"]["code"] == error_code
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], list)
    if detail_path is not None:
        assert any(detail["path"] == detail_path for detail in body["error"]["details"])
    return body


def test_import_behavior_day_csv_returns_user_uploaded_timeline_without_persistence(client: TestClient, session):
    user = _create_user(session)
    _auth_as(user)
    before_counts = _side_effect_counts(session, user.id)

    response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file(
            "patient_id,local_date,time,event_type,label,meal_type,food_items,calories,carbs,protein,fat,sodium_mg\n"
            'patient_a,2026-05-13,07:00,diet_vision,Breakfast,breakfast,"oatmeal;egg",420,48,18,14,480\n'
            "patient_a,2026-05-13,22:30,sleep,Sleep start,,,,,,,\n",
            "behavior.csv",
            "text/csv",
        ),
    )

    body = response.json()
    behavior_day = body["behavior_day"]
    lifestyle_context = body["lifestyle_context"]
    import_result = body["import"]
    after_counts = _side_effect_counts(session, user.id)
    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert import_result["schema_version"] == "platform_behavior_day_import_result.v1"
    assert import_result["data_mode"] == "user_uploaded"
    assert import_result["source_format"] == "csv"
    assert import_result["filename"] == "behavior.csv"
    assert import_result["validation"]["event_count"] == 2
    assert import_result["validation"]["warnings"] == []
    assert import_result["source_provenance"] == {
        "source_type": "user_uploaded",
        "source_label": "uploaded_csv",
        "source_format": "csv",
        "artifact_schema": "platform_behavior_day_csv.v1",
        "filename": "behavior.csv",
    }
    assert body["metadata"]["format"] == "csv"
    assert body["validation"]["event_count"] == 2
    assert behavior_day["schema_version"] == "behavior_day_scenario.v1"
    assert behavior_day["patient_id"] == "patient_a"
    assert behavior_day["local_date"] == "2026-05-13"
    assert behavior_day["data_mode"] == "user_uploaded"
    assert behavior_day["source_provenance"]["source_type"] == "user_uploaded"
    assert behavior_day["source_provenance"]["source_label"] == "uploaded_csv"
    assert all(event["data_mode"] == "user_uploaded" for event in behavior_day["timeline"])
    assert behavior_day["timeline"][0]["payload"]["schema_version"] == "diet_vision_event.v1"
    assert behavior_day["timeline"][0]["payload"]["vision_provenance"]["source_type"] == "user_uploaded"
    assert lifestyle_context["schema_version"] == "lifestyle_context.v1"
    assert lifestyle_context["data_mode"] == "user_uploaded"
    assert lifestyle_context["source_provenance"]["source_type"] == "user_uploaded"
    assert lifestyle_context["source_provenance"]["source_label"] == "uploaded_csv"
    assert lifestyle_context["source_provenance"]["source_format"] == "csv"
    assert lifestyle_context["source_provenance"]["artifact_schema"] == "platform_behavior_day_csv.v1"
    assert lifestyle_context["summary"]["estimated_calories"] == 420
    assert behavior_day["lifestyle_context"] == lifestyle_context
    assert after_counts == before_counts
    assert stored_profile.risk_history is None

    app.dependency_overrides.clear()


def test_import_behavior_day_accepts_matching_selectors(client: TestClient, session):
    user = _create_user(session, "behavior_import_selector_user")
    _auth_as(user)

    response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        data={"patient_id": "patient_a", "local_date": "2026-05-13"},
        files=_upload_file(
            "patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,activity\n",
            "behavior.csv",
            "text/csv",
        ),
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["behavior_day"]["patient_id"] == "patient_a"
    assert body["behavior_day"]["local_date"] == "2026-05-13"

    app.dependency_overrides.clear()


def test_import_behavior_day_rejects_selector_mismatch_with_structured_error(client: TestClient, session):
    user = _create_user(session, "behavior_import_selector_mismatch_user")
    _auth_as(user)

    patient_response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        data={"patient_id": "other_patient"},
        files=_upload_file(
            "patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,activity\n",
            "behavior.csv",
            "text/csv",
        ),
    )
    date_response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        data={"local_date": "2026-05-14"},
        files=_upload_file(
            "patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,activity\n",
            "behavior.csv",
            "text/csv",
        ),
    )

    _assert_error(patient_response, 400, "behavior_day_validation_failed", "patient_id")
    _assert_error(date_response, 400, "behavior_day_validation_failed", "local_date")

    app.dependency_overrides.clear()


def test_import_behavior_day_json_returns_user_uploaded_context(client: TestClient, session):
    user = _create_user(session, "behavior_import_json_user")
    _auth_as(user)

    response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file(
            json.dumps(
                {
                    "schema_version": "platform_behavior_day_json.v1",
                    "patient_id": "patient_json",
                    "local_date": "2026-05-13",
                    "timeline": [
                        {
                            "time": "08:10",
                            "event_type": "activity",
                            "label": "Morning walk",
                            "payload": {"steps": 1800, "active_minutes": 18},
                        }
                    ],
                    "summary": {"steps": 1800, "active_minutes": 18, "sleep_hours": 6.5},
                }
            ),
            "behavior.json",
            "application/json",
        ),
    )

    body = response.json()

    assert response.status_code == 200
    assert body["import"]["schema_version"] == "platform_behavior_day_import_result.v1"
    assert body["import"]["source_format"] == "json"
    assert body["import"]["source_provenance"] == {
        "source_type": "user_uploaded",
        "source_label": "uploaded_json",
        "source_format": "json",
        "artifact_schema": "platform_behavior_day_json.v1",
        "filename": "behavior.json",
    }
    assert body["metadata"]["format"] == "json"
    assert body["behavior_day"]["scenario_id"] == "uploaded_2026-05-13_patient_json"
    assert body["behavior_day"]["timeline"][0]["event_id"] == "evt_0810_activity_001"
    assert body["lifestyle_context"]["summary"]["steps"] == 1800
    assert body["lifestyle_context"]["modifier_inputs"]["activity_level"] == "light"
    assert body["behavior_day"]["lifestyle_context"]["data_mode"] == "user_uploaded"
    assert body["behavior_day"]["lifestyle_context"] == body["lifestyle_context"]

    app.dependency_overrides.clear()


def test_import_behavior_day_rejects_unsupported_malformed_and_multi_scope_files(client: TestClient, session):
    user = _create_user(session, "behavior_import_invalid_user")
    _auth_as(user)

    unsupported = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file("{}", "behavior.txt", "text/plain"),
    )
    malformed = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file('{"schema_version": "platform_behavior_day_json.v1"', "behavior.json", "application/json"),
    )
    multiple_patients = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file(
            "patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,activity\npatient_b,2026-05-13,08:00,activity\n",
            "behavior.csv",
            "text/csv",
        ),
    )
    multiple_dates = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file(
            "patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,activity\npatient_a,2026-05-14,08:00,activity\n",
            "behavior.csv",
            "text/csv",
        ),
    )
    unsupported_event = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file(
            "patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,device_sync\n",
            "behavior.csv",
            "text/csv",
        ),
    )

    _assert_error(unsupported, 415, "unsupported_media_type", "file")
    malformed_body = _assert_error(malformed, 400, "behavior_day_validation_failed", "$")
    assert "JSON" in malformed_body["error"]["message"]
    _assert_error(multiple_patients, 400, "behavior_day_validation_failed", "patient_id")
    _assert_error(multiple_dates, 400, "behavior_day_validation_failed", "local_date")
    _assert_error(unsupported_event, 400, "behavior_day_validation_failed", "timeline[0].event_type")

    app.dependency_overrides.clear()


def test_import_behavior_day_rejects_over_max_size(client: TestClient, session):
    user = _create_user(session, "behavior_import_large_user")
    _auth_as(user)

    response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file(b"a" * (1024 * 1024 + 1), "behavior.csv", "text/csv"),
    )

    _assert_error(response, 413, "payload_too_large", "file")

    app.dependency_overrides.clear()


def test_import_behavior_day_rejects_more_than_200_events(client: TestClient, session):
    user = _create_user(session, "behavior_import_too_many_user")
    _auth_as(user)
    rows = ["patient_id,local_date,time,event_type"]
    rows.extend(f"patient_a,2026-05-13,07:{index % 60:02d},activity" for index in range(201))

    response = client.post(
        "/api/v1/lifestyle/import-behavior-day",
        files=_upload_file("\n".join(rows), "behavior.csv", "text/csv"),
    )

    _assert_error(response, 400, "behavior_day_validation_failed", "timeline")

    app.dependency_overrides.clear()


def test_analyze_comprehensive_accepts_user_uploaded_lifestyle_context_without_persistence(
    client: TestClient,
    session,
    monkeypatch,
):
    user = _create_user(session, "behavior_import_analysis_user")
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
                "data_mode": "user_uploaded",
                "scenario_id": "uploaded_2026-05-13_patient_a",
                "summary": {"steps": 1800, "active_minutes": 18},
                "modifier_inputs": {"activity_level": "light"},
                "source_provenance": {
                    "source_type": "user_uploaded",
                    "artifact_schema": "platform_behavior_day_json.v1",
                    "generated_from": ["platform_behavior_day_json.v1"],
                    "source_label": "uploaded_json",
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
