from datetime import datetime
from unittest.mock import AsyncMock
from types import SimpleNamespace

from backend.auth import get_current_user
from backend.main import app
from backend.models import User


def create_chat_user():
    return User(
        id=1,
        username="chat_user",
        email="chat_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )


def test_chat_send_returns_conversation_id_for_new_session(client, monkeypatch):
    async_mock = AsyncMock(
        return_value={
            "conversation_id": 42,
            "reply": "new conversation reply",
            "sources": ["guideline.pdf"],
            "evidence_tags": ["guideline_search"],
            "decision_summary": {"intent": "guideline_lookup"},
            "response_verdict": {
                "schema_version": "response_verdict.v1",
                "response_mode": "direct_answer",
                "medical_risk_level": "low",
                "evidence_sufficiency": "sufficient",
                "human_escalation_required": False,
                "degraded_reason": None,
            },
            "suggestion_card": {
                "headline": "Keep monitoring your glucose",
                "risk_level": "medium",
                "key_actions": ["Track fasting glucose"],
                "follow_up_hint": "Review again in 2 weeks",
                "when_to_seek_care": "Seek urgent care if severe symptoms appear",
            },
        }
    )
    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.chat", async_mock)
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/send",
        json={
            "message": "What should I do about high blood sugar?",
            "force_refresh": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == 42
    assert response.json()["reply"] == "new conversation reply"
    assert response.json()["sources"] == ["guideline.pdf"]
    assert response.json()["evidence_tags"] == ["guideline_search"]
    assert response.json()["decision_summary"] == {"intent": "guideline_lookup"}
    assert response.json()["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert response.json()["suggestion_card"]["risk_level"] == "medium"
    assert async_mock.await_args.kwargs["conversation_id"] is None

    app.dependency_overrides.clear()


def test_chat_send_accepts_existing_conversation_id(client, monkeypatch):
    async_mock = AsyncMock(
        return_value={
            "conversation_id": 7,
            "reply": "continue current conversation",
            "sources": [],
            "evidence_tags": [],
            "decision_summary": {"intent": "general_consultation"},
            "response_verdict": {
                "schema_version": "response_verdict.v1",
                "response_mode": "direct_answer",
                "medical_risk_level": "low",
                "evidence_sufficiency": "sufficient",
                "human_escalation_required": False,
                "degraded_reason": None,
            },
        }
    )
    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.chat", async_mock)
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/send",
        json={
            "message": "continue follow-up",
            "conversation_id": 7,
            "force_refresh": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == 7
    assert response.json()["decision_summary"] == {"intent": "general_consultation"}
    assert response.json()["response_verdict"]["schema_version"] == "response_verdict.v1"
    assert async_mock.await_args.kwargs["conversation_id"] == 7
    assert async_mock.await_args.kwargs["force_refresh"] is True

    app.dependency_overrides.clear()


def test_chat_stream_returns_sse_status_and_final_events(client, monkeypatch):
    async def fake_stream_chat(**kwargs):
        yield {
            "event": "status",
            "data": {
                "stage": "reading_profile",
                "message": "Reading health profile",
                "conversation_id": 9,
            },
        }
        yield {
            "event": "tool_start",
            "data": {
                "tool_name": "get_user_profile_summary",
                "message": "Reading health profile",
                "conversation_id": 9,
            },
        }
        yield {
            "event": "tool_done",
            "data": {
                "tool_name": "get_user_profile_summary",
                "message": "Health profile ready",
                "conversation_id": 9,
            },
        }
        yield {
            "event": "final",
            "data": {
                "conversation_id": 9,
                "reply": "final streamed answer",
                "sources": ["guideline.pdf"],
                "evidence_tags": ["profile_summary"],
                "decision_summary": {"intent": "general_consultation"},
                "response_verdict": {
                    "schema_version": "response_verdict.v1",
                    "response_mode": "bounded_answer",
                    "medical_risk_level": "medium",
                    "evidence_sufficiency": "limited",
                    "human_escalation_required": False,
                    "degraded_reason": "insufficient_evidence",
                },
                "suggestion_card": {
                    "headline": "Monitor glucose consistently",
                    "risk_level": "medium",
                    "key_actions": ["Keep a daily log"],
                    "follow_up_hint": "Discuss with your clinician",
                    "when_to_seek_care": "Seek care sooner if symptoms worsen",
                },
            },
        }

    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.stream_chat", fake_stream_chat)
    app.dependency_overrides[get_current_user] = create_chat_user

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "message": "stream a response",
            "conversation_id": 9,
            "force_refresh": False,
        },
    ) as response:
        body = "\n".join(response.iter_lines())

    assert response.status_code == 200
    assert "event: status" in body
    assert '"stage": "reading_profile"' in body
    assert "event: tool_start" in body
    assert "event: tool_done" in body
    assert "event: final" in body
    assert '"conversation_id": 9' in body
    assert "final streamed answer" in body
    assert '"response_verdict"' in body

    app.dependency_overrides.clear()


def test_chat_conversations_returns_summaries(client, monkeypatch):
    conversation_items = [
        {
            "conversation_id": 12,
            "title": "Blood sugar tracking",
            "preview": "Recent glucose has been fluctuating",
            "message_count": 4,
            "updated_at": "2026-03-24T10:00:00",
            "last_accessed_at": "2026-03-24T10:00:01",
            "pinned": True,
            "archived": False,
            "group_key": "pinned",
            "group_label": "Pinned",
        }
    ]
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.list_conversations",
        lambda session, user, limit=20, query=None, archived=False: conversation_items,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.get("/chat/conversations")

    assert response.status_code == 200
    assert response.json()[0]["conversation_id"] == 12
    assert response.json()[0]["title"] == "Blood sugar tracking"
    assert response.json()[0]["message_count"] == 4
    assert response.json()[0]["last_accessed_at"] == "2026-03-24T10:00:01"
    assert response.json()[0]["pinned"] is True
    assert response.json()[0]["archived"] is False
    assert response.json()[0]["group_key"] == "pinned"
    assert response.json()[0]["group_label"] == "Pinned"

    app.dependency_overrides.clear()


def test_chat_conversations_accept_query_and_archived_filters(client, monkeypatch):
    captured = {}

    def fake_list_conversations(session, user, limit=20, query=None, archived=False):
        captured["query"] = query
        captured["archived"] = archived
        return []

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.list_conversations",
        fake_list_conversations,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.get("/chat/conversations?query=blood&archived=true")

    assert response.status_code == 200
    assert captured == {"query": "blood", "archived": True}

    app.dependency_overrides.clear()


def test_chat_conversation_archive_and_restore_endpoints(client, monkeypatch):
    archive_calls = []
    restore_calls = []

    def fake_archive(session, user, conversation_id):
        archive_calls.append(conversation_id)
        return SimpleNamespace(id=conversation_id)

    def fake_restore(session, user, conversation_id):
        restore_calls.append(conversation_id)
        return SimpleNamespace(id=conversation_id)

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.archive_conversation",
        fake_archive,
    )
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.restore_conversation",
        fake_restore,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    archive_response = client.post("/chat/conversations/9/archive")
    restore_response = client.post("/chat/conversations/9/restore")

    assert archive_response.status_code == 200
    assert restore_response.status_code == 200
    assert archive_response.json() == {"conversation_id": 9, "archived": True}
    assert restore_response.json() == {"conversation_id": 9, "archived": False}
    assert archive_calls == [9]
    assert restore_calls == [9]

    app.dependency_overrides.clear()


def test_chat_batch_archive_prepare_endpoint_classifies_requested_ids(client, session, monkeypatch):
    from backend.models import ChatConversation, User

    user = User(
        username="batch_prepare_user",
        email="batch_prepare_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    other_user = User(
        username="batch_prepare_other",
        email="batch_prepare_other@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.add(other_user)
    session.commit()
    session.refresh(user)
    session.refresh(other_user)

    active = ChatConversation(user_id=user.id, title="Active conversation")
    archived = ChatConversation(
        user_id=user.id,
        title="Archived conversation",
        archived_at=datetime(2026, 3, 28, 10, 0, 0),
    )
    other = ChatConversation(user_id=other_user.id, title="Other user's conversation")
    session.add(active)
    session.add(archived)
    session.add(other)
    session.commit()
    session.refresh(active)
    session.refresh(archived)
    session.refresh(other)

    captured = {}

    def fake_prepare(*, session, user, conversation_ids):
        captured["conversation_ids"] = conversation_ids
        return {
            "requested_conversation_ids": conversation_ids,
            "archiveable_conversation_ids": [active.id],
            "already_archived_conversation_ids": [archived.id],
            "missing_conversation_ids": [999],
            "duplicate_conversation_ids": [active.id],
            "archiveable_count": 1,
        }

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.prepare_batch_archive",
        fake_prepare,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/conversations/batch/archive/prepare",
        json={"conversation_ids": [active.id, archived.id, active.id, 999]},
    )

    assert response.status_code == 200
    assert response.json()["archiveable_conversation_ids"] == [active.id]
    assert response.json()["already_archived_conversation_ids"] == [archived.id]
    assert response.json()["missing_conversation_ids"] == [999]
    assert response.json()["duplicate_conversation_ids"] == [active.id]
    assert response.json()["archiveable_count"] == 1
    assert captured["conversation_ids"] == [active.id, archived.id, active.id, 999]

    app.dependency_overrides.clear()


def test_chat_batch_archive_endpoint_archives_owned_conversations_only(client, session, monkeypatch):
    from backend.models import ChatConversation, User

    user = User(
        username="batch_archive_user",
        email="batch_archive_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    other_user = User(
        username="batch_archive_other",
        email="batch_archive_other@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.add(other_user)
    session.commit()
    session.refresh(user)
    session.refresh(other_user)

    active = ChatConversation(user_id=user.id, title="Active conversation")
    archived = ChatConversation(
        user_id=user.id,
        title="Archived conversation",
        archived_at=datetime(2026, 3, 28, 10, 0, 0),
    )
    other = ChatConversation(user_id=other_user.id, title="Other user's conversation")
    session.add(active)
    session.add(archived)
    session.add(other)
    session.commit()
    session.refresh(active)
    session.refresh(archived)
    session.refresh(other)

    captured = {}

    def fake_archive(*, session, user, conversation_ids):
        captured["conversation_ids"] = conversation_ids
        return {
            "requested_conversation_ids": conversation_ids,
            "archived_conversation_ids": [active.id],
            "already_archived_conversation_ids": [archived.id],
            "missing_conversation_ids": [999],
            "duplicate_conversation_ids": [active.id],
            "archived_count": 1,
        }

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.batch_archive_conversations",
        fake_archive,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/conversations/batch/archive",
        json={"conversation_ids": [active.id, archived.id, active.id, 999]},
    )

    assert response.status_code == 200
    assert response.json()["archived_conversation_ids"] == [active.id]
    assert response.json()["already_archived_conversation_ids"] == [archived.id]
    assert response.json()["missing_conversation_ids"] == [999]
    assert response.json()["duplicate_conversation_ids"] == [active.id]
    assert response.json()["archived_count"] == 1
    assert captured["conversation_ids"] == [active.id, archived.id, active.id, 999]

    app.dependency_overrides.clear()


def test_chat_batch_restore_prepare_endpoint_classifies_requested_ids(client, session, monkeypatch):
    from backend.models import ChatConversation, User

    user = User(
        username="batch_restore_prepare_user",
        email="batch_restore_prepare_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    other_user = User(
        username="batch_restore_prepare_other",
        email="batch_restore_prepare_other@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.add(other_user)
    session.commit()
    session.refresh(user)
    session.refresh(other_user)

    archived = ChatConversation(
        user_id=user.id,
        title="Archived conversation",
        archived_at=datetime(2026, 3, 28, 10, 0, 0),
    )
    active = ChatConversation(user_id=user.id, title="Active conversation")
    other = ChatConversation(user_id=other_user.id, title="Other user's conversation")
    session.add(archived)
    session.add(active)
    session.add(other)
    session.commit()
    session.refresh(archived)
    session.refresh(active)
    session.refresh(other)

    captured = {}

    def fake_prepare(*, session, user, conversation_ids):
        captured["conversation_ids"] = conversation_ids
        return {
            "requested_conversation_ids": conversation_ids,
            "restorable_conversation_ids": [archived.id],
            "already_active_conversation_ids": [active.id],
            "missing_conversation_ids": [999],
            "duplicate_conversation_ids": [archived.id],
            "restorable_count": 1,
        }

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.prepare_batch_restore",
        fake_prepare,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/conversations/batch/restore/prepare",
        json={"conversation_ids": [archived.id, active.id, archived.id, 999]},
    )

    assert response.status_code == 200
    assert response.json()["restorable_conversation_ids"] == [archived.id]
    assert response.json()["already_active_conversation_ids"] == [active.id]
    assert response.json()["missing_conversation_ids"] == [999]
    assert response.json()["duplicate_conversation_ids"] == [archived.id]
    assert response.json()["restorable_count"] == 1
    assert captured["conversation_ids"] == [archived.id, active.id, archived.id, 999]

    app.dependency_overrides.clear()


def test_chat_batch_restore_endpoint_restores_owned_conversations_only(client, session, monkeypatch):
    from backend.models import ChatConversation, User

    user = User(
        username="batch_restore_user",
        email="batch_restore_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    other_user = User(
        username="batch_restore_other",
        email="batch_restore_other@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.add(other_user)
    session.commit()
    session.refresh(user)
    session.refresh(other_user)

    archived = ChatConversation(
        user_id=user.id,
        title="Archived conversation",
        archived_at=datetime(2026, 3, 28, 10, 0, 0),
    )
    active = ChatConversation(user_id=user.id, title="Active conversation")
    other = ChatConversation(
        user_id=other_user.id,
        title="Other user's conversation",
        archived_at=datetime(2026, 3, 28, 10, 0, 0),
    )
    session.add(archived)
    session.add(active)
    session.add(other)
    session.commit()
    session.refresh(archived)
    session.refresh(active)
    session.refresh(other)

    captured = {}

    def fake_restore(*, session, user, conversation_ids):
        captured["conversation_ids"] = conversation_ids
        return {
            "requested_conversation_ids": conversation_ids,
            "restored_conversation_ids": [archived.id],
            "already_active_conversation_ids": [active.id],
            "missing_conversation_ids": [999],
            "duplicate_conversation_ids": [archived.id],
            "restored_count": 1,
        }

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.batch_restore_conversations",
        fake_restore,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/conversations/batch/restore",
        json={"conversation_ids": [archived.id, active.id, archived.id, 999]},
    )

    assert response.status_code == 200
    assert response.json()["restored_conversation_ids"] == [archived.id]
    assert response.json()["already_active_conversation_ids"] == [active.id]
    assert response.json()["missing_conversation_ids"] == [999]
    assert response.json()["duplicate_conversation_ids"] == [archived.id]
    assert response.json()["restored_count"] == 1
    assert captured["conversation_ids"] == [archived.id, active.id, archived.id, 999]

    app.dependency_overrides.clear()


def test_chat_batch_restore_endpoint_rejects_empty_ids(client, monkeypatch):
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.batch_restore_conversations",
        lambda **kwargs: None,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/conversations/batch/restore",
        json={"conversation_ids": []},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "conversation_ids cannot be empty"

    app.dependency_overrides.clear()


def test_chat_conversation_pin_and_unpin_endpoints(client, monkeypatch):
    pin_calls = []
    unpin_calls = []

    def fake_pin(session, user, conversation_id):
        pin_calls.append(conversation_id)
        return SimpleNamespace(id=conversation_id)

    def fake_unpin(session, user, conversation_id):
        unpin_calls.append(conversation_id)
        return SimpleNamespace(id=conversation_id)

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.pin_conversation",
        fake_pin,
    )
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.unpin_conversation",
        fake_unpin,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    pin_response = client.post("/chat/conversations/11/pin")
    unpin_response = client.post("/chat/conversations/11/unpin")

    assert pin_response.status_code == 200
    assert unpin_response.status_code == 200
    assert pin_response.json() == {"conversation_id": 11, "pinned": True}
    assert unpin_response.json() == {"conversation_id": 11, "pinned": False}
    assert pin_calls == [11]
    assert unpin_calls == [11]

    app.dependency_overrides.clear()


def test_chat_conversation_messages_returns_history_with_metadata(client, monkeypatch):
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.get_conversation_detail",
        lambda session, user, conversation_id: {
            "conversation_id": conversation_id,
            "title": "History follow-up",
            "messages": [
                {
                    "role": "user",
                    "content": "Please review my blood sugar",
                    "sequence": 1,
                    "sources": [],
                    "evidence_tags": [],
                    "decision_summary": {},
                    "response_verdict": None,
                    "created_at": "2026-03-24T10:00:00",
                },
                {
                    "role": "assistant",
                    "content": "This is the previous answer",
                    "sequence": 2,
                    "sources": ["guideline.pdf"],
                    "evidence_tags": ["profile_summary"],
                    "decision_summary": {"intent": "guideline_lookup"},
                    "response_verdict": {
                        "schema_version": "response_verdict.v1",
                        "response_mode": "direct_answer",
                        "medical_risk_level": "low",
                        "evidence_sufficiency": "sufficient",
                        "human_escalation_required": False,
                        "degraded_reason": None,
                    },
                    "created_at": "2026-03-24T10:00:03",
                },
            ],
        },
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.get("/chat/conversations/8/messages")

    assert response.status_code == 200
    assert response.json()["conversation_id"] == 8
    assert response.json()["title"] == "History follow-up"
    assert len(response.json()["messages"]) == 2
    assert response.json()["messages"][1]["role"] == "assistant"
    assert response.json()["messages"][1]["sources"] == ["guideline.pdf"]
    assert response.json()["messages"][1]["evidence_tags"] == ["profile_summary"]
    assert response.json()["messages"][0]["response_verdict"] is None
    assert response.json()["messages"][1]["response_verdict"]["schema_version"] == "response_verdict.v1"

    app.dependency_overrides.clear()


def test_chat_conversation_rename_endpoint_trims_title(client, monkeypatch):
    captured = {}

    def fake_rename(session, user, conversation_id, title):
        captured["conversation_id"] = conversation_id
        captured["title"] = title
        return SimpleNamespace(id=conversation_id, title=title)

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.rename_conversation",
        fake_rename,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.patch(
        "/chat/conversations/13",
        json={"title": "  Weekly glucose check-in  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": 13,
        "title": "Weekly glucose check-in",
    }
    assert captured == {
        "conversation_id": 13,
        "title": "Weekly glucose check-in",
    }

    app.dependency_overrides.clear()


def test_chat_conversation_rename_endpoint_rejects_blank_title(client, monkeypatch):
    def fake_rename(session, user, conversation_id, title):
        raise ValueError("Title cannot be empty")

    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.rename_conversation",
        fake_rename,
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.patch(
        "/chat/conversations/13",
        json={"title": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Title cannot be empty"

    app.dependency_overrides.clear()


def test_chat_send_contract_allows_evidence_panel(client, monkeypatch):
    async_mock = AsyncMock(
        return_value={
            "conversation_id": 42,
            "reply": "new conversation reply",
            "sources": ["guideline.pdf"],
            "evidence_tags": ["guideline_search"],
            "decision_summary": {"intent": "guideline_lookup"},
            "response_verdict": {
                "schema_version": "response_verdict.v1",
                "response_mode": "direct_answer",
                "medical_risk_level": "low",
                "evidence_sufficiency": "sufficient",
                "human_escalation_required": False,
                "degraded_reason": None,
            },
            "evidence_panel": {
                "chips": [{"key": "guideline_search", "label": "Guideline Evidence"}],
                "sections": [
                    {
                        "label": "Guideline Evidence",
                        "summary": "Retrieved guidance supported the answer.",
                        "key_facts": ["The reply used retrieved guidance"],
                        "decision_basis": "External guidance reinforced the recommendation.",
                        "source_refs": ["guideline.pdf"],
                        "source_items": [
                            {
                                "source_type": "guideline",
                                "title": "Retrieved guideline reference",
                                "snippet": "Retrieved guidance supported the answer.",
                                "timestamp": None,
                                "relevance": 0.91,
                            }
                        ],
                    }
                ],
            },
            "suggestion_card": None,
        }
    )
    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.chat", async_mock)
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "force_refresh": False},
    )

    assert response.status_code == 200
    assert response.json()["evidence_panel"]["chips"][0]["key"] == "guideline_search"
    assert response.json()["evidence_panel"]["sections"][0]["source_refs"] == ["guideline.pdf"]
    assert response.json()["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == "guideline"
    assert response.json()["response_verdict"]["schema_version"] == "response_verdict.v1"

    app.dependency_overrides.clear()


def test_chat_send_contract_allows_takeover(client, monkeypatch):
    async_mock = AsyncMock(
        return_value={
            "conversation_id": 42,
            "reply": "new conversation reply",
            "sources": ["guideline.pdf"],
            "evidence_tags": ["guideline_search"],
            "decision_summary": {"intent": "guideline_lookup"},
            "response_verdict": {
                "schema_version": "response_verdict.v1",
                "response_mode": "clarify_missing_context",
                "medical_risk_level": "medium",
                "evidence_sufficiency": "insufficient",
                "human_escalation_required": True,
                "degraded_reason": "insufficient_evidence",
            },
            "takeover": {
                "schema_version": "takeover.v1",
                "status": "required",
                "trigger_reason": "insufficient_evidence",
                "summary": "Available evidence is not sufficient for a safe answer, so human review is recommended.",
            },
            "suggestion_card": None,
        }
    )
    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.chat", async_mock)
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.post(
        "/chat/send",
        json={"message": "What should I do about high blood sugar?", "force_refresh": False},
    )

    assert response.status_code == 200
    assert response.json()["takeover"]["schema_version"] == "takeover.v1"
    assert response.json()["takeover"]["status"] == "required"
    assert response.json()["takeover"]["trigger_reason"] == "insufficient_evidence"

    app.dependency_overrides.clear()


def test_chat_stream_contract_final_event_allows_evidence_panel(client, monkeypatch):
    async def fake_stream_chat(**kwargs):
        yield {
            "event": "final",
            "data": {
                "conversation_id": 9,
                "reply": "final streamed answer",
                "sources": ["guideline.pdf"],
                "evidence_tags": ["profile_summary"],
                "decision_summary": {"intent": "general_consultation"},
                "response_verdict": {
                    "schema_version": "response_verdict.v1",
                    "response_mode": "bounded_answer",
                    "medical_risk_level": "medium",
                    "evidence_sufficiency": "limited",
                    "human_escalation_required": False,
                    "degraded_reason": "insufficient_evidence",
                },
                "evidence_panel": {
                    "chips": [{"key": "profile_summary", "label": "Health Profile"}],
                    "sections": [
                        {
                            "label": "Health Profile",
                            "summary": "Profile context influenced the answer.",
                            "key_facts": ["Recent glucose context was considered"],
                            "decision_basis": "The reply matched stored profile context.",
                            "source_refs": ["profile_summary"],
                            "source_items": [
                                {
                                    "source_type": "profile",
                                    "title": "Stored profile snapshot",
                                    "snippet": "Recent glucose context was considered.",
                                    "timestamp": None,
                                    "confidence": 0.86,
                                }
                            ],
                        }
                    ],
                },
                "suggestion_card": None,
            },
        }

    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.stream_chat", fake_stream_chat)
    app.dependency_overrides[get_current_user] = create_chat_user

    with client.stream(
        "POST",
        "/chat/stream",
        json={"message": "stream a response", "conversation_id": 9, "force_refresh": False},
    ) as response:
        body = "\n".join(response.iter_lines())

    assert response.status_code == 200
    assert '"evidence_panel"' in body
    assert '"response_verdict"' in body
    assert '"source_refs": ["profile_summary"]' in body
    assert '"source_type": "profile"' in body

    app.dependency_overrides.clear()


def test_chat_stream_contract_final_event_allows_takeover(client, monkeypatch):
    async def fake_stream_chat(**kwargs):
        yield {
            "event": "final",
            "data": {
                "conversation_id": 9,
                "reply": "final streamed answer",
                "sources": ["guideline.pdf"],
                "evidence_tags": ["profile_summary"],
                "decision_summary": {"intent": "general_consultation"},
                "response_verdict": {
                    "schema_version": "response_verdict.v1",
                    "response_mode": "clarify_missing_context",
                    "medical_risk_level": "medium",
                    "evidence_sufficiency": "insufficient",
                    "human_escalation_required": True,
                    "degraded_reason": "insufficient_evidence",
                },
                "takeover": {
                    "schema_version": "takeover.v1",
                    "status": "required",
                    "trigger_reason": "insufficient_evidence",
                    "summary": "Available evidence is not sufficient for a safe answer, so human review is recommended.",
                },
                "suggestion_card": None,
            },
        }

    monkeypatch.setattr("backend.api.api_v1.endpoints.chat.chat_service.stream_chat", fake_stream_chat)
    app.dependency_overrides[get_current_user] = create_chat_user

    with client.stream(
        "POST",
        "/chat/stream",
        json={"message": "stream a response", "conversation_id": 9, "force_refresh": False},
    ) as response:
        body = "\n".join(response.iter_lines())

    assert response.status_code == 200
    assert '"takeover"' in body
    assert '"schema_version": "takeover.v1"' in body
    assert '"trigger_reason": "insufficient_evidence"' in body

    app.dependency_overrides.clear()


def test_chat_history_contract_allows_evidence_panel_and_null_user_turn(client, monkeypatch):
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.get_conversation_detail",
        lambda session, user, conversation_id: {
            "conversation_id": conversation_id,
            "title": "History follow-up",
            "messages": [
                {
                    "role": "user",
                    "content": "Please review my blood sugar",
                    "sequence": 1,
                    "sources": [],
                    "evidence_tags": [],
                    "decision_summary": {},
                    "response_verdict": None,
                    "evidence_panel": None,
                    "created_at": "2026-03-24T10:00:00",
                },
                {
                    "role": "assistant",
                    "content": "This is the previous answer",
                    "sequence": 2,
                    "sources": ["guideline.pdf"],
                    "evidence_tags": ["profile_summary"],
                    "decision_summary": {"intent": "guideline_lookup"},
                    "response_verdict": {
                        "schema_version": "response_verdict.v1",
                        "response_mode": "direct_answer",
                        "medical_risk_level": "low",
                        "evidence_sufficiency": "sufficient",
                        "human_escalation_required": False,
                        "degraded_reason": None,
                    },
                    "evidence_panel": {
                        "chips": [{"key": "profile_summary", "label": "Health Profile"}],
                        "sections": [
                            {
                                "label": "Health Profile",
                                "summary": "Profile context influenced the answer.",
                                "key_facts": ["Recent glucose context was considered"],
                                "decision_basis": "The reply matched stored profile context.",
                                "source_refs": ["profile_summary"],
                                "source_items": [
                                    {
                                        "source_type": "profile",
                                        "title": "Stored profile snapshot",
                                        "snippet": "Recent glucose context was considered.",
                                        "timestamp": None,
                                        "confidence": 0.86,
                                    }
                                ],
                            }
                        ],
                    },
                    "created_at": "2026-03-24T10:00:03",
                },
            ],
        },
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.get("/chat/conversations/8/messages")

    assert response.status_code == 200
    assert response.json()["messages"][0]["evidence_panel"] is None
    assert response.json()["messages"][0]["response_verdict"] is None
    assert response.json()["messages"][1]["evidence_panel"]["chips"][0]["key"] == "profile_summary"
    assert response.json()["messages"][1]["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == "profile"
    assert response.json()["messages"][1]["response_verdict"]["schema_version"] == "response_verdict.v1"

    app.dependency_overrides.clear()


def test_chat_history_contract_allows_takeover_and_null_user_turn(client, monkeypatch):
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.chat.conversation_service.get_conversation_detail",
        lambda session, user, conversation_id: {
            "conversation_id": conversation_id,
            "title": "History follow-up",
            "messages": [
                {
                    "role": "user",
                    "content": "Please review my blood sugar",
                    "sequence": 1,
                    "sources": [],
                    "evidence_tags": [],
                    "decision_summary": {},
                    "response_verdict": None,
                    "takeover": None,
                    "created_at": "2026-03-24T10:00:00",
                },
                {
                    "role": "assistant",
                    "content": "This is the previous answer",
                    "sequence": 2,
                    "sources": ["guideline.pdf"],
                    "evidence_tags": ["profile_summary"],
                    "decision_summary": {"intent": "guideline_lookup"},
                    "response_verdict": {
                        "schema_version": "response_verdict.v1",
                        "response_mode": "clarify_missing_context",
                        "medical_risk_level": "medium",
                        "evidence_sufficiency": "insufficient",
                        "human_escalation_required": True,
                        "degraded_reason": "insufficient_evidence",
                    },
                    "takeover": {
                        "schema_version": "takeover.v1",
                        "status": "required",
                        "trigger_reason": "insufficient_evidence",
                        "summary": "Available evidence is not sufficient for a safe answer, so human review is recommended.",
                    },
                    "created_at": "2026-03-24T10:00:03",
                },
            ],
        },
    )
    app.dependency_overrides[get_current_user] = create_chat_user

    response = client.get("/chat/conversations/8/messages")

    assert response.status_code == 200
    assert response.json()["messages"][0]["takeover"] is None
    assert response.json()["messages"][1]["takeover"]["schema_version"] == "takeover.v1"
    assert response.json()["messages"][1]["takeover"]["status"] == "required"
    assert response.json()["messages"][1]["takeover"]["trigger_reason"] == "insufficient_evidence"

    app.dependency_overrides.clear()
