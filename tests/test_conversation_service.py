from datetime import datetime, timedelta

from sqlmodel import select

from backend.models import ChatMessage, User
from backend.services.conversation_service import build_message_window, conversation_service


def create_user(session, suffix=""):
    username_suffix = f"_{suffix}" if suffix else ""
    user = User(
        username=f"conversation_service_user{username_suffix}",
        email=f"conversation_service_user{username_suffix}@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_build_message_window_keeps_system_and_latest_rounds():
    history = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
        {"role": "assistant", "content": "a3"},
    ]

    window = build_message_window(
        system_prompt="system",
        history=history,
        max_rounds=2,
    )

    assert window == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
        {"role": "assistant", "content": "a3"},
    ]


def test_build_message_window_handles_short_history():
    window = build_message_window(
        system_prompt="system",
        history=[{"role": "user", "content": "hello"}],
        max_rounds=3,
    )

    assert window == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "hello"},
    ]


def test_append_message_sets_title_from_first_user_message(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=conversation,
        role="user",
        content="This is the first user question and should become the title.",
    )

    refreshed = conversation_service.get_or_create_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )
    assert refreshed.title.startswith("This is the first user quest")


def test_get_or_create_conversation_repairs_legacy_auto_generated_title_on_read(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)
    conversation.title = "Dr. AI Session"
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    session.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content="Need help reviewing my recent glucose trend and exercise plan.",
            sequence=1,
        )
    )
    session.commit()

    refreshed = conversation_service.get_or_create_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert refreshed.title == conversation_service._build_title(
        "Need help reviewing my recent glucose trend and exercise plan."
    )


def test_get_or_create_conversation_leaves_manual_title_unchanged(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)
    conversation.title = "Weekly glucose check-in"
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    session.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content="Need help reviewing my recent glucose trend and exercise plan.",
            sequence=1,
        )
    )
    session.commit()

    refreshed = conversation_service.get_or_create_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert refreshed.title == "Weekly glucose check-in"


def test_list_conversations_repairs_legacy_titles_in_place(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)
    conversation.title = "Dr. AI Session"
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    session.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content="Need help reviewing my recent glucose trend and exercise plan.",
            sequence=1,
        )
    )
    session.commit()

    items = conversation_service.list_conversations(session=session, user=user)

    assert items[0]["conversation_id"] == conversation.id
    assert items[0]["title"] == conversation_service._build_title(
        "Need help reviewing my recent glucose trend and exercise plan."
    )
    assert session.get(type(conversation), conversation.id).title == items[0]["title"]


def test_append_message_builds_more_natural_title_summary(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=conversation,
        role="user",
        content="请问我最近血糖一直偏高，应该重点注意什么？我还需要继续复查吗？",
    )

    refreshed = conversation_service.get_or_create_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )
    assert refreshed.title == "血糖一直偏高应该重点注意什么"


def test_list_conversations_returns_latest_first_with_preview(session):
    user = create_user(session)
    older = conversation_service.get_or_create_conversation(session=session, user=user)
    newer = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=older,
        role="user",
        content="Older conversation content",
    )
    conversation_service.append_message(
        session=session,
        conversation=newer,
        role="user",
        content="Newest conversation summary content",
    )

    items = conversation_service.list_conversations(session=session, user=user)

    assert len(items) == 2
    assert items[0]["conversation_id"] == newer.id
    assert items[0]["preview"] == "Newest conversation summary content"
    assert items[0]["message_count"] == 1


def test_list_conversations_supports_query_and_archived_filter(session):
    user = create_user(session)
    active = conversation_service.get_or_create_conversation(session=session, user=user)
    archived = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=active,
        role="user",
        content="Blood sugar trend review",
    )
    conversation_service.append_message(
        session=session,
        conversation=archived,
        role="user",
        content="Sleep quality discussion",
    )
    conversation_service.archive_conversation(
        session=session,
        user=user,
        conversation_id=archived.id,
    )

    search_items = conversation_service.list_conversations(
        session=session,
        user=user,
        query="blood sugar",
    )
    archived_items = conversation_service.list_conversations(
        session=session,
        user=user,
        archived=True,
    )

    assert [item["conversation_id"] for item in search_items] == [active.id]
    assert [item["conversation_id"] for item in archived_items] == [archived.id]
    assert archived_items[0]["archived"] is True


def test_list_conversations_sorts_pinned_before_recent(session):
    user = create_user(session)
    pinned = conversation_service.get_or_create_conversation(session=session, user=user)
    recent = conversation_service.get_or_create_conversation(session=session, user=user)
    older = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=older,
        role="user",
        content="Older follow-up",
    )
    conversation_service.append_message(
        session=session,
        conversation=recent,
        role="user",
        content="Most recently accessed active conversation",
    )
    conversation_service.append_message(
        session=session,
        conversation=pinned,
        role="user",
        content="Pinned blood sugar review",
    )

    conversation_service.pin_conversation(
        session=session,
        user=user,
        conversation_id=pinned.id,
    )
    conversation_service.get_conversation_detail(
        session=session,
        user=user,
        conversation_id=recent.id,
    )

    items = conversation_service.list_conversations(session=session, user=user)

    assert [item["conversation_id"] for item in items] == [pinned.id, recent.id, older.id]
    assert items[0]["pinned"] is True
    assert items[1]["pinned"] is False
    assert items[1]["last_accessed_at"] is not None


def test_get_conversation_detail_refreshes_last_accessed_at(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)
    conversation_service.append_message(
        session=session,
        conversation=conversation,
        role="user",
        content="Need a follow-up review",
    )

    before = conversation_service.get_or_create_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )
    before_accessed_at = before.last_accessed_at
    assert before_accessed_at is not None

    detail = conversation_service.get_conversation_detail(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )
    refreshed = conversation_service.get_or_create_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert detail["conversation_id"] == conversation.id
    assert refreshed.last_accessed_at is not None
    assert refreshed.last_accessed_at >= before_accessed_at


def test_pin_and_unpin_conversation(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    pinned = conversation_service.pin_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )
    assert pinned.pinned_at is not None

    unpinned = conversation_service.unpin_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert unpinned.pinned_at is None


def test_archive_and_restore_conversation(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    archived = conversation_service.archive_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )
    assert archived.archived_at is not None

    restored = conversation_service.restore_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert restored.archived_at is None


def test_prepare_batch_archive_classifies_owned_archived_missing_and_duplicate_ids(session):
    user = create_user(session)
    other_user = create_user(session, "other")
    archiveable = conversation_service.get_or_create_conversation(session=session, user=user)
    already_archived = conversation_service.get_or_create_conversation(session=session, user=user)
    other_user_conversation = conversation_service.get_or_create_conversation(session=session, user=other_user)

    conversation_service.archive_conversation(
        session=session,
        user=user,
        conversation_id=already_archived.id,
    )

    result = conversation_service.prepare_batch_archive(
        session=session,
        user=user,
        conversation_ids=[
            archiveable.id,
            already_archived.id,
            archiveable.id,
            other_user_conversation.id,
            999,
        ],
    )

    assert result["requested_conversation_ids"] == [
        archiveable.id,
        already_archived.id,
        archiveable.id,
        other_user_conversation.id,
        999,
    ]
    assert result["archiveable_conversation_ids"] == [archiveable.id]
    assert result["already_archived_conversation_ids"] == [already_archived.id]
    assert result["missing_conversation_ids"] == [other_user_conversation.id, 999]
    assert result["duplicate_conversation_ids"] == [archiveable.id]
    assert result["archiveable_count"] == 1


def test_batch_archive_conversations_archives_only_owned_archiveable_rows(session):
    user = create_user(session)
    other_user = create_user(session, "other")
    archiveable = conversation_service.get_or_create_conversation(session=session, user=user)
    already_archived = conversation_service.get_or_create_conversation(session=session, user=user)
    other_user_conversation = conversation_service.get_or_create_conversation(session=session, user=other_user)

    conversation_service.archive_conversation(
        session=session,
        user=user,
        conversation_id=already_archived.id,
    )
    conversation_service.append_message(
        session=session,
        conversation=archiveable,
        role="user",
        content="Keep this history intact",
    )
    original_message_count = len(
        session.exec(select(ChatMessage).where(ChatMessage.conversation_id == archiveable.id)).all()
    )

    result = conversation_service.batch_archive_conversations(
        session=session,
        user=user,
        conversation_ids=[
            archiveable.id,
            already_archived.id,
            archiveable.id,
            other_user_conversation.id,
            999,
        ],
    )

    refreshed_archiveable = session.get(type(archiveable), archiveable.id)
    refreshed_already_archived = session.get(type(already_archived), already_archived.id)
    refreshed_other_user_conversation = session.get(type(other_user_conversation), other_user_conversation.id)
    archived_message_count = len(
        session.exec(select(ChatMessage).where(ChatMessage.conversation_id == archiveable.id)).all()
    )

    assert result["requested_conversation_ids"] == [
        archiveable.id,
        already_archived.id,
        archiveable.id,
        other_user_conversation.id,
        999,
    ]
    assert result["archived_conversation_ids"] == [archiveable.id]
    assert result["already_archived_conversation_ids"] == [already_archived.id]
    assert result["missing_conversation_ids"] == [other_user_conversation.id, 999]
    assert result["duplicate_conversation_ids"] == [archiveable.id]
    assert result["archived_count"] == 1
    assert refreshed_archiveable.archived_at is not None
    assert refreshed_already_archived.archived_at is not None
    assert refreshed_other_user_conversation.archived_at is None
    assert archived_message_count == original_message_count


def test_prepare_batch_restore_classifies_owned_active_missing_and_duplicate_ids(session):
    user = create_user(session)
    other_user = create_user(session, "other")
    restorable = conversation_service.get_or_create_conversation(session=session, user=user)
    already_active = conversation_service.get_or_create_conversation(session=session, user=user)
    other_user_conversation = conversation_service.get_or_create_conversation(session=session, user=other_user)

    conversation_service.archive_conversation(
        session=session,
        user=user,
        conversation_id=restorable.id,
    )

    result = conversation_service.prepare_batch_restore(
        session=session,
        user=user,
        conversation_ids=[
            restorable.id,
            already_active.id,
            restorable.id,
            other_user_conversation.id,
            999,
        ],
    )

    assert result["requested_conversation_ids"] == [
        restorable.id,
        already_active.id,
        restorable.id,
        other_user_conversation.id,
        999,
    ]
    assert result["restorable_conversation_ids"] == [restorable.id]
    assert result["already_active_conversation_ids"] == [already_active.id]
    assert result["missing_conversation_ids"] == [other_user_conversation.id, 999]
    assert result["duplicate_conversation_ids"] == [restorable.id]
    assert result["restorable_count"] == 1


def test_batch_restore_conversations_restores_only_owned_archived_rows(session):
    user = create_user(session)
    other_user = create_user(session, "other")
    restorable = conversation_service.get_or_create_conversation(session=session, user=user)
    already_active = conversation_service.get_or_create_conversation(session=session, user=user)
    other_user_conversation = conversation_service.get_or_create_conversation(session=session, user=other_user)

    conversation_service.archive_conversation(
        session=session,
        user=user,
        conversation_id=restorable.id,
    )
    conversation_service.append_message(
        session=session,
        conversation=restorable,
        role="user",
        content="Keep my custom title and ordering metadata",
    )
    restorable.title = "Archived follow-up"
    restorable.archived_at = datetime.utcnow() - timedelta(days=1)
    restorable.pinned_at = datetime.utcnow() - timedelta(days=3)
    restorable.last_accessed_at = datetime.utcnow() - timedelta(days=2)
    original_updated_at = datetime.utcnow() - timedelta(days=4)
    restorable.updated_at = original_updated_at
    session.add(restorable)
    session.commit()
    session.refresh(restorable)

    result = conversation_service.batch_restore_conversations(
        session=session,
        user=user,
        conversation_ids=[
            restorable.id,
            already_active.id,
            restorable.id,
            other_user_conversation.id,
            999,
        ],
    )

    refreshed_restorable = session.get(type(restorable), restorable.id)
    refreshed_already_active = session.get(type(already_active), already_active.id)
    refreshed_other_user_conversation = session.get(type(other_user_conversation), other_user_conversation.id)

    assert result["requested_conversation_ids"] == [
        restorable.id,
        already_active.id,
        restorable.id,
        other_user_conversation.id,
        999,
    ]
    assert result["restored_conversation_ids"] == [restorable.id]
    assert result["already_active_conversation_ids"] == [already_active.id]
    assert result["missing_conversation_ids"] == [other_user_conversation.id, 999]
    assert result["duplicate_conversation_ids"] == [restorable.id]
    assert result["restored_count"] == 1
    assert refreshed_restorable.archived_at is None
    assert refreshed_restorable.title == "Archived follow-up"
    assert refreshed_restorable.pinned_at is not None
    assert refreshed_restorable.last_accessed_at is not None
    assert refreshed_restorable.updated_at == original_updated_at
    assert refreshed_already_active.archived_at is None
    assert refreshed_other_user_conversation.archived_at is None


def test_conversation_detail_returns_message_metadata(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=conversation,
        role="assistant",
        content="historical assistant reply with metadata",
        sources=["guide.pdf"],
        evidence_tags=["profile_summary"],
        decision_summary={"intent": "guideline_lookup", "safety_level": "normal"},
    )

    detail = conversation_service.get_conversation_detail(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert detail["messages"][0]["sources"] == ["guide.pdf"]
    assert detail["messages"][0]["evidence_tags"] == ["profile_summary"]
    assert detail["messages"][0]["decision_summary"]["intent"] == "guideline_lookup"


def test_rename_conversation_trims_title_without_changing_order_metadata(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)
    original_updated_at = datetime.utcnow() - timedelta(days=2)
    original_accessed_at = datetime.utcnow() - timedelta(days=1)
    conversation.title = "Dr. AI Session"
    conversation.updated_at = original_updated_at
    conversation.last_accessed_at = original_accessed_at
    conversation.pinned_at = None
    conversation.archived_at = None
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    renamed = conversation_service.rename_conversation(
        session=session,
        user=user,
        conversation_id=conversation.id,
        title="  Weekly glucose check-in  ",
    )

    assert renamed.title == "Weekly glucose check-in"
    assert renamed.updated_at == original_updated_at
    assert renamed.last_accessed_at == original_accessed_at
    assert renamed.pinned_at is None
    assert renamed.archived_at is None


def test_rename_conversation_rejects_blank_title(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    try:
        conversation_service.rename_conversation(
            session=session,
            user=user,
            conversation_id=conversation.id,
            title="   ",
        )
    except ValueError as exc:
        assert "Title cannot be empty" in str(exc)
    else:
        raise AssertionError("Expected rename_conversation to reject blank titles")


def test_list_conversations_includes_backend_group_metadata(session):
    user = create_user(session)
    now = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

    pinned = conversation_service.get_or_create_conversation(session=session, user=user)
    today = conversation_service.get_or_create_conversation(session=session, user=user)
    last_week = conversation_service.get_or_create_conversation(session=session, user=user)
    older = conversation_service.get_or_create_conversation(session=session, user=user)

    pinned.updated_at = now - timedelta(days=1)
    pinned.last_accessed_at = now - timedelta(days=1)
    pinned.pinned_at = now - timedelta(hours=1)

    today.updated_at = now
    today.last_accessed_at = now

    last_week.updated_at = now - timedelta(days=3)
    last_week.last_accessed_at = now - timedelta(days=3)

    older.updated_at = now - timedelta(days=10)
    older.last_accessed_at = None

    for conversation in [pinned, today, last_week, older]:
        session.add(conversation)
    session.commit()

    conversation_service.pin_conversation(
        session=session,
        user=user,
        conversation_id=pinned.id,
    )

    items = conversation_service.list_conversations(session=session, user=user)

    assert [item["conversation_id"] for item in items] == [pinned.id, today.id, last_week.id, older.id]
    assert items[0]["group_key"] == "pinned"
    assert items[0]["group_label"] == "Pinned"
    assert items[1]["group_key"] == "today"
    assert items[1]["group_label"] == "Today"
    assert items[2]["group_key"] == "last_7_days"
    assert items[2]["group_label"] == "Last 7 Days"
    assert items[3]["group_key"] == "older"
    assert items[3]["group_label"] == "Older"


def test_conversation_detail_includes_assistant_evidence_panel(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=conversation,
        role="assistant",
        content="historical assistant reply with metadata",
        sources=["guide.pdf"],
        evidence_tags=["profile_summary"],
        decision_summary={"intent": "guideline_lookup", "safety_level": "normal"},
        evidence_panel={
            "chips": [{"key": "profile_summary", "label": "Health Profile"}],
            "sections": [
                {
                    "label": "Health Profile",
                    "summary": "Profile context influenced the answer.",
                    "key_facts": ["Recent glucose context was considered"],
                    "decision_basis": "The answer matched stored profile context.",
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
    )

    detail = conversation_service.get_conversation_detail(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert detail["messages"][0]["evidence_panel"]["chips"][0]["key"] == "profile_summary"
    assert detail["messages"][0]["evidence_panel"]["sections"][0]["source_refs"] == ["profile_summary"]
    assert detail["messages"][0]["evidence_panel"]["sections"][0]["source_items"][0]["source_type"] == "profile"


def test_conversation_detail_returns_null_evidence_panel_for_user_messages(session):
    user = create_user(session)
    conversation = conversation_service.get_or_create_conversation(session=session, user=user)

    conversation_service.append_message(
        session=session,
        conversation=conversation,
        role="user",
        content="Please review my latest glucose result",
    )

    detail = conversation_service.get_conversation_detail(
        session=session,
        user=user,
        conversation_id=conversation.id,
    )

    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][0]["evidence_panel"] is None
