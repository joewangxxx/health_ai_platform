import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

OCR_SUMMARY_SCHEMA_VERSION = "ocr_summary.v1"
OCR_PROCESSING_STATUS_SCHEMA_VERSION = "ocr_processing_status.v1"
RISK_SNAPSHOT_SCHEMA_VERSION = "risk_snapshot.v1"
MEDICATION_SUMMARY_SCHEMA_VERSION = "medication_summary.v1"

OCR_PATIENT_FIELDS = ("Age", "Gender", "Height", "Weight")
OCR_RESERVED_KEYS = {
    "schema_version",
    "document_type",
    "patient_context",
    "metrics",
    "extra_findings",
    "narrative_summary",
    "summary",
    "extra_data",
}
OCR_ALIAS_MAP = {
    "FPG": "Glucose_Fasting",
    "GLU": "Glucose_Fasting",
    "Glucose": "Glucose_Fasting",
    "Glu": "Glucose_Fasting",
    "HbA1C": "HbA1c",
    "A1c": "HbA1c",
    "TC": "Cholesterol_Total",
    "TG": "Triglycerides",
    "HDL": "Cholesterol_HDL",
    "HDL-C": "Cholesterol_HDL",
    "HDL_C": "Cholesterol_HDL",
    "HDLC": "Cholesterol_HDL",
    "LDL": "Cholesterol_LDL",
    "LDL-C": "Cholesterol_LDL",
    "LDL_C": "Cholesterol_LDL",
    "LDLC": "Cholesterol_LDL",
    "Cr": "Creatinine",
    "CREA": "Creatinine",
    "Scr": "Creatinine",
    "GFR": "eGFR",
    "PLT": "Platelet",
}
OCR_CANONICAL_METRIC_KEYS = {
    "Glucose_Fasting",
    "HbA1c",
    "Cholesterol_Total",
    "Triglycerides",
    "Cholesterol_HDL",
    "Cholesterol_LDL",
    "eGFR",
    "Creatinine",
    "WBC",
    "HGB",
    "Platelet",
    "GGT",
    "ALP",
    "ALT",
    "AST",
    "UA",
    "BMI",
    "SBP",
    "DBP",
    "Weight",
    "WaistCircum",
}
MEDICATION_FIELD_ALIASES = {
    "name": ("name", "medication_name", "drug_name", "item"),
    "dose": ("dose", "amount"),
    "unit": ("unit", "dose_unit"),
    "frequency": ("frequency", "freq"),
    "route": ("route",),
    "instruction": ("instruction", "instructions", "note"),
}
MEDICATION_SOURCE_KEYS = ("medications", "medication_items", "medication_summary")
RISK_RESERVED_KEYS = {
    "schema_version",
    "generated_at",
    "source",
    "findings",
    "ckm",
    "ckm_stage",
    "CKM",
    "CKM_stage",
    "captured_at",
    "raw_snapshot_present",
    "summary",
}
RISK_LEVEL_MAP = {
    "very high": "very_high",
    "very_high": "very_high",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low",
}


def _parse_json_payload(payload: Any) -> Any:
    """中文说明：_parse_json_payload 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return payload
    return payload


def _is_non_empty_mapping(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def _normalize_metric_object(value: Any) -> Dict[str, Any]:
    """中文说明：_normalize_metric_object 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if isinstance(value, dict):
        normalized: Dict[str, Any] = {}
        for key in ("value", "unit", "ref_range", "hospital_flag"):
            if key in value and value[key] is not None:
                normalized[key] = value[key]
        if "value" not in normalized:
            normalized["value"] = value.get("value")
        if "unit" in normalized:
            normalized["unit"] = _normalize_unit(normalized["unit"])
        return normalized
    return {"value": value}


def _normalize_unit(unit: Any) -> Any:
    if not isinstance(unit, str):
        return unit
    normalized = unit.strip()
    replacements = {
        "μ": "u",
        "µ": "u",
        "ｍ": "m",
        "ｌ": "l",
        "Ｌ": "L",
    }
    for src, target in replacements.items():
        normalized = normalized.replace(src, target)
    return normalized


def _normalize_metric_mapping(mapping: Any) -> Dict[str, Dict[str, Any]]:
    """中文说明：_normalize_metric_mapping 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(mapping, dict):
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for key, value in mapping.items():
        if key is None:
            continue
        normalized[str(key)] = _normalize_metric_object(value)
    return normalized


def _normalize_patient_context(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """中文说明：_normalize_patient_context 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if isinstance(payload.get("patient_context"), dict):
        context = payload["patient_context"]
    else:
        context = {key: payload.get(key) for key in OCR_PATIENT_FIELDS if payload.get(key) is not None}

    if not context:
        return None

    return {key: context[key] for key in OCR_PATIENT_FIELDS if key in context and context[key] is not None}


def _collect_ocr_metric_entries(payload: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    metrics: Dict[str, Dict[str, Any]] = {}
    extra_findings: Dict[str, Dict[str, Any]] = {}

    if isinstance(payload.get("metrics"), dict):
        source_mapping = payload["metrics"]
    else:
        source_mapping = {
            key: value
            for key, value in payload.items()
            if key not in OCR_RESERVED_KEYS and key not in OCR_PATIENT_FIELDS
        }

    for raw_key, raw_value in source_mapping.items():
        canonical_key = OCR_ALIAS_MAP.get(raw_key, raw_key)
        normalized_value = _normalize_metric_object(raw_value)
        if canonical_key in OCR_CANONICAL_METRIC_KEYS:
            metrics[canonical_key] = normalized_value
        else:
            extra_findings[canonical_key] = normalized_value

    if isinstance(payload.get("extra_findings"), dict):
        for key, value in payload["extra_findings"].items():
            extra_findings[str(key)] = _normalize_metric_object(value)
    if isinstance(payload.get("extra_data"), dict):
        for key, value in payload["extra_data"].items():
            extra_findings[str(key)] = _normalize_metric_object(value)

    return metrics, extra_findings


def normalize_ocr_summary_payload(payload: Any) -> Optional[Dict[str, Any]]:
    """中文说明：normalize_ocr_summary_payload 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    parsed = _parse_json_payload(payload)
    if not isinstance(parsed, dict):
        return None

    normalized = {
        "schema_version": OCR_SUMMARY_SCHEMA_VERSION,
        "document_type": parsed.get("document_type") if "document_type" in parsed else None,
        "patient_context": _normalize_patient_context(parsed),
        "metrics": {},
        "extra_findings": {},
        "narrative_summary": parsed.get("narrative_summary") or parsed.get("summary"),
    }
    metrics, extra_findings = _collect_ocr_metric_entries(parsed)
    normalized["metrics"] = metrics
    normalized["extra_findings"] = extra_findings
    return normalized


def has_structured_ocr_summary_data(payload: Any) -> bool:
    """中文说明：has_structured_ocr_summary_data 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    normalized = normalize_ocr_summary_payload(payload)
    if not normalized:
        return False

    return any(
        [
            bool(normalized.get("patient_context")),
            bool(normalized.get("metrics")),
            bool(normalized.get("extra_findings")),
            bool(normalized.get("narrative_summary")),
        ]
    )


def normalize_ocr_processing_status_payload(
    payload: Any,
    *,
    default_status: Optional[str] = None,
    default_reason: Optional[str] = None,
    structured_data_present: Optional[bool] = None,
    raw_text_present: Optional[bool] = None,
    saved_at: Optional[str] = None,
    processed_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    parsed = _parse_json_payload(payload)
    if parsed is None:
        if default_status is None:
            return None
        parsed = {}

    if not isinstance(parsed, dict):
        return None

    normalized = {
        "schema_version": OCR_PROCESSING_STATUS_SCHEMA_VERSION,
        "status": parsed.get("status") or default_status,
        "reason": parsed.get("reason") if "reason" in parsed else default_reason,
        "structured_data_present": parsed.get("structured_data_present"),
        "raw_text_present": parsed.get("raw_text_present"),
        "saved_at": parsed.get("saved_at") or saved_at,
        "processed_at": parsed.get("processed_at") or processed_at,
    }

    if normalized["structured_data_present"] is None:
        normalized["structured_data_present"] = bool(structured_data_present)
    if normalized["raw_text_present"] is None:
        normalized["raw_text_present"] = bool(raw_text_present)

    if normalized["status"] is None:
        return None

    return normalized


def project_ocr_summary_for_tool(payload: Any, *, metric_limit: int = 5) -> Optional[Dict[str, Any]]:
    """中文说明：project_ocr_summary_for_tool 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    normalized = normalize_ocr_summary_payload(payload)
    if normalized is None:
        return None

    metric_items = list(normalized["metrics"].items())
    metrics_truncated = len(metric_items) > metric_limit
    metric_items = metric_items[:metric_limit]

    return {
        "schema_version": normalized["schema_version"],
        "document_type": normalized.get("document_type"),
        "narrative_summary": normalized.get("narrative_summary"),
        "patient_context": normalized.get("patient_context"),
        "metrics": [
            {
                "metric_key": metric_key,
                "value": metric_value.get("value"),
                "unit": metric_value.get("unit"),
                "ref_range": metric_value.get("ref_range"),
                "hospital_flag": metric_value.get("hospital_flag"),
            }
            for metric_key, metric_value in metric_items
        ],
        "metrics_truncated": metrics_truncated,
        "extra_findings_count": len(normalized["extra_findings"]),
    }


def _normalize_medication_item(value: Any) -> Optional[Dict[str, Any]]:
    """中文说明：_normalize_medication_item 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(value, dict):
        return None

    normalized: Dict[str, Any] = {}
    for target_key, aliases in MEDICATION_FIELD_ALIASES.items():
        for alias in aliases:
            if value.get(alias) not in (None, ""):
                normalized[target_key] = value.get(alias)
                break

    if not normalized.get("name"):
        return None

    return {
        key: normalized[key]
        for key in ("name", "dose", "unit", "frequency", "route", "instruction")
        if normalized.get(key) not in (None, "")
    }


def _collect_medication_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """中文说明：_collect_medication_items 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    candidates: List[Any] = []
    for key in MEDICATION_SOURCE_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            nested_items = value.get("medication_items")
            if isinstance(nested_items, list):
                candidates.extend(nested_items)
            elif any(value.get(field) not in (None, "") for field in ("name", "medication_name", "drug_name", "item")):
                candidates.append(value)

    extra_data = payload.get("extra_data")
    if isinstance(extra_data, dict):
        for value in extra_data.values():
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                nested_items = value.get("medication_items")
                if isinstance(nested_items, list):
                    candidates.extend(nested_items)
                elif any(value.get(field) not in (None, "") for field in ("name", "medication_name", "drug_name", "item")):
                    candidates.append(value)

    normalized_items: List[Dict[str, Any]] = []
    for item in candidates:
        normalized_item = _normalize_medication_item(item)
        if normalized_item:
            normalized_items.append(normalized_item)
    return normalized_items


def project_medication_summary_for_tool(
    payload: Any,
    *,
    document_id: Optional[int] = None,
    file_name: Optional[str] = None,
    source_ref: Optional[str] = None,
    summary_source: Optional[str] = None,
    limit: int = 5,
) -> Optional[Dict[str, Any]]:
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    parsed = _parse_json_payload(payload)
    if not isinstance(parsed, dict):
        return None

    medication_items = _collect_medication_items(parsed)
    if not medication_items:
        return None

    bounded_limit = min(max(limit, 1), 10)
    selected_items = medication_items[:bounded_limit]
    source_refs = [source_ref] if source_ref else []
    resolved_source = summary_source or "medical_document_ocr_summary"
    if resolved_source == "user_profile_extra_data" and not source_refs:
        source_refs = ["profile_extra_data"]
    elif not source_refs and document_id is not None:
        source_refs = [f"report:{document_id}"]

    return {
        "has_medication_summary": True,
        "document_id": document_id,
        "file_name": file_name,
        "summary_source": resolved_source,
        "medication_summary": {
            "schema_version": MEDICATION_SUMMARY_SCHEMA_VERSION,
            "status": "info",
            "count": len(selected_items),
            "message": f"{len(selected_items)} medication facts found",
            "medication_items": selected_items,
            "medication_items_truncated": len(medication_items) > bounded_limit,
            "source_refs": source_refs,
        },
    }


def _coerce_probability(value: Any) -> Optional[float]:
    """中文说明：_coerce_probability 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric > 1:
        numeric = numeric / 100.0
    return round(numeric, 4)


def _normalize_risk_level_value(payload: Dict[str, Any]) -> Optional[str]:
    """中文说明：_normalize_risk_level_value 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    risk_level = payload.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip():
        return RISK_LEVEL_MAP.get(risk_level.strip().lower(), risk_level.strip().lower())

    level = payload.get("level")
    if isinstance(level, str) and level.strip():
        return RISK_LEVEL_MAP.get(level.strip().lower(), level.strip().lower())
    return None


def _normalize_ckm(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """中文说明：_normalize_ckm 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
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


def _normalize_finding(key: str, value: Any) -> Optional[Dict[str, Any]]:
    """中文说明：_normalize_finding 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if isinstance(value, dict):
        normalized = {
            "key": key,
            "label": value.get("label") or value.get("disease_cn") or key,
            "risk_level": _normalize_risk_level_value(value),
            "probability": _coerce_probability(value.get("probability", value.get("final_risk", value.get("risk")))),
        }
        if normalized["probability"] is None and normalized["risk_level"] is None:
            return None
        return normalized

    probability = _coerce_probability(value)
    if probability is None:
        return None
    return {
        "key": key,
        "label": key,
        "risk_level": None,
        "probability": probability,
    }


def _rank_finding(finding: Dict[str, Any]) -> Tuple[int, float, str]:
    """中文说明：_rank_finding 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    risk_level = str(finding.get("risk_level") or "").lower()
    risk_weight = {
        "very_high": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(risk_level, 0)
    probability = finding.get("probability")
    return (-risk_weight, -(probability if probability is not None else -1.0), str(finding.get("key") or ""))


def _compare_metric_values(baseline_value: Any, comparison_value: Any) -> Optional[str]:
    """中文说明：_compare_metric_values 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if baseline_value == comparison_value:
        return None
    try:
        baseline_num = float(baseline_value)
        comparison_num = float(comparison_value)
    except (TypeError, ValueError):
        return "changed"
    if comparison_num > baseline_num:
        return "up"
    if comparison_num < baseline_num:
        return "down"
    return "changed"


def project_report_comparison_for_tool(
    baseline_payload: Any,
    comparison_payload: Any,
    *,
    baseline_document_id: Optional[int] = None,
    comparison_document_id: Optional[int] = None,
    baseline_file_name: Optional[str] = None,
    comparison_file_name: Optional[str] = None,
    limit: int = 5,
) -> Optional[Dict[str, Any]]:
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    baseline_normalized = normalize_ocr_summary_payload(baseline_payload)
    comparison_normalized = normalize_ocr_summary_payload(comparison_payload)
    if not baseline_normalized or not comparison_normalized:
        return None

    baseline_metrics = baseline_normalized.get("metrics") or {}
    comparison_metrics = comparison_normalized.get("metrics") or {}
    delta_items: List[Dict[str, Any]] = []

    shared_metric_keys = sorted(set(baseline_metrics.keys()) & set(comparison_metrics.keys()))
    new_findings_keys = sorted(set(comparison_metrics.keys()) - set(baseline_metrics.keys()))
    removed_findings_keys = sorted(set(baseline_metrics.keys()) - set(comparison_metrics.keys()))

    for metric_key in shared_metric_keys:
        baseline_metric = baseline_metrics.get(metric_key) or {}
        comparison_metric = comparison_metrics.get(metric_key) or {}
        change = _compare_metric_values(baseline_metric.get("value"), comparison_metric.get("value"))
        if change is None:
            continue
        delta_items.append(
            {
                "field": metric_key,
                "baseline_value": baseline_metric.get("value"),
                "comparison_value": comparison_metric.get("value"),
                "change": change,
                "source_refs": ["baseline_report", "comparison_report"],
            }
        )

    for metric_key in new_findings_keys:
        metric = comparison_metrics.get(metric_key) or {}
        delta_items.append(
            {
                "field": metric_key,
                "baseline_value": None,
                "comparison_value": metric.get("value"),
                "change": "new",
                "source_refs": ["baseline_report", "comparison_report"],
            }
        )

    for metric_key in removed_findings_keys:
        metric = baseline_metrics.get(metric_key) or {}
        delta_items.append(
            {
                "field": metric_key,
                "baseline_value": metric.get("value"),
                "comparison_value": None,
                "change": "removed",
                "source_refs": ["baseline_report", "comparison_report"],
            }
        )

    bounded_limit = min(max(limit, 1), 10)
    selected_items = delta_items[:bounded_limit]

    return {
        "has_report_comparison": True,
        "baseline_document_id": baseline_document_id,
        "comparison_document_id": comparison_document_id,
        "baseline_file_name": baseline_file_name,
        "comparison_file_name": comparison_file_name,
        "comparison_basis": "medical_document_ocr_summary",
        "summary": {
            "status": "different" if selected_items else "same",
            "count": len(selected_items),
            "message": f"{len(selected_items)} bounded differences found" if selected_items else "No bounded differences found",
        },
        "delta_items": selected_items,
        "shared_metric_count": len(shared_metric_keys),
        "new_findings_count": len(new_findings_keys),
        "removed_findings_count": len(removed_findings_keys),
        "source_refs": ["baseline_report", "comparison_report"],
    }


def _collect_snapshot_findings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """中文说明：_collect_snapshot_findings 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    findings: List[Dict[str, Any]] = []

    if isinstance(payload.get("findings"), list):
        for entry in payload["findings"]:
            if isinstance(entry, dict):
                key = str(entry.get("key") or entry.get("item") or entry.get("label") or "finding")
                finding = _normalize_finding(key, entry)
                if finding:
                    findings.append(finding)
        return sorted(findings, key=_rank_finding)

    for key, value in payload.items():
        if key in RISK_RESERVED_KEYS:
            continue
        if not isinstance(value, dict):
            continue
        finding = _normalize_finding(str(key), value)
        if finding:
            findings.append(finding)

    return sorted(findings, key=_rank_finding)


def normalize_risk_snapshot_payload(
    payload: Any,
    *,
    source: Optional[str] = None,
    generated_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """中文说明：normalize_risk_snapshot_payload 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    parsed = _parse_json_payload(payload)
    if not isinstance(parsed, dict):
        return None

    normalized = {
        "schema_version": RISK_SNAPSHOT_SCHEMA_VERSION,
        "generated_at": parsed.get("generated_at")
        or parsed.get("captured_at")
        or generated_at,
        "source": parsed.get("source") or source,
        "findings": [],
        "ckm": _normalize_ckm(parsed),
    }
    normalized["findings"] = _collect_snapshot_findings(parsed)
    return normalized


def project_risk_snapshot_for_tool(
    payload: Any,
    *,
    snapshot_source: Optional[str] = None,
    captured_at: Optional[str] = None,
    finding_limit: int = 3,
) -> Dict[str, Any]:
    """中文说明：project_risk_snapshot_for_tool 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    normalized = normalize_risk_snapshot_payload(payload, source=snapshot_source, generated_at=captured_at)
    if normalized is None:
        return {
            "has_analysis_snapshot": False,
            "snapshot_source": snapshot_source,
            "captured_at": captured_at,
            "top_findings": [],
            "ckm": None,
            "raw_snapshot_present": False,
        }

    top_findings = normalized["findings"][:finding_limit]
    has_snapshot = bool(normalized["findings"] or normalized.get("ckm") or normalized.get("generated_at") or normalized.get("source"))
    resolved_captured_at = captured_at
    if resolved_captured_at is None and snapshot_source is None:
        resolved_captured_at = normalized.get("generated_at")
    return {
        "has_analysis_snapshot": has_snapshot,
        "snapshot_source": snapshot_source or normalized.get("source"),
        "captured_at": resolved_captured_at,
        "top_findings": top_findings,
        "ckm": normalized.get("ckm"),
        "raw_snapshot_present": True,
    }


def summarize_risk_snapshot_for_context(payload: Any) -> str:
    """中文说明：summarize_risk_snapshot_for_context 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    projection = project_risk_snapshot_for_tool(payload)
    if not projection["has_analysis_snapshot"]:
        return "暂无可用风险快照"

    parts: List[str] = []
    top_findings = projection.get("top_findings") or []
    if top_findings:
        rendered = []
        for finding in top_findings[:3]:
            label = finding.get("label") or finding.get("key")
            risk_level = finding.get("risk_level")
            probability = finding.get("probability")
            if risk_level and probability is not None:
                rendered.append(f"{label}({risk_level}, {probability})")
            elif risk_level:
                rendered.append(f"{label}({risk_level})")
            elif probability is not None:
                rendered.append(f"{label}({probability})")
            else:
                rendered.append(str(label))
        parts.append("主要风险: " + ", ".join(rendered))

    ckm = projection.get("ckm") or {}
    if ckm.get("stage") is not None or ckm.get("stage_name"):
        stage_bits = []
        if ckm.get("stage") is not None:
            stage_bits.append(f"stage {ckm['stage']}")
        if ckm.get("stage_name"):
            stage_bits.append(str(ckm["stage_name"]))
        parts.append("CKM: " + ", ".join(stage_bits))

    if projection.get("captured_at"):
        parts.append(f"captured_at={projection['captured_at']}")

    return "; ".join(parts) if parts else "已读取最新风险快照"


def summarize_ocr_summary_for_context(payload: Any) -> str:
    """中文说明：summarize_ocr_summary_for_context 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    projection = project_ocr_summary_for_tool(payload)
    if not projection:
        return "暂无可用报告摘要"

    parts: List[str] = []
    patient_context = projection.get("patient_context") or {}
    if patient_context:
        context_bits = [f"{key}={value}" for key, value in patient_context.items()]
        parts.append("患者信息: " + ", ".join(context_bits))

    metrics = projection.get("metrics") or []
    if metrics:
        metric_bits = []
        for metric in metrics[:3]:
            metric_key = metric.get("metric_key")
            value = metric.get("value")
            unit = metric.get("unit") or ""
            metric_bits.append(f"{metric_key}={value}{unit}")
        parts.append("关键指标: " + ", ".join(metric_bits))

    narrative = projection.get("narrative_summary")
    if narrative:
        parts.append(f"摘要: {narrative}")

    return "; ".join(parts) if parts else "已读取最新报告摘要"


def is_canonical_ocr_summary_payload(payload: Any) -> bool:
    """中文说明：is_canonical_ocr_summary_payload 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    parsed = _parse_json_payload(payload)
    return isinstance(parsed, dict) and parsed.get("schema_version") == OCR_SUMMARY_SCHEMA_VERSION and isinstance(parsed.get("metrics"), dict)


def is_canonical_risk_snapshot_payload(payload: Any) -> bool:
    """中文说明：is_canonical_risk_snapshot_payload 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    parsed = _parse_json_payload(payload)
    return isinstance(parsed, dict) and parsed.get("schema_version") == RISK_SNAPSHOT_SCHEMA_VERSION and isinstance(parsed.get("findings"), list)


def scan_legacy_payload_shapes(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """中文说明：scan_legacy_payload_shapes 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    findings: List[Dict[str, Any]] = []
    for row in rows:
        entity = row.get("entity")
        raw_payload = row.get("payload")
        if entity == "MedicalDocument":
            if raw_payload is not None and not is_canonical_ocr_summary_payload(raw_payload):
                findings.append(
                    {
                        "entity": entity,
                        "id": row.get("id"),
                        "field": "ocr_summary",
                        "shape": "legacy",
                    }
                )
        elif entity in {"HealthRecord", "UserProfile"}:
            if raw_payload is not None and not is_canonical_risk_snapshot_payload(raw_payload):
                findings.append(
                    {
                        "entity": entity,
                        "id": row.get("id"),
                        "field": "risk_snapshot" if entity == "HealthRecord" else "risk_history",
                        "shape": "legacy",
                    }
                )
    return findings


def _repairable_payload_for_row(entity: str, raw_payload: Any) -> Optional[Dict[str, Any]]:
    # 按实体类型选择可逆的规范化策略，返回统一结构；无法修复时返回 None。
    """中文说明：_repairable_payload_for_row 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if entity == "MedicalDocument":
        return normalize_ocr_summary_payload(raw_payload)
    if entity == "HealthRecord":
        return normalize_risk_snapshot_payload(raw_payload, source="health_record_legacy_backfill")
    if entity == "UserProfile":
        return normalize_risk_snapshot_payload(raw_payload, source="user_profile_legacy_backfill")
    return None


def repair_legacy_payload_rows(session: Any) -> Dict[str, Any]:
    # 批量修复历史遗留 payload 结构：
    # 1) 全量扫描三类实体字段；
    # 2) 仅处理“非 canonical 且非空”的记录；
    # 3) 可修复则写回规范化 JSON，不可修复仅登记。
    from backend.models import HealthRecord, MedicalDocument, UserProfile
    from sqlmodel import select

    entity_map = {
        "MedicalDocument": (MedicalDocument, "ocr_summary"),
        "HealthRecord": (HealthRecord, "risk_snapshot"),
        "UserProfile": (UserProfile, "risk_history"),
    }

    rows: List[Dict[str, Any]] = []
    # 先把候选行拍平，便于统一扫描与统计。
    for entity, (model, field_name) in entity_map.items():
        for item in session.exec(select(model)).all():
            rows.append(
                {
                    "entity": entity,
                    "id": item.id,
                    "field": field_name,
                    "payload": getattr(item, field_name),
                }
            )

    findings_before = scan_legacy_payload_shapes(rows)
    repaired_rows: List[Dict[str, Any]] = []
    unrepairable_rows: List[Dict[str, Any]] = []

    # 只转换确认为 legacy 形态的数据，避免覆盖已规范内容。
    for row in rows:
        entity = row["entity"]
        raw_payload = row["payload"]
        if entity == "MedicalDocument" and is_canonical_ocr_summary_payload(raw_payload):
            continue
        if entity in {"HealthRecord", "UserProfile"} and is_canonical_risk_snapshot_payload(raw_payload):
            continue
        if raw_payload is None:
            continue

        normalized_payload = _repairable_payload_for_row(entity, raw_payload)
        if normalized_payload is None:
            unrepairable_rows.append(
                {
                    "entity": entity,
                    "id": row["id"],
                    "field": row["field"],
                }
            )
            continue

        repaired_rows.append(
            {
                "entity": entity,
                "id": row["id"],
                "field": row["field"],
                "payload": normalized_payload,
            }
        )

    # 回写阶段与扫描阶段分离，确保统计口径稳定。
    for repaired_row in repaired_rows:
        model, field_name = entity_map[repaired_row["entity"]]
        record = session.get(model, repaired_row["id"])
        if not record:
            continue
        setattr(record, field_name, json.dumps(repaired_row["payload"], ensure_ascii=False))
        session.add(record)

    # 仅在存在实际修复时提交事务，避免无意义写入。
    if repaired_rows:
        session.commit()

    rows_after: List[Dict[str, Any]] = []
    for entity, (model, field_name) in entity_map.items():
        for item in session.exec(select(model)).all():
            rows_after.append(
                {
                    "entity": entity,
                    "id": item.id,
                    "field": field_name,
                    "payload": getattr(item, field_name),
                }
            )

    findings_after = scan_legacy_payload_shapes(rows_after)
    checked_rows = len(rows)
    repaired_count = len(repaired_rows)
    unrepairable_count = len(unrepairable_rows)

    return {
        "checked_rows": checked_rows,
        "legacy_count_before": len(findings_before),
        "repaired_count": repaired_count,
        "unrepairable_count": unrepairable_count,
        "skipped_count": checked_rows - repaired_count - unrepairable_count,
        "legacy_count_after": len(findings_after),
        "repaired_rows": repaired_rows,
        "unrepairable_rows": unrepairable_rows,
    }
