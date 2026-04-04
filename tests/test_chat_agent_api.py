import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlmodel import select

from backend.auth import get_current_user
from backend.main import app
from backend.models import ChatMessage, User, UserProfile
from backend.services.chat_service import chat_service


def create_persisted_user(session):
    user = User(
        username="chat_api_user",
        email="chat_api_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        Age=45,
        Gender=1,
        BMI=26.8,
        Glucose_Fasting=6.5,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    user.profile = profile
    return user


def test_urgent_prompt_short_circuits_agent_flow(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    monkeypatch.setattr(
        "backend.services.chat_service.classify_query_safety",
        lambda query: {"route": "medical_escalation", "safety_level": "urgent"},
    )
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr("backend.services.chat_service.rag_service.search_context", lambda query, k=3: "")

    response = client.post(
        "/chat/send",
        json={"message": "I have chest pain and trouble breathing right now", "conversation_id": None, "force_refresh": True},
    )

    assert response.status_code == 200
    assert response.json()["evidence_tags"] == ["urgent_route"]
    assert response.json()["decision_summary"]["safety_level"] == "urgent"
    assert response.json()["decision_summary"]["policy"]["selected_rule"] == "urgent_symptom"
    assert response.json()["decision_summary"]["policy"]["answer_mode"] == "urgent_care_disclaimer"
    assert response.json()["decision_summary"]["policy"]["disclaimer_mode"] == "urgent_care"
    assert response.json()["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert response.json()["response_verdict"]["response_mode"] == "urgent_care_disclaimer"
    assert response.json()["response_verdict"]["medical_risk_level"] == "high"
    assert response.json()["response_verdict"]["evidence_sufficiency"] == "insufficient"
    assert response.json()["response_verdict"]["human_escalation_required"] is True
    assert response.json()["response_verdict"]["degraded_reason"] == "urgent_risk_detected"

    app.dependency_overrides.clear()


def test_chat_response_contains_agent_fields(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please start with diet control and keep monitoring glucose."))]
        )
    )
    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "conversation_id": None, "force_refresh": True},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] is not None
    assert "decision_summary" in response.json()
    assert "evidence_tags" in response.json()
    assert "profile_summary" in response.json()["evidence_tags"]
    assert response.json()["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert response.json()["response_verdict"]["response_mode"] == response.json()["decision_summary"]["policy"]["answer_mode"]
    assert response.json().get("takeover") is None
    assert response.json()["suggestion_card"]["headline"]
    assert response.json()["suggestion_card"]["key_actions"]

    app.dependency_overrides.clear()


def test_chat_api_reuses_conversation_id_across_turns(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="This is a follow-up reply."))]
        )
    )
    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Ongoing guidance for follow-up questions",
    )

    first_response = client.post(
        "/chat/send",
        json={"message": "Please review my current status", "conversation_id": None, "force_refresh": True},
    )
    conversation_id = first_response.json()["conversation_id"]

    second_response = client.post(
        "/chat/send",
        json={"message": "Please continue with a trend explanation", "conversation_id": conversation_id, "force_refresh": True},
    )

    stored_messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.sequence)
    ).all()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["conversation_id"] == conversation_id
    assert first_response.json().get("takeover") is None
    assert second_response.json()["takeover"]["schema_version"] == "takeover.v1"
    assert second_response.json()["takeover"]["status"] == "required"
    assert second_response.json()["takeover"]["trigger_reason"] == "insufficient_evidence"
    assert len(stored_messages) == 4
    assert [message.role for message in stored_messages] == ["user", "assistant", "user", "assistant"]
    assert stored_messages[3].takeover == second_response.json()["takeover"]

    app.dependency_overrides.clear()


def test_chat_history_detail_replays_assistant_metadata(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers."))]
        )
    )
    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    send_response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "conversation_id": None, "force_refresh": True},
    )
    conversation_id = send_response.json()["conversation_id"]

    history_response = client.get(f"/chat/conversations/{conversation_id}/messages")

    assert history_response.status_code == 200
    assistant_message = history_response.json()["messages"][1]
    assert history_response.json()["messages"][0]["response_verdict"] is None
    assert assistant_message["sources"] == ["guideline.pdf"]
    assert "profile_summary" in assistant_message["evidence_tags"]
    assert assistant_message["decision_summary"]["safety_level"] == "normal"
    assert assistant_message["decision_summary"]["policy"]["selected_rule"] == "general_health"
    assert assistant_message["decision_summary"]["policy"]["answer_mode"] == "direct_answer"
    assert assistant_message["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert assistant_message["response_verdict"]["response_mode"] == "direct_answer"
    assert assistant_message.get("takeover") is None
    assert assistant_message["suggestion_card"]["headline"]
    assert assistant_message["suggestion_card"]["key_actions"]

    app.dependency_overrides.clear()


def test_chat_send_response_includes_evidence_panel(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please start with diet control and keep monitoring glucose."))]
        )
    )
    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "conversation_id": None, "force_refresh": True},
    )

    assert response.status_code == 200
    assert response.json()["evidence_panel"]["chips"][0]["key"] == "profile_summary"
    assert response.json()["evidence_panel"]["sections"][0]["source_refs"] == ["profile_summary"]

    app.dependency_overrides.clear()


def test_chat_history_detail_replays_evidence_panel_and_null_user_turn(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please keep monitoring your glucose and review recent markers."))]
        )
    )
    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    send_response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "conversation_id": None, "force_refresh": True},
    )

    history_response = client.get(f"/chat/conversations/{send_response.json()['conversation_id']}/messages")

    assert history_response.status_code == 200
    assert history_response.json()["messages"][0]["evidence_panel"] is None
    assert history_response.json()["messages"][0]["response_verdict"] is None
    assert history_response.json()["messages"][1]["evidence_panel"]["chips"][0]["key"] == "profile_summary"
    assert history_response.json()["messages"][1]["evidence_panel"]["sections"][0]["source_refs"] == ["profile_summary"]
    assert history_response.json()["messages"][1]["response_verdict"]["schema_version"] == "response_verdict.v1"

    app.dependency_overrides.clear()


def test_chat_send_stream_and_replay_share_explanation_metadata(client, session, monkeypatch):
    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    mocked_completion = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Please start with diet control and keep monitoring glucose."))]
        )
    )
    chat_service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mocked_completion)))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.get", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.services.chat_service.CacheManager.set", AsyncMock())
    monkeypatch.setattr(
        "backend.services.chat_service.rag_service.search_context",
        lambda query, k=3: "[Ref 1 - guideline.pdf]: Glucose management guidance",
    )

    send_response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "conversation_id": None, "force_refresh": True},
    )
    send_payload = send_response.json()

    final_payload = None
    with client.stream(
        "POST",
        "/chat/stream",
        json={"message": "What should I do about high blood sugar?", "conversation_id": None, "force_refresh": True},
    ) as stream_response:
        lines = list(stream_response.iter_lines())

    current_event = None
    for line in lines:
        if line.startswith("event: "):
            current_event = line.split(": ", 1)[1]
            continue
        if line.startswith("data: ") and current_event == "final":
            final_payload = json.loads(line.split(": ", 1)[1])

    history_response = client.get(f"/chat/conversations/{send_payload['conversation_id']}/messages")
    assistant_message = history_response.json()["messages"][1]

    assert send_response.status_code == 200
    assert stream_response.status_code == 200
    assert final_payload is not None
    assert final_payload["decision_summary"] == send_payload["decision_summary"]
    assert final_payload["response_verdict"] == send_payload["response_verdict"]
    assert final_payload["evidence_panel"]["chips"] == send_payload["evidence_panel"]["chips"]
    assert final_payload["evidence_panel"]["sections"][0]["label"] == send_payload["evidence_panel"]["sections"][0]["label"]
    assert final_payload["evidence_panel"]["sections"][0]["summary"] == send_payload["evidence_panel"]["sections"][0]["summary"]
    assert final_payload["evidence_panel"]["sections"][0]["decision_basis"] == send_payload["evidence_panel"]["sections"][0]["decision_basis"]
    assert final_payload["evidence_panel"]["sections"][0]["source_refs"] == send_payload["evidence_panel"]["sections"][0]["source_refs"]
    assert final_payload["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == send_payload["evidence_panel"]["sections"][0]["source_items"][0]["source_type"]
    assert final_payload["suggestion_card"] == send_payload["suggestion_card"]
    assert assistant_message["decision_summary"] == send_payload["decision_summary"]
    assert assistant_message["response_verdict"] == send_payload["response_verdict"]
    assert assistant_message["evidence_panel"]["chips"] == send_payload["evidence_panel"]["chips"]
    assert assistant_message["evidence_panel"]["sections"][0]["label"] == send_payload["evidence_panel"]["sections"][0]["label"]
    assert assistant_message["evidence_panel"]["sections"][0]["summary"] == send_payload["evidence_panel"]["sections"][0]["summary"]
    assert assistant_message["evidence_panel"]["sections"][0]["decision_basis"] == send_payload["evidence_panel"]["sections"][0]["decision_basis"]
    assert assistant_message["evidence_panel"]["sections"][0]["source_refs"] == send_payload["evidence_panel"]["sections"][0]["source_refs"]
    assert assistant_message["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == send_payload["evidence_panel"]["sections"][0]["source_items"][0]["source_type"]
    assert assistant_message["suggestion_card"] == send_payload["suggestion_card"]

    app.dependency_overrides.clear()


def test_chat_history_detail_returns_null_response_verdict_for_legacy_assistant_row(client, session):
    from backend.models import ChatConversation, ChatMessage

    user = create_persisted_user(session)
    app.dependency_overrides[get_current_user] = lambda: user

    conversation = ChatConversation(user_id=user.id, title="Legacy history")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    session.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content="Please review my older session",
            sequence=1,
        )
    )
    session.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content="Legacy stored answer without response verdict",
            sequence=2,
            sources=["guideline.pdf"],
            evidence_tags=["profile_summary"],
            decision_summary={"intent": "guideline_lookup"},
        )
    )
    session.commit()

    history_response = client.get(f"/chat/conversations/{conversation.id}/messages")

    assert history_response.status_code == 200
    assert history_response.json()["messages"][0]["response_verdict"] is None
    assert history_response.json()["messages"][1]["response_verdict"] is None

    app.dependency_overrides.clear()
