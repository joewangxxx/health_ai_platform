import asyncio
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlmodel import select

from backend.models import AgentAuditEvent, ChatMessage, HealthRecord, MedicalDocument, User, UserProfile
from backend.services.context_builder import DEFAULT_CONTEXT_BUDGETS
from backend.services.chat_service import ChatService


def assert_response_verdict(
    payload,
    decision_summary,
    *,
    degraded_reason,
    human_escalation_required,
):
    policy = decision_summary["policy"]

    assert payload["schema_version"] == "response_verdict.v1"
    assert payload["response_mode"] == policy["answer_mode"]
    assert payload["medical_risk_level"] == policy["risk_level"]
    assert payload["evidence_sufficiency"] == policy["evidence_state"]
    assert payload["human_escalation_required"] is human_escalation_required
    assert payload["degraded_reason"] == degraded_reason


def assert_takeover(
    payload,
    *,
    status,
    trigger_reason,
):
    assert payload is not None
    assert payload["schema_version"] == "takeover.v1"
    assert payload["status"] == status
    assert payload["trigger_reason"] == trigger_reason
    assert payload["summary"]


def assert_audit_responsibility(
    row,
    *,
    decision_summary,
    response_verdict,
    tool_plan_source,
    cache_hit,
    model_name,
    fallback_used,
):
    policy = decision_summary["policy"]

    assert row.schema_version == "agent_audit_responsibility.v2"
    assert row.governance_version == "agent_runtime_governance.v1"
    assert row.intent == decision_summary["intent"]
    assert row.lane == decision_summary["lane"]
    assert row.verdict == decision_summary["verdict"]
    assert row.selected_rule == policy["selected_rule"]
    assert row.policy_version == policy["policy_version"]
    assert row.response_mode == response_verdict["response_mode"]
    assert row.evidence_sufficiency == response_verdict["evidence_sufficiency"]
    assert row.degraded_reason == response_verdict["degraded_reason"]
    assert row.human_escalation_required == response_verdict["human_escalation_required"]
    assert row.tool_plan_source == tool_plan_source
    assert row.cache_hit is cache_hit
    assert row.model_name == model_name
    assert row.fallback_used is fallback_used


def create_test_user(session):
    user = User(
        username="chat_agent_user",
        email="chat_agent_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        Age=52,
        Gender=1,
        BMI=27.5,
        Glucose_Fasting=6.7,
        risk_history='{"diabetes": {"risk_level": "medium"}}',
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile
    return user


def create_tool_expansion_context(session, user):
    document = MedicalDocument(
        user_id=user.id,
        file_name="glucose-report.pdf",
        file_path="uploads/glucose-report.pdf",
        file_url="/static/glucose-report.pdf",
        upload_date=datetime.utcnow(),
        ocr_summary=json.dumps(
            {
                "schema_version": "ocr_summary.v1",
                "summary": "Persisted OCR summary for glucose report",
                "medications": [
                    {
                        "name": "Metformin",
                        "dose": "500",
                        "unit": "mg",
                        "frequency": "BID",
                    }
                ],
            },
            ensure_ascii=False,
        ),
    )
    record = HealthRecord(
        user_id=user.id,
        source="manual_update",
        record_date=datetime.utcnow(),
        metrics=json.dumps({"Glucose_Fasting": 6.9, "SBP": 146, "BMI": 27.8}, ensure_ascii=False),
        risk_snapshot=json.dumps(
            {
                "diabetes": {"risk_level": "medium", "probability": 0.42},
                "heart_failure": {"risk_level": "high", "probability": 0.76},
                "ckm": {"stage": 1, "stage_name": "stage_1"},
            },
            ensure_ascii=False,
        ),
    )
    session.add(document)
    session.add(record)
    session.commit()
    return document, record


def test_build_cache_key_changes_with_context():
    service = ChatService()

    key1 = service._build_cache_key(
        user_id=1,
        conversation_id=1,
        messages=[{"role": "system", "content": "a"}],
    )
    key2 = service._build_cache_key(
        user_id=1,
        conversation_id=1,
        messages=[{"role": "system", "content": "b"}],
    )

    assert key1 != key2


def test_urgent_query_short_circuits_llm(session, monkeypatch):
    service = ChatService()
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    user = create_test_user(session)

    monkeypatch.setattr(
        "backend.services.chat_service.classify_query_safety",
        lambda query: {"route": "medical_escalation", "safety_level": "urgent"},
    )
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="I have chest pain and trouble breathing right now",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["conversation_id"] is not None
    assert response["decision_summary"]["lane"] == "urgent_symptom"
    assert response["decision_summary"]["verdict"] == "seek_urgent_care"
    assert response["decision_summary"]["safety_level"] == "urgent"
    assert response["evidence_tags"] == ["urgent_route"]
    assert_response_verdict(
        response["response_verdict"],
        response["decision_summary"],
        degraded_reason="urgent_risk_detected",
        human_escalation_required=True,
    )
    assert "线下" in response["reply"] or "就医" in response["reply"]
    assert_takeover(
        response["takeover"],
        status="required",
        trigger_reason="high_risk",
    )
    assert service.client.chat.completions.create.await_count == 0


def test_chat_service_executes_tools_and_returns_decision_summary(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    response = asyncio.run(
        service.chat(
            user=user,
            query="What should I pay attention to in daily life for mildly high blood sugar?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["conversation_id"] is not None
    assert response["decision_summary"]["lane"] == "general_health"
    assert response["decision_summary"]["verdict"] == "general_guidance"
    assert response["decision_summary"]["tool_needed"] is True
    assert "get_user_profile_summary" in response["decision_summary"]["tool_used"]
    assert response["decision_summary"]["safety_level"] == "normal"
    assert response["decision_summary"]["policy"]["selected_rule"] == "general_health"
    assert response["decision_summary"]["policy"]["answer_mode"] == "direct_answer"
    assert response["decision_summary"]["policy"]["disclaimer_mode"] == "none"
    assert "profile_summary" in response["evidence_tags"]
    assert_response_verdict(
        response["response_verdict"],
        response["decision_summary"],
        degraded_reason=None,
        human_escalation_required=False,
    )
    assert response["takeover"] is None
    assert response["suggestion_card"]["headline"]
    assert response["suggestion_card"]["risk_level"] in {"low", "medium", "high"}
    assert response["suggestion_card"]["key_actions"]
    assert mocked_completion.await_count == 2


def test_chat_service_uses_rag_quality_summary_to_conservatively_degrade(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: (
            "[Ref 1 - guideline.pdf]: Glucose management guidance\n\n"
            "[Ref 2 - followup.pdf]: Follow-up advice with enough detail to look trustworthy."
        ),
    )
    calls = []

    def fake_search_context_with_quality(query, k=3):
        calls.append((query, k))
        return {
            "context": "[Ref 1 - guideline.pdf]: Glucose management guidance",
            "rag_quality_summary": {
                "retrieval_status": "ok",
                "hit_count": 1,
                "unique_source_count": 1,
                "source_kind": "pdf_text",
                "density_status": "low_density",
                "ocr_fallback_state": "degraded",
                "provenance_state": "partial",
                "chunk_quality": "weak",
            },
        }

    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context_with_quality",
        fake_search_context_with_quality,
    )

    response = asyncio.run(
        service.chat(
            user=user,
            query="What should I pay attention to in daily life for mildly high blood sugar?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["policy"]["evidence_state"] == "insufficient"
    assert response["decision_summary"]["policy"]["disclaimer_mode"] == "conservative"
    assert response["response_verdict"]["evidence_sufficiency"] == "insufficient"
    assert response["response_verdict"]["degraded_reason"] in {
        "insufficient_evidence",
        "missing_required_context",
        "tool_unavailable",
    }
    assert_takeover(
        response["takeover"],
        status="required",
        trigger_reason="insufficient_evidence",
    )
    assert calls == [("What should I pay attention to in daily life for mildly high blood sugar?", 3)]
    assert mocked_completion.await_count == 1


def test_stream_chat_emits_status_events_before_final(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and combine it with your recent trend review."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    async def collect():
        events = []
        async for event in service.stream_chat(
            user=user,
            query="Please review my risk and recent trend for high blood sugar",
            session=session,
            conversation_id=None,
            force_refresh=True,
        ):
            events.append(event)
        return events

    events = asyncio.run(collect())

    assert events[-1]["event"] == "final"
    assert events[-1]["data"]["conversation_id"] is not None
    stages = [event["data"]["stage"] for event in events if event["event"] == "status"]
    assert "reading_profile" in stages
    assert "searching_knowledge" in stages
    assert "generating_answer" in stages
    tool_events = [event for event in events if event["event"] in {"tool_start", "tool_done"}]
    assert tool_events
    assert tool_events[0]["event"] == "tool_start"
    assert tool_events[-1]["event"] == "tool_done"
    assert "tool_name" in tool_events[0]["data"]


def test_chat_service_trims_context_before_llm_call(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and combine it with your recent trend review."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "R" * 12000)
    monkeypatch.setattr(service, "_get_user_context", lambda current_user, current_session: "P" * 4000)

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please combine my profile, history, and guidelines to explain what I should do",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    llm_messages = mocked_completion.await_args.kwargs["messages"]
    user_prompt = llm_messages[-1]["content"]

    assert response["conversation_id"] is not None
    assert "[truncated]" in user_prompt
    assert len(user_prompt) < 12000


def test_chat_service_prefers_native_function_calling_when_available(session, monkeypatch):
    service = ChatService()
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_user_profile_summary", arguments="{}"),
    )
    mocked_completion = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call]))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and adjust your diet.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Use my profile to explain what I should watch out for",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    first_call_kwargs = mocked_completion.await_args_list[0].kwargs

    assert response["conversation_id"] is not None
    assert response["decision_summary"]["tool_used"] == ["get_user_profile_summary"]
    assert response["decision_summary"]["verdict"] == "insufficient_evidence"
    assert response["decision_summary"]["policy"]["evidence_state"] == "limited"
    assert first_call_kwargs["tools"][0]["type"] == "function"
    assert mocked_completion.await_count == 1


def test_chat_service_falls_back_when_native_function_calling_errors(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        side_effect=[
            RuntimeError("tool calling unsupported"),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please review my risk and trend",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["conversation_id"] is not None
    assert response["decision_summary"]["lane"] == "trend_review"
    assert response["decision_summary"]["verdict"] == "insufficient_evidence"
    assert set(response["decision_summary"]["tool_used"]).issubset(
        {"get_history_trends", "recent_metric_anomaly_lookup", "latest_analysis_snapshot_lookup", "search_medical_guidelines"}
    )
    assert mocked_completion.await_count == 1


def test_urgent_query_returns_evidence_panel(session, monkeypatch):
    service = ChatService()
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    user = create_test_user(session)

    monkeypatch.setattr(
        "backend.services.chat_service.classify_query_safety",
        lambda query: {"route": "medical_escalation", "safety_level": "urgent"},
    )
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="I have chest pain and trouble breathing right now",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["evidence_panel"]["chips"][0]["key"] == "urgent_route"
    assert response["evidence_panel"]["sections"][0]["source_refs"] == ["urgent_route"]
    assert response["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == "profile"


def test_chat_service_returns_evidence_panel_for_tool_backed_reply(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please review my risk and recent trend for high blood sugar",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["evidence_panel"]["chips"][0]["key"] == "history_trends"
    assert response["evidence_panel"]["sections"][0]["label"] == "Trend Review"
    assert response["evidence_panel"]["sections"][0]["source_refs"] == ["history_trends"]
    assert response["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == "trend"


def test_stream_chat_final_event_contains_evidence_panel(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and combine it with your recent trend review."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    async def collect():
        events = []
        async for event in service.stream_chat(
            user=user,
            query="Please review my risk and recent trend for high blood sugar",
            session=session,
            conversation_id=None,
            force_refresh=True,
        ):
            events.append(event)
        return events

    events = asyncio.run(collect())

    assert events[-1]["event"] == "final"
    assert events[-1]["data"]["evidence_panel"]["chips"][0]["key"] == "history_trends"
    assert events[-1]["data"]["evidence_panel"]["sections"][0]["source_refs"] == ["history_trends"]
    assert events[-1]["data"]["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == "trend"
    assert_response_verdict(
        events[-1]["data"]["response_verdict"],
        events[-1]["data"]["decision_summary"],
        degraded_reason="insufficient_evidence",
        human_escalation_required=False,
    )
    assert events[-1]["data"]["takeover"] is None


def test_chat_service_cache_hit_replays_evidence_panel(session, monkeypatch):
    service = ChatService()
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    user = create_test_user(session)
    cached_panel = {
        "chips": [
            {"key": "profile_summary", "label": "Health Profile"},
            {"key": "guideline_search", "label": "Guideline Evidence"},
        ],
        "sections": [
            {
                "label": "Health Profile",
                "summary": "Profile context influenced the reply.",
                "key_facts": ["Recent fasting glucose context was considered"],
                "decision_basis": "The reply was tailored to stored profile context.",
                "source_refs": ["profile_summary"],
                "source_items": [
                    {
                        "source_type": "profile",
                        "title": "Stored profile snapshot",
                        "snippet": "Recent fasting glucose context was considered.",
                        "timestamp": None,
                        "confidence": 0.86,
                    }
                ],
            },
            {
                "label": "Guideline Evidence",
                "summary": "Guideline evidence supported the recommendation.",
                "key_facts": ["Retrieved guidance informed the answer"],
                "decision_basis": "External evidence reinforced the recommendation.",
                "source_refs": ["guideline.pdf"],
                "source_items": [
                    {
                        "source_type": "guideline",
                        "title": "Retrieved guideline reference",
                        "snippet": "Guideline evidence supported the recommendation.",
                        "timestamp": None,
                        "relevance": 0.91,
                    }
                ],
            },
        ],
    }

    monkeypatch.setattr(
        "backend.services.chat_service.CacheManager.get",
        AsyncMock(
            return_value={
                "reply": "cached response",
                "sources": ["guideline.pdf"],
                "evidence_tags": ["profile_summary", "guideline_search"],
                "decision_summary": {
                    "intent": "guideline_lookup",
                    "lane": "general_health",
                    "verdict": "general_guidance",
                    "tool_used": ["get_user_profile_summary"],
                    "safety_level": "normal",
                    "policy": {
                        "policy_version": "explicit_policy.v1",
                        "selected_rule": "general_health",
                        "risk_level": "low",
                        "evidence_state": "sufficient",
                        "tool_availability": "full",
                        "answer_mode": "direct_answer",
                        "disclaimer_mode": "none",
                    },
                },
                "response_verdict": {
                    "schema_version": "response_verdict.v1",
                    "response_mode": "direct_answer",
                    "medical_risk_level": "low",
                    "evidence_sufficiency": "sufficient",
                    "human_escalation_required": False,
                    "degraded_reason": None,
                },
                "evidence_panel": cached_panel,
                "suggestion_card": None,
            }
        ),
    )
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please review my blood sugar",
            session=session,
            conversation_id=None,
            force_refresh=False,
        )
    )

    history = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == response["conversation_id"])
        .order_by(ChatMessage.sequence)
    ).all()

    assert response["reply"] == "cached response"
    assert response["evidence_panel"] == cached_panel
    assert response["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert response["response_verdict"]["response_mode"] == "direct_answer"
    assert history[-1].role == "assistant"
    assert history[-1].evidence_panel == cached_panel
    assert history[-1].response_verdict == response["response_verdict"]


def test_plan_tools_includes_new_safe_read_only_tools():
    service = ChatService()

    planned = service._plan_tools(
        "Please summarize my medication summary, recent metric anomalies, and report comparison",
        lane="medication_related",
    )

    assert "medication_summary_lookup" in planned
    assert "recent_metric_anomaly_lookup" not in planned
    assert "report_comparison_lookup" not in planned


def test_medication_question_routes_to_medication_lane(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        side_effect=[
            RuntimeError("tool calling unsupported"),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="I can summarize the medication facts on file, but I cannot tell you to start, stop, or change a dose."
                        )
                    )
                ]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)
    create_tool_expansion_context(session, user)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please summarize my current medications",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "medication_related"
    assert response["decision_summary"]["verdict"] == "medication_context_only"
    assert response["decision_summary"]["policy"]["selected_rule"] == "medication_related"
    assert response["decision_summary"]["policy"]["answer_mode"] == "bounded_answer"
    assert response["decision_summary"]["policy"]["disclaimer_mode"] == "conservative"
    assert "medication_summary_lookup" in response["decision_summary"]["tool_used"]
    assert set(response["decision_summary"]["tool_used"]).issubset(
        {"medication_summary_lookup", "report_summary_lookup", "search_medical_guidelines"}
    )
    assert "start" not in response["reply"].lower()
    assert "stop" not in response["reply"].lower()


def test_chat_service_stops_at_boundary_for_empty_medication_tool_result(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        side_effect=[
            RuntimeError("tool calling unsupported"),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="This should not be used because the post-check must stop the reply."
                        )
                    )
                ]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    async def fake_select_tools_with_fallback(*args, **kwargs):
        return (
            None,
            [
                {
                    "status": "ok",
                    "tool": "medication_summary_lookup",
                    "result": {
                        "has_medication_summary": False,
                        "medication_summary": None,
                    },
                }
            ],
            True,
            0,
        )

    monkeypatch.setattr(service, "_select_tools_with_fallback", fake_select_tools_with_fallback)

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please summarize my current medications",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "medication_related"
    assert response["decision_summary"]["policy"]["evidence_state"] == "insufficient"
    assert response["response_verdict"]["evidence_sufficiency"] == "insufficient"
    assert "cannot" in response["reply"].lower() or "不能" in response["reply"]
    assert mocked_completion.await_count == 0


def test_diagnosis_seeking_prompt_routes_to_diagnosis_sensitive_lane(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(side_effect=[RuntimeError("tool calling unsupported")])
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)
    create_tool_expansion_context(session, user)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Can you diagnose whether I already have diabetes from my current data?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "diagnosis_sensitive"
    assert response["decision_summary"]["verdict"] == "needs_clinical_diagnosis"
    assert response["decision_summary"]["policy"]["selected_rule"] == "diagnosis_sensitive"
    assert response["decision_summary"]["policy"]["answer_mode"] == "refusal_with_disclaimer"
    assert response["decision_summary"]["policy"]["disclaimer_mode"] == "diagnosis_guardrail"
    assert "诊断" in response["reply"]
    assert "线下" in response["reply"]
    assert set(response["decision_summary"]["tool_used"]).issubset(
        {
            "get_user_profile_summary",
            "report_summary_lookup",
            "latest_analysis_snapshot_lookup",
            "search_medical_guidelines",
        }
    )
    assert mocked_completion.await_count == 1


def test_medication_start_request_uses_refusal_policy(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(side_effect=[RuntimeError("tool calling unsupported")])
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)
    create_tool_expansion_context(session, user)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Should I start metformin now or increase my current dose?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "medication_related"
    assert response["decision_summary"]["policy"]["selected_rule"] == "medication_related"
    assert response["decision_summary"]["policy"]["answer_mode"] == "refusal_with_disclaimer"
    assert response["decision_summary"]["policy"]["disclaimer_mode"] == "conservative"
    assert response["decision_summary"]["policy"]["degrade_reason"] == "unsafe_medication_request"
    assert mocked_completion.await_count == 1


def test_missing_report_context_keeps_report_lane_and_degrades_to_insufficient_evidence(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(side_effect=[RuntimeError("tool calling unsupported")])
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please explain my latest report",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "report_interpretation"
    assert response["decision_summary"]["verdict"] == "insufficient_evidence"
    assert "report_summary_lookup" in response["decision_summary"]["tool_used"]
    assert "上传" in response["reply"]
    assert mocked_completion.await_count == 1


def test_chat_service_fallback_planner_uses_new_safe_read_only_tools(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        side_effect=[
            RuntimeError("tool calling unsupported"),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Here is a concise review of your stored report, abnormal metrics, and latest analysis snapshot.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)
    create_tool_expansion_context(session, user)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please summarize my medication summary, recent metric anomalies, and report comparison",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["conversation_id"] is not None
    assert response["decision_summary"]["lane"] == "medication_related"
    assert "medication_summary_lookup" in response["decision_summary"]["tool_used"]
    assert "recent_metric_anomaly_lookup" not in response["decision_summary"]["tool_used"]
    assert "report_comparison_lookup" not in response["decision_summary"]["tool_used"]
    assert "medication_summary" in response["evidence_tags"]
    assert "metric_anomalies" not in response["evidence_tags"]
    assert "report_comparison" not in response["evidence_tags"]
    chip_keys = [chip["key"] for chip in response["evidence_panel"]["chips"]]
    assert "medication_summary" in chip_keys
    assert "metric_anomalies" not in chip_keys
    assert "report_comparison" not in chip_keys


def test_chat_service_native_function_calling_exposes_new_tools(session, monkeypatch):
    service = ChatService()
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="medication_summary_lookup", arguments="{}"),
    )
    mocked_completion = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call]))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Here is a concise medication summary.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please summarize my medications",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["tool_used"] == ["medication_summary_lookup"]
    assert mocked_completion.await_count == 1


def test_chat_service_audit_includes_runtime_metadata_on_native_tool_call(session, monkeypatch):
    service = ChatService()
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_user_profile_summary", arguments="{}"),
    )
    mocked_completion = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call]))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review your profile context.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    captured = {}

    def fake_build_audit_record(**kwargs):
        captured.update(kwargs)
        return {"captured": True}

    monkeypatch.setattr("backend.services.chat_service.build_audit_record", fake_build_audit_record)
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Use my profile to explain what I should watch out for",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["conversation_id"] is not None
    assert captured["tool_count"] == 1
    assert captured["fallback_used"] is False
    assert captured["tool_latency_ms"] is not None
    assert captured["response_latency_ms"] is not None
    assert captured["governance_version"] == "agent_runtime_governance.v1"
    assert captured["lane"] == response["decision_summary"]["lane"]
    assert captured["verdict"] == response["decision_summary"]["verdict"]
    assert captured["selected_rule"] == response["decision_summary"]["policy"]["selected_rule"]
    assert captured["policy_version"] == response["decision_summary"]["policy"]["policy_version"]
    assert captured["response_mode"] == response["response_verdict"]["response_mode"]
    assert captured["evidence_sufficiency"] == response["response_verdict"]["evidence_sufficiency"]
    assert captured["degraded_reason"] == response["response_verdict"]["degraded_reason"]
    assert captured["human_escalation_required"] is False
    assert captured["tool_plan_source"] == "native_function_calling"
    assert captured["cache_hit"] is False
    assert captured["model_name"] == service.model
    assert captured["context_budget_summary"]["history"]["budget"] == DEFAULT_CONTEXT_BUDGETS["history"]
    assert captured["tool_used"] == ["get_user_profile_summary"]


def test_chat_service_audit_marks_fallback_used_when_native_tool_calling_errors(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        side_effect=[
            RuntimeError("tool calling unsupported"),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    captured = {}

    def fake_build_audit_record(**kwargs):
        captured.update(kwargs)
        return {"captured": True}

    monkeypatch.setattr("backend.services.chat_service.build_audit_record", fake_build_audit_record)
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please review my risk and trend",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["conversation_id"] is not None
    assert captured["fallback_used"] is True
    assert captured["tool_count"] > 0
    assert captured["tool_latency_ms"] is not None
    assert captured["response_latency_ms"] is not None
    assert captured["tool_plan_source"] == "local_fallback_planner"
    assert captured["cache_hit"] is False
    assert captured["model_name"] is None


def test_chat_service_persists_audit_row_for_completed_turn(session, monkeypatch):
    service = ChatService()
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_user_profile_summary", arguments="{}"),
    )
    mocked_completion = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call]))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review your profile context.", tool_calls=None))]
            ),
        ]
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Use my profile to explain what I should watch out for",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    rows = session.exec(
        select(AgentAuditEvent)
        .where(AgentAuditEvent.conversation_id == response["conversation_id"])
        .order_by(AgentAuditEvent.id)
    ).all()

    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].tool_used == ["get_user_profile_summary"]
    assert rows[0].safety_level == "normal"
    assert rows[0].tool_count == 1
    assert rows[0].response_latency_ms is not None
    assert rows[0].context_budget_summary["history"]["budget"] == DEFAULT_CONTEXT_BUDGETS["history"]
    assert_audit_responsibility(
        rows[0],
        decision_summary=response["decision_summary"],
        response_verdict=response["response_verdict"],
        tool_plan_source="native_function_calling",
        cache_hit=False,
        model_name=service.model,
        fallback_used=False,
    )


def test_urgent_query_persists_audit_row(session, monkeypatch):
    service = ChatService()
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    user = create_test_user(session)

    monkeypatch.setattr(
        "backend.services.chat_service.classify_query_safety",
        lambda query: {"route": "medical_escalation", "safety_level": "urgent"},
    )
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="I have chest pain and trouble breathing right now",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    rows = session.exec(
        select(AgentAuditEvent)
        .where(AgentAuditEvent.conversation_id == response["conversation_id"])
        .order_by(AgentAuditEvent.id)
    ).all()

    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].tool_used == []
    assert rows[0].safety_level == "urgent"
    assert rows[0].evidence_tags == ["urgent_route"]
    assert rows[0].tool_count == 0
    assert_audit_responsibility(
        rows[0],
        decision_summary=response["decision_summary"],
        response_verdict=response["response_verdict"],
        tool_plan_source="urgent_short_circuit",
        cache_hit=False,
        model_name=None,
        fallback_used=False,
    )


def test_chat_service_cache_hit_persists_audit_row(session, monkeypatch):
    service = ChatService()
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    user = create_test_user(session)

    monkeypatch.setattr(
        "backend.services.chat_service.CacheManager.get",
        AsyncMock(
            return_value={
                "reply": "cached response",
                "sources": ["guideline.pdf"],
                "evidence_tags": ["profile_summary", "guideline_search"],
                "decision_summary": {
                    "intent": "guideline_lookup",
                    "tool_used": ["get_user_profile_summary"],
                    "safety_level": "normal",
                },
                "evidence_panel": None,
                "suggestion_card": None,
            }
        ),
    )
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please review my blood sugar",
            session=session,
            conversation_id=None,
            force_refresh=False,
        )
    )

    rows = session.exec(
        select(AgentAuditEvent)
        .where(AgentAuditEvent.conversation_id == response["conversation_id"])
        .order_by(AgentAuditEvent.id)
    ).all()

    assert len(rows) == 1
    assert rows[0].intent == "guideline_lookup"
    assert rows[0].tool_used == ["get_user_profile_summary"]
    assert rows[0].evidence_tags == ["profile_summary", "guideline_search"]
    assert rows[0].context_budget_summary["history"]["budget"] == DEFAULT_CONTEXT_BUDGETS["history"]
    assert response["decision_summary"]["lane"] == "general_health"
    assert response["decision_summary"]["policy"]["selected_rule"] == "general_health"
    assert response["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert_audit_responsibility(
        rows[0],
        decision_summary=response["decision_summary"],
        response_verdict=response["response_verdict"],
        tool_plan_source="cache_replay",
        cache_hit=True,
        model_name=None,
        fallback_used=False,
    )


def test_get_user_context_uses_normalized_risk_snapshot_text(session):
    service = ChatService()
    user = User(
        username="normalized_context_user",
        email="normalized_context_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        Age=51,
        Gender=1,
        risk_history=json.dumps(
            {
                "schema_version": "risk_snapshot.v1",
                "generated_at": datetime.utcnow().isoformat(),
                "source": "analyze_comprehensive",
                "findings": [
                    {"key": "kidney_risk", "label": "kidney_risk", "risk_level": "high", "probability": 0.81},
                    {"key": "diabetes", "label": "diabetes", "risk_level": "medium", "probability": 0.42},
                ],
                "ckm": {"stage": 2, "stage_name": "stage_2"},
            },
            ensure_ascii=False,
        ),
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile

    context = service._get_user_context(user, session)

    assert "kidney_risk" in context
    assert "diabetes" in context
    assert "{" not in context
    assert "schema_version" not in context


def test_policy_evaluator_marks_urgent_queries_as_urgent_care_disclaimer():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="I have chest pain and trouble breathing right now",
        safety_result={"lane": "urgent_symptom", "safety_level": "urgent", "route": "medical_escalation"},
        planned_tool_names=[],
        tool_outputs=[],
    )

    assert policy["policy_version"] == "explicit_policy.v1"
    assert policy["selected_rule"] == "urgent_symptom"
    assert policy["risk_level"] == "high"
    assert policy["answer_mode"] == "urgent_care_disclaimer"
    assert policy["disclaimer_mode"] == "urgent_care"
    assert policy["tool_availability"] == "none"
    assert policy["must_refuse"] is False


def test_policy_evaluator_refuses_medication_change_requests():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="Should I stop metformin and double the dose tomorrow?",
        safety_result={"lane": "medication_related", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["medication_summary_lookup"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "medication_summary_lookup",
                "result": {
                    "has_medication_summary": True,
                    "medication_summary": {
                        "medication_items": [
                            {"name": "Metformin", "dose": "500", "unit": "mg", "frequency": "BID"}
                        ]
                    },
                },
            }
        ],
    )

    assert policy["selected_rule"] == "medication_related"
    assert policy["tool_availability"] == "full"
    assert policy["evidence_state"] == "sufficient"
    assert policy["answer_mode"] == "refusal_with_disclaimer"
    assert policy["disclaimer_mode"] == "conservative"
    assert policy["must_refuse"] is True
    assert policy["degrade_reason"] == "unsafe_medication_request"


def test_policy_evaluator_changes_for_same_query_when_tool_support_changes():
    service = ChatService()
    query = "Please summarize my current medications"
    safety_result = {"lane": "medication_related", "safety_level": "normal", "route": "agent"}

    supported_policy = service._evaluate_response_policy(
        query=query,
        safety_result=safety_result,
        planned_tool_names=["medication_summary_lookup"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "medication_summary_lookup",
                "result": {
                    "has_medication_summary": True,
                    "medication_summary": {"medication_items": [{"name": "Metformin"}]},
                },
            }
        ],
    )
    unavailable_policy = service._evaluate_response_policy(
        query=query,
        safety_result=safety_result,
        planned_tool_names=["medication_summary_lookup"],
        tool_outputs=[
            {
                "status": "blocked",
                "tool": "medication_summary_lookup",
                "reason": "tool_not_allowed_for_lane",
            }
        ],
    )

    assert supported_policy["answer_mode"] == "bounded_answer"
    assert supported_policy["tool_availability"] == "full"
    assert supported_policy["evidence_state"] == "sufficient"
    assert supported_policy["degrade_reason"] is None

    assert unavailable_policy["answer_mode"] == "clarify_missing_context"
    assert unavailable_policy["tool_availability"] == "none"
    assert unavailable_policy["evidence_state"] == "insufficient"
    assert unavailable_policy["degrade_reason"] == "tool_unavailable"


def test_policy_evaluator_treats_partial_medication_metadata_as_limited():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="Please summarize my current medications",
        safety_result={"lane": "medication_related", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["medication_summary_lookup"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "medication_summary_lookup",
                "result": {
                    "has_medication_summary": True,
                    "medication_summary": {
                        "medication_items": [{"name": "Metformin"}],
                    },
                    "evidence_metadata": {
                        "schema_version": "tool_evidence_metadata.v1",
                        "freshness": "recent",
                        "coverage": "partial",
                        "confidence": "medium",
                        "missing_fields": ["dose", "frequency"],
                    },
                },
            }
        ],
    )

    assert policy["tool_availability"] == "partial"
    assert policy["evidence_state"] == "limited"
    assert policy["answer_mode"] == "bounded_answer"
    assert policy["degrade_reason"] == "evidence_insufficient"


def test_chat_service_formats_bounded_tool_evidence_text_with_metadata():
    service = ChatService()

    text = service._build_tool_evidence_text(
        [
            {
                "status": "ok",
                "tool": "medication_summary_lookup",
                "result": {
                    "has_medication_summary": True,
                    "medication_summary": {
                        "medication_items": [{"name": "Metformin", "dose": "500"}],
                    },
                    "evidence_metadata": {
                        "schema_version": "tool_evidence_metadata.v1",
                        "freshness": "recent",
                        "coverage": "partial",
                        "confidence": "medium",
                        "missing_fields": ["additional_medication_items"],
                    },
                },
            }
        ]
    )

    assert "coverage=partial" in text
    assert "missing_fields=additional_medication_items" in text
    assert "{\n" not in text
    assert '"has_medication_summary"' not in text


def test_medication_change_request_returns_refusal_policy_in_response(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(side_effect=[RuntimeError("tool calling unsupported")])
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)
    create_tool_expansion_context(session, user)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Should I stop metformin and double the dose tomorrow?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    policy = response["decision_summary"]["policy"]
    assert response["decision_summary"]["lane"] == "medication_related"
    assert policy["policy_version"] == "explicit_policy.v1"
    assert policy["answer_mode"] == "refusal_with_disclaimer"
    assert policy["disclaimer_mode"] == "conservative"
    assert policy["must_refuse"] is True
    assert_takeover(
        response["takeover"],
        status="suppressed",
        trigger_reason="boundary_false_positive",
    )
    assert_response_verdict(
        response["response_verdict"],
        response["decision_summary"],
        degraded_reason="policy_guardrail",
        human_escalation_required=True,
    )
    assert "不能" in response["reply"]
    assert "调整" in response["reply"] or "剂量" in response["reply"]
    assert mocked_completion.await_count == 1


def test_chat_service_persists_response_verdict_on_assistant_turn(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers."))]
        )
    )
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    response = asyncio.run(
        service.chat(
            user=user,
            query="What should I pay attention to in daily life for mildly high blood sugar?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    stored_messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == response["conversation_id"])
        .order_by(ChatMessage.sequence)
    ).all()

    assert stored_messages[0].role == "user"
    assert stored_messages[0].response_verdict is None
    assert stored_messages[1].role == "assistant"
    assert stored_messages[1].response_verdict == response["response_verdict"]
    assert stored_messages[1].takeover is None


def test_report_lane_hard_gate_sets_insufficient_policy_and_explicit_next_step(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(side_effect=[RuntimeError("tool calling unsupported")])
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    user = create_test_user(session)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="Please explain my latest report",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "report_interpretation"
    assert response["decision_summary"]["verdict"] == "insufficient_evidence"
    assert response["decision_summary"]["policy"]["evidence_state"] == "insufficient"
    assert response["decision_summary"]["policy"]["degrade_reason"] == "tool_unavailable"
    assert response["response_verdict"]["evidence_sufficiency"] == "insufficient"
    assert response["response_verdict"]["degraded_reason"] == "tool_unavailable"
    assert response["response_verdict"]["human_escalation_required"] is True
    assert_takeover(
        response["takeover"],
        status="required",
        trigger_reason="insufficient_evidence",
    )
    assert "还不能安全地解释" in response["reply"]
    assert "必要上下文" in response["reply"]
    assert "请上传报告" in response["reply"]
    assert mocked_completion.await_count == 1


def test_general_health_without_profile_or_guideline_stays_in_lane_and_degrades(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(side_effect=[RuntimeError("tool calling unsupported")])
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))

    user = User(
        username="no_profile_user",
        email="no_profile_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = asyncio.run(
        service.chat(
            user=user,
            query="What should I do about high blood sugar in daily life?",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    assert response["decision_summary"]["lane"] == "general_health"
    assert response["decision_summary"]["verdict"] == "insufficient_evidence"
    assert response["decision_summary"]["policy"]["evidence_state"] == "insufficient"
    assert response["response_verdict"]["evidence_sufficiency"] == "insufficient"
    assert response["response_verdict"]["degraded_reason"] == "tool_unavailable"
    assert response["response_verdict"]["human_escalation_required"] is True
    assert_takeover(
        response["takeover"],
        status="required",
        trigger_reason="insufficient_evidence",
    )
    assert "只能给出保守的一般健康建议" in response["reply"]
    assert "必要上下文" in response["reply"]
    assert "准确的指标数值" in response["reply"]
    assert mocked_completion.await_count == 1


def test_policy_evaluator_marks_guideline_only_general_health_as_limited():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="What should I pay attention to for mildly high blood sugar?",
        safety_result={"lane": "general_health", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["get_user_profile_summary", "search_medical_guidelines"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "search_medical_guidelines",
                "result": {
                    "matches_found": True,
                    "context": "General glucose management guidance",
                },
            }
        ],
        profile_evidence=None,
        retrieval_evidence="General glucose management guidance",
    )

    assert policy["tool_availability"] == "partial"
    assert policy["evidence_state"] == "limited"
    assert policy["answer_mode"] == "bounded_answer"
    assert policy["degrade_reason"] == "evidence_insufficient"


def test_policy_evaluator_treats_empty_report_results_as_insufficient_missing_context():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="Please explain my latest report",
        safety_result={"lane": "report_interpretation", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["report_summary_lookup", "get_uploaded_documents_summary"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "report_summary_lookup",
                "result": {
                    "has_report_summary": False,
                    "report_summary": None,
                },
            },
            {
                "status": "ok",
                "tool": "get_uploaded_documents_summary",
                "result": {
                    "count": 0,
                    "items": [],
                },
            },
        ],
    )

    assert policy["tool_availability"] == "none"
    assert policy["evidence_state"] == "insufficient"
    assert policy["answer_mode"] == "clarify_missing_context"
    assert policy["degrade_reason"] == "tool_unavailable"


def test_policy_evaluator_detects_report_profile_conflict_as_conflicting_evidence():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="Please explain my latest glucose report",
        safety_result={"lane": "report_interpretation", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["report_summary_lookup"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "report_summary_lookup",
                "result": {
                    "has_report_summary": True,
                    "report_summary": {
                        "metrics": [
                            {"metric_key": "Glucose_Fasting", "value": 5.1, "unit": "mmol/L"},
                        ]
                    },
                },
            }
        ],
        profile_evidence={"glucose_fasting": 8.2},
    )

    assert policy["tool_availability"] == "partial"
    assert policy["evidence_state"] == "insufficient"
    assert policy["answer_mode"] == "clarify_missing_context"
    assert policy["degrade_reason"] == "conflicting_evidence"


def test_policy_evaluator_detects_personal_data_vs_retrieval_conflict_as_conflicting_evidence():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="What should I do about my glucose?",
        safety_result={"lane": "general_health", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["get_user_profile_summary", "search_medical_guidelines"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "get_user_profile_summary",
                "result": {
                    "has_profile": True,
                    "glucose_fasting": 9.1,
                    "abnormal_flags": ["high fasting glucose"],
                },
            },
            {
                "status": "ok",
                "tool": "search_medical_guidelines",
                "result": {
                    "matches_found": True,
                    "context": "This guidance is intended for healthy adults with normal fasting glucose and no abnormalities.",
                },
            },
        ],
        retrieval_evidence="This guidance is intended for healthy adults with normal fasting glucose and no abnormalities.",
    )

    assert policy["tool_availability"] == "partial"
    assert policy["evidence_state"] == "insufficient"
    assert policy["answer_mode"] == "clarify_missing_context"
    assert policy["degrade_reason"] == "conflicting_evidence"


def test_policy_evaluator_detects_report_trend_conflict_as_conflicting_evidence():
    service = ChatService()

    policy = service._evaluate_response_policy(
        query="Do my report and recent trend tell the same story?",
        safety_result={"lane": "report_interpretation", "safety_level": "normal", "route": "agent"},
        planned_tool_names=["report_summary_lookup", "get_history_trends"],
        tool_outputs=[
            {
                "status": "ok",
                "tool": "report_summary_lookup",
                "result": {
                    "has_report_summary": True,
                    "report_summary": {
                        "metrics": [
                            {"metric_key": "Glucose_Fasting", "value": 5.2, "unit": "mmol/L"},
                        ]
                    },
                },
            },
            {
                "status": "ok",
                "tool": "get_history_trends",
                "result": {
                    "count": 2,
                    "items": [
                        {"metrics": {"Glucose_Fasting": 8.7}},
                        {"metrics": {"Glucose_Fasting": 8.9}},
                    ],
                },
            },
        ],
    )

    assert policy["tool_availability"] == "partial"
    assert policy["evidence_state"] == "insufficient"
    assert policy["answer_mode"] == "clarify_missing_context"
    assert policy["degrade_reason"] == "conflicting_evidence"
