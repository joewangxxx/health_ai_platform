from typing import Any, Dict, List, Optional


URGENT_PATTERNS = [
    "chest pain",
    "trouble breathing",
    "difficulty breathing",
    "shortness of breath",
    "fainting",
    "passed out",
    "suicidal",
    "self harm",
    "anaphylaxis",
    "severe allergic reaction",
    "drug allergy",
    "胸痛",
    "呼吸困难",
    "呼吸急促",
    "气短",
    "晕厥",
    "昏厥",
    "自杀",
    "自伤",
    "严重过敏",
    "药物过敏",
    "鑳哥棝",
    "鍛煎惛鍥伴毦",
    "鍛煎惛鎬ヤ績",
    "姘旂煭",
    "鏅曞€?",
    "鏄忓帴",
    "鑷潃",
    "鑷激",
    "涓ラ噸杩囨晱",
    "鑽墿杩囨晱",
    "閼冲摜妫?",
    "閸涚厧鎯涢崶浼存",
    "濮樻梻鐓?",
    "閺勫繐甯?",
    "閺呮洖鈧?",
    "閼奉亝娼?",
    "閼奉亙婵€",
    "娑撱儵鍣告潻鍥ㄦ櫛",
    "閼筋垳澧挎潻鍥ㄦ櫛",
]

DIAGNOSIS_PATTERNS = [
    "diagnose",
    "diagnosis",
    "do i have",
    "is it",
    "what disease",
    "rule out",
    "confirm",
    "确诊",
    "诊断",
    "是不是",
    "排除",
    "纭瘖",
    "璇婃柇",
    "鏄笉鏄?",
    "鎺掗櫎",
    "绾喛鐦?",
    "鐠囧﹥鏌?",
    "閺勵垯绗夐弰?",
    "閹烘帡娅?",
    "閼虫垝绗夐懗钘夊灲閺?",
    "閸掓澘绨抽弰顖欑瑝閺?",
]

MEDICATION_PATTERNS = [
    "medication",
    "medications",
    "medicine",
    "drug",
    "prescription",
    "dose",
    "pill",
    "药",
    "药物",
    "用药",
    "处方",
    "剂量",
    "鑽?",
    "鑽墿",
    "鐢ㄨ嵂",
    "澶勬柟",
    "鍓傞噺",
    "閼?",
    "閼筋垳澧?",
    "閻劏宓?",
    "婢跺嫭鏌?",
    "閸撳倿鍣?",
]

TREND_PATTERNS = [
    "trend",
    "trends",
    "history",
    "historical",
    "over time",
    "going up",
    "going down",
    "变化",
    "趋势",
    "历史",
    "升高",
    "下降",
    "波动",
    "鍙樺寲",
    "瓒嬪娍",
    "鍘嗗彶",
    "鍗囬珮",
    "涓嬮檷",
    "娉㈠姩",
    "閸欐ê瀵?",
    "鐡掑濞?",
    "閸樺棗褰?",
    "閸楀洭鐝?",
    "娑撳妾?",
    "濞夈垹濮?",
]

REPORT_PATTERNS = [
    "report",
    "reports",
    "lab result",
    "test result",
    "uploaded result",
    "uploaded report",
    "ocr summary",
    "体检报告",
    "报告",
    "检查单",
    "化验单",
    "浣撴鎶ュ憡",
    "鎶ュ憡",
    "鎶ュ憡鍗?",
    "妫€鏌ュ崟",
    "鍖栭獙鍗?",
    "娴ｆ挻顥呴幎銉ユ啞",
    "閹躲儱鎲?",
    "閹躲儱鎲￠崡?",
    "濡偓閺屻儱宕?",
    "閸栨牠鐛欓崡?",
]

MEDICATION_CHANGE_PATTERNS = [
    "should i stop",
    "stop taking",
    "start taking",
    "increase the dose",
    "decrease the dose",
    "double the dose",
    "change my dose",
    "switch medication",
    "prescribe",
    "increase my current dose",
    "start metformin",
    "stop metformin",
    "停药",
    "换药",
    "加量",
    "减量",
    "剂量调整",
    "开药",
    "鍋滆嵂",
    "鎹㈣嵂",
    "鍔犻噺",
    "鍑忛噺",
    "鍓傞噺璋冩暣",
    "寮€鑽?",
]

URGENT_OVERRIDE_PATTERNS = [
    "can i wait",
    "do i need to go",
    "can i stay home",
    "ignore the symptoms",
    "先不去医院",
    "能不能先观察",
    "可不可以不去医院",
    "鍏堜笉鍘诲尰闄?",
    "鑳戒笉鑳藉厛瑙傚療",
    "鍙互涓嶅幓鍖婚櫌鍚?",
]

ELEVATED_RISK_PATTERNS = [
    "high",
    "abnormal",
    "worsening",
    "getting worse",
    "risk",
    "偏高",
    "异常",
    "加重",
    "恶化",
    "风险",
    "鍋忛珮",
    "寮傚父",
    "鍔犻噸",
    "鎭跺寲",
    "椋庨櫓",
]

POLICY_EVALUATION_ORDER = [
    "urgent_symptom",
    "diagnosis_sensitive",
    "medication_related",
    "trend_review",
    "report_interpretation",
    "general_health",
]
POLICY_VERSION = "explicit_policy.v1"
EVIDENCE_STATES = {"sufficient", "limited", "insufficient"}
TOOL_AVAILABILITY_STATES = {"none", "partial", "full"}

_METRIC_ALIASES = {
    "glucose_fasting": "glucose_fasting",
    "glucose": "glucose_fasting",
    "fasting_glucose": "glucose_fasting",
    "sbp": "sbp",
    "dbp": "dbp",
    "bmi": "bmi",
}
_NORMAL_HINTS = (
    "healthy adult",
    "healthy adults",
    "normal fasting glucose",
    "normal glucose",
    "within normal range",
    "no abnormalities",
    "no abnormality",
)
_ABNORMAL_HINTS = (
    "high fasting glucose",
    "elevated glucose",
    "abnormal glucose",
    "abnormal fasting glucose",
    "high blood sugar",
)


def _contains_any(normalized_query: str, patterns: List[str]) -> bool:
    return any(pattern in normalized_query for pattern in patterns)


def _classify_lane(normalized_query: str) -> str:
    if _contains_any(normalized_query, URGENT_PATTERNS):
        return "urgent_symptom"
    if _contains_any(normalized_query, DIAGNOSIS_PATTERNS):
        return "diagnosis_sensitive"
    if _contains_any(normalized_query, MEDICATION_PATTERNS):
        return "medication_related"
    if _contains_any(normalized_query, TREND_PATTERNS):
        return "trend_review"
    if _contains_any(normalized_query, REPORT_PATTERNS):
        return "report_interpretation"
    return "general_health"


def classify_policy_pressure(query: str, lane: Optional[str] = None) -> Dict[str, Any]:
    normalized = (query or "").strip().lower()
    effective_lane = lane or _classify_lane(normalized)
    return {
        "requests_medication_change": effective_lane == "medication_related"
        and _contains_any(normalized, MEDICATION_CHANGE_PATTERNS),
        "requests_urgent_override": effective_lane == "urgent_symptom"
        and _contains_any(normalized, URGENT_OVERRIDE_PATTERNS),
        "requests_diagnostic_certainty": effective_lane == "diagnosis_sensitive",
        "mentions_elevated_risk": _contains_any(normalized, ELEVATED_RISK_PATTERNS),
    }


def _normalize_policy_lane(safety_result: Dict[str, Any]) -> str:
    if safety_result.get("route") == "medical_escalation" or safety_result.get("safety_level") == "urgent":
        return "urgent_symptom"
    lane = safety_result.get("lane") or "general_health"
    return lane if lane in POLICY_EVALUATION_ORDER else "general_health"


def _infer_policy_risk_level(*, lane: str, policy_pressure: Dict[str, Any]) -> str:
    if lane in {"urgent_symptom", "diagnosis_sensitive"}:
        return "high"
    if lane == "medication_related" and policy_pressure.get("requests_medication_change"):
        return "high"
    if lane in {"report_interpretation", "trend_review", "medication_related"}:
        return "medium"
    if policy_pressure.get("mentions_elevated_risk"):
        return "medium"
    return "low"


def _tool_result(tool_outputs: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    for item in tool_outputs:
        if item.get("status") == "ok" and item.get("tool") == tool_name:
            result = item.get("result")
            if isinstance(result, dict):
                return result
    return {}


def _normalize_metric_key(metric_key: Any) -> Optional[str]:
    if metric_key is None:
        return None
    return _METRIC_ALIASES.get(str(metric_key).strip().lower().replace(" ", "_"))


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_status(metric_key: str, value: float) -> Optional[str]:
    if metric_key == "glucose_fasting":
        return "high" if value > 6.1 else "normal"
    if metric_key == "sbp":
        return "high" if value > 140 else "normal"
    if metric_key == "dbp":
        return "high" if value > 90 else "normal"
    if metric_key == "bmi":
        return "high" if value > 24 else "normal"
    return None


def _extract_report_metrics(tool_outputs: List[Dict[str, Any]]) -> Dict[str, float]:
    report_summary = _tool_result(tool_outputs, "report_summary_lookup").get("report_summary") or {}
    metrics = report_summary.get("metrics") or []
    normalized: Dict[str, float] = {}
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        metric_key = _normalize_metric_key(metric.get("metric_key"))
        value = _as_float(metric.get("value"))
        if metric_key and value is not None:
            normalized[metric_key] = value
    return normalized


def _extract_trend_metrics(tool_outputs: List[Dict[str, Any]]) -> Dict[str, float]:
    trend_result = _tool_result(tool_outputs, "get_history_trends")
    items = trend_result.get("items") or []
    if not items:
        return {}
    latest = items[0] if isinstance(items[0], dict) else {}
    metrics = latest.get("metrics") if isinstance(latest, dict) else {}
    if not isinstance(metrics, dict):
        return {}
    normalized: Dict[str, float] = {}
    for metric_key, raw_value in metrics.items():
        normalized_key = _normalize_metric_key(metric_key)
        value = _as_float(raw_value)
        if normalized_key and value is not None:
            normalized[normalized_key] = value
    return normalized


def _extract_profile_metrics(
    tool_outputs: List[Dict[str, Any]],
    profile_evidence: Optional[Dict[str, Any]],
) -> Dict[str, float]:
    profile_result = _tool_result(tool_outputs, "get_user_profile_summary")
    normalized: Dict[str, float] = {}
    for source in (profile_result, profile_evidence or {}):
        if not isinstance(source, dict):
            continue
        for metric_key in ("glucose_fasting", "sbp", "dbp", "bmi"):
            value = _as_float(source.get(metric_key))
            if value is not None:
                normalized[metric_key] = value
    return normalized


def _metric_maps_conflict(left: Dict[str, float], right: Dict[str, float]) -> bool:
    for metric_key in set(left).intersection(right):
        left_status = _metric_status(metric_key, left[metric_key])
        right_status = _metric_status(metric_key, right[metric_key])
        if left_status and right_status and left_status != right_status:
            return True
    return False


def _has_abnormal_personal_data(
    tool_outputs: List[Dict[str, Any]],
    profile_evidence: Optional[Dict[str, Any]],
) -> bool:
    abnormal_flags = _tool_result(tool_outputs, "get_user_profile_summary").get("abnormal_flags") or []
    abnormal_flags = abnormal_flags or (profile_evidence or {}).get("abnormal_flags") or []
    if abnormal_flags:
        return True

    for metric_map in (
        _extract_profile_metrics(tool_outputs, profile_evidence),
        _extract_report_metrics(tool_outputs),
        _extract_trend_metrics(tool_outputs),
    ):
        for metric_key, value in metric_map.items():
            if _metric_status(metric_key, value) == "high":
                return True
    return False


def _retrieval_conflicts_with_personal_data(
    retrieval_evidence: Optional[str],
    tool_outputs: List[Dict[str, Any]],
    profile_evidence: Optional[Dict[str, Any]],
) -> bool:
    if not retrieval_evidence:
        return False
    normalized = retrieval_evidence.lower()
    has_abnormal = _has_abnormal_personal_data(tool_outputs, profile_evidence)
    if has_abnormal and any(token in normalized for token in _NORMAL_HINTS):
        return True
    if not has_abnormal and any(token in normalized for token in _ABNORMAL_HINTS):
        return True
    return False


def _tool_evidence_metadata(tool_outputs: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    result = _tool_result(tool_outputs, tool_name)
    metadata = result.get("evidence_metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def _tool_support_state(tool_outputs: List[Dict[str, Any]], tool_name: str) -> str:
    result = _tool_result(tool_outputs, tool_name)
    if not _tool_result_has_useful_evidence(tool_name, result):
        return "empty"

    metadata = _tool_evidence_metadata(tool_outputs, tool_name)
    if not metadata:
        return "full"

    coverage = metadata.get("coverage")
    freshness = metadata.get("freshness")
    confidence = metadata.get("confidence")
    if coverage == "empty":
        return "empty"
    if coverage == "partial" or freshness == "stale" or confidence == "low":
        return "limited"
    return "full"


def _apply_rag_quality_summary(
    *,
    evidence_state: str,
    tool_availability: str,
    degrade_reason: Optional[str],
    rag_quality_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(rag_quality_summary, dict):
        return {
            "evidence_state": evidence_state,
            "tool_availability": tool_availability,
            "degrade_reason": degrade_reason,
        }

    retrieval_status = rag_quality_summary.get("retrieval_status")
    chunk_quality = rag_quality_summary.get("chunk_quality")
    density_status = rag_quality_summary.get("density_status")
    provenance_state = rag_quality_summary.get("provenance_state")
    ocr_fallback_state = rag_quality_summary.get("ocr_fallback_state")
    hit_count = int(rag_quality_summary.get("hit_count") or 0)

    if retrieval_status == "unavailable":
        return {
            "evidence_state": "insufficient",
            "tool_availability": "none",
            "degrade_reason": "tool_unavailable",
        }
    if retrieval_status == "empty" or chunk_quality == "empty" or hit_count <= 0:
        return {
            "evidence_state": "insufficient",
            "tool_availability": "partial" if tool_availability != "none" else "none",
            "degrade_reason": "missing_required_context",
        }
    if chunk_quality == "weak":
        return {
            "evidence_state": "insufficient",
            "tool_availability": "partial" if tool_availability != "none" else "none",
            "degrade_reason": "missing_required_context",
        }
    if density_status == "low_density" or provenance_state == "partial" or ocr_fallback_state in {"degraded", "unavailable"}:
        return {
            "evidence_state": "limited",
            "tool_availability": "partial" if tool_availability != "none" else "none",
            "degrade_reason": degrade_reason or "evidence_insufficient",
        }
    return {
        "evidence_state": evidence_state,
        "tool_availability": tool_availability,
        "degrade_reason": degrade_reason,
    }


def _merge_rag_quality_into_result(
    result: Dict[str, Any],
    rag_quality_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    merged = dict(result)
    original_should_continue = bool(merged.get("should_continue"))
    merged.update(
        _apply_rag_quality_summary(
            evidence_state=str(merged.get("evidence_state") or "insufficient"),
            tool_availability=str(merged.get("tool_availability") or "none"),
            degrade_reason=merged.get("degrade_reason"),
            rag_quality_summary=rag_quality_summary,
        )
    )
    if merged.get("evidence_state") != "sufficient":
        merged["should_continue"] = False
    else:
        merged["should_continue"] = original_should_continue
    return merged


def _evaluate_evidence_gate(
    *,
    lane: str,
    allowed_tool_names: List[str],
    tool_outputs: List[Dict[str, Any]],
    profile_evidence: Optional[Dict[str, Any]] = None,
    retrieval_evidence: Optional[str] = None,
    legacy_evidence_state: Optional[str] = None,
    legacy_tool_availability: Optional[str] = None,
) -> Dict[str, Any]:
    if lane == "urgent_symptom":
        return {
            "evidence_state": "insufficient",
            "tool_availability": "none",
            "degrade_reason": "urgent_symptom",
            "missing_classes": [],
            "conflict_classes": [],
        }

    if not tool_outputs:
        evidence_state = legacy_evidence_state if legacy_evidence_state in EVIDENCE_STATES else "insufficient"
        if legacy_tool_availability in TOOL_AVAILABILITY_STATES:
            tool_availability = legacy_tool_availability
        elif evidence_state == "sufficient":
            tool_availability = "full"
        elif allowed_tool_names:
            tool_availability = "partial"
        else:
            tool_availability = "none"
        degrade_reason = None
        if evidence_state == "limited":
            degrade_reason = "evidence_insufficient"
        elif evidence_state == "insufficient":
            degrade_reason = "tool_unavailable" if tool_availability == "none" and allowed_tool_names else "missing_required_context"
        return {
            "evidence_state": evidence_state,
            "tool_availability": tool_availability,
            "degrade_reason": degrade_reason,
            "missing_classes": [],
            "conflict_classes": [],
        }

    profile_state = _tool_support_state(tool_outputs, "get_user_profile_summary")
    has_profile = profile_state == "full"
    has_profile_support = profile_state in {"full", "limited"} or bool(profile_evidence)
    has_guideline = bool(_tool_result(tool_outputs, "search_medical_guidelines").get("matches_found"))
    report_summary_state = _tool_support_state(tool_outputs, "report_summary_lookup")
    has_report_summary = report_summary_state == "full"
    has_report_summary_support = report_summary_state in {"full", "limited"}
    report_comparison_state = _tool_support_state(tool_outputs, "report_comparison_lookup")
    has_report_comparison = report_comparison_state == "full"
    has_report_comparison_support = report_comparison_state in {"full", "limited"}
    uploaded_documents_state = _tool_support_state(tool_outputs, "get_uploaded_documents_summary")
    has_uploaded_documents = (_tool_result(tool_outputs, "get_uploaded_documents_summary").get("count") or 0) > 0
    has_uploaded_documents_support = has_uploaded_documents and uploaded_documents_state in {"full", "limited"}
    trend_count = int(_tool_result(tool_outputs, "get_history_trends").get("count") or 0)
    trend_state = _tool_support_state(tool_outputs, "get_history_trends")
    has_trend_floor = trend_state == "full" and trend_count >= 2
    has_trend_partial = trend_count == 1 or trend_state == "limited"
    anomaly_state = _tool_support_state(tool_outputs, "recent_abnormal_metrics_lookup")
    has_abnormal_metrics = anomaly_state == "full"
    has_abnormal_support = anomaly_state in {"full", "limited"}
    analysis_state = _tool_support_state(tool_outputs, "latest_analysis_snapshot_lookup")
    has_analysis_snapshot = analysis_state == "full"
    has_analysis_support = analysis_state in {"full", "limited"}
    medication_summary = _tool_result(tool_outputs, "medication_summary_lookup")
    medication_items = (medication_summary.get("medication_summary") or {}).get("medication_items") or []
    medication_state = _tool_support_state(tool_outputs, "medication_summary_lookup")
    has_medication_facts = medication_state == "full" and bool(medication_items)
    has_medication_support = medication_state in {"full", "limited"} and bool(medication_items)
    blocked_attempts = any(item.get("status") == "blocked" for item in tool_outputs)
    usable_tool_outputs = [
        item
        for item in tool_outputs
        if item.get("status") == "ok" and _tool_result_has_useful_evidence(item.get("tool"), item.get("result"))
    ]
    empty_ok_tools = [
        item
        for item in tool_outputs
        if item.get("status") == "ok" and not _tool_result_has_useful_evidence(item.get("tool"), item.get("result"))
    ]

    if empty_ok_tools and not usable_tool_outputs:
        return {
            "evidence_state": "insufficient",
            "tool_availability": "none",
            "degrade_reason": "tool_unavailable",
            "missing_classes": [],
            "conflict_classes": [],
        }

    conflict_classes: List[str] = []
    if _metric_maps_conflict(_extract_report_metrics(tool_outputs), _extract_trend_metrics(tool_outputs)):
        conflict_classes.append("report data vs trend history")
    if _metric_maps_conflict(
        _extract_report_metrics(tool_outputs),
        _extract_profile_metrics(tool_outputs, profile_evidence),
    ):
        conflict_classes.append("report data vs profile data")
    if _retrieval_conflicts_with_personal_data(retrieval_evidence, tool_outputs, profile_evidence):
        conflict_classes.append("personal data vs retrieved guidance")
    if conflict_classes:
        return {
            "evidence_state": "insufficient",
            "tool_availability": "partial",
            "degrade_reason": "conflicting_evidence",
            "missing_classes": [],
            "conflict_classes": conflict_classes,
        }

    if lane == "general_health":
        floor_met = has_profile and has_guideline
        partial_support = has_profile_support or has_guideline or has_abnormal_support
        missing_classes = []
        if not has_profile:
            missing_classes.append("profile data")
        if not has_guideline:
            missing_classes.append("retrieved guidance")
    elif lane == "report_interpretation":
        floor_met = has_report_summary or has_report_comparison
        partial_support = has_uploaded_documents_support or has_guideline or has_report_summary_support or has_report_comparison_support
        missing_classes = [] if floor_met else ["report data"]
    elif lane == "trend_review":
        floor_met = has_trend_floor
        partial_support = has_trend_partial or has_abnormal_support or has_analysis_support or has_guideline
        missing_classes = [] if floor_met else ["trend history"]
    elif lane == "medication_related":
        floor_met = has_medication_facts
        partial_support = has_medication_support or has_report_summary_support or has_guideline
        missing_classes = [] if floor_met else ["medication facts"]
    elif lane == "diagnosis_sensitive":
        floor_met = has_profile or has_report_summary or has_analysis_snapshot
        partial_support = has_guideline or has_profile_support or has_report_summary_support or has_analysis_support
        missing_classes = [] if floor_met else ["profile or report context"]
    else:
        floor_met = False
        partial_support = False
        missing_classes = ["required context"]

    if floor_met:
        return {
            "evidence_state": "sufficient",
            "tool_availability": "full",
            "degrade_reason": None,
            "missing_classes": [],
            "conflict_classes": [],
        }
    if partial_support:
        evidence_state = "limited"
        degrade_reason = "evidence_insufficient"
        return {
            "evidence_state": evidence_state,
            "tool_availability": "partial",
            "degrade_reason": degrade_reason,
            "missing_classes": missing_classes,
            "conflict_classes": [],
        }
    if blocked_attempts:
        return {
            "evidence_state": "insufficient",
            "tool_availability": "none",
            "degrade_reason": "tool_unavailable",
            "missing_classes": missing_classes,
            "conflict_classes": [],
        }
    return {
        "evidence_state": "insufficient",
        "tool_availability": "partial" if allowed_tool_names else "none",
        "degrade_reason": "missing_required_context",
        "missing_classes": missing_classes,
        "conflict_classes": [],
    }


def _tool_result_has_useful_evidence(tool_name: Optional[str], result: Any) -> bool:
    if not tool_name or not isinstance(result, dict):
        return False

    if tool_name == "get_user_profile_summary":
        return bool(result.get("has_profile"))
    if tool_name == "get_latest_risk_report":
        risk_report = result.get("risk_report")
        return bool(result.get("has_risk_report") and isinstance(risk_report, dict) and risk_report)
    if tool_name == "get_history_trends":
        return int(result.get("count") or 0) > 0 and bool(result.get("items"))
    if tool_name == "get_uploaded_documents_summary":
        return int(result.get("count") or 0) > 0 and bool(result.get("items"))
    if tool_name == "report_summary_lookup":
        return bool(result.get("has_report_summary")) and bool(result.get("report_summary"))
    if tool_name == "report_comparison_lookup":
        return bool(result.get("has_report_comparison")) and bool(result.get("delta_items"))
    if tool_name in {"recent_metric_anomaly_lookup", "recent_abnormal_metrics_lookup"}:
        return bool(result.get("has_metric_anomalies")) and bool(result.get("items"))
    if tool_name == "latest_analysis_snapshot_lookup":
        return bool(result.get("has_analysis_snapshot")) and bool(result.get("top_findings"))
    if tool_name == "medication_summary_lookup":
        summary = result.get("medication_summary") or {}
        return bool(result.get("has_medication_summary")) and bool(summary.get("medication_items"))
    if tool_name == "search_medical_guidelines":
        return bool(result.get("matches_found")) and bool(result.get("context"))
    return bool(result)


def evaluate_post_tool_sufficiency(
    *,
    lane: str,
    allowed_tool_names: List[str],
    tool_outputs: List[Dict[str, Any]],
    profile_evidence: Optional[Dict[str, Any]] = None,
    retrieval_evidence: Optional[str] = None,
    rag_quality_summary: Optional[Dict[str, Any]] = None,
    legacy_evidence_state: Optional[str] = None,
    legacy_tool_availability: Optional[str] = None,
) -> Dict[str, Any]:
    gate = _evaluate_evidence_gate(
        lane=lane,
        allowed_tool_names=allowed_tool_names,
        tool_outputs=tool_outputs,
        profile_evidence=profile_evidence,
        retrieval_evidence=retrieval_evidence,
        legacy_evidence_state=legacy_evidence_state,
        legacy_tool_availability=legacy_tool_availability,
    )
    usable_tool_outputs = [
        item
        for item in tool_outputs
        if item.get("status") == "ok" and _tool_result_has_useful_evidence(item.get("tool"), item.get("result"))
    ]
    empty_ok_tools = [
        item
        for item in tool_outputs
        if item.get("status") == "ok" and not _tool_result_has_useful_evidence(item.get("tool"), item.get("result"))
    ]

    if gate["degrade_reason"] == "conflicting_evidence":
        return _merge_rag_quality_into_result(
            {
                "should_continue": False,
                "evidence_state": "insufficient",
                "tool_availability": gate["tool_availability"],
                "degrade_reason": "conflicting_evidence",
                "stop_reason": "conflicting_evidence",
                "usable_tool_count": len(usable_tool_outputs),
            },
            rag_quality_summary,
        )

    if gate["evidence_state"] == "sufficient" and usable_tool_outputs:
        return _merge_rag_quality_into_result(
            {
                "should_continue": True,
                "evidence_state": "sufficient",
                "tool_availability": gate["tool_availability"],
                "degrade_reason": None,
                "stop_reason": None,
                "usable_tool_count": len(usable_tool_outputs),
            },
            rag_quality_summary,
        )

    if empty_ok_tools and not usable_tool_outputs:
        stop_reason = "tool_unavailable"
        if gate["degrade_reason"] == "missing_required_context" and gate["tool_availability"] != "none":
            stop_reason = "missing_required_context"
        return _merge_rag_quality_into_result(
            {
                "should_continue": False,
                "evidence_state": "insufficient",
                "tool_availability": "none",
                "degrade_reason": stop_reason,
                "stop_reason": stop_reason,
                "usable_tool_count": 0,
            },
            rag_quality_summary,
        )

    if gate["evidence_state"] == "limited":
        stop_reason = gate["degrade_reason"] or "evidence_insufficient"
        return _merge_rag_quality_into_result(
            {
                "should_continue": False,
                "evidence_state": "limited",
                "tool_availability": gate["tool_availability"],
                "degrade_reason": stop_reason,
                "stop_reason": stop_reason,
                "usable_tool_count": len(usable_tool_outputs),
            },
            rag_quality_summary,
        )

    stop_reason = gate["degrade_reason"] or "missing_required_context"
    return _merge_rag_quality_into_result(
        {
            "should_continue": False,
            "evidence_state": gate["evidence_state"],
            "tool_availability": gate["tool_availability"],
            "degrade_reason": stop_reason,
            "stop_reason": stop_reason,
            "usable_tool_count": len(usable_tool_outputs),
        },
        rag_quality_summary,
    )


def describe_evidence_gap(
    *,
    lane: str,
    allowed_tool_names: List[str],
    tool_outputs: List[Dict[str, Any]],
    profile_evidence: Optional[Dict[str, Any]] = None,
    retrieval_evidence: Optional[str] = None,
) -> Dict[str, Any]:
    gate = _evaluate_evidence_gate(
        lane=lane,
        allowed_tool_names=allowed_tool_names,
        tool_outputs=tool_outputs,
        profile_evidence=profile_evidence,
        retrieval_evidence=retrieval_evidence,
    )
    if gate["degrade_reason"] == "conflicting_evidence":
        return {
            "degrade_reason": "conflicting_evidence",
            "classes": gate["conflict_classes"] or ["conflicting evidence"],
            "next_steps": [
                "Upload the exact report values and dates so the discrepancy can be checked.",
                "Ask a clinician to review the conflicting evidence before making decisions.",
            ],
        }
    lane_steps = {
        "general_health": "Share your recent exact values and dates, or update your profile data.",
        "report_interpretation": "Upload the report (上传报告) or paste the exact values and reference ranges.",
        "trend_review": "Add at least one more comparable result with its date.",
        "medication_related": "Share the medication name and dose, or upload the relevant report.",
        "diagnosis_sensitive": "Bring your report values and symptom history to a clinician for diagnosis.",
    }
    return {
        "degrade_reason": gate["degrade_reason"],
        "classes": gate["missing_classes"] or ["required context"],
        "next_steps": [lane_steps.get(lane, "Provide the missing context before continuing.")],
    }


def enforce_tool_policy(
    *,
    user_is_admin: bool,
    tool_meta: Dict[str, Any],
    acting_user_id: int,
    target_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not tool_meta.get("read_only", True) and not user_is_admin:
        return {"allowed": False, "reason": "permission_denied"}
    scope = tool_meta.get("scope", "self_only")
    if scope == "admin_only" and not user_is_admin:
        return {"allowed": False, "reason": "permission_denied"}
    if scope == "self_only" and target_user_id is not None and target_user_id != acting_user_id:
        return {"allowed": False, "reason": "scope_denied"}
    return {"allowed": True}


def classify_query_safety(query: str) -> Dict[str, str]:
    normalized = (query or "").strip().lower()
    lane = _classify_lane(normalized)
    policy_pressure = classify_policy_pressure(normalized, lane=lane)
    if lane == "urgent_symptom":
        return {
            "safety_level": "urgent",
            "risk_level": "urgent",
            "route": "medical_escalation",
            "lane": lane,
            "policy_pressure": policy_pressure,
        }
    risk_level = (
        "elevated"
        if lane in {"diagnosis_sensitive", "medication_related"} or policy_pressure["mentions_elevated_risk"]
        else "normal"
    )
    return {
        "safety_level": "normal",
        "risk_level": risk_level,
        "route": "agent",
        "lane": lane,
        "policy_pressure": policy_pressure,
    }


def evaluate_chat_policy(
    *,
    query: str,
    safety_result: Dict[str, Any],
    allowed_tool_names: List[str],
    tool_outputs: Optional[List[Dict[str, Any]]] = None,
    evidence_state: Optional[str] = None,
    tool_availability: Optional[str] = None,
    profile_evidence: Optional[Dict[str, Any]] = None,
    retrieval_evidence: Optional[str] = None,
    rag_quality_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    lane = _normalize_policy_lane(safety_result)
    policy_pressure = safety_result.get("policy_pressure") or classify_policy_pressure(query, lane=lane)
    post_check = evaluate_post_tool_sufficiency(
        lane=lane,
        allowed_tool_names=allowed_tool_names,
        tool_outputs=tool_outputs or [],
        profile_evidence=profile_evidence,
        retrieval_evidence=retrieval_evidence,
        rag_quality_summary=rag_quality_summary,
        legacy_evidence_state=evidence_state,
        legacy_tool_availability=tool_availability,
    )
    effective_evidence_state = post_check["evidence_state"]
    effective_tool_availability = post_check["tool_availability"]
    effective_degrade_reason = post_check["degrade_reason"]

    if lane == "urgent_symptom":
        return {
            "policy_version": POLICY_VERSION,
            "evaluation_order": POLICY_EVALUATION_ORDER,
            "selected_rule": lane,
            "risk_level": "high",
            "evidence_state": "insufficient",
            "tool_availability": "none",
            "answer_mode": "urgent_care_disclaimer",
            "disclaimer_mode": "urgent_care",
            "degrade_reason": "urgent_symptom",
        }
    if lane == "diagnosis_sensitive":
        return {
            "policy_version": POLICY_VERSION,
            "evaluation_order": POLICY_EVALUATION_ORDER,
            "selected_rule": lane,
            "risk_level": "high",
            "evidence_state": effective_evidence_state,
            "tool_availability": effective_tool_availability,
            "answer_mode": "refusal_with_disclaimer",
            "disclaimer_mode": "diagnosis_guardrail",
            "degrade_reason": "diagnosis_sensitive_request",
        }
    if lane == "medication_related" and policy_pressure.get("requests_medication_change"):
        return {
            "policy_version": POLICY_VERSION,
            "evaluation_order": POLICY_EVALUATION_ORDER,
            "selected_rule": lane,
            "risk_level": "high",
            "evidence_state": effective_evidence_state,
            "tool_availability": effective_tool_availability,
            "answer_mode": "refusal_with_disclaimer",
            "disclaimer_mode": "conservative",
            "degrade_reason": "unsafe_medication_request",
        }

    answer_mode = "clarify_missing_context"
    disclaimer_mode = "conservative"
    degrade_reason = effective_degrade_reason
    if effective_evidence_state == "sufficient":
        answer_mode = "direct_answer" if lane == "general_health" else "bounded_answer"
        disclaimer_mode = "conservative" if lane == "medication_related" else "none"
        degrade_reason = None
    elif effective_evidence_state == "limited":
        answer_mode = "bounded_answer"
        disclaimer_mode = "conservative"
        degrade_reason = degrade_reason or "evidence_insufficient"

    return {
        "policy_version": POLICY_VERSION,
        "evaluation_order": POLICY_EVALUATION_ORDER,
        "selected_rule": lane,
        "risk_level": _infer_policy_risk_level(lane=lane, policy_pressure=policy_pressure),
        "evidence_state": effective_evidence_state,
        "tool_availability": effective_tool_availability,
        "answer_mode": answer_mode,
        "disclaimer_mode": disclaimer_mode,
        "degrade_reason": degrade_reason,
    }
