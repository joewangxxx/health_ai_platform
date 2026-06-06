from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlmodel import Session, select

from backend.models import ChatConversation, ChatMessage, User


def build_message_window(
    system_prompt: str,
    history: List[Dict[str, str]],
    max_rounds: int = 5,
) -> List[Dict[str, str]]:
    """中文说明：build_message_window 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    max_messages = max_rounds * 2
    recent_history = history[-max_messages:] if max_messages > 0 else history
    return [{"role": "system", "content": system_prompt}, *recent_history]


class ConversationService:
    """中文说明：ConversationService 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""

    # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
    LEGACY_AUTO_TITLES = {"Dr. AI Session", "Untitled Conversation"}

    def get_or_create_conversation(
        self,
        session: Session,
        user: User,
        conversation_id: Optional[int] = None,
    ) -> ChatConversation:
        """中文说明：get_or_create_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        if conversation_id is not None:
            conversation = session.get(ChatConversation, conversation_id)
            if not conversation or conversation.user_id != user.id:
                raise ValueError("Conversation not found")
            if self.repair_legacy_title(session=session, conversation=conversation):
                session.commit()
                session.refresh(conversation)
            return conversation

        now = datetime.utcnow()
        conversation = ChatConversation(
            user_id=user.id,
            title="Dr. AI Session",
            last_accessed_at=now,
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def append_message(
        self,
        session: Session,
        conversation: ChatConversation,
        role: str,
        content: str,
        sources: Optional[List[str]] = None,
        evidence_tags: Optional[List[str]] = None,
        decision_summary: Optional[Dict[str, object]] = None,
        response_verdict: Optional[Dict[str, object]] = None,
        evidence_panel: Optional[Dict[str, object]] = None,
        suggestion_card: Optional[Dict[str, object]] = None,
        takeover: Optional[Dict[str, object]] = None,
    ) -> ChatMessage:
        latest_sequence = session.exec(
            select(ChatMessage.sequence)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.sequence.desc())
        ).first()
        next_sequence = (latest_sequence or 0) + 1

        message = ChatMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            sequence=next_sequence,
            sources=sources or [],
            evidence_tags=evidence_tags or [],
            decision_summary=decision_summary or {},
            response_verdict=response_verdict if role == "assistant" else None,
            evidence_panel=evidence_panel if role == "assistant" else None,
            suggestion_card=suggestion_card or {},
            takeover=takeover if role == "assistant" else None,
        )
        session.add(message)
        if role == "user" and (
            not conversation.title or conversation.title == "Dr. AI Session"
            or conversation.title == "Untitled Conversation"
        ):
            conversation.title = self._build_title(content)
        conversation.archived_at = None
        conversation.updated_at = datetime.utcnow()
        conversation.last_accessed_at = conversation.updated_at
        session.add(conversation)
        session.commit()
        session.refresh(message)
        session.refresh(conversation)
        return message

    def get_recent_history(
        self,
        session: Session,
        conversation: ChatConversation,
        max_rounds: int = 5,
    ) -> List[Dict[str, str]]:
        """中文说明：get_recent_history 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        max_messages = max_rounds * 2
        messages = list(
            session.exec(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation.id)
                .order_by(ChatMessage.sequence.desc())
                .limit(max_messages)
            ).all()
        )
        messages.reverse()
        return [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

    def list_conversations(
        self,
        session: Session,
        user: User,
        limit: int = 20,
        query: Optional[str] = None,
        archived: bool = False,
    ) -> List[Dict[str, object]]:
        # 列表查询分三步：
        # 1) 拉取用户会话并修复历史自动标题；
        # 2) 按固定排序键排序；
        # 3) 按归档状态与关键字过滤后截断到 limit。
        conversations = list(
            session.exec(
                select(ChatConversation).where(ChatConversation.user_id == user.id)
            ).all()
        )
        repaired_any = False
        for conversation in conversations:
            if self.repair_legacy_title(session=session, conversation=conversation):
                repaired_any = True

        conversations.sort(key=self._conversation_sort_key, reverse=True)

        items = []
        normalized_query = (query or "").strip().lower()
        for conversation in conversations:
            is_archived = conversation.archived_at is not None
            if archived != is_archived:
                continue

            # preview 基于最后一条消息生成，用于会话列表摘要展示。
            messages = list(
                session.exec(
                    select(ChatMessage)
                    .where(ChatMessage.conversation_id == conversation.id)
                    .order_by(ChatMessage.sequence)
                ).all()
            )
            preview = messages[-1].content[:80] if messages else ""
            haystack = " ".join(
                part for part in [conversation.title or "", preview] if part
            ).lower()
            if normalized_query and normalized_query not in haystack:
                continue

            items.append(
                {
                    "conversation_id": conversation.id,
                    "title": conversation.title or "Untitled Conversation",
                    "preview": preview,
                    "message_count": len(messages),
                    "updated_at": conversation.updated_at.isoformat(),
                    "last_accessed_at": (
                        conversation.last_accessed_at.isoformat()
                        if conversation.last_accessed_at
                        else None
                    ),
                    "pinned": conversation.pinned_at is not None,
                    "archived": is_archived,
                    "group_key": self._conversation_group_key(conversation),
                    "group_label": self._conversation_group_label(conversation),
                }
            )
            if len(items) >= limit:
                break
        if repaired_any:
            session.commit()
        return items

    def rename_conversation(
        self,
        session: Session,
        user: User,
        conversation_id: int,
        title: str,
    ) -> ChatConversation:
        """中文说明：rename_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        conversation = self.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        normalized_title = (title or "").strip()
        if not normalized_title:
            raise ValueError("Title cannot be empty")
        if len(normalized_title) > 255:
            raise ValueError("Title is too long")

        conversation.title = normalized_title
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def get_conversation_detail(
        self,
        session: Session,
        user: User,
        conversation_id: int,
    ) -> Dict[str, object]:
        """中文说明：get_conversation_detail 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        conversation = self.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        conversation.last_accessed_at = datetime.utcnow()
        self.repair_legacy_title(session=session, conversation=conversation)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        messages = list(
            session.exec(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation.id)
                .order_by(ChatMessage.sequence)
            ).all()
        )
        return {
            "conversation_id": conversation.id,
            "title": conversation.title or "Untitled Conversation",
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    "sequence": message.sequence,
                    "sources": message.sources or [],
                    "evidence_tags": message.evidence_tags or [],
                    "decision_summary": message.decision_summary or {},
                    "response_verdict": message.response_verdict if message.role == "assistant" else None,
                    "evidence_panel": message.evidence_panel if message.role == "assistant" else None,
                    "suggestion_card": message.suggestion_card or {},
                    "takeover": message.takeover if message.role == "assistant" else None,
                    "created_at": message.created_at.isoformat(),
                }
                for message in messages
            ],
        }

    def archive_conversation(
        self,
        session: Session,
        user: User,
        conversation_id: int,
    ) -> ChatConversation:
        """中文说明：archive_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        conversation = self.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        conversation.archived_at = datetime.utcnow()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def pin_conversation(
        self,
        session: Session,
        user: User,
        conversation_id: int,
    ) -> ChatConversation:
        """中文说明：pin_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        conversation = self.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        conversation.pinned_at = datetime.utcnow()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def unpin_conversation(
        self,
        session: Session,
        user: User,
        conversation_id: int,
    ) -> ChatConversation:
        """中文说明：unpin_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        conversation = self.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        conversation.pinned_at = None
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def restore_conversation(
        self,
        session: Session,
        user: User,
        conversation_id: int,
    ) -> ChatConversation:
        """中文说明：restore_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        conversation = self.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        conversation.archived_at = None
        conversation.updated_at = datetime.utcnow()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def prepare_batch_archive(
        self,
        session: Session,
        user: User,
        conversation_ids: List[int],
    ) -> Dict[str, object]:
        """中文说明：prepare_batch_archive 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        requested_conversation_ids, unique_conversation_ids, duplicate_conversation_ids = self._normalize_batch_conversation_ids(
            conversation_ids
        )
        archiveable_conversation_ids: List[int] = []
        already_archived_conversation_ids: List[int] = []
        missing_conversation_ids: List[int] = []

        for conversation_id in unique_conversation_ids:
            conversation = session.get(ChatConversation, conversation_id)
            if not conversation or conversation.user_id != user.id:
                missing_conversation_ids.append(conversation_id)
                continue
            if conversation.archived_at is not None:
                already_archived_conversation_ids.append(conversation_id)
                continue
            archiveable_conversation_ids.append(conversation_id)

        return {
            "requested_conversation_ids": requested_conversation_ids,
            "archiveable_conversation_ids": archiveable_conversation_ids,
            "already_archived_conversation_ids": already_archived_conversation_ids,
            "missing_conversation_ids": missing_conversation_ids,
            "duplicate_conversation_ids": duplicate_conversation_ids,
            "archiveable_count": len(archiveable_conversation_ids),
        }

    def prepare_batch_restore(
        self,
        session: Session,
        user: User,
        conversation_ids: List[int],
    ) -> Dict[str, object]:
        """中文说明：prepare_batch_restore 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        requested_conversation_ids, unique_conversation_ids, duplicate_conversation_ids = self._normalize_batch_conversation_ids(
            conversation_ids
        )
        restorable_conversation_ids: List[int] = []
        already_active_conversation_ids: List[int] = []
        missing_conversation_ids: List[int] = []

        for conversation_id in unique_conversation_ids:
            conversation = session.get(ChatConversation, conversation_id)
            if not conversation or conversation.user_id != user.id:
                missing_conversation_ids.append(conversation_id)
                continue
            if conversation.archived_at is None:
                already_active_conversation_ids.append(conversation_id)
                continue
            restorable_conversation_ids.append(conversation_id)

        return {
            "requested_conversation_ids": requested_conversation_ids,
            "restorable_conversation_ids": restorable_conversation_ids,
            "already_active_conversation_ids": already_active_conversation_ids,
            "missing_conversation_ids": missing_conversation_ids,
            "duplicate_conversation_ids": duplicate_conversation_ids,
            "restorable_count": len(restorable_conversation_ids),
        }

    def batch_archive_conversations(
        self,
        session: Session,
        user: User,
        conversation_ids: List[int],
    ) -> Dict[str, object]:
        """中文说明：batch_archive_conversations 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        prepared = self.prepare_batch_archive(
            session=session,
            user=user,
            conversation_ids=conversation_ids,
        )

        archived_conversation_ids: List[int] = []
        for conversation_id in prepared["archiveable_conversation_ids"]:
            conversation = session.get(ChatConversation, conversation_id)
            if not conversation or conversation.user_id != user.id:
                continue
            if conversation.archived_at is not None:
                continue
            conversation.archived_at = datetime.utcnow()
            session.add(conversation)
            archived_conversation_ids.append(conversation_id)

        if archived_conversation_ids:
            session.commit()

        return {
            "requested_conversation_ids": prepared["requested_conversation_ids"],
            "archived_conversation_ids": archived_conversation_ids,
            "already_archived_conversation_ids": prepared["already_archived_conversation_ids"],
            "missing_conversation_ids": prepared["missing_conversation_ids"],
            "duplicate_conversation_ids": prepared["duplicate_conversation_ids"],
            "archived_count": len(archived_conversation_ids),
        }

    def batch_restore_conversations(
        self,
        session: Session,
        user: User,
        conversation_ids: List[int],
    ) -> Dict[str, object]:
        """中文说明：batch_restore_conversations 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        prepared = self.prepare_batch_restore(
            session=session,
            user=user,
            conversation_ids=conversation_ids,
        )

        restored_conversation_ids: List[int] = []
        for conversation_id in prepared["restorable_conversation_ids"]:
            conversation = session.get(ChatConversation, conversation_id)
            if not conversation or conversation.user_id != user.id:
                continue
            if conversation.archived_at is None:
                continue
            conversation.archived_at = None
            session.add(conversation)
            restored_conversation_ids.append(conversation_id)

        if restored_conversation_ids:
            session.commit()

        return {
            "requested_conversation_ids": prepared["requested_conversation_ids"],
            "restored_conversation_ids": restored_conversation_ids,
            "already_active_conversation_ids": prepared["already_active_conversation_ids"],
            "missing_conversation_ids": prepared["missing_conversation_ids"],
            "duplicate_conversation_ids": prepared["duplicate_conversation_ids"],
            "restored_count": len(restored_conversation_ids),
        }

    def repair_legacy_title(self, session: Session, conversation: ChatConversation) -> bool:
        normalized_title = (conversation.title or "").strip()
        if normalized_title and normalized_title not in self.LEGACY_AUTO_TITLES:
            return False

        messages = list(
            session.exec(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation.id)
                .order_by(ChatMessage.sequence)
            ).all()
        )
        first_user_message = next(
            (
                message.content
                for message in messages
                if message.role == "user" and (message.content or "").strip()
            ),
            None,
        )
        if not first_user_message:
            return False

        repaired_title = self._build_title(first_user_message)
        if repaired_title == conversation.title:
            return False

        conversation.title = repaired_title
        session.add(conversation)
        return True

    def _conversation_sort_key(self, conversation: ChatConversation) -> tuple:
        """中文说明：_conversation_sort_key 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        pinned_rank = 1 if conversation.pinned_at is not None else 0
        pin_time = conversation.pinned_at or datetime.min
        access_time = conversation.last_accessed_at or datetime.min
        updated_time = conversation.updated_at or datetime.min
        conversation_id = conversation.id or 0
        return (pinned_rank, pin_time, access_time, updated_time, conversation_id)

    def _conversation_group_key(self, conversation: ChatConversation) -> str:
        """中文说明：_conversation_group_key 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        if conversation.pinned_at is not None:
            return "pinned"

        source_timestamp = conversation.last_accessed_at or conversation.updated_at
        if source_timestamp is None:
            return "older"

        now = datetime.utcnow()
        if source_timestamp.date() == now.date():
            return "today"
        if source_timestamp >= now - timedelta(days=7):
            return "last_7_days"
        return "older"

    def _conversation_group_label(self, conversation: ChatConversation) -> str:
        """中文说明：_conversation_group_label 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        labels = {
            "pinned": "Pinned",
            "today": "Today",
            "last_7_days": "Last 7 Days",
            "older": "Older",
        }
        return labels[self._conversation_group_key(conversation)]

    def _build_title(self, content: str) -> str:
        """中文说明：_build_title 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        compact = " ".join((content or "").replace("\n", " ").split())
        if not compact:
            return "Dr. AI Session"

        sentence = compact
        for separator in ["？", "?", "。", "！", "!", "\n"]:
            if separator in sentence:
                sentence = sentence.split(separator, 1)[0]
                break

        filler_prefixes = [
            "请问我最近",
            "请问我",
            "请问",
            "我最近",
            "我想咨询一下",
            "帮我看看",
            "麻烦帮我看看",
        ]
        for prefix in filler_prefixes:
            if sentence.startswith(prefix):
                sentence = sentence[len(prefix) :]
                break

        sentence = sentence.strip(" ，,.:：;；")
        sentence = sentence.replace("，", "")
        sentence = sentence.replace(",", "")
        return sentence[:30] if sentence else compact[:30]


    def _normalize_batch_conversation_ids(
        self,
        conversation_ids: List[int],
    ) -> tuple[List[int], List[int], List[int]]:
        """中文说明：_normalize_batch_conversation_ids 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
        requested_conversation_ids = list(conversation_ids)
        unique_conversation_ids: List[int] = []
        duplicate_conversation_ids: List[int] = []
        seen_conversation_ids = set()

        for conversation_id in requested_conversation_ids:
            if conversation_id in seen_conversation_ids:
                if conversation_id not in duplicate_conversation_ids:
                    duplicate_conversation_ids.append(conversation_id)
                continue
            seen_conversation_ids.add(conversation_id)
            unique_conversation_ids.append(conversation_id)

        return requested_conversation_ids, unique_conversation_ids, duplicate_conversation_ids


conversation_service = ConversationService()
