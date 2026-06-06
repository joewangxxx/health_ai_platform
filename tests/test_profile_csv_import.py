from fastapi.testclient import TestClient
from sqlmodel import select

from backend.auth import get_current_user
from backend.main import app
from backend.models import HealthRecord, MedicalDocument, User, UserProfile


def _create_user(session, username="csv_import_user"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1, BMI=21.0)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)
    return user


def _auth_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _csv_file(content: str, filename: str = "profiles.csv", content_type: str = "text/csv"):
    return {"file": (filename, content.encode("utf-8"), content_type)}


def test_import_csv_parses_single_row_with_extra_data_without_persistence(client: TestClient, session):
    user = _create_user(session)
    _auth_as(user)
    before_counts = {
        "profiles": len(session.exec(select(UserProfile)).all()),
        "records": len(session.exec(select(HealthRecord)).all()),
        "documents": len(session.exec(select(MedicalDocument)).all()),
    }

    response = client.post(
        "/api/v1/profile/import-csv",
        files=_csv_file(
            "demo_patient_id,Age,Gender,Height,Weight,BMI,GGT,extra_data,extra_data.demo_role,ignored_column\n"
            'synthea_8505e011,60,2,162.5,77.9,29.5,,"{""synthea_patient_id"": ""8505e011""}",high_risk,should_not_escape\n'
        ),
    )

    body = response.json()
    after_counts = {
        "profiles": len(session.exec(select(UserProfile)).all()),
        "records": len(session.exec(select(HealthRecord)).all()),
        "documents": len(session.exec(select(MedicalDocument)).all()),
    }
    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()

    assert response.status_code == 200
    assert body["schema_version"] == "platform_profile_import.v1"
    assert body["demo_patient_id"] == "synthea_8505e011"
    assert body["profile"]["Age"] == 60
    assert body["profile"]["Gender"] == 2
    assert body["profile"]["Height"] == 162.5
    assert body["profile"]["GGT"] is None
    assert body["profile"]["extra_data"] == {
        "synthea_patient_id": "8505e011",
        "demo_role": "high_risk",
    }
    assert body["source_tags"] == [
        "platform_profile_csv",
        "platform_demo_profiles.v1",
        "demo_patient:synthea_8505e011",
    ]
    assert body["metadata"]["row_count"] == 1
    assert "ignored_column" in body["metadata"]["ignored_columns"]
    assert after_counts == before_counts
    assert stored_profile.BMI == 21.0

    app.dependency_overrides.clear()


def test_import_csv_requires_selector_for_multi_row_files(client: TestClient, session):
    user = _create_user(session, "csv_multi_missing_selector")
    _auth_as(user)

    response = client.post(
        "/api/v1/profile/import-csv",
        files=_csv_file("demo_patient_id,Age\nsynthea_a,40\nsynthea_b,50\n"),
    )

    assert response.status_code == 400
    assert "demo_patient_id" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_import_csv_rejects_unknown_or_duplicate_demo_patient_id(client: TestClient, session):
    user = _create_user(session, "csv_selector_errors")
    _auth_as(user)

    unknown_response = client.post(
        "/api/v1/profile/import-csv",
        params={"demo_patient_id": "synthea_missing"},
        files=_csv_file("demo_patient_id,Age\nsynthea_a,40\n"),
    )
    duplicate_response = client.post(
        "/api/v1/profile/import-csv",
        params={"demo_patient_id": "synthea_a"},
        files=_csv_file("demo_patient_id,Age\nsynthea_a,40\nsynthea_a,41\n"),
    )

    assert unknown_response.status_code == 400
    assert "No row found" in unknown_response.json()["detail"]
    assert duplicate_response.status_code == 400
    assert "Multiple rows" in duplicate_response.json()["detail"]

    app.dependency_overrides.clear()


def test_import_csv_rejects_non_csv_and_invalid_numeric_values(client: TestClient, session):
    user = _create_user(session, "csv_type_errors")
    _auth_as(user)

    non_csv_response = client.post(
        "/api/v1/profile/import-csv",
        files=_csv_file('{"Age": 40}', filename="profiles.json", content_type="application/json"),
    )
    invalid_numeric_response = client.post(
        "/api/v1/profile/import-csv",
        files=_csv_file("demo_patient_id,Age,BMI\nsynthea_a,not-a-number,25.2\n"),
    )

    assert non_csv_response.status_code == 400
    assert "CSV" in non_csv_response.json()["detail"]
    assert invalid_numeric_response.status_code == 400
    assert "Age" in invalid_numeric_response.json()["detail"]

    app.dependency_overrides.clear()
