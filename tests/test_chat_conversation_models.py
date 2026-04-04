from sqlmodel import select

from backend.models import ChatConversation, ChatMessage, User


def test_chat_conversation_and_messages_persist(session):
    user = User(
        username="chat_user",
        email="chat_user@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    conversation = ChatConversation(user_id=user.id, title="Dr. AI Session")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    first_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content="最近血糖偏高怎么办？",
        sequence=1,
    )
    second_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content="先结合最近指标和生活方式一起看。",
        sequence=2,
    )
    session.add(first_message)
    session.add(second_message)
    session.commit()

    stored_conversation = session.exec(
        select(ChatConversation).where(ChatConversation.id == conversation.id)
    ).one()
    stored_messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.sequence)
    ).all()

    assert stored_conversation.user_id == user.id
    assert len(stored_messages) == 2
    assert [message.role for message in stored_messages] == ["user", "assistant"]
    assert stored_messages[0].content == "最近血糖偏高怎么办？"
