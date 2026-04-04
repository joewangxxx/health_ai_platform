import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlmodel import select

from backend.models import AgentAnswerReplay, ChatMessage, User, UserProfile
from backend.services.chat_service import ChatService


def create_test_user(session):
    user = User(
        username="replay_user",
        email="replay_user@example.com",
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
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile
    return user


def test_chat_service_persists_bounded_answer_replay_for_normal_finalize(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Please keep monitoring your glucose and review recent markers."
                    )
                )
            ]
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

    replay_row = session.exec(select(AgentAnswerReplay)).one()
    assistant_message = session.exec(
        select(ChatMessage).where(ChatMessage.id == replay_row.chat_message_id)
    ).one()

    assert replay_row.schema_version == "agent_answer_replay.v1"
    assert replay_row.user_id == user.id
    assert replay_row.conversation_id == response["conversation_id"]
    assert replay_row.audit_event_id is not None
    assert replay_row.chat_message_id == assistant_message.id
    assert assistant_message.role == "assistant"
    assert replay_row.policy_snapshot["lane"] == response["decision_summary"]["lane"]
    assert replay_row.policy_snapshot["verdict"] == response["decision_summary"]["verdict"]
    assert replay_row.policy_snapshot["policy_version"] == response["decision_summary"]["policy"]["policy_version"]
    assert replay_row.execution_snapshot["tool_count"] >= 1
    assert replay_row.execution_snapshot["cache_hit"] is False
    assert replay_row.execution_snapshot["tool_plan_source"] in {
        "native_function_calling",
        "local_fallback_planner",
    }
    assert replay_row.context_budget_summary["query"]["budget"] > 0
    assert replay_row.tool_result_summary
    assert replay_row.tool_result_summary[0]["tool_name"]
    assert replay_row.tool_result_summary[0]["status"] == "ok"
    assert replay_row.rag_source_refs
    assert replay_row.rag_source_refs[0]["source"] == "guideline.pdf"


def test_chat_service_persists_bounded_answer_replay_for_cache_hit_finalize(session, monkeypatch):
    service = ChatService()
    service.client = None
    user = create_test_user(session)

    cached_data = {
        "reply": "Cached guidance reply",
        "decision_summary": {
            "intent": "guideline_lookup",
            "lane": "general_health",
            "verdict": "general_guidance",
            "tool_needed": True,
            "tool_used": ["get_user_profile_summary"],
            "safety_level": "normal",
            "policy": {
                "policy_version": "explicit_policy.v1",
                "selected_rule": "general_health",
                "answer_mode": "direct_answer",
                "risk_level": "low",
                "evidence_state": "limited",
                "degrade_reason": "evidence_insufficient",
            },
        },
        "response_verdict": {
            "schema_version": "response_verdict.v1",
            "response_mode": "direct_answer",
            "medical_risk_level": "low",
            "evidence_sufficiency": "limited",
            "human_escalation_required": False,
            "degraded_reason": "insufficient_evidence",
        },
        "sources": ["guideline.pdf"],
        "evidence_tags": ["guideline_search"],
        "evidence_panel": None,
        "suggestion_card": None,
    }

    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=cached_data))
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
            force_refresh=False,
        )
    )

    replay_row = session.exec(select(AgentAnswerReplay)).one()

    assert response["reply"] == "Cached guidance reply"
    assert replay_row.execution_snapshot["cache_hit"] is True
    assert replay_row.execution_snapshot["tool_plan_source"] == "cache_replay"
    assert replay_row.policy_snapshot["lane"] == "general_health"
    assert replay_row.rag_source_refs == [{"source": "guideline.pdf"}]


def test_chat_service_persists_bounded_answer_replay_when_model_fails(session, monkeypatch):
    service = ChatService()
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=Exception("boom")))))
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

    replay_row = session.exec(select(AgentAnswerReplay)).one()

    assert "无法完成分析" in response["reply"] or "请稍后" in response["reply"]
    assert replay_row.execution_snapshot["cache_hit"] is False
    assert replay_row.execution_snapshot["model_name"] is None
    assert replay_row.execution_snapshot["tool_plan_source"] in {
        "native_function_calling",
        "local_fallback_planner",
    }


def test_chat_service_persists_bounded_answer_replay_for_urgent_short_circuit(session, monkeypatch):
    service = ChatService()
    service.client = None
    user = create_test_user(session)

    monkeypatch.setattr(
        "backend.services.chat_service.classify_query_safety",
        lambda query: {"route": "medical_escalation", "safety_level": "urgent"},
    )

    response = asyncio.run(
        service.chat(
            user=user,
            query="I have chest pain and trouble breathing right now",
            session=session,
            conversation_id=None,
            force_refresh=True,
        )
    )

    replay_row = session.exec(select(AgentAnswerReplay)).one()

    assert response["decision_summary"]["lane"] == "urgent_symptom"
    assert replay_row.execution_snapshot["tool_plan_source"] == "urgent_short_circuit"
    assert replay_row.execution_snapshot["tool_count"] == 0
    assert replay_row.policy_snapshot["degraded_reason"] == "urgent_risk_detected"
    assert replay_row.tool_result_summary == []
    assert replay_row.rag_source_refs == []


def test_chat_service_rolls_back_session_when_answer_replay_persist_fails(session, monkeypatch):
    service = ChatService()
    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Please keep monitoring your glucose and review recent markers."
                    )
                )
            ]
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

    def exploding_persist(*, session, replay_record):
        from backend.services.agent_answer_replay import persist_answer_replay_record as real_persist

        real_persist(session=session, replay_record=replay_record)
        return real_persist(session=session, replay_record=replay_record)

    monkeypatch.setattr("backend.services.chat_service.persist_answer_replay_record", exploding_persist)

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
    assert session.exec(select(User).where(User.id == user.id)).one().id == user.id
