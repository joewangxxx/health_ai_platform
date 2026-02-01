from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session
from typing import Dict, List, Any
from pydantic import BaseModel

from backend.database import get_session
from backend.models import User
from backend.auth import get_current_user
from backend.services.chat_service import chat_service

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    force_refresh: bool = False  # Task 111: 强制刷新，忽略缓存

class ChatResponse(BaseModel):
    reply: str
    sources: List[str] = []

@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Dr. AI RAG Chat Endpoint
    - Context-aware: Uses User Profile
    - Evidence-based: Uses Knowledge Base
    - Task 111: Supports force_refresh to bypass cache
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    response = await chat_service.chat(
        user=current_user,
        query=request.message,
        session=session,
        force_refresh=request.force_refresh  # Task 111
    )
    
    return response
