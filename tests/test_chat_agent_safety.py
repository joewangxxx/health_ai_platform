from backend.services.agent_safety import (
    POLICY_EVALUATION_ORDER,
    classify_query_safety,
    evaluate_chat_policy,
)


def test_urgent_query_is_flagged_with_real_chinese_text():
    result = classify_query_safety("我胸痛而且呼吸困难，现在很难受")

    assert result["safety_level"] == "urgent"
    assert result["route"] == "medical_escalation"
    assert result["lane"] == "urgent_symptom"


def test_normal_query_stays_in_agent_flow():
    result = classify_query_safety("我最近空腹血糖偏高，平时饮食应该注意什么？")

    assert result["safety_level"] == "normal"
    assert result["route"] == "agent"
    assert result["lane"] == "general_health"


def test_medication_query_routes_to_medication_lane():
    result = classify_query_safety("Please summarize my current medications and what is already on file.")

    assert result["route"] == "agent"
    assert result["lane"] == "medication_related"


def test_diagnosis_seeking_query_routes_to_diagnosis_sensitive_lane():
    result = classify_query_safety("Can you diagnose whether I have diabetes based on this chat?")

    assert result["route"] == "agent"
    assert result["lane"] == "diagnosis_sensitive"


def test_explicit_policy_short_circuits_urgent_queries():
    policy = evaluate_chat_policy(
        query="I have chest pain and trouble breathing right now",
        safety_result={"route": "medical_escalation", "safety_level": "urgent", "lane": "urgent_symptom"},
        allowed_tool_names=[],
        evidence_state="missing",
    )

    assert policy["policy_version"] == "explicit_policy.v1"
    assert policy["evaluation_order"] == POLICY_EVALUATION_ORDER
    assert policy["selected_rule"] == "urgent_symptom"
    assert policy["risk_level"] == "high"
    assert policy["tool_availability"] == "none"
    assert policy["answer_mode"] == "urgent_care_disclaimer"
    assert policy["disclaimer_mode"] == "urgent_care"
    assert policy["degrade_reason"] == "urgent_symptom"


def test_explicit_policy_uses_guardrail_for_diagnosis_requests():
    policy = evaluate_chat_policy(
        query="Can you diagnose whether I already have diabetes?",
        safety_result={"route": "agent", "safety_level": "normal", "lane": "diagnosis_sensitive"},
        allowed_tool_names=["get_user_profile_summary", "search_medical_guidelines"],
        evidence_state="limited",
    )

    assert policy["selected_rule"] == "diagnosis_sensitive"
    assert policy["risk_level"] == "high"
    assert policy["tool_availability"] == "partial"
    assert policy["answer_mode"] == "refusal_with_disclaimer"
    assert policy["disclaimer_mode"] == "diagnosis_guardrail"
    assert policy["degrade_reason"] == "diagnosis_sensitive_request"


def test_explicit_policy_refuses_medication_start_or_stop_requests():
    policy = evaluate_chat_policy(
        query="Should I start metformin, stop my current medicine, or increase the dose?",
        safety_result={"route": "agent", "safety_level": "normal", "lane": "medication_related"},
        allowed_tool_names=["medication_summary_lookup", "report_summary_lookup", "search_medical_guidelines"],
        evidence_state="sufficient",
    )

    assert policy["selected_rule"] == "medication_related"
    assert policy["risk_level"] == "high"
    assert policy["tool_availability"] == "full"
    assert policy["answer_mode"] == "refusal_with_disclaimer"
    assert policy["disclaimer_mode"] == "conservative"
    assert policy["degrade_reason"] == "unsafe_medication_request"


def test_explicit_policy_bounds_general_health_when_evidence_is_limited():
    policy = evaluate_chat_policy(
        query="What should I pay attention to for mildly high blood sugar?",
        safety_result={"route": "agent", "safety_level": "normal", "lane": "general_health"},
        allowed_tool_names=["get_user_profile_summary", "search_medical_guidelines"],
        evidence_state="limited",
    )

    assert policy["selected_rule"] == "general_health"
    assert policy["risk_level"] == "medium"
    assert policy["tool_availability"] == "partial"
    assert policy["answer_mode"] == "bounded_answer"
    assert policy["disclaimer_mode"] == "conservative"
    assert policy["degrade_reason"] == "evidence_insufficient"
