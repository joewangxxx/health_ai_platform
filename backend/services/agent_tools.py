import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlmodel import Session, select

from backend.models import HealthRecord, MedicalDocument, User
from backend.services.analysis_service import anomaly_service
from backend.services.agent_safety import classify_query_safety, enforce_tool_policy
from backend.services.rag_service import rag_service
from backend.services.payload_normalization import (
    project_medication_summary_for_tool,
    project_ocr_summary_for_tool,
    project_report_comparison_for_tool,
    project_risk_snapshot_for_tool,
    summarize_ocr_summary_for_context,
    summarize_risk_snapshot_for_context,
)

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}
EVIDENCE_METADATA_SCHEMA_VERSION = "tool_evidence_metadata.v1"

LANE_TOOL_WHITELIST: Dict[str, List[str]] = {
    "general_health": [
        "get_user_profile_summary",
        "get_latest_risk_report",
        "recent_metric_anomaly_lookup",
        "search_medical_guidelines",
    ],
    "report_interpretation": [
        "report_summary_lookup",
        "report_comparison_lookup",
        "get_uploaded_documents_summary",
        "search_medical_guidelines",
    ],
    "trend_review": [
        "get_history_trends",
        "recent_metric_anomaly_lookup",
        "latest_analysis_snapshot_lookup",
        "search_medical_guidelines",
    ],
    "medication_related": [
        "medication_summary_lookup",
        "report_summary_lookup",
        "search_medical_guidelines",
    ],
    "urgent_symptom": [],
    "diagnosis_sensitive": [
        "get_user_profile_summary",
        "report_summary_lookup",
        "latest_analysis_snapshot_lookup",
        "search_medical_guidelines",
    ],
}


def agent_tool(
    *,
    name: str,
    read_only: bool = True,
    scope: str = "self_only",
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
):
    def decorator(func: Callable[..., Dict[str, Any]]):
        TOOL_REGISTRY[name] = {
            "func": func,
            "read_only": read_only,
            "scope": scope,
            "description": description,
            "parameters": parameters or {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
        return func

    return decorator


def get_allowed_tool_names_for_lane(lane: str) -> List[str]:
    return list(LANE_TOOL_WHITELIST.get(lane, []))


def get_tool_definitions(
    tool_names: Optional[list[str]] = None,
    *,
    lane: Optional[str] = None,
) -> list[Dict[str, Any]]:
    names = tool_names or list(TOOL_REGISTRY.keys())
    if lane is not None:
        allowed = set(get_allowed_tool_names_for_lane(lane))
        names = [tool_name for tool_name in names if tool_name in allowed]
    definitions = []
    for tool_name in names:
        tool_meta = TOOL_REGISTRY.get(tool_name)
        if not tool_meta:
            continue
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_meta.get("description", ""),
                    "parameters": tool_meta.get("parameters", {"type": "object", "properties": {}, "required": []}),
                },
            }
        )
    return definitions


def _normalize_tool_arguments(tool_meta: Dict[str, Any], raw_arguments: Any) -> Dict[str, Any]:
    if raw_arguments in (None, ""):
        arguments = {}
    elif isinstance(raw_arguments, str):
        arguments = json.loads(raw_arguments)
    elif isinstance(raw_arguments, dict):
        arguments = raw_arguments
    else:
        raise ValueError("tool_arguments_must_be_object")

    if not isinstance(arguments, dict):
        raise ValueError("tool_arguments_must_be_object")

    schema = tool_meta.get("parameters", {})
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    normalized: Dict[str, Any] = {}
    for name, value in arguments.items():
        if name not in properties:
            raise ValueError(f"unknown_argument:{name}")
        normalized[name] = value

    for required_name in required:
        if required_name not in normalized or normalized[required_name] in (None, ""):
            raise ValueError(f"missing_argument:{required_name}")

    return normalized


def _get_tool_applicability_reason(
    *,
    tool_name: str,
    lane: Optional[str],
    query_text: Optional[str],
) -> Optional[str]:
    normalized_query = (query_text or "").strip()
    if lane == "urgent_symptom":
        return "tool_not_allowed_for_lane"

    if not normalized_query:
        return None

    safety_result = classify_query_safety(normalized_query)
    policy_pressure = safety_result.get("policy_pressure") or {}

    if tool_name == "medication_summary_lookup" and policy_pressure.get("requests_medication_change"):
        return "tool_not_applicable_for_question"

    return None


def execute_registered_tool(
    tool_name: str,
    *,
    user: User,
    session: Session,
    target_user_id: Optional[int] = None,
    allowed_tool_names: Optional[List[str]] = None,
    lane: Optional[str] = None,
    query_text: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    tool_meta = TOOL_REGISTRY.get(tool_name)
    if not tool_meta:
        return {"status": "error", "reason": "tool_not_found", "tool": tool_name}

    if allowed_tool_names is not None and tool_name not in set(allowed_tool_names):
        return {"status": "blocked", "reason": "tool_not_allowed_for_lane", "tool": tool_name}

    try:
        normalized_kwargs = _normalize_tool_arguments(tool_meta, kwargs)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "error",
            "reason": "invalid_arguments",
            "tool": tool_name,
            "detail": str(exc),
        }

    effective_target_user_id = target_user_id or user.id
    applicability_reason = _get_tool_applicability_reason(
        tool_name=tool_name,
        lane=lane,
        query_text=query_text,
    )
    if applicability_reason:
        return {
            "status": "blocked",
            "reason": applicability_reason,
            "tool": tool_name,
        }

    policy = enforce_tool_policy(
        user_is_admin=bool(user.is_superuser),
        tool_meta=tool_meta,
        acting_user_id=user.id,
        target_user_id=effective_target_user_id,
    )
    if not policy["allowed"]:
        return {
            "status": "blocked",
            "reason": policy["reason"],
            "tool": tool_name,
        }

    result = tool_meta["func"](
        user=user,
        session=session,
        target_user_id=effective_target_user_id,
        **normalized_kwargs,
    )
    result = _attach_evidence_metadata(
        tool_name=tool_name,
        result=result,
        session=session,
        target_user_id=effective_target_user_id,
        tool_kwargs=normalized_kwargs,
    )
    return {"status": "ok", "tool": tool_name, "result": result}


def execute_tool_call(
    tool_call: Any,
    *,
    user: User,
    session: Session,
    allowed_tool_names: Optional[List[str]] = None,
    lane: Optional[str] = None,
    query_text: Optional[str] = None,
) -> Dict[str, Any]:
    function_call = getattr(tool_call, "function", None)
    tool_name = getattr(function_call, "name", None)
    raw_arguments = getattr(function_call, "arguments", None)

    tool_meta = TOOL_REGISTRY.get(tool_name)
    if not tool_meta:
        return {
            "status": "error",
            "reason": "tool_not_found",
            "tool": tool_name,
            "tool_call_id": getattr(tool_call, "id", None),
        }

    try:
        normalized_kwargs = _normalize_tool_arguments(tool_meta, raw_arguments)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "error",
            "reason": "invalid_arguments",
            "tool": tool_name,
            "detail": str(exc),
            "tool_call_id": getattr(tool_call, "id", None),
        }

    result = execute_registered_tool(
        tool_name,
        user=user,
        session=session,
        allowed_tool_names=allowed_tool_names,
        lane=lane,
        query_text=query_text,
        **normalized_kwargs,
    )
    result["tool_call_id"] = getattr(tool_call, "id", None)
    return result


def _safe_json_loads(payload: Optional[str]) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return payload


def _collect_profile_flags(profile) -> list[str]:
    if not profile:
        return []

    flags = []
    if profile.BMI and profile.BMI > 24:
        flags.append(f"BMI偏高({profile.BMI})")
    if profile.SBP and profile.SBP > 140:
        flags.append(f"收缩压偏高({profile.SBP})")
    if profile.Glucose_Fasting and profile.Glucose_Fasting > 6.1:
        flags.append(f"空腹血糖偏高({profile.Glucose_Fasting})")
    return flags


def _safe_isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _profile_metrics_payload(profile: Any) -> Dict[str, Any]:
    if not profile:
        return {}

    metric_keys = [
        "BMI",
        "SBP",
        "DBP",
        "Glucose_Fasting",
        "HbA1c",
        "Cholesterol_Total",
        "Triglycerides",
        "Cholesterol_HDL",
        "Cholesterol_LDL",
        "eGFR",
        "Creatinine",
        "WBC",
        "Platelet",
        "GGT",
        "ALP",
        "ALT",
    ]
    payload = {}
    for key in metric_keys:
        value = getattr(profile, key, None)
        if value is not None:
            payload[key] = value
    return payload


def _severity_rank(status: Optional[str]) -> int:
    return {
        "abnormal": 3,
        "high": 2,
        "low": 2,
    }.get((status or "").lower(), 0)


def _tag_rank(tag: Optional[str]) -> int:
    return {
        "Diabetes_Risk": 6,
        "Cardiovascular_Risk": 5,
        "Kidney_Alert": 4,
        "Liver_Alert": 3,
        "Lipid_Abnormality": 2,
        "Metabolic_Alert": 1,
    }.get(tag or "", 0)


def _rank_anomalies(anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        anomalies,
        key=lambda item: (
            -_tag_rank(item.get("tag")),
            -_severity_rank(item.get("status")),
            str(item.get("item") or ""),
        ),
    )


def _empty_report_summary_result() -> Dict[str, Any]:
    return {
        "has_report_summary": False,
        "document_id": None,
        "file_name": None,
        "upload_date": None,
        "summary_source": None,
        "report_summary": None,
        "evidence_metadata": _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["report_summary"],
        ),
    }


def _empty_recent_abnormal_metrics_result(evaluated_source: Optional[str] = None) -> Dict[str, Any]:
    return {
        "has_abnormal_metrics": False,
        "evaluated_at": _safe_isoformat(datetime.utcnow()),
        "evaluated_source": evaluated_source,
        "summary": {
            "status": "healthy",
            "count": 0,
            "message": "0 abnormal metrics found",
        },
        "items": [],
        "evidence_metadata": _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["metric_anomalies"],
        ),
    }


def _empty_recent_metric_anomalies_result(evaluated_source: Optional[str] = None) -> Dict[str, Any]:
    return {
        "has_metric_anomalies": False,
        "evaluated_at": _safe_isoformat(datetime.utcnow()),
        "evaluated_source": evaluated_source,
        "summary": {
            "status": "healthy",
            "count": 0,
            "message": "0 abnormal metrics found",
        },
        "items": [],
        "evidence_metadata": _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["metric_anomalies"],
        ),
    }


def _empty_medication_summary_result() -> Dict[str, Any]:
    return {
        "has_medication_summary": False,
        "document_id": None,
        "file_name": None,
        "summary_source": None,
        "medication_summary": None,
        "evidence_metadata": _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["medication_summary"],
        ),
    }


def _empty_report_comparison_result() -> Dict[str, Any]:
    return {
        "has_report_comparison": False,
        "baseline_document_id": None,
        "comparison_document_id": None,
        "baseline_file_name": None,
        "comparison_file_name": None,
        "comparison_basis": None,
        "summary": None,
        "delta_items": [],
        "shared_metric_count": 0,
        "new_findings_count": 0,
        "removed_findings_count": 0,
        "source_refs": [],
        "evidence_metadata": _build_comparison_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["report_comparison"],
            comparable_fields_count=0,
        ),
    }


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _freshness_from_timestamp(value: Any) -> str:
    timestamp = _parse_iso_datetime(value)
    if timestamp is None:
        return "unknown"

    age_days = max(0.0, (datetime.utcnow() - timestamp).total_seconds() / 86400.0)
    if age_days <= 7:
        return "fresh"
    if age_days <= 30:
        return "recent"
    return "stale"


def _freshness_from_timestamps(values: List[Any]) -> str:
    timestamps = []
    for value in values:
        timestamp = _parse_iso_datetime(value)
        if timestamp is not None:
            timestamps.append(timestamp)
    if not timestamps:
        return "unknown"
    return _freshness_from_timestamp(min(timestamps))


def _dedupe_labels(values: List[str]) -> List[str]:
    return list(dict.fromkeys([value for value in values if value]))


def _confidence_from_quality(*, freshness: str, coverage: str) -> str:
    if coverage == "empty":
        return "low"
    if coverage == "partial":
        return "low" if freshness == "stale" else "medium"
    if coverage == "full":
        if freshness == "stale":
            return "low"
        if freshness == "unknown":
            return "medium"
        return "high"
    return "unknown"


def _build_summary_evidence_metadata(
    *,
    freshness: str,
    coverage: str,
    missing_fields: Optional[List[str]] = None,
    confidence: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_confidence = confidence or _confidence_from_quality(freshness=freshness, coverage=coverage)
    metadata: Dict[str, Any] = {
        "schema_version": EVIDENCE_METADATA_SCHEMA_VERSION,
        "freshness": freshness,
        "coverage": coverage,
        "confidence": resolved_confidence,
    }
    if missing_fields:
        metadata["missing_fields"] = _dedupe_labels(missing_fields)
    return metadata


def _build_comparison_evidence_metadata(
    *,
    freshness: str,
    coverage: str,
    missing_fields: Optional[List[str]] = None,
    comparable_fields_count: Optional[int] = None,
    confidence: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
        confidence=confidence,
    )
    metadata["comparable_fields_count"] = max(0, comparable_fields_count or 0)
    return metadata


def _profile_summary_missing_fields(profile: Any) -> List[str]:
    missing = []
    for label, attribute in (
        ("age", "Age"),
        ("gender", "Gender"),
        ("bmi", "BMI"),
        ("sbp", "SBP"),
        ("dbp", "DBP"),
        ("glucose_fasting", "Glucose_Fasting"),
    ):
        if getattr(profile, attribute, None) is None:
            missing.append(label)
    return missing


def _tool_summary_result_freshness(result: Dict[str, Any]) -> str:
    for key in ("captured_at", "upload_date", "evaluated_at"):
        freshness = _freshness_from_timestamp(result.get(key))
        if freshness != "unknown":
            return freshness
    return "unknown"


def _trend_freshness(result: Dict[str, Any]) -> str:
    items = result.get("items") or []
    timestamps = [item.get("record_date") for item in items if isinstance(item, dict)]
    parsed = [_parse_iso_datetime(timestamp) for timestamp in timestamps]
    parsed = [timestamp for timestamp in parsed if timestamp is not None]
    if not parsed:
        return "unknown"
    latest = max(parsed)
    return _freshness_from_timestamp(latest)


def _report_summary_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    report_summary = result.get("report_summary") or {}
    if not report_summary:
        return _build_summary_evidence_metadata(
            freshness=_freshness_from_timestamp(result.get("upload_date")),
            coverage="empty",
            missing_fields=["report_summary"],
        )

    missing_fields = []
    if not report_summary.get("patient_context"):
        missing_fields.append("patient_context")
    if not report_summary.get("metrics"):
        missing_fields.append("metrics")
    if not report_summary.get("narrative_summary"):
        missing_fields.append("narrative_summary")
    if report_summary.get("metrics_truncated"):
        missing_fields.append("metric_rows")

    coverage = "full" if not missing_fields else "partial"
    freshness = _freshness_from_timestamp(result.get("upload_date"))
    return _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _profile_summary_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    if not result.get("has_profile"):
        return _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["profile_summary"],
        )

    missing_fields = [
        label
        for label, key in (
            ("age", "age"),
            ("gender", "gender"),
            ("bmi", "bmi"),
            ("glucose_fasting", "glucose_fasting"),
        )
        if result.get(key) is None
    ]
    coverage = "full" if not missing_fields else "partial"
    return _build_summary_evidence_metadata(
        freshness="unknown",
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _risk_snapshot_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    if not result.get("has_risk_report"):
        return _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["risk_snapshot"],
        )

    risk_report = result.get("risk_report") or {}
    missing_fields = []
    if not risk_report.get("top_findings") and not risk_report.get("findings"):
        missing_fields.append("risk_findings")
    if not risk_report.get("ckm"):
        missing_fields.append("ckm")
    coverage = "full" if not missing_fields else "partial"
    freshness = _freshness_from_timestamp(risk_report.get("captured_at") or risk_report.get("generated_at"))
    return _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _analysis_snapshot_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    if not result.get("has_analysis_snapshot"):
        return _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["analysis_snapshot"],
        )

    missing_fields = []
    if not result.get("top_findings"):
        missing_fields.append("analysis_findings")
    if not result.get("ckm"):
        missing_fields.append("ckm")
    coverage = "full" if not missing_fields else "partial"
    freshness = _freshness_from_timestamp(result.get("captured_at"))
    return _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _trend_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    count = int(result.get("count") or 0)
    freshness = _trend_freshness(result)
    if count <= 0:
        return _build_comparison_evidence_metadata(
            freshness=freshness,
            coverage="empty",
            missing_fields=["trend_points"],
            comparable_fields_count=0,
        )

    coverage = "full" if count >= 2 else "partial"
    missing_fields = [] if coverage == "full" else ["trend_points"]
    return _build_comparison_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
        comparable_fields_count=count,
    )


def _uploaded_documents_metadata(result: Dict[str, Any], *, limit: int) -> Dict[str, Any]:
    items = result.get("items") or []
    count = int(result.get("count") or 0)
    freshness = "unknown"
    upload_dates = []
    for item in items:
        if isinstance(item, dict):
            parsed = _parse_iso_datetime(item.get("upload_date"))
            if parsed is not None:
                upload_dates.append(parsed)
    if upload_dates:
        freshness = _freshness_from_timestamp(max(upload_dates))

    if count <= 0:
        return _build_summary_evidence_metadata(
            freshness=freshness,
            coverage="empty",
            missing_fields=["document_summaries"],
        )

    missing_fields = []
    if any(not isinstance(item, dict) or not item.get("ocr_summary") for item in items):
        missing_fields.append("ocr_summary")
    if count >= limit:
        missing_fields.append("additional_documents")
    coverage = "full" if not missing_fields else "partial"
    return _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _medication_metadata(result: Dict[str, Any], *, upload_date: Any = None) -> Dict[str, Any]:
    summary = result.get("medication_summary") or {}
    items = summary.get("medication_items") or []
    if not result.get("has_medication_summary") or not items:
        return _build_summary_evidence_metadata(
            freshness="unknown",
            coverage="empty",
            missing_fields=["medication_summary"],
        )

    missing_fields = []
    for field_name in ("name", "dose", "unit", "frequency"):
        if any(not isinstance(item, dict) or item.get(field_name) in (None, "") for item in items):
            missing_fields.append(field_name)
    if summary.get("medication_items_truncated"):
        missing_fields.append("additional_medication_items")

    freshness = _freshness_from_timestamp(upload_date or result.get("upload_date"))
    if freshness == "unknown" and result.get("summary_source") == "user_profile_extra_data":
        freshness = "unknown"
    coverage = "full" if not missing_fields else "partial"
    return _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _attach_evidence_metadata(
    *,
    tool_name: str,
    result: Dict[str, Any],
    session: Session,
    target_user_id: int,
    tool_kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(result, dict) or result.get("evidence_metadata"):
        return result

    if tool_name == "get_user_profile_summary":
        result["evidence_metadata"] = _profile_summary_metadata(result)
        return result

    if tool_name == "get_latest_risk_report":
        result["evidence_metadata"] = _risk_snapshot_metadata(result)
        return result

    if tool_name == "get_history_trends":
        result["evidence_metadata"] = _trend_metadata(result)
        return result

    if tool_name == "get_uploaded_documents_summary":
        result["evidence_metadata"] = _uploaded_documents_metadata(
            result,
            limit=int(tool_kwargs.get("limit") or 3),
        )
        return result

    if tool_name == "report_summary_lookup":
        result["evidence_metadata"] = _report_summary_metadata(result)
        return result

    if tool_name in {"recent_metric_anomaly_lookup", "recent_abnormal_metrics_lookup"}:
        result["evidence_metadata"] = _anomaly_metadata(result)
        return result

    if tool_name == "latest_analysis_snapshot_lookup":
        result["evidence_metadata"] = _analysis_snapshot_metadata(result)
        return result

    if tool_name == "medication_summary_lookup":
        upload_date = None
        document_id = result.get("document_id") or tool_kwargs.get("document_id")
        if document_id is not None:
            document = session.exec(
                select(MedicalDocument)
                .where(MedicalDocument.user_id == target_user_id)
                .where(MedicalDocument.id == document_id)
            ).first()
            if document:
                upload_date = document.upload_date
        result["evidence_metadata"] = _medication_metadata(result, upload_date=upload_date)
        return result

    if tool_name == "report_comparison_lookup":
        baseline_document = None
        comparison_document = None
        baseline_document_id = result.get("baseline_document_id") or tool_kwargs.get("baseline_document_id")
        comparison_document_id = result.get("comparison_document_id") or tool_kwargs.get("comparison_document_id")
        if baseline_document_id is not None or comparison_document_id is not None:
            query = select(MedicalDocument).where(MedicalDocument.user_id == target_user_id)
            if baseline_document_id is not None:
                baseline_document = session.exec(query.where(MedicalDocument.id == baseline_document_id)).first()
            if comparison_document_id is not None:
                comparison_document = session.exec(query.where(MedicalDocument.id == comparison_document_id)).first()
        result["evidence_metadata"] = _comparison_metadata(
            result,
            baseline_document=baseline_document,
            comparison_document=comparison_document,
        )
        return result

    return result


def _anomaly_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    items = result.get("items") or []
    if not result.get("has_metric_anomalies") or not items:
        return _build_summary_evidence_metadata(
            freshness=_freshness_from_timestamp(result.get("evaluated_at")),
            coverage="empty",
            missing_fields=["metric_anomalies"],
        )

    missing_fields = []
    for field_name in ("metric_key", "value", "status"):
        if any(not isinstance(item, dict) or item.get(field_name) in (None, "") for item in items):
            missing_fields.append(field_name)
    if int(result.get("summary", {}).get("count") or len(items)) > len(items):
        missing_fields.append("additional_anomalies")

    freshness = _freshness_from_timestamp(result.get("evaluated_at"))
    if result.get("evaluated_source") == "user_profile" and freshness == "fresh":
        freshness = "unknown"
    coverage = "full" if not missing_fields else "partial"
    return _build_summary_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
    )


def _comparison_metadata(result: Dict[str, Any], *, baseline_document: Any = None, comparison_document: Any = None) -> Dict[str, Any]:
    delta_items = result.get("delta_items") or []
    shared_count = int(result.get("shared_metric_count") or 0)
    total_diff_count = shared_count + int(result.get("new_findings_count") or 0) + int(result.get("removed_findings_count") or 0)
    if not result.get("has_report_comparison"):
        freshness = _freshness_from_timestamps([
            getattr(baseline_document, "upload_date", None) if baseline_document else None,
            getattr(comparison_document, "upload_date", None) if comparison_document else None,
        ])
        return _build_comparison_evidence_metadata(
            freshness=freshness,
            coverage="empty",
            missing_fields=["report_comparison"],
            comparable_fields_count=0,
        )

    missing_fields = []
    if total_diff_count > len(delta_items):
        missing_fields.append("additional_differences")
    if any(not isinstance(item, dict) or item.get("field") in (None, "") for item in delta_items):
        missing_fields.append("comparison_fields")

    freshness = _freshness_from_timestamps([
        getattr(baseline_document, "upload_date", None) if baseline_document else None,
        getattr(comparison_document, "upload_date", None) if comparison_document else None,
    ])
    coverage = "full" if not missing_fields else "partial"
    return _build_comparison_evidence_metadata(
        freshness=freshness,
        coverage=coverage,
        missing_fields=missing_fields,
        comparable_fields_count=shared_count,
    )


def _coerce_probability(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric > 1:
        numeric = numeric / 100.0
    return round(numeric, 4)


def _normalize_risk_level(payload: Dict[str, Any]) -> Optional[str]:
    risk_level = payload.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip():
        return risk_level

    level = payload.get("level")
    if isinstance(level, str) and level.strip():
        lowered = level.lower()
        if "very high" in lowered or "极高" in level:
            return "very_high"
        if "high" in lowered or "高" in level:
            return "high"
        if "medium" in lowered or "中" in level:
            return "medium"
        if "low" in lowered or "低" in level:
            return "low"
        return level
    return None


def _finding_rank(finding: Dict[str, Any]) -> tuple:
    probability = finding.get("probability")
    risk_level = str(finding.get("risk_level") or "").lower()
    risk_weight = {
        "very_high": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(risk_level, 0)
    return (
        -(probability if probability is not None else -1),
        -risk_weight,
        str(finding.get("key") or ""),
    )


def _extract_ckm(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key in ("ckm", "ckm_stage", "CKM", "CKM_stage"):
        value = payload.get(key)
        if isinstance(value, dict):
            stage = value.get("stage")
            stage_name = value.get("stage_name")
            if stage is not None or stage_name is not None:
                return {
                    "stage": stage,
                    "stage_name": stage_name,
                }
    return None


def _normalize_snapshot_findings(payload: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for key, value in payload.items():
        if key in {"ckm", "ckm_stage", "CKM", "CKM_stage"}:
            continue
        if not isinstance(value, dict):
            continue

        probability = _coerce_probability(
            value.get("probability", value.get("final_risk", value.get("risk")))
        )
        risk_level = _normalize_risk_level(value)
        if probability is None and risk_level is None:
            continue

        findings.append(
            {
                "key": key,
                "label": value.get("disease_cn") or value.get("label") or key,
                "risk_level": risk_level,
                "probability": probability,
            }
        )

    return sorted(findings, key=_finding_rank)[:limit]


def _empty_analysis_snapshot_result() -> Dict[str, Any]:
    return {
        "has_analysis_snapshot": False,
        "snapshot_source": None,
        "captured_at": None,
        "top_findings": [],
        "ckm": None,
        "raw_snapshot_present": False,
        "evidence_metadata": _analysis_snapshot_metadata(
            {
                "has_analysis_snapshot": False,
                "top_findings": [],
                "ckm": None,
                "captured_at": None,
            }
        ),
    }


@agent_tool(
    name="get_user_profile_summary",
    read_only=True,
    scope="self_only",
    description="Read the current user's key health profile summary.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_user_profile_summary(*, user: User, session: Session, target_user_id: int) -> Dict[str, Any]:
    profile = user.profile
    if not profile:
        return {
            "has_profile": False,
            "message": "暂无详细健康档案。",
        }

    gender = "男" if profile.Gender == 1 else "女" if profile.Gender == 2 else "未知"
    return {
        "has_profile": True,
        "age": profile.Age,
        "gender": gender,
        "bmi": profile.BMI,
        "sbp": profile.SBP,
        "dbp": profile.DBP,
        "glucose_fasting": profile.Glucose_Fasting,
        "abnormal_flags": _collect_profile_flags(profile),
    }


@agent_tool(
    name="get_latest_risk_report",
    read_only=True,
    scope="self_only",
    description="Read the latest saved risk report from the current user's profile.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_latest_risk_report(*, user: User, session: Session, target_user_id: int) -> Dict[str, Any]:
    profile = user.profile
    return {
        "has_risk_report": bool(profile and profile.risk_history),
        "risk_report": project_risk_snapshot_for_tool(profile.risk_history if profile else None),
    }


@agent_tool(
    name="get_history_trends",
    read_only=True,
    scope="self_only",
    description="Read recent structured health trend records for the current user.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_history_trends(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    limit: int = 5,
) -> Dict[str, Any]:
    records = list(
        session.exec(
            select(HealthRecord)
            .where(HealthRecord.user_id == target_user_id)
            .order_by(HealthRecord.record_date.desc())
            .limit(limit)
        ).all()
    )
    return {
        "count": len(records),
        "items": [
            {
                "record_date": record.record_date.isoformat(),
                "source": record.source,
                "metrics": _safe_json_loads(record.metrics),
                "risk_snapshot": _safe_json_loads(record.risk_snapshot),
            }
            for record in records
        ],
    }


@agent_tool(
    name="get_uploaded_documents_summary",
    read_only=True,
    scope="self_only",
    description="Read recent OCR summary results from uploaded medical documents.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_uploaded_documents_summary(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    limit: int = 3,
) -> Dict[str, Any]:
    documents = list(
        session.exec(
            select(MedicalDocument)
            .where(MedicalDocument.user_id == target_user_id)
            .order_by(MedicalDocument.upload_date.desc())
            .limit(limit)
        ).all()
    )
    return {
        "count": len(documents),
        "items": [
            {
                "file_name": doc.file_name,
                "upload_date": doc.upload_date.isoformat(),
                "ocr_summary": project_ocr_summary_for_tool(doc.ocr_summary),
            }
            for doc in documents
        ],
    }


def _resolve_medication_summary_source(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    document_id: Optional[int],
    limit: int,
) -> Dict[str, Any]:
    query = select(MedicalDocument).where(MedicalDocument.user_id == target_user_id)
    if document_id is not None:
        document = session.exec(query.where(MedicalDocument.id == document_id)).first()
        if not document:
            return _empty_medication_summary_result()
        summary = project_medication_summary_for_tool(
            document.ocr_summary,
            document_id=document.id,
            file_name=document.file_name,
            source_ref=f"report:{document.id}",
            summary_source="medical_document_ocr_summary",
            limit=limit,
        )
        return summary or _empty_medication_summary_result()

    documents = list(session.exec(query.order_by(MedicalDocument.upload_date.desc())).all())
    for document in documents:
        if not document.ocr_summary:
            continue
        summary = project_medication_summary_for_tool(
            document.ocr_summary,
            document_id=document.id,
            file_name=document.file_name,
            source_ref=f"report:{document.id}",
            summary_source="medical_document_ocr_summary",
            limit=limit,
        )
        if summary:
            return summary

    if user.profile and user.profile.extra_data:
        summary = project_medication_summary_for_tool(
            user.profile.extra_data,
            summary_source="user_profile_extra_data",
            source_ref="profile_extra_data",
            limit=limit,
        )
        if summary:
            return summary

    return _empty_medication_summary_result()


def _resolve_report_comparison_source(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    baseline_document_id: Optional[int],
    comparison_document_id: Optional[int],
    limit: int,
) -> Dict[str, Any]:
    query = select(MedicalDocument).where(MedicalDocument.user_id == target_user_id)

    if baseline_document_id is not None and comparison_document_id is not None:
        baseline_document = session.exec(query.where(MedicalDocument.id == baseline_document_id)).first()
        comparison_document = session.exec(query.where(MedicalDocument.id == comparison_document_id)).first()
        if not baseline_document or not comparison_document:
            return _empty_report_comparison_result()
        if not baseline_document.ocr_summary or not comparison_document.ocr_summary:
            return _empty_report_comparison_result()
        comparison = project_report_comparison_for_tool(
            baseline_document.ocr_summary,
            comparison_document.ocr_summary,
            baseline_document_id=baseline_document.id,
            comparison_document_id=comparison_document.id,
            baseline_file_name=baseline_document.file_name,
            comparison_file_name=comparison_document.file_name,
            limit=limit,
        )
        return comparison or _empty_report_comparison_result()

    documents = list(session.exec(query.order_by(MedicalDocument.upload_date.desc())).all())
    readable_documents = [document for document in documents if document.ocr_summary]
    if len(readable_documents) < 2:
        return _empty_report_comparison_result()

    baseline_document = readable_documents[-1]
    comparison_document = readable_documents[0]
    if baseline_document.id == comparison_document.id:
        return _empty_report_comparison_result()

    comparison = project_report_comparison_for_tool(
        baseline_document.ocr_summary,
        comparison_document.ocr_summary,
        baseline_document_id=baseline_document.id,
        comparison_document_id=comparison_document.id,
        baseline_file_name=baseline_document.file_name,
        comparison_file_name=comparison_document.file_name,
        limit=limit,
    )
    return comparison or _empty_report_comparison_result()


@agent_tool(
    name="medication_summary_lookup",
    read_only=True,
    scope="self_only",
    description="Read a bounded medication summary for the current user.",
    parameters={
        "type": "object",
        "properties": {
            "document_id": {
                "type": ["integer", "null"],
                "description": "Optional user-owned document id. If omitted, use the latest document or profile medication facts that contain a persisted medication summary.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "Maximum medication items to return after backend normalization.",
            },
        },
        "required": [],
    },
)
def medication_summary_lookup(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    document_id: Optional[int] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    bounded_limit = min(max(limit, 1), 10)
    return _resolve_medication_summary_source(
        user=user,
        session=session,
        target_user_id=target_user_id,
        document_id=document_id,
        limit=bounded_limit,
    )


@agent_tool(
    name="recent_metric_anomaly_lookup",
    read_only=True,
    scope="self_only",
    description="Read a bounded set of recent metric anomalies for the current user.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "Maximum abnormal metrics to return after backend ranking.",
            },
        },
        "required": [],
    },
)
def recent_metric_anomaly_lookup(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    limit: int = 5,
) -> Dict[str, Any]:
    bounded_limit = min(max(limit, 1), 10)
    record = session.exec(
        select(HealthRecord)
        .where(HealthRecord.user_id == target_user_id)
        .order_by(HealthRecord.record_date.desc())
    ).first()

    evaluated_source = None
    evaluated_at = _safe_isoformat(datetime.utcnow())
    metrics_payload: Dict[str, Any] = {}

    if record:
        metrics_payload = _safe_json_loads(record.metrics) or {}
        if isinstance(metrics_payload, dict) and metrics_payload:
            evaluated_source = "health_record"
            evaluated_at = record.record_date.isoformat()
        else:
            metrics_payload = {}

    if not metrics_payload:
        metrics_payload = _profile_metrics_payload(user.profile)
        if metrics_payload:
            evaluated_source = "user_profile"

    if not metrics_payload:
        return _empty_recent_metric_anomalies_result(evaluated_source)

    anomalies = _rank_anomalies(anomaly_service.detect_anomalies(metrics_payload))
    if not anomalies:
        result = _empty_recent_metric_anomalies_result(evaluated_source)
        result["evaluated_at"] = evaluated_at
        return result

    summary = anomaly_service.generate_summary(anomalies)
    source_ref = "health_record_metrics" if evaluated_source == "health_record" else "user_profile_metrics"
    return {
        "has_metric_anomalies": True,
        "evaluated_at": evaluated_at,
        "evaluated_source": evaluated_source,
        "summary": {
            "status": summary.get("status"),
            "count": summary.get("count", len(anomalies)),
            "message": summary.get("message", f"{len(anomalies)} abnormal metrics found"),
        },
        "items": [
            {
                "metric_key": item.get("item"),
                "display_name": item.get("item"),
                "value": item.get("value"),
                "unit": item.get("unit", ""),
                "status": item.get("status"),
                "tag": item.get("tag"),
                "message": item.get("msg"),
                "detection_source": item.get("source"),
                "source_ref": source_ref,
            }
            for item in anomalies[:bounded_limit]
        ],
    }


@agent_tool(
    name="report_comparison_lookup",
    read_only=True,
    scope="self_only",
    description="Compare two persisted report summaries for the current user.",
    parameters={
        "type": "object",
        "properties": {
            "baseline_document_id": {
                "type": ["integer", "null"],
                "description": "Optional older user-owned document id to compare from.",
            },
            "comparison_document_id": {
                "type": ["integer", "null"],
                "description": "Optional newer user-owned document id to compare against.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "Maximum comparison items to return after backend ranking.",
            },
        },
        "required": [],
    },
)
def report_comparison_lookup(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    baseline_document_id: Optional[int] = None,
    comparison_document_id: Optional[int] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    bounded_limit = min(max(limit, 1), 10)
    return _resolve_report_comparison_source(
        user=user,
        session=session,
        target_user_id=target_user_id,
        baseline_document_id=baseline_document_id,
        comparison_document_id=comparison_document_id,
        limit=bounded_limit,
    )


@agent_tool(
    name="report_summary_lookup",
    read_only=True,
    scope="self_only",
    description="Read one persisted uploaded-report OCR summary for the current user.",
    parameters={
        "type": "object",
        "properties": {
            "document_id": {
                "type": ["integer", "null"],
                "description": "Optional user-owned document id. If omitted, use the latest document with a persisted OCR summary.",
            },
        },
        "required": [],
    },
)
def report_summary_lookup(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    document_id: Optional[int] = None,
) -> Dict[str, Any]:
    query = select(MedicalDocument).where(MedicalDocument.user_id == target_user_id)
    if document_id is not None:
        document = session.exec(query.where(MedicalDocument.id == document_id)).first()
        if not document or not document.ocr_summary:
            return _empty_report_summary_result()
    else:
        documents = list(session.exec(query.order_by(MedicalDocument.upload_date.desc())).all())
        document = next((item for item in documents if item.ocr_summary), None)

    summary = project_ocr_summary_for_tool(document.ocr_summary) if document and document.ocr_summary else None
    if not document or not summary:
        return _empty_report_summary_result()

    return {
        "has_report_summary": True,
        "document_id": document.id,
        "file_name": document.file_name,
        "upload_date": document.upload_date.isoformat(),
        "summary_source": "medical_document_ocr_summary",
        "report_summary": summary,
    }


@agent_tool(
    name="recent_abnormal_metrics_lookup",
    read_only=True,
    scope="self_only",
    description="Read a bounded set of recent abnormal metrics for the current user.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "Maximum abnormal metrics to return after backend ranking.",
            },
        },
        "required": [],
    },
)
def recent_abnormal_metrics_lookup(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    limit: int = 5,
) -> Dict[str, Any]:
    bounded_limit = min(max(limit, 1), 10)
    record = session.exec(
        select(HealthRecord)
        .where(HealthRecord.user_id == target_user_id)
        .order_by(HealthRecord.record_date.desc())
    ).first()

    evaluated_source = None
    evaluated_at = _safe_isoformat(datetime.utcnow())
    metrics_payload: Dict[str, Any] = {}

    if record:
        metrics_payload = _safe_json_loads(record.metrics) or {}
        if isinstance(metrics_payload, dict) and metrics_payload:
            evaluated_source = "health_record"
            evaluated_at = record.record_date.isoformat()
        else:
            metrics_payload = {}

    if not metrics_payload:
        metrics_payload = _profile_metrics_payload(user.profile)
        if metrics_payload:
            evaluated_source = "user_profile"

    if not metrics_payload:
        return _empty_recent_abnormal_metrics_result(evaluated_source)

    anomalies = _rank_anomalies(anomaly_service.detect_anomalies(metrics_payload))
    if not anomalies:
        result = _empty_recent_abnormal_metrics_result(evaluated_source)
        result["evaluated_at"] = evaluated_at
        return result

    summary = anomaly_service.generate_summary(anomalies)
    return {
        "has_abnormal_metrics": True,
        "evaluated_at": evaluated_at,
        "evaluated_source": evaluated_source,
        "summary": {
            "status": summary.get("status"),
            "count": summary.get("count", len(anomalies)),
            "message": summary.get("message", f"{len(anomalies)} abnormal metrics found"),
        },
        "items": [
            {
                "metric_key": item.get("item"),
                "display_name": item.get("item"),
                "value": item.get("value"),
                "unit": item.get("unit", ""),
                "status": item.get("status"),
                "tag": item.get("tag"),
                "message": item.get("msg"),
                "detection_source": item.get("source"),
            }
            for item in anomalies[:bounded_limit]
        ],
    }


@agent_tool(
    name="latest_analysis_snapshot_lookup",
    read_only=True,
    scope="self_only",
    description="Read the latest bounded saved analysis snapshot for the current user.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def latest_analysis_snapshot_lookup(
    *,
    user: User,
    session: Session,
    target_user_id: int,
) -> Dict[str, Any]:
    record = session.exec(
        select(HealthRecord)
        .where(HealthRecord.user_id == target_user_id)
        .order_by(HealthRecord.record_date.desc())
    ).first()

    snapshot_payload = None
    snapshot_source = None
    captured_at = None

    if record and record.risk_snapshot:
        snapshot_payload = record.risk_snapshot
        snapshot_source = "health_record_risk_snapshot"
        captured_at = record.record_date.isoformat()
    elif user.profile and user.profile.risk_history:
        snapshot_payload = user.profile.risk_history
        snapshot_source = "user_profile_risk_history"

    if not snapshot_payload:
        return _empty_analysis_snapshot_result()

    projection = project_risk_snapshot_for_tool(
        snapshot_payload,
        snapshot_source=snapshot_source,
        captured_at=captured_at,
    )
    return projection


@agent_tool(
    name="search_medical_guidelines",
    read_only=True,
    scope="self_only",
    description="Search the platform knowledge base for relevant medical guidelines.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The medical question to search for in the knowledge base."},
        },
        "required": ["query"],
    },
)
def search_medical_guidelines(
    *,
    user: User,
    session: Session,
    target_user_id: int,
    query: str,
    k: int = 3,
) -> Dict[str, Any]:
    context = rag_service.search_context(query, k=k)
    return {
        "query": query,
        "matches_found": bool(context),
        "context": context,
    }
