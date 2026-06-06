from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from backend.models import AgentAnswerReplay


REPLAY_SCHEMA_VERSION = "agent_answer_replay.v1"
GOVERNANCE_VERSION = "agent_runtime_governance.v1"
ALLOWED_CONTEXT_LANES = {"profile", "rag", "tools", "query", "history"}
ALLOWED_FRESHNESS = {"fresh", "recent", "stale", "unknown"}
ALLOWED_COVERAGE = {"empty", "partial", "full"}
ALLOWED_CONFIDENCE = {"low", "medium", "high", "unknown"}


def build_answer_replay_record(
    *,
    user_id: int,
    conversation_id: int,
    chat_message_id: int,
    audit_event_id: int,
    decision_summary: Dict[str, Any],
    response_verdict: Optional[Dict[str, Any]],
    context_budget_summary: Optional[Dict[str, Any]],
    tool_outputs: Optional[List[Dict[str, Any]]],
    rag_source_refs: Optional[List[Any]],
    tool_latency_ms: Optional[int],
    response_latency_ms: Optional[int],
    tool_count: int,
    fallback_used: bool,
    model_name: Optional[str],
    tool_plan_source: str,
    cache_hit: bool,
    governance_version: str = GOVERNANCE_VERSION,
) -> Dict[str, Any]:
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    policy = decision_summary.get("policy") or {}
    verdict_payload = response_verdict or {}
    evidence_sufficiency = verdict_payload.get("evidence_sufficiency") or _public_evidence_sufficiency(
        policy.get("evidence_state")
    )
    degraded_reason = verdict_payload.get("degraded_reason") or policy.get("degrade_reason")

    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "created_at": datetime.utcnow(),
        "user_id": user_id,
        "conversation_id": conversation_id,
        "chat_message_id": chat_message_id,
        "audit_event_id": audit_event_id,
        "policy_snapshot": {
            "lane": decision_summary.get("lane"),
            "verdict": decision_summary.get("verdict"),
            "selected_rule": policy.get("selected_rule") or decision_summary.get("lane"),
            "policy_version": policy.get("policy_version"),
            "response_mode": verdict_payload.get("response_mode") or policy.get("answer_mode"),
            "evidence_sufficiency": evidence_sufficiency,
            "medical_risk_level": verdict_payload.get("medical_risk_level") or policy.get("risk_level"),
            "human_escalation_required": bool(verdict_payload.get("human_escalation_required")),
            "degraded_reason": degraded_reason,
        },
        "execution_snapshot": {
            "governance_version": governance_version,
            "model_name": model_name,
            "tool_plan_source": tool_plan_source,
            "cache_hit": cache_hit,
            "fallback_used": fallback_used,
            "tool_count": max(0, int(tool_count)),
            "tool_latency_ms": tool_latency_ms,
            "response_latency_ms": response_latency_ms,
        },
        "context_budget_summary": _sanitize_context_budget_summary(context_budget_summary),
        "tool_result_summary": _sanitize_tool_result_summary(tool_outputs or []),
        "rag_source_refs": _sanitize_rag_source_refs(rag_source_refs or []),
    }


def persist_answer_replay_record(*, session: Session, replay_record: Dict[str, Any]) -> AgentAnswerReplay:
    """中文说明：persist_answer_replay_record 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    event = AgentAnswerReplay(
        schema_version=_string_or_none(
            replay_record.get("schema_version"),
            max_length=64,
            default=REPLAY_SCHEMA_VERSION,
        )
        or REPLAY_SCHEMA_VERSION,
        created_at=_parse_datetime(replay_record.get("created_at")),
        user_id=int(replay_record["user_id"]),
        conversation_id=int(replay_record["conversation_id"]),
        chat_message_id=int(replay_record["chat_message_id"]),
        audit_event_id=int(replay_record["audit_event_id"]),
        policy_snapshot=_dict_or_default(replay_record.get("policy_snapshot")),
        execution_snapshot=_dict_or_default(replay_record.get("execution_snapshot")),
        context_budget_summary=_sanitize_context_budget_summary(replay_record.get("context_budget_summary")),
        tool_result_summary=_sanitize_tool_result_summary(replay_record.get("tool_result_summary") or []),
        rag_source_refs=_sanitize_rag_source_refs(replay_record.get("rag_source_refs") or []),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def _public_evidence_sufficiency(evidence_state: Optional[str]) -> str:
    if evidence_state in {"sufficient", "limited", "insufficient"}:
        return str(evidence_state)
    return "insufficient"


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.utcnow()


def _string_or_none(
    value: Any,
    *,
    max_length: Optional[int] = None,
    default: Optional[str] = None,
) -> Optional[str]:
    if value is None:
        return default
    normalized = str(value).strip()
    if not normalized:
        return default
    if max_length is not None:
        normalized = normalized[:max_length]
    return normalized


def _dict_or_default(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _sanitize_context_budget_summary(value: Any) -> Optional[Dict[str, Dict[str, int]]]:
    """中文说明：_sanitize_context_budget_summary 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(value, dict):
        return None

    sanitized: Dict[str, Dict[str, int]] = {}
    for lane, lane_summary in value.items():
        if lane not in ALLOWED_CONTEXT_LANES or not isinstance(lane_summary, dict):
            continue

        facts: Dict[str, int] = {}
        for fact_key in ("budget", "used"):
            fact_value = lane_summary.get(fact_key)
            if isinstance(fact_value, bool):
                continue
            if isinstance(fact_value, int):
                facts[fact_key] = max(0, fact_value)
        if "budget" in facts:
            sanitized[lane] = facts
    return sanitized or None


def _sanitize_tool_result_summary(value: Any) -> List[Dict[str, Any]]:
    """中文说明：_sanitize_tool_result_summary 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(value, list):
        return []

    sanitized: List[Dict[str, Any]] = []
    for item in value[:8]:
        if not isinstance(item, dict):
            continue
        tool_name = _string_or_none(item.get("tool_name") or item.get("tool"), max_length=64)
        if not tool_name:
            continue
        status = _string_or_none(item.get("status"), max_length=32) or "unknown"
        source_refs = _sanitize_string_list(
            item.get("source_refs") or item.get("source_ref") or [],
            max_items=4,
            max_length=128,
        )
        sanitized.append(
            {
                "tool_name": tool_name,
                "status": status,
                "summary_label": _string_or_none(item.get("summary_label"), max_length=128)
                or _default_summary_label(tool_name),
                "count": max(0, _int_or_default(item.get("count"), default=0)),
                "freshness": _enum_or_default(
                    item.get("freshness"),
                    allowed=ALLOWED_FRESHNESS,
                    default="unknown",
                ),
                "coverage": _enum_or_default(
                    item.get("coverage"),
                    allowed=ALLOWED_COVERAGE,
                    default="empty" if status != "ok" else "partial",
                ),
                "confidence": _enum_or_default(
                    item.get("confidence"),
                    allowed=ALLOWED_CONFIDENCE,
                    default="unknown",
                ),
                "blocked_reason": _string_or_none(item.get("blocked_reason"), max_length=128),
                "source_refs": source_refs,
            }
        )
    return sanitized


def _sanitize_rag_source_refs(value: Any) -> List[Dict[str, Any]]:
    """中文说明：_sanitize_rag_source_refs 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(value, list):
        return []

    sanitized: List[Dict[str, Any]] = []
    for item in value[:12]:
        if isinstance(item, str):
            source = _string_or_none(item, max_length=128)
            if source:
                sanitized.append({"source": source})
            continue

        if not isinstance(item, dict):
            continue

        source = _string_or_none(item.get("source"), max_length=128)
        if not source:
            continue
        ref: Dict[str, Any] = {"source": source}
        page = _int_or_none(item.get("page"))
        chunk_index = _int_or_none(item.get("chunk_index"))
        page_range = item.get("page_range")
        if page is not None:
            ref["page"] = page
        if chunk_index is not None:
            ref["chunk_index"] = chunk_index
        if isinstance(page_range, list) and len(page_range) == 2:
            start_page = _int_or_none(page_range[0])
            end_page = _int_or_none(page_range[1])
            if start_page is not None and end_page is not None:
                ref["page_range"] = [start_page, end_page]
        sanitized.append(ref)

    return sanitized


def _sanitize_string_list(
    value: Any,
    *,
    max_items: int,
    max_length: int,
) -> List[str]:
    if not isinstance(value, list):
        return []

    items: List[str] = []
    for item in value:
        normalized = _string_or_none(item, max_length=max_length)
        if normalized is None:
            continue
        items.append(normalized)
        if len(items) >= max_items:
            break
    return items


def _default_summary_label(tool_name: str) -> str:
    labels = {
        "get_user_profile_summary": "Profile context reviewed",
        "get_latest_risk_report": "Latest risk report reviewed",
        "get_history_trends": "Trend history reviewed",
        "get_uploaded_documents_summary": "Uploaded document summaries reviewed",
        "report_summary_lookup": "Report summary reviewed",
        "recent_metric_anomaly_lookup": "Recent metric anomalies reviewed",
        "recent_abnormal_metrics_lookup": "Recent metric anomalies reviewed",
        "latest_analysis_snapshot_lookup": "Latest analysis snapshot reviewed",
        "medication_summary_lookup": "Medication summary reviewed",
        "report_comparison_lookup": "Report comparison reviewed",
        "search_medical_guidelines": "Guideline evidence retrieved",
    }
    return labels.get(tool_name, tool_name.replace("_", " ").strip().title())


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_or_default(value: Any, *, default: int) -> int:
    normalized = _int_or_none(value)
    if normalized is None:
        return default
    return max(0, normalized)


def _enum_or_default(value: Any, *, allowed: set[str], default: str) -> str:
    normalized = _string_or_none(value)
    if normalized is None or normalized not in allowed:
        return default
    return normalized
