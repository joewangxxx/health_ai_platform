from backend.models import ChatConversation, ChatMessage, User
from backend.scripts.repair_conversation_titles import repair_conversation_titles


def test_repair_conversation_titles_only_updates_legacy_titles(session):
    user = User(
        username="repair_titles_user",
        email="repair_titles_user@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    legacy = ChatConversation(user_id=user.id, title="Dr. AI Session")
    manual = ChatConversation(user_id=user.id, title="Weekly glucose check-in")
    session.add(legacy)
    session.add(manual)
    session.commit()
    session.refresh(legacy)
    session.refresh(manual)

    session.add(
        ChatMessage(
            conversation_id=legacy.id,
            role="user",
            content="Need help reviewing my recent glucose trend and exercise plan.",
            sequence=1,
        )
    )
    session.add(
        ChatMessage(
            conversation_id=manual.id,
            role="user",
            content="Keep this manual title intact.",
            sequence=1,
        )
    )
    session.commit()

    report = repair_conversation_titles(session)

    assert report["checked_count"] == 2
    assert report["repaired_count"] == 1
    assert report["skipped_count"] == 1
    assert report["repaired_conversation_ids"] == [legacy.id]
    assert session.get(ChatConversation, legacy.id).title != "Dr. AI Session"
    assert session.get(ChatConversation, manual.id).title == "Weekly glucose check-in"
