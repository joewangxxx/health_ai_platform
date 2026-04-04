from sqlmodel import select

from backend.models import AgentAuditEvent
from backend.services.agent_audit import build_audit_record, persist_audit_record


def test_build_audit_record_contains_core_fields():
    record = build_audit_record(
        user_id=1,
        conversation_id=2,
        intent="guideline_lookup",
        lane="general_health",
        verdict="general_guidance",
        selected_rule="general_health",
        policy_version="explicit_policy.v1",
        response_mode="bounded_answer",
        evidence_sufficiency="limited",
        degraded_reason="insufficient_evidence",
        human_escalation_required=False,
        governance_version="agent_runtime_governance.v1",
        model_name="moonshot-v1-8k",
        tool_plan_source="native_function_calling",
        tool_used=["search_medical_guidelines"],
        cache_hit=False,
    )

    assert record["user_id"] == 1
    assert record["conversation_id"] == 2
    assert record["intent"] == "guideline_lookup"
    assert record["lane"] == "general_health"
    assert record["verdict"] == "general_guidance"
    assert record["selected_rule"] == "general_health"
    assert record["policy_version"] == "explicit_policy.v1"
    assert record["response_mode"] == "bounded_answer"
    assert record["evidence_sufficiency"] == "limited"
    assert record["degraded_reason"] == "insufficient_evidence"
    assert record["human_escalation_required"] is False
    assert record["governance_version"] == "agent_runtime_governance.v1"
    assert record["model_name"] == "moonshot-v1-8k"
    assert record["tool_plan_source"] == "native_function_calling"
    assert record["tool_used"] == ["search_medical_guidelines"]
    assert record["cache_hit"] is False


def test_build_audit_record_includes_expanded_observability_fields():
    budget_summary = {
        "profile": {"budget": 500, "used": 120},
        "rag": {"budget": 1500, "used": 240},
        "tools": {"budget": 800, "used": 80},
        "query": {"budget": 300, "used": 40},
        "history": {"budget": 320},
    }

    record = build_audit_record(
        user_id=1,
        conversation_id=2,
        intent="guideline_lookup",
        lane="general_health",
        verdict="general_guidance",
        selected_rule="general_health",
        policy_version="explicit_policy.v1",
        response_mode="bounded_answer",
        evidence_sufficiency="limited",
        degraded_reason="insufficient_evidence",
        human_escalation_required=False,
        governance_version="agent_runtime_governance.v1",
        model_name="moonshot-v1-8k",
        tool_plan_source="native_function_calling",
        tool_used=["search_medical_guidelines"],
        cache_hit=False,
        context_budget_summary=budget_summary,
        tool_latency_ms=17,
        tool_count=2,
        response_latency_ms=93,
        fallback_used=True,
    )

    assert record["context_budget_summary"] == budget_summary
    assert record["tool_latency_ms"] == 17
    assert record["tool_count"] == 2
    assert record["response_latency_ms"] == 93
    assert record["fallback_used"] is True


def test_persist_audit_record_stores_metadata_only_row(session):
    record = build_audit_record(
        user_id=1,
        conversation_id=2,
        intent="guideline_lookup",
        lane="general_health",
        verdict="general_guidance",
        selected_rule="general_health",
        policy_version="explicit_policy.v1",
        response_mode="bounded_answer",
        evidence_sufficiency="limited",
        degraded_reason="insufficient_evidence",
        human_escalation_required=False,
        governance_version="agent_runtime_governance.v1",
        model_name="moonshot-v1-8k",
        tool_plan_source="native_function_calling",
        tool_used=["search_medical_guidelines"],
        cache_hit=False,
        safety_level="normal",
        evidence_tags=["guideline_search"],
        context_budget_summary={
            "profile": {"budget": 500, "used": 120, "raw_text": "should not persist"},
            "rag": {"budget": 1500, "used": 240, "payload": {"a": 1}},
            "tools": {"budget": 800, "used": True},
            "query": {"budget": 300, "used": 40, "text": "should not persist"},
            "history": {"budget": 320, "used": 18, "reply": "should not persist"},
            "ignored_lane": "bad-shape",
        },
        tool_latency_ms=17,
        tool_count=2,
        response_latency_ms=93,
        fallback_used=True,
    )

    row = persist_audit_record(session=session, audit_record=record)
    stored = session.exec(select(AgentAuditEvent).where(AgentAuditEvent.id == row.id)).one()

    assert stored.user_id == 1
    assert stored.conversation_id == 2
    assert stored.schema_version == "agent_audit_responsibility.v2"
    assert stored.governance_version == "agent_runtime_governance.v1"
    assert stored.intent == "guideline_lookup"
    assert stored.lane == "general_health"
    assert stored.verdict == "general_guidance"
    assert stored.selected_rule == "general_health"
    assert stored.policy_version == "explicit_policy.v1"
    assert stored.response_mode == "bounded_answer"
    assert stored.evidence_sufficiency == "limited"
    assert stored.degraded_reason == "insufficient_evidence"
    assert stored.human_escalation_required is False
    assert stored.model_name == "moonshot-v1-8k"
    assert stored.tool_plan_source == "native_function_calling"
    assert stored.tool_used == ["search_medical_guidelines"]
    assert stored.cache_hit is False
    assert stored.evidence_tags == ["guideline_search"]
    assert stored.context_budget_summary == {
        "profile": {"budget": 500, "used": 120},
        "rag": {"budget": 1500, "used": 240},
        "tools": {"budget": 800},
        "query": {"budget": 300, "used": 40},
        "history": {"budget": 320, "used": 18},
    }
    assert stored.tool_latency_ms == 17
    assert stored.tool_count == 2
    assert stored.response_latency_ms == 93
    assert stored.fallback_used is True
    assert "raw_text" not in stored.context_budget_summary.get("profile", {})
    assert "payload" not in stored.context_budget_summary.get("rag", {})
    assert "ignored_lane" not in stored.context_budget_summary
