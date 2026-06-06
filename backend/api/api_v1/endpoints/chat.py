import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.auth import get_current_user
from backend.database import get_session
from backend.models import User
from backend.services.chat_service import chat_service
from backend.services.conversation_service import conversation_service

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    force_refresh: bool = False


class EvidenceChip(BaseModel):
    key: str
    label: str


class EvidenceSourceItem(BaseModel):
    source_type: str
    title: str
    snippet: str
    timestamp: Optional[str] = None
    confidence: Optional[float] = None
    relevance: Optional[float] = None


class EvidenceSection(BaseModel):
    label: str
    summary: str
    key_facts: List[str] = Field(default_factory=list)
    decision_basis: str
    source_refs: List[str] = Field(default_factory=list)
    source_items: List[EvidenceSourceItem] = Field(default_factory=list)


class EvidencePanel(BaseModel):
    chips: List[EvidenceChip] = Field(default_factory=list)
    sections: List[EvidenceSection] = Field(default_factory=list)


class ResponseVerdict(BaseModel):
    schema_version: str
    response_mode: str
    medical_risk_level: str
    evidence_sufficiency: str
    human_escalation_required: bool
    degraded_reason: Optional[str] = None


class Takeover(BaseModel):
    schema_version: str
    status: str
    trigger_reason: str
    summary: str


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    sources: List[str] = Field(default_factory=list)
    evidence_tags: List[str] = Field(default_factory=list)
    decision_summary: dict = Field(default_factory=dict)
    response_verdict: Optional[ResponseVerdict] = None
    takeover: Optional[Takeover] = None
    evidence_panel: Optional[EvidencePanel] = None
    suggestion_card: Optional[dict] = None


class ConversationSummary(BaseModel):
    conversation_id: int
    title: str
    preview: str = ""
    message_count: int = 0
    updated_at: str
    last_accessed_at: Optional[str] = None
    pinned: bool = False
    archived: bool = False
    group_key: str
    group_label: str


class ConversationRenameRequest(BaseModel):
    title: str


class ConversationRenameState(BaseModel):
    conversation_id: int
    title: str


class ConversationArchiveState(BaseModel):
    conversation_id: int
    archived: bool


class BatchConversationArchiveRequest(BaseModel):
    conversation_ids: List[int] = Field(default_factory=list)


class BatchConversationArchivePrepareState(BaseModel):
    requested_conversation_ids: List[int] = Field(default_factory=list)
    archiveable_conversation_ids: List[int] = Field(default_factory=list)
    already_archived_conversation_ids: List[int] = Field(default_factory=list)
    missing_conversation_ids: List[int] = Field(default_factory=list)
    duplicate_conversation_ids: List[int] = Field(default_factory=list)
    archiveable_count: int = 0


class BatchConversationArchiveState(BaseModel):
    requested_conversation_ids: List[int] = Field(default_factory=list)
    archived_conversation_ids: List[int] = Field(default_factory=list)
    already_archived_conversation_ids: List[int] = Field(default_factory=list)
    missing_conversation_ids: List[int] = Field(default_factory=list)
    duplicate_conversation_ids: List[int] = Field(default_factory=list)
    archived_count: int = 0


class BatchConversationRestorePrepareState(BaseModel):
    requested_conversation_ids: List[int] = Field(default_factory=list)
    restorable_conversation_ids: List[int] = Field(default_factory=list)
    already_active_conversation_ids: List[int] = Field(default_factory=list)
    missing_conversation_ids: List[int] = Field(default_factory=list)
    duplicate_conversation_ids: List[int] = Field(default_factory=list)
    restorable_count: int = 0


class BatchConversationRestoreState(BaseModel):
    requested_conversation_ids: List[int] = Field(default_factory=list)
    restored_conversation_ids: List[int] = Field(default_factory=list)
    already_active_conversation_ids: List[int] = Field(default_factory=list)
    missing_conversation_ids: List[int] = Field(default_factory=list)
    duplicate_conversation_ids: List[int] = Field(default_factory=list)
    restored_count: int = 0


class ConversationPinState(BaseModel):
    conversation_id: int
    pinned: bool


class ConversationMessage(BaseModel):
    role: str
    content: str
    sequence: int
    sources: List[str] = Field(default_factory=list)
    evidence_tags: List[str] = Field(default_factory=list)
    decision_summary: dict = Field(default_factory=dict)
    response_verdict: Optional[ResponseVerdict] = None
    takeover: Optional[Takeover] = None
    evidence_panel: Optional[EvidencePanel] = None
    suggestion_card: dict = Field(default_factory=dict)
    created_at: str


class ConversationDetail(BaseModel):
    conversation_id: int
    title: str
    messages: List[ConversationMessage] = Field(default_factory=list)


def _encode_sse(event: str, payload: dict) -> str:
    """中文说明：_encode_sse 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    response = await chat_service.chat(
        user=current_user,
        query=request.message,
        session=session,
        conversation_id=request.conversation_id,
        force_refresh=request.force_refresh,
    )
    return response


@router.get("/conversations", response_model=List[ConversationSummary])
def list_chat_conversations(
    query: Optional[str] = Query(default=None),
    archived: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：list_chat_conversations 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    return conversation_service.list_conversations(
        session=session,
        user=current_user,
        query=query,
        archived=archived,
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationRenameState)
def rename_chat_conversation(
    conversation_id: int,
    request: ConversationRenameRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：rename_chat_conversation 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    normalized_title = (request.title or "").strip()
    if not normalized_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if len(normalized_title) > 255:
        raise HTTPException(status_code=400, detail="Title is too long")

    try:
        conversation = conversation_service.rename_conversation(
            session=session,
            user=current_user,
            conversation_id=conversation_id,
            title=normalized_title,
        )
        return {"conversation_id": conversation.id, "title": conversation.title}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/conversations/batch/archive/prepare", response_model=BatchConversationArchivePrepareState)
def prepare_batch_archive_chat_conversations(
    request: BatchConversationArchiveRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return conversation_service.prepare_batch_archive(
        session=session,
        user=current_user,
        conversation_ids=request.conversation_ids,
    )


@router.post("/conversations/batch/archive", response_model=BatchConversationArchiveState)
def batch_archive_chat_conversations(
    request: BatchConversationArchiveRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：batch_archive_chat_conversations 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not request.conversation_ids:
        raise HTTPException(status_code=400, detail="conversation_ids cannot be empty")

    return conversation_service.batch_archive_conversations(
        session=session,
        user=current_user,
        conversation_ids=request.conversation_ids,
    )


@router.post("/conversations/batch/restore/prepare", response_model=BatchConversationRestorePrepareState)
def prepare_batch_restore_chat_conversations(
    request: BatchConversationArchiveRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return conversation_service.prepare_batch_restore(
        session=session,
        user=current_user,
        conversation_ids=request.conversation_ids,
    )


@router.post("/conversations/batch/restore", response_model=BatchConversationRestoreState)
def batch_restore_chat_conversations(
    request: BatchConversationArchiveRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：batch_restore_chat_conversations 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not request.conversation_ids:
        raise HTTPException(status_code=400, detail="conversation_ids cannot be empty")

    return conversation_service.batch_restore_conversations(
        session=session,
        user=current_user,
        conversation_ids=request.conversation_ids,
    )


@router.post("/conversations/{conversation_id}/archive", response_model=ConversationArchiveState)
def archive_chat_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        conversation = conversation_service.archive_conversation(
            session=session,
            user=current_user,
            conversation_id=conversation_id,
        )
        return {"conversation_id": conversation.id, "archived": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/pin", response_model=ConversationPinState)
def pin_chat_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        conversation = conversation_service.pin_conversation(
            session=session,
            user=current_user,
            conversation_id=conversation_id,
        )
        return {"conversation_id": conversation.id, "pinned": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/unpin", response_model=ConversationPinState)
def unpin_chat_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        conversation = conversation_service.unpin_conversation(
            session=session,
            user=current_user,
            conversation_id=conversation_id,
        )
        return {"conversation_id": conversation.id, "pinned": False}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/restore", response_model=ConversationArchiveState)
def restore_chat_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        conversation = conversation_service.restore_conversation(
            session=session,
            user=current_user,
            conversation_id=conversation_id,
        )
        return {"conversation_id": conversation.id, "archived": False}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conversations/{conversation_id}/messages", response_model=ConversationDetail)
def get_chat_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：get_chat_conversation_messages 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    try:
        return conversation_service.get_conversation_detail(
            session=session,
            user=current_user,
            conversation_id=conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/stream")
async def stream_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """中文说明：当前单元 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def event_generator():
        # 中文注释：该步骤承担当前流程的关键状态衔接，需与上下游契约保持一致。
        try:
            async for event in chat_service.stream_chat(
                user=current_user,
                query=request.message,
                session=session,
                conversation_id=request.conversation_id,
                force_refresh=request.force_refresh,
            ):
                yield _encode_sse(event["event"], event["data"])
        except Exception as exc:
            yield _encode_sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
