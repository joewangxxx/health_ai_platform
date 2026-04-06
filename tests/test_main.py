import asyncio
import json
import importlib
import types
import sys
import logging

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.auth import get_current_user
import backend.main as backend_main
from backend.main import app
from backend.models import HealthRecord, MedicalDocument, User, UserProfile


def _fresh_import(module_name: str, modules_to_clear: list[str]):
    saved_modules = {name: sys.modules[name] for name in modules_to_clear if name in sys.modules}
    try:
        for name in modules_to_clear:
            sys.modules.pop(name, None)
        return importlib.import_module(module_name)
    finally:
        for name, module in saved_modules.items():
            sys.modules[name] = module


def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "HealthAI Platform API is Running", "status": "active"}


def test_device_status(client: TestClient):
    response = client.get("/api/device/current")
    assert response.status_code == 200
    data = response.json()
    assert "hr" in data


def test_ocr_upload_persists_canonical_ocr_summary_envelope(client, session, monkeypatch):
    user = User(
        username="ocr_canonical_user",
        email="ocr_canonical_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    def create_current_user():
        return user

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.ocr.medical_ocr_service.parse_medical_report",
        lambda file_bytes: {
            "status": "success",
            "message": "ok",
            "data": {
                "Age": 45,
                "Gender": 1,
                "Glu": {"value": 6.8, "unit": "mmol/L", "ref_range": "3.9-6.1", "hospital_flag": "H"},
                "TC": 5.4,
                "summary": "legacy OCR summary",
            },
        },
    )
    monkeypatch.setattr("backend.core.cache.CacheManager.invalidate_user_cache", lambda user_id: None)
    app.dependency_overrides[get_current_user] = create_current_user

    response = client.post(
        "/api/v1/ocr/upload",
        files={"file": ("report.pdf", b"fake pdf bytes", "application/pdf")},
    )

    doc = session.exec(select(MedicalDocument).where(MedicalDocument.user_id == user.id)).first()
    parsed_summary = json.loads(doc.ocr_summary)

    assert response.status_code == 200
    assert parsed_summary["schema_version"] == "ocr_summary.v1"
    assert parsed_summary["patient_context"] == {"Age": 45, "Gender": 1}
    assert parsed_summary["metrics"]["Glucose_Fasting"]["value"] == 6.8
    assert parsed_summary["metrics"]["Cholesterol_Total"]["value"] == 5.4

    app.dependency_overrides.clear()


def test_ocr_upload_returns_stored_unprocessed_instead_of_500_when_document_is_saved(client, session, monkeypatch):
    user = User(
        username="ocr_degraded_user",
        email="ocr_degraded_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    def create_current_user():
        return user

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.ocr.medical_ocr_service.parse_medical_report",
        lambda file_bytes: {
            "status": "stored_unprocessed",
            "message": "OCR provider unavailable.",
            "data": None,
            "raw_text": None,
            "extraction_method": None,
            "ocr_processing_status": {
                "schema_version": "ocr_processing_status.v1",
                "status": "stored_unprocessed",
                "reason": "ocr_service_unavailable",
                "structured_data_present": False,
                "raw_text_present": False,
            },
        },
    )
    monkeypatch.setattr("backend.core.cache.CacheManager.invalidate_user_cache", lambda user_id: None)
    app.dependency_overrides[get_current_user] = create_current_user

    response = client.post(
        "/api/v1/ocr/upload",
        files={"file": ("report.pdf", b"fake pdf bytes", "application/pdf")},
    )

    doc = session.exec(select(MedicalDocument).where(MedicalDocument.user_id == user.id)).first()
    documents_response = client.get("/api/v1/user/documents")
    body = response.json()
    listed_doc = documents_response.json()["documents"][0]

    assert response.status_code == 200
    assert body["status"] == "stored_unprocessed"
    assert body["document_id"] == doc.id
    assert body["ocr_processing_status"]["status"] == "stored_unprocessed"
    assert body["ocr_processing_status"]["reason"] == "ocr_service_unavailable"
    assert doc.ocr_summary is None
    assert listed_doc["ocr_summary"] is None
    assert listed_doc["has_data"] is False
    assert listed_doc["ocr_processing_status"]["status"] == "stored_unprocessed"

    app.dependency_overrides.clear()


def test_ocr_upload_persists_partial_structured_summary_and_processing_status(client, session, monkeypatch):
    user = User(
        username="ocr_partial_user",
        email="ocr_partial_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    def create_current_user():
        return user

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.ocr.medical_ocr_service.parse_medical_report",
        lambda file_bytes: {
            "status": "partial_success",
            "message": "OCR recovered bounded structured data.",
            "raw_text": "BMI 24.2",
            "extraction_method": "regex_fallback",
            "data": {
                "BMI": {"value": 24.2, "unit": "kg/m2"},
                "summary": "Only one metric extracted.",
            },
            "ocr_processing_status": {
                "schema_version": "ocr_processing_status.v1",
                "status": "partial_success",
                "reason": "structured_data_incomplete",
                "structured_data_present": True,
                "raw_text_present": True,
            },
        },
    )
    monkeypatch.setattr("backend.core.cache.CacheManager.invalidate_user_cache", lambda user_id: None)
    app.dependency_overrides[get_current_user] = create_current_user

    response = client.post(
        "/api/v1/ocr/upload",
        files={"file": ("report.pdf", b"fake pdf bytes", "application/pdf")},
    )

    doc = session.exec(select(MedicalDocument).where(MedicalDocument.user_id == user.id)).first()
    parsed_summary = json.loads(doc.ocr_summary)
    listed_doc = client.get("/api/v1/user/documents").json()["documents"][0]
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "partial_success"
    assert body["ocr_processing_status"]["status"] == "partial_success"
    assert parsed_summary["schema_version"] == "ocr_summary.v1"
    assert parsed_summary["metrics"]["BMI"]["value"] == 24.2
    assert listed_doc["ocr_processing_status"]["status"] == "partial_success"
    assert listed_doc["has_data"] is True

    app.dependency_overrides.clear()


def test_profile_update_persists_canonical_risk_snapshot_and_history_record(client, session, monkeypatch):
    user = User(
        username="risk_snapshot_user",
        email="risk_snapshot_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    def create_current_user():
        return user

    monkeypatch.setattr("backend.core.cache.CacheManager.invalidate_user_cache", lambda user_id: None)
    app.dependency_overrides[get_current_user] = create_current_user

    response = client.post(
        "/user/profile",
        json={
            "BMI": 28.4,
            "risk_report": {
                "diabetes": {"risk_level": "medium", "probability": 42},
                "ckm": {"stage": 2, "stage_name": "stage_2"},
            },
        },
    )

    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    stored_record = session.exec(select(HealthRecord).where(HealthRecord.user_id == user.id)).first()
    profile_snapshot = json.loads(stored_profile.risk_history)
    record_snapshot = json.loads(stored_record.risk_snapshot)

    assert response.status_code == 200
    assert profile_snapshot["schema_version"] == "risk_snapshot.v1"
    assert profile_snapshot["source"] == "analyze_comprehensive"
    assert profile_snapshot["findings"][0]["key"] == "diabetes"
    assert record_snapshot["schema_version"] == "risk_snapshot.v1"
    assert record_snapshot["findings"][0]["key"] == "diabetes"
    assert record_snapshot["ckm"] == {"stage": 2, "stage_name": "stage_2"}

    app.dependency_overrides.clear()


def test_profile_update_preserves_extra_data_as_json_object(client, session, monkeypatch):
    user = User(
        username="extra_data_user",
        email="extra_data_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    def create_current_user():
        return user

    monkeypatch.setattr("backend.core.cache.CacheManager.invalidate_user_cache", lambda user_id: None)
    app.dependency_overrides[get_current_user] = create_current_user

    payload = {
        "BMI": 22.8,
        "extra_data": {
            "notes": ["follow_up_required"],
            "source": {"kind": "manual"},
        },
    }

    update_response = client.post("/user/profile", json=payload)
    stored_profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    profile_response = client.get("/user/profile")
    profile_body = profile_response.json()["profile"]

    assert update_response.status_code == 200
    assert isinstance(stored_profile.extra_data, dict)
    assert stored_profile.extra_data == payload["extra_data"]
    assert isinstance(profile_body["extra_data"], dict)
    assert profile_body["extra_data"]["source"]["kind"] == "manual"

    app.dependency_overrides.clear()


def test_analyze_comprehensive_falls_back_when_fusion_engine_is_missing(client, session, monkeypatch):
    user = User(
        username="comprehensive_fallback_user",
        email="comprehensive_fallback_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    class DummyRiskEngine:
        def assess_health(self, clinical_profile, include_breakdown=True):
            assert clinical_profile["Age"] == 52
            assert clinical_profile["BMI"] == 27.5
            return {
                "Diabetes": {
                    "probability": 42.0,
                    "level": "High",
                }
            }

    def create_current_user():
        return user

    app.dependency_overrides[get_current_user] = create_current_user
    monkeypatch.setattr(backend_main, "fusion_engine", None)
    monkeypatch.setattr(backend_main, "risk_engine", DummyRiskEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {
                "Age": 52,
                "BMI": 27.5,
                "Gender": 1,
            },
            "user_snps": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["risk_report"]["Diabetes"]["final_risk"] == 42.0
    assert body["risk_report"]["Diabetes"]["level"] == "High"
    assert body["risk_report"]["Diabetes"]["breakdown"] == {
        "base_clinical": "42.0%",
        "gene_modifier": "x1.0",
        "lifestyle_modifier": "x1.0",
    }

    app.dependency_overrides.clear()


def test_analyze_comprehensive_keeps_fusion_path_when_engine_exists(client, session, monkeypatch):
    user = User(
        username="comprehensive_fusion_user",
        email="comprehensive_fusion_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    class DummyFusionEngine:
        def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
            assert clinical_profile["Age"] == 49
            assert clinical_profile["BMI"] == 26.0
            return {
                "Hypertension": {
                    "final_risk": 18.5,
                    "level": "Medium",
                    "breakdown": {
                        "base_clinical": "18.5%",
                        "gene_modifier": "x1.2",
                        "lifestyle_modifier": "x0.9",
                    },
                }
            }

    class FailingRiskEngine:
        def assess_health(self, clinical_profile, include_breakdown=True):
            raise AssertionError("fallback engine should not be used when fusion engine is available")

    def create_current_user():
        return user

    app.dependency_overrides[get_current_user] = create_current_user
    monkeypatch.setattr(backend_main, "fusion_engine", DummyFusionEngine())
    monkeypatch.setattr(backend_main, "risk_engine", FailingRiskEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {
                "Age": 49,
                "BMI": 26.0,
                "Gender": 1,
            },
            "user_snps": {"example": "value"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["risk_report"]["Hypertension"]["final_risk"] == 18.5
    assert body["risk_report"]["Hypertension"]["breakdown"]["gene_modifier"] == "x1.2"

    app.dependency_overrides.clear()


def test_analyze_comprehensive_falls_back_when_fusion_engine_returns_error_report(client, session, monkeypatch):
    user = User(
        username="analysis_context_error_user",
        email="analysis_context_error_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    class ErrorFusionEngine:
        def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
            return {"error": "模型未加载"}

    class DegradedRiskEngine:
        def assess_health(self, clinical_profile, include_breakdown=True):
            return {
                "Hypertension": {
                    "probability": 42.0,
                    "level": "High",
                }
            }

    def create_current_user():
        return user

    app.dependency_overrides[get_current_user] = create_current_user
    monkeypatch.setattr(backend_main, "fusion_engine", ErrorFusionEngine())
    monkeypatch.setattr(backend_main, "risk_engine", DegradedRiskEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {
                "Age": 49,
                "Gender": 1,
                "BMI": 26.0,
                "Glucose_Fasting": 5.6,
                "HbA1c": 5.4,
                "Cholesterol_Total": 4.8,
                "Triglycerides": 1.2,
                "Cholesterol_HDL": 1.5,
                "Creatinine": 82.0,
                "eGFR": 96.0,
                "ALT": 21.0,
                "ALP": 72.0,
                "SBP": 118,
                "DBP": 76,
            },
            "user_snps": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["risk_report"]["Hypertension"]["final_risk"] == 42.0
    assert body["analysis_context"]["analysis_mode"] == "final"

    app.dependency_overrides.clear()


def test_analyze_comprehensive_uses_rule_based_fallback_when_models_are_unavailable(client, session, monkeypatch):
    user = User(
        username="analysis_context_rule_fallback_user",
        email="analysis_context_rule_fallback_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    class UnavailableRiskEngine:
        def assess_health(self, clinical_profile, include_breakdown=True):
            return {"error": "models unavailable"}

    def create_current_user():
        return user

    app.dependency_overrides[get_current_user] = create_current_user
    monkeypatch.setattr(backend_main, "fusion_engine", None)
    monkeypatch.setattr(backend_main, "risk_engine", UnavailableRiskEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {
                "Age": 52,
                "Gender": 1,
                "Height": 172,
                "Weight": 75,
                "BMI": 25.4,
                "SBP": 138,
                "DBP": 88,
                "Glucose_Fasting": 6.1,
                "Creatinine": 98.0,
            },
            "user_snps": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert isinstance(body["risk_report"]["Hypertension"]["final_risk"], float)
    assert body["risk_report"]["Hypertension"]["final_risk"] > 0
    assert body["risk_report"]["Hypertension"]["breakdown"]["gene_modifier"] == "x1.0"
    assert body["analysis_context"]["analysis_mode"] == "provisional"
    assert "HbA1c" in body["analysis_context"]["field_state_summary"]["missing"]
    assert "eGFR" in body["analysis_context"]["field_state_summary"]["derived"]

    app.dependency_overrides.clear()


def test_analyze_comprehensive_emits_analysis_context_for_complete_inputs(client, session, monkeypatch):
    user = User(
        username="analysis_context_user",
        email="analysis_context_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    class DummyFusionEngine:
        def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
            return {
                "Hypertension": {
                    "final_risk": 18.5,
                    "level": "Medium",
                    "breakdown": {
                        "base_clinical": "18.5%",
                        "gene_modifier": "x1.2",
                        "lifestyle_modifier": "x0.9",
                    },
                }
            }

    def create_current_user():
        return user

    app.dependency_overrides[get_current_user] = create_current_user
    monkeypatch.setattr(backend_main, "fusion_engine", DummyFusionEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {
                "Age": 49,
                "Gender": 1,
                "BMI": 26.0,
                "Glucose_Fasting": 5.2,
                "HbA1c": 5.3,
                "Cholesterol_Total": 4.7,
                "Triglycerides": 1.0,
                "Cholesterol_HDL": 1.4,
                "Creatinine": 78.0,
                "eGFR": 99.0,
                "ALT": 20.0,
                "ALP": 70.0,
            },
            "user_snps": {"example": "value"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["analysis_context"]["schema_version"] == "analysis_context.v1"
    assert body["analysis_context"]["analysis_mode"] == "final"
    assert body["analysis_context"]["blocking_fields"] == []
    assert body["analysis_context"]["field_state_summary"]["missing"] == []

    app.dependency_overrides.clear()


def test_analyze_comprehensive_emits_provisional_context_when_fields_are_sparse(client, session, monkeypatch):
    user = User(
        username="analysis_context_sparse_user",
        email="analysis_context_sparse_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    class DummyFusionEngine:
        def calculate_composite_risk(self, clinical_profile, user_snps, iot_data):
            return {
                "Hypertension": {
                    "final_risk": 18.5,
                    "level": "Medium",
                    "breakdown": {
                        "base_clinical": "18.5%",
                        "gene_modifier": "x1.0",
                        "lifestyle_modifier": "x1.0",
                    },
                }
            }

    def create_current_user():
        return user

    app.dependency_overrides[get_current_user] = create_current_user
    monkeypatch.setattr(backend_main, "fusion_engine", DummyFusionEngine())

    response = client.post(
        "/analyze/comprehensive",
        json={
            "clinical": {
                "Age": 49,
                "Gender": 1,
                "BMI": 26.0,
            },
            "user_snps": {},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["analysis_context"]["analysis_mode"] == "provisional"
    assert "BMI" in body["analysis_context"]["blocking_fields"]
    assert "BMI" in body["analysis_context"]["field_state_summary"]["missing"]

    app.dependency_overrides.clear()


def test_backend_main_does_not_expose_dead_optional_runtime_helpers():
    assert not hasattr(backend_main, "_safe_import_service")
    assert not hasattr(backend_main, "_build_optional_runtime_components")


def test_backend_main_import_stays_quiet(monkeypatch, caplog):
    modules_to_clear = [
        "backend.main",
        "backend.api.api_v1.endpoints.chat",
        "backend.api.api_v1.endpoints.ocr",
        "backend.services.chat_service",
        "backend.services.ocr_service",
        "backend.services.rag_service",
        "backend.services.agent_tools",
    ]

    with caplog.at_level(logging.INFO):
        _fresh_import("backend.main", modules_to_clear)

    startup_records = [record.getMessage() for record in caplog.records if record.name.startswith("backend.")]

    assert startup_records == []


def test_ocr_service_emits_one_concise_degraded_warning_on_init(monkeypatch, caplog):
    ocr_module = _fresh_import(
        "backend.services.ocr_service",
        ["backend.services.ocr_service"],
    )

    monkeypatch.setattr(ocr_module.settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ocr_module, "BAIDU_OCR_AVAILABLE", False)
    monkeypatch.setattr(ocr_module, "AipOcr", None)

    with caplog.at_level(logging.WARNING):
        service = ocr_module.MedicalOCRService()

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]

    assert service.ocr_ready is False
    assert warning_messages == ["Baidu OCR unavailable; OCR will run in degraded mode."]


def test_nutrition_router_import_is_quiet_and_lazy(monkeypatch, capsys):
    import backend.api.nutrition as nutrition_module
    import backend.services.nutrition_service as nutrition_service_module

    init_calls = []

    class NoisyDietOptimizer:
        def __init__(self):
            init_calls.append("called")
            print("nutrition optimizer initialized")

    monkeypatch.setattr(nutrition_service_module, "DietOptimizer", NoisyDietOptimizer)

    sys.modules.pop("backend.api.nutrition", None)
    reloaded_module = importlib.import_module("backend.api.nutrition")
    captured = capsys.readouterr()

    assert captured.out == ""
    assert init_calls == []
    assert hasattr(reloaded_module, "optimizer")

    sys.modules["backend.api.nutrition"] = nutrition_module


def test_cache_manager_logs_single_concise_warning_when_redis_unavailable(monkeypatch, caplog):
    from backend.core.cache import CacheManager

    monkeypatch.setattr("backend.core.cache.REDIS_AVAILABLE", False)
    monkeypatch.setattr(CacheManager, "_redis", None)
    monkeypatch.setattr(CacheManager, "_initialized", False)
    monkeypatch.setattr(CacheManager, "_availability_warning_emitted", False, raising=False)

    with caplog.at_level("WARNING"):
        result = asyncio.run(CacheManager.init("redis://example:6379/0"))

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]

    assert result is False
    assert warning_messages == ["Redis cache unavailable; continuing without cache."]


def test_lifestyle_service_logs_single_concise_warning_when_model_missing(monkeypatch, caplog):
    lifestyle_module = _fresh_import(
        "backend.services.lifestyle_service",
        ["backend.services.lifestyle_service"],
    )

    monkeypatch.setattr(lifestyle_module.os.path, "exists", lambda path: False)

    with caplog.at_level(logging.WARNING):
        service = lifestyle_module.LifestyleService()

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]

    assert service.model is None
    assert warning_messages == ["Lifestyle model unavailable; continuing without XGBoost modifier."]


def test_risk_engine_degrades_cleanly_on_model_version_mismatch_without_runtime_warning(monkeypatch, caplog):
    risk_module = _fresh_import(
        "backend.services.risk_engine",
        ["backend.services.risk_engine"],
    )

    class FakeVersionMismatch(Exception):
        pass

    monkeypatch.setattr(risk_module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        risk_module.joblib,
        "load",
        lambda path: (_ for _ in ()).throw(FakeVersionMismatch("model version mismatch")),
    )

    with caplog.at_level(logging.WARNING):
        engine = risk_module.DiseaseRiskEngine()
        asyncio.run(engine.load_models())

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]

    assert engine.models == {}
    assert engine._loaded is True
    assert warning_messages == [
        "Risk model artifacts unavailable; continuing without disease risk models (model version mismatch)."
    ]


def test_inference_service_imports_and_degrades_cleanly_without_torch(caplog):
    inference_module = _fresh_import(
        "backend.services.inference_service",
        ["backend.services.inference_service"],
    )

    with caplog.at_level(logging.WARNING):
        predictor = inference_module.Predictor()
        asyncio.run(predictor.load_models())

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]

    assert predictor.model is None
    assert predictor.scaler is None
    assert warning_messages == ["Glucose predictor unavailable; continuing without torch runtime."]


def test_export_pdf_returns_500_when_pdf_service_raises(client, session, monkeypatch):
    from backend.auth import get_current_user
    from backend.api.api_v1.endpoints import analysis as analysis_module

    user = User(
        username="pdf_error_user",
        email="pdf_error_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()

    class DummyRiskEngine:
        def assess_health(self, profile_data):
            return {"diabetes": {"probability": 12}}

        def assess_ckm_stage(self, profile_data):
            return {"stage": 1, "stage_name": "stage_1"}

    class DummyHydrationAdvisor:
        def calculate_water_plan(self, profile_data):
            return {"target_ml": 2000}

    class DummyPDFService:
        def create_health_report(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(backend_main, "risk_engine", DummyRiskEngine())
    monkeypatch.setattr(analysis_module, "_get_hydration_advisor", lambda: DummyHydrationAdvisor())
    monkeypatch.setattr(analysis_module, "_get_pdf_service", lambda: DummyPDFService())
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post("/analysis/export/pdf", params={"include_hydration": True})

    assert response.status_code == 500
    assert "报告生成过程中发生错误" in response.json()["detail"]

    app.dependency_overrides.clear()
