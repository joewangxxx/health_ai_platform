import json
from pathlib import Path

from sqlmodel import select

from backend.models import HealthRecord, MedicalDocument, User, UserProfile
from backend.services import payload_normalization
from backend.services.payload_normalization import scan_legacy_payload_shapes


def test_ocr_normalization_promotes_approved_report_level_biomarkers():
    normalized = payload_normalization.normalize_ocr_summary_payload(
        {
            "AST": {"value": 19, "unit": "U/L"},
            "HGB": {"value": 165, "unit": "g/L"},
            "UA": {"value": 420, "unit": "umol/L"},
        }
    )

    assert normalized is not None
    assert normalized["metrics"]["AST"]["value"] == 19
    assert normalized["metrics"]["HGB"]["value"] == 165
    assert normalized["metrics"]["UA"]["value"] == 420
    assert "AST" not in normalized["extra_findings"]
    assert "HGB" not in normalized["extra_findings"]
    assert "UA" not in normalized["extra_findings"]


def _collect_payload_rows(session):
    return [
        {
            "entity": "MedicalDocument",
            "id": document.id,
            "payload": document.ocr_summary,
        }
        for document in session.exec(select(MedicalDocument)).all()
    ] + [
        {
            "entity": "HealthRecord",
            "id": record.id,
            "payload": record.risk_snapshot,
        }
        for record in session.exec(select(HealthRecord)).all()
    ] + [
        {
            "entity": "UserProfile",
            "id": profile.id,
            "payload": profile.risk_history,
        }
        for profile in session.exec(select(UserProfile)).all()
    ]


def test_repair_legacy_payload_rows_backfills_only_legacy_rows(session):
    repair_legacy_payload_rows = getattr(payload_normalization, "repair_legacy_payload_rows", None)
    assert callable(repair_legacy_payload_rows)

    user = User(
        username="legacy_payload_user",
        email="legacy_payload_user@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    canonical_user = User(
        username="canonical_payload_user",
        email="canonical_payload_user@example.com",
        hashed_password="hashed",
    )
    session.add(canonical_user)
    session.commit()
    session.refresh(canonical_user)

    legacy_ocr_payload = json.dumps(
        {
            "Age": 52,
            "Gender": 1,
            "Height": 172,
            "Weight": 78,
            "Glu": {"value": 6.1, "unit": "mmol/L"},
            "summary": "Legacy report summary",
        },
        ensure_ascii=False,
    )
    canonical_ocr_payload = json.dumps(
        {
            "schema_version": "ocr_summary.v1",
            "document_type": "lab_report",
            "patient_context": {"Age": 52, "Gender": 1},
            "metrics": {},
            "extra_findings": {},
            "narrative_summary": "Canonical report summary",
        },
        ensure_ascii=False,
    )

    legacy_risk_payload = json.dumps(
        {
            "diabetes": {"label": "Diabetes", "risk_level": "High", "probability": 0.82},
            "ckm": {"stage": 3, "stage_name": "CKM-3"},
            "captured_at": "2026-03-28T00:00:00",
        },
        ensure_ascii=False,
    )
    canonical_risk_payload = json.dumps(
        {
            "schema_version": "risk_snapshot.v1",
            "generated_at": "2026-03-28T00:00:00",
            "source": "canonical_test",
            "findings": [],
            "ckm": None,
        },
        ensure_ascii=False,
    )

    legacy_document = MedicalDocument(
        user_id=user.id,
        file_name="legacy-report.pdf",
        file_path="/tmp/legacy-report.pdf",
        file_url="/static/legacy-report.pdf",
        ocr_summary=legacy_ocr_payload,
    )
    canonical_document = MedicalDocument(
        user_id=user.id,
        file_name="canonical-report.pdf",
        file_path="/tmp/canonical-report.pdf",
        file_url="/static/canonical-report.pdf",
        ocr_summary=canonical_ocr_payload,
    )

    legacy_profile = UserProfile(user_id=user.id, risk_history=legacy_risk_payload)
    canonical_profile = UserProfile(user_id=canonical_user.id, risk_history=canonical_risk_payload)

    session.add(legacy_document)
    session.add(canonical_document)
    session.add(legacy_profile)
    session.add(canonical_profile)
    legacy_record = HealthRecord(
        user_id=user.id,
        source="manual",
        metrics=json.dumps({"BMI": 24.5}, ensure_ascii=False),
        risk_snapshot=legacy_risk_payload,
    )
    canonical_record = HealthRecord(
        user_id=canonical_user.id,
        source="manual",
        metrics=json.dumps({"BMI": 24.5}, ensure_ascii=False),
        risk_snapshot=canonical_risk_payload,
    )
    session.add(legacy_record)
    session.add(canonical_record)
    session.commit()

    before_rows = _collect_payload_rows(session)
    assert len(scan_legacy_payload_shapes(before_rows)) == 3

    report = repair_legacy_payload_rows(session)

    assert report["checked_rows"] == 6
    assert report["legacy_count_before"] == 3
    assert report["repaired_count"] == 3
    assert report["unrepairable_count"] == 0
    assert report["legacy_count_after"] == 0

    repaired_document = session.get(MedicalDocument, legacy_document.id)
    repaired_profile = session.get(UserProfile, legacy_profile.id)
    repaired_record = session.get(HealthRecord, legacy_record.id)

    assert repaired_document is not None
    assert repaired_profile is not None
    assert repaired_record is not None

    repaired_ocr = json.loads(repaired_document.ocr_summary)
    repaired_risk_history = json.loads(repaired_profile.risk_history)
    repaired_risk_snapshot = json.loads(repaired_record.risk_snapshot)

    assert repaired_ocr["schema_version"] == "ocr_summary.v1"
    assert repaired_ocr["metrics"]["Glucose_Fasting"]["value"] == 6.1
    assert repaired_ocr["narrative_summary"] == "Legacy report summary"

    assert repaired_risk_history["schema_version"] == "risk_snapshot.v1"
    assert repaired_risk_history["findings"][0]["key"] == "diabetes"
    assert repaired_risk_snapshot["schema_version"] == "risk_snapshot.v1"
    assert repaired_risk_snapshot["findings"][0]["key"] == "diabetes"

    canonical_document_after = session.get(MedicalDocument, canonical_document.id)
    assert canonical_document_after is not None
    assert canonical_document_after.ocr_summary == canonical_ocr_payload


def test_repair_legacy_payload_script_exists():
    assert (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "scripts"
        / "repair_legacy_payload_shapes.py"
    ).exists()
