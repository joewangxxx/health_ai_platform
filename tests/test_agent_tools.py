import json
from datetime import datetime, timedelta

from backend.models import HealthRecord, MedicalDocument, User, UserProfile
from backend.services.agent_tools import (
    TOOL_REGISTRY,
    agent_tool,
    execute_registered_tool,
    get_tool_definitions,
)


def test_agent_tool_registry_tracks_read_only_metadata():
    @agent_tool(name="demo_registry_tool", read_only=True, scope="self_only")
    def demo_registry_tool(*, user, session):
        return {"ok": True}

    assert TOOL_REGISTRY["demo_registry_tool"]["read_only"] is True
    assert TOOL_REGISTRY["demo_registry_tool"]["scope"] == "self_only"


def test_execute_registered_tool_reads_current_user_profile(session):
    user = User(
        username="agent_tool_user",
        email="agent_tool_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        Age=48,
        Gender=1,
        BMI=27.2,
        SBP=148,
        Glucose_Fasting=6.8,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile

    result = execute_registered_tool(
        "get_user_profile_summary",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["tool"] == "get_user_profile_summary"
    assert result["result"]["age"] == 48
    assert any("BMI偏高" in flag for flag in result["result"]["abnormal_flags"])


def test_execute_registered_tool_rejects_unknown_tool(session):
    user = User(
        id=99,
        username="unknown_tool_user",
        email="unknown_tool_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )

    result = execute_registered_tool(
        "missing_tool",
        user=user,
        session=session,
    )

    assert result["status"] == "error"
    assert result["reason"] == "tool_not_found"


def test_execute_registered_tool_blocks_tool_when_question_type_is_not_applicable(session):
    user = User(
        username="lane_mismatch_user",
        email="lane_mismatch_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    result = execute_registered_tool(
        "medication_summary_lookup",
        user=user,
        session=session,
        allowed_tool_names=["medication_summary_lookup"],
        lane="medication_related",
        query_text="Should I start metformin now or increase my current dose?",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "tool_not_applicable_for_question"
    assert result["tool"] == "medication_summary_lookup"


def test_tool_definitions_expose_openai_tool_schema():
    definitions = get_tool_definitions(["get_user_profile_summary", "search_medical_guidelines"])

    assert definitions[0]["type"] == "function"
    assert definitions[0]["function"]["name"] == "get_user_profile_summary"
    assert definitions[0]["function"]["parameters"]["type"] == "object"
    assert definitions[1]["function"]["name"] == "search_medical_guidelines"
    assert "query" in definitions[1]["function"]["parameters"]["properties"]


def test_tool_definitions_include_new_safe_read_only_tool_schemas():
    definitions = get_tool_definitions(
        [
            "medication_summary_lookup",
            "recent_metric_anomaly_lookup",
            "report_comparison_lookup",
        ]
    )

    by_name = {item["function"]["name"]: item["function"] for item in definitions}

    assert by_name["medication_summary_lookup"]["parameters"]["properties"]["document_id"]["type"] == ["integer", "null"]
    assert by_name["recent_metric_anomaly_lookup"]["parameters"]["properties"]["limit"]["maximum"] == 10
    assert by_name["report_comparison_lookup"]["parameters"]["properties"]["baseline_document_id"]["type"] == ["integer", "null"]


def test_medication_summary_lookup_returns_bounded_normalized_summary(session):
    user = User(
        username="medication_lookup_user",
        email="medication_lookup_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    document = MedicalDocument(
        user_id=user.id,
        file_name="med-report.pdf",
        file_path="uploads/med-report.pdf",
        file_url="/static/med-report.pdf",
        upload_date=datetime.utcnow(),
        ocr_summary=json.dumps(
            {
                "schema_version": "ocr_summary.v1",
                "metrics": {},
                "extra_findings": {},
                "medications": [
                    {
                        "name": "Metformin",
                        "dose": "500",
                        "unit": "mg",
                        "frequency": "BID",
                        "route": "oral",
                        "instruction": "after meals",
                    },
                    {
                        "name": "Amlodipine",
                        "dose": "5",
                        "unit": "mg",
                        "frequency": "QD",
                    },
                ],
            },
            ensure_ascii=False,
        ),
    )
    session.add(document)
    session.commit()

    result = execute_registered_tool(
        "medication_summary_lookup",
        user=user,
        session=session,
        limit=1,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_medication_summary"] is True
    assert result["result"]["document_id"] == document.id
    assert result["result"]["summary_source"] == "medical_document_ocr_summary"
    assert result["result"]["medication_summary"]["schema_version"] == "medication_summary.v1"
    assert result["result"]["medication_summary"]["count"] == 1
    assert result["result"]["medication_summary"]["medication_items_truncated"] is True
    assert len(result["result"]["medication_summary"]["medication_items"]) == 1
    assert result["result"]["evidence_metadata"]["coverage"] == "partial"
    assert result["result"]["evidence_metadata"]["freshness"] == "fresh"
    assert result["result"]["evidence_metadata"]["confidence"] == "medium"
    assert "additional_medication_items" in result["result"]["evidence_metadata"]["missing_fields"]


def test_recent_metric_anomaly_lookup_returns_bounded_anomalies(session):
    user = User(
        username="metric_anomaly_user",
        email="metric_anomaly_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    record = HealthRecord(
        user_id=user.id,
        source="manual_update",
        record_date=datetime.utcnow(),
        metrics=json.dumps(
            {
                "Glucose_Fasting": 6.9,
                "SBP": 148,
                "BMI": 28.1,
            },
            ensure_ascii=False,
        ),
    )
    session.add(record)
    session.commit()

    result = execute_registered_tool(
        "recent_metric_anomaly_lookup",
        user=user,
        session=session,
        limit=1,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_metric_anomalies"] is True
    assert result["result"]["evaluated_source"] == "health_record"
    assert result["result"]["summary"]["count"] >= 1
    assert len(result["result"]["items"]) == 1
    assert result["result"]["items"][0]["source_ref"] == "health_record_metrics"
    assert result["result"]["evidence_metadata"]["coverage"] == "partial"
    assert result["result"]["evidence_metadata"]["freshness"] == "fresh"
    assert result["result"]["evidence_metadata"]["confidence"] == "medium"
    assert "additional_anomalies" in result["result"]["evidence_metadata"]["missing_fields"]


def test_report_comparison_lookup_compares_two_user_documents(session):
    user = User(
        username="comparison_lookup_user",
        email="comparison_lookup_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    baseline_document = MedicalDocument(
        user_id=user.id,
        file_name="baseline-report.pdf",
        file_path="uploads/baseline-report.pdf",
        file_url="/static/baseline-report.pdf",
        upload_date=datetime.utcnow() - timedelta(days=3),
        ocr_summary=json.dumps(
            {
                "Glucose_Fasting": {"value": 5.6, "unit": "mmol/L"},
                "HbA1c": {"value": 5.7, "unit": "%"},
            },
            ensure_ascii=False,
        ),
    )
    comparison_document = MedicalDocument(
        user_id=user.id,
        file_name="comparison-report.pdf",
        file_path="uploads/comparison-report.pdf",
        file_url="/static/comparison-report.pdf",
        upload_date=datetime.utcnow(),
        ocr_summary=json.dumps(
            {
                "Glucose_Fasting": {"value": 6.8, "unit": "mmol/L"},
                "HbA1c": {"value": 6.0, "unit": "%"},
            },
            ensure_ascii=False,
        ),
    )
    session.add(baseline_document)
    session.add(comparison_document)
    session.commit()

    result = execute_registered_tool(
        "report_comparison_lookup",
        user=user,
        session=session,
        baseline_document_id=baseline_document.id,
        comparison_document_id=comparison_document.id,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_report_comparison"] is True
    assert result["result"]["baseline_document_id"] == baseline_document.id
    assert result["result"]["evidence_metadata"]["coverage"] == "full"
    assert result["result"]["evidence_metadata"]["freshness"] == "fresh"
    assert result["result"]["evidence_metadata"]["confidence"] == "high"
    assert result["result"]["evidence_metadata"]["comparable_fields_count"] == 2


def test_medication_summary_lookup_returns_empty_summary_when_no_medication_facts_exist(session):
    user = User(
        username="empty_medication_user",
        email="empty_medication_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    result = execute_registered_tool(
        "medication_summary_lookup",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_medication_summary"] is False
    assert result["result"]["medication_summary"] is None
    assert result["result"]["evidence_metadata"]["coverage"] == "empty"
    assert result["result"]["evidence_metadata"]["freshness"] == "unknown"
    assert result["result"]["evidence_metadata"]["confidence"] == "low"
    assert "medication_summary" in result["result"]["evidence_metadata"]["missing_fields"]


def test_report_summary_lookup_marks_stale_old_documents_with_partial_metadata(session):
    user = User(
        username="stale_report_user",
        email="stale_report_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    document = MedicalDocument(
        user_id=user.id,
        file_name="stale-report.pdf",
        file_path="uploads/stale-report.pdf",
        file_url="/static/stale-report.pdf",
        upload_date=datetime.utcnow() - timedelta(days=45),
        ocr_summary=json.dumps({"summary": "stale report summary only"}, ensure_ascii=False),
    )
    session.add(document)
    session.commit()

    result = execute_registered_tool(
        "report_summary_lookup",
        user=user,
        session=session,
        document_id=document.id,
    )

    assert result["status"] == "ok"
    assert result["result"]["evidence_metadata"]["freshness"] == "stale"
    assert result["result"]["evidence_metadata"]["coverage"] == "partial"
    assert result["result"]["evidence_metadata"]["confidence"] == "low"


def test_compatibility_aliases_continue_to_work(session):
    user = User(
        username="alias_tool_user",
        email="alias_tool_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    result = execute_registered_tool(
        "report_summary_lookup",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["tool"] == "report_summary_lookup"


def test_report_summary_lookup_returns_latest_user_owned_ocr_summary(session):
    user = User(
        username="report_lookup_user",
        email="report_lookup_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    older_document = MedicalDocument(
        user_id=user.id,
        file_name="older-report.pdf",
        file_path="uploads/older-report.pdf",
        file_url="/static/older-report.pdf",
        upload_date=datetime.utcnow() - timedelta(days=2),
        ocr_summary=json.dumps({"glucose": {"value": 5.2}}, ensure_ascii=False),
    )
    latest_document = MedicalDocument(
        user_id=user.id,
        file_name="latest-report.pdf",
        file_path="uploads/latest-report.pdf",
        file_url="/static/latest-report.pdf",
        upload_date=datetime.utcnow(),
        ocr_summary=json.dumps({"summary": "latest persisted OCR summary"}, ensure_ascii=False),
    )
    session.add(older_document)
    session.add(latest_document)
    session.commit()
    session.refresh(latest_document)

    result = execute_registered_tool(
        "report_summary_lookup",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_report_summary"] is True
    assert result["result"]["document_id"] == latest_document.id
    assert result["result"]["file_name"] == "latest-report.pdf"
    assert result["result"]["summary_source"] == "medical_document_ocr_summary"
    assert result["result"]["report_summary"]["schema_version"] == "ocr_summary.v1"
    assert result["result"]["report_summary"]["narrative_summary"] == "latest persisted OCR summary"
    assert result["result"]["report_summary"]["metrics"] == []
    assert result["result"]["report_summary"]["extra_findings_count"] == 0


def test_report_summary_lookup_normalizes_legacy_flat_payload(session):
    user = User(
        username="legacy_report_user",
        email="legacy_report_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    document = MedicalDocument(
        user_id=user.id,
        file_name="legacy-report.pdf",
        file_path="uploads/legacy-report.pdf",
        file_url="/static/legacy-report.pdf",
        upload_date=datetime.utcnow(),
        ocr_summary=json.dumps(
            {
                "Age": 45,
                "Gender": 1,
                "Glu": {"value": 6.8, "unit": "mmol/L", "ref_range": "3.9-6.1", "hospital_flag": "H"},
                "TC": 5.4,
                "summary": "Legacy summary text",
            },
            ensure_ascii=False,
        ),
    )
    session.add(document)
    session.commit()

    result = execute_registered_tool(
        "report_summary_lookup",
        user=user,
        session=session,
        document_id=document.id,
    )

    summary = result["result"]["report_summary"]

    assert result["status"] == "ok"
    assert summary["schema_version"] == "ocr_summary.v1"
    assert summary["patient_context"] == {"Age": 45, "Gender": 1}
    assert [metric["metric_key"] for metric in summary["metrics"]] == [
        "Glucose_Fasting",
        "Cholesterol_Total",
    ]
    assert summary["metrics_truncated"] is False


def test_report_summary_lookup_returns_empty_shape_for_missing_or_cross_user_document(session):
    owner = User(
        username="report_owner",
        email="report_owner@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    other_user = User(
        username="report_other_user",
        email="report_other_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(owner)
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_document = MedicalDocument(
        user_id=other_user.id,
        file_name="other-report.pdf",
        file_path="uploads/other-report.pdf",
        file_url="/static/other-report.pdf",
        upload_date=datetime.utcnow(),
        ocr_summary=json.dumps({"summary": "other user data"}, ensure_ascii=False),
    )
    session.add(other_document)
    session.commit()
    session.refresh(other_document)

    result = execute_registered_tool(
        "report_summary_lookup",
        user=owner,
        session=session,
        document_id=other_document.id,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_report_summary"] is False
    assert result["result"]["document_id"] is None
    assert result["result"]["report_summary"] is None


def test_recent_abnormal_metrics_lookup_uses_latest_health_record_and_applies_limit(session):
    user = User(
        username="abnormal_metrics_user",
        email="abnormal_metrics_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    record = HealthRecord(
        user_id=user.id,
        source="manual_update",
        record_date=datetime.utcnow(),
        metrics=json.dumps(
            {
                "Glucose_Fasting": 6.8,
                "SBP": 148,
                "BMI": 28.1,
            },
            ensure_ascii=False,
        ),
    )
    session.add(record)
    session.commit()

    result = execute_registered_tool(
        "recent_abnormal_metrics_lookup",
        user=user,
        session=session,
        limit=2,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_abnormal_metrics"] is True
    assert result["result"]["evaluated_source"] == "health_record"
    assert result["result"]["summary"]["count"] >= 2
    assert len(result["result"]["items"]) == 2
    assert result["result"]["items"][0]["metric_key"] in {"Glucose_Fasting", "SBP", "BMI"}
    assert result["result"]["items"][0]["detection_source"] in {"standard_range", "hospital_flag", "extracted_range"}


def test_recent_abnormal_metrics_lookup_falls_back_to_profile_when_no_history_exists(session):
    user = User(
        username="profile_metrics_user",
        email="profile_metrics_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        BMI=29.4,
        SBP=152,
        Glucose_Fasting=7.1,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile

    result = execute_registered_tool(
        "recent_abnormal_metrics_lookup",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_abnormal_metrics"] is True
    assert result["result"]["evaluated_source"] == "user_profile"
    assert result["result"]["summary"]["status"] in {"warning", "alert"}
    assert any(item["metric_key"] == "Glucose_Fasting" for item in result["result"]["items"])


def test_latest_analysis_snapshot_lookup_prefers_latest_health_record_snapshot(session):
    user = User(
        username="analysis_snapshot_user",
        email="analysis_snapshot_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    record = HealthRecord(
        user_id=user.id,
        source="analysis_run",
        record_date=datetime.utcnow(),
        metrics="{}",
        risk_snapshot=json.dumps(
            {
                "schema_version": "risk_snapshot.v1",
                "generated_at": datetime.utcnow().isoformat(),
                "source": "analyze_comprehensive",
                "findings": [
                    {"key": "diabetes", "label": "diabetes", "risk_level": "medium", "probability": 0.42},
                    {"key": "heart_failure", "label": "heart_failure", "risk_level": "high", "probability": 0.88},
                ],
                "ckm": {"stage": 2, "stage_name": "stage_2"},
            },
            ensure_ascii=False,
        ),
    )
    session.add(record)
    session.commit()

    result = execute_registered_tool(
        "latest_analysis_snapshot_lookup",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_analysis_snapshot"] is True
    assert result["result"]["snapshot_source"] == "health_record_risk_snapshot"
    assert result["result"]["captured_at"] == record.record_date.isoformat()
    assert result["result"]["raw_snapshot_present"] is True
    assert result["result"]["top_findings"][0]["key"] == "heart_failure"
    assert result["result"]["ckm"] == {"stage": 2, "stage_name": "stage_2"}


def test_latest_analysis_snapshot_lookup_falls_back_to_profile_risk_history(session):
    user = User(
        username="analysis_profile_user",
        email="analysis_profile_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        risk_history=json.dumps(
            {
                "schema_version": "risk_snapshot.v1",
                "generated_at": datetime.utcnow().isoformat(),
                "source": "analyze_comprehensive",
                "findings": [
                    {"key": "kidney_risk", "label": "kidney_risk", "risk_level": "high", "probability": 0.815}
                ],
                "ckm": {"stage": 1, "stage_name": "stage_1"},
            },
            ensure_ascii=False,
        ),
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile

    result = execute_registered_tool(
        "latest_analysis_snapshot_lookup",
        user=user,
        session=session,
    )

    assert result["status"] == "ok"
    assert result["result"]["has_analysis_snapshot"] is True
    assert result["result"]["snapshot_source"] == "user_profile_risk_history"
    assert result["result"]["captured_at"] is None
    assert result["result"]["top_findings"][0]["key"] == "kidney_risk"
    assert result["result"]["top_findings"][0]["probability"] == 0.815
