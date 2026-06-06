from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from backend.models import AgentAuditEvent


RESPONSIBILITY_SCHEMA_VERSION = "agent_audit_responsibility.v2"
GOVERNANCE_VERSION = "agent_runtime_governance.v1"
ALLOWED_CONTEXT_LANES = {"profile", "rag", "tools", "query", "history"}
ALLOWED_RESPONSE_MODES = {
    "direct_answer",
    "bounded_answer",
    "clarify_missing_context",
    "refusal_with_disclaimer",
    "urgent_care_disclaimer",
}
ALLOWED_EVIDENCE_SUFFICIENCY = {"sufficient", "limited", "insufficient"}
ALLOWED_DEGRADED_REASONS = {
    "insufficient_evidence",
    "missing_required_context",
    "tool_unavailable",
    "conflicting_evidence",
    "policy_guardrail",
    "urgent_risk_detected",
    "unsafe_medication_request",
    "diagnosis_sensitive_request",
    "urgent_symptom",
}
ALLOWED_TOOL_PLAN_SOURCES = {
    "native_function_calling",
    "local_fallback_planner",
    "no_tool_path",
    "cache_replay",
    "urgent_short_circuit",
}


def build_audit_record(
    *,
    user_id: int,
    conversation_id: int,
    intent: Optional[str] = None,
    lane: Optional[str] = None,
    verdict: Optional[str] = None,
    selected_rule: Optional[str] = None,
    policy_version: Optional[str] = None,
    response_mode: Optional[str] = None,
    evidence_sufficiency: Optional[str] = None,
    degraded_reason: Optional[str] = None,
    human_escalation_required: bool = False,
    governance_version: str = GOVERNANCE_VERSION,
    model_name: Optional[str] = None,
    tool_plan_source: Optional[str] = None,
    tool_used: Optional[List[str]] = None,
    cache_hit: bool = False,
    safety_level: Optional[str] = None,
    evidence_tags: Optional[List[str]] = None,
    context_budget_summary: Optional[Dict[str, Any]] = None,
    tool_latency_ms: Optional[int] = None,
    tool_count: int = 0,
    response_latency_ms: Optional[int] = None,
    fallback_used: Optional[bool] = None,
) -> Dict[str, Any]:
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    return {
        "schema_version": RESPONSIBILITY_SCHEMA_VERSION,
        "governance_version": governance_version,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "conversation_id": conversation_id,
        "intent": intent,
        "lane": lane,
        "verdict": verdict,
        "selected_rule": selected_rule,
        "policy_version": policy_version,
        "response_mode": response_mode,
        "evidence_sufficiency": evidence_sufficiency,
        "degraded_reason": degraded_reason,
        "human_escalation_required": human_escalation_required,
        "model_name": model_name,
        "tool_plan_source": tool_plan_source,
        "tool_used": tool_used or [],
        "cache_hit": cache_hit,
        "safety_level": safety_level,
        "evidence_tags": evidence_tags or [],
        "context_budget_summary": context_budget_summary,
        "tool_latency_ms": tool_latency_ms,
        "tool_count": tool_count,
        "response_latency_ms": response_latency_ms,
        "fallback_used": fallback_used,
    }


def persist_audit_record(*, session: Session, audit_record: Dict[str, Any]) -> AgentAuditEvent:
    """中文说明：persist_audit_record 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    event = AgentAuditEvent(
        schema_version=_string_or_none(
            audit_record.get("schema_version"),
            max_length=64,
            default=RESPONSIBILITY_SCHEMA_VERSION,
        )
        or RESPONSIBILITY_SCHEMA_VERSION,
        timestamp=_parse_timestamp(audit_record.get("timestamp")),
        user_id=int(audit_record["user_id"]),
        conversation_id=int(audit_record["conversation_id"]),
        intent=_string_or_none(audit_record.get("intent"), max_length=128),
        governance_version=_string_or_none(
            audit_record.get("governance_version"),
            max_length=64,
            default=GOVERNANCE_VERSION,
        ),
        lane=_string_or_none(audit_record.get("lane"), max_length=64),
        verdict=_string_or_none(audit_record.get("verdict"), max_length=64),
        selected_rule=_string_or_none(audit_record.get("selected_rule"), max_length=64),
        policy_version=_string_or_none(audit_record.get("policy_version"), max_length=64),
        response_mode=_enum_or_none(
            audit_record.get("response_mode"),
            allowed=ALLOWED_RESPONSE_MODES,
            max_length=64,
        ),
        evidence_sufficiency=_enum_or_none(
            audit_record.get("evidence_sufficiency"),
            allowed=ALLOWED_EVIDENCE_SUFFICIENCY,
            max_length=32,
        ),
        degraded_reason=_enum_or_none(
            audit_record.get("degraded_reason"),
            allowed=ALLOWED_DEGRADED_REASONS,
            max_length=64,
        ),
        human_escalation_required=_bool_or_default(
            audit_record.get("human_escalation_required"),
            default=False,
        ),
        model_name=_string_or_none(audit_record.get("model_name"), max_length=128),
        tool_plan_source=_enum_or_none(
            audit_record.get("tool_plan_source"),
            allowed=ALLOWED_TOOL_PLAN_SOURCES,
            max_length=64,
        ),
        tool_used=_string_list(audit_record.get("tool_used"), max_items=8, max_length=128),
        cache_hit=_bool_or_default(audit_record.get("cache_hit"), default=False),
        safety_level=_string_or_none(audit_record.get("safety_level"), max_length=64),
        evidence_tags=_string_list(audit_record.get("evidence_tags"), max_items=12, max_length=128),
        context_budget_summary=_sanitize_context_budget_summary(audit_record.get("context_budget_summary")),
        tool_latency_ms=_int_or_none(audit_record.get("tool_latency_ms")),
        tool_count=_int_or_default(audit_record.get("tool_count"), default=0),
        response_latency_ms=_int_or_none(audit_record.get("response_latency_ms")),
        fallback_used=_bool_or_default(audit_record.get("fallback_used"), default=False),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
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


def _string_list(
    value: Any,
    *,
    max_items: Optional[int] = None,
    max_length: Optional[int] = None,
) -> List[str]:
    if not isinstance(value, list):
        return []

    items: List[str] = []
    for item in value:
        normalized = _string_or_none(item, max_length=max_length)
        if normalized is None:
            continue
        items.append(normalized)
        if max_items is not None and len(items) >= max_items:
            break
    return items


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
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


def _bool_or_none(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _bool_or_default(value: Any, *, default: bool) -> bool:
    normalized = _bool_or_none(value)
    if normalized is None:
        return default
    return normalized


def _enum_or_none(
    value: Any,
    *,
    allowed: set[str],
    max_length: Optional[int] = None,
) -> Optional[str]:
    normalized = _string_or_none(value, max_length=max_length)
    if normalized is None:
        return None
    if normalized not in allowed:
        return None
    return normalized


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
            if isinstance(fact_value, (int, float)):
                facts[fact_key] = int(fact_value)

        if facts:
            sanitized[lane] = facts

    return sanitized or None
