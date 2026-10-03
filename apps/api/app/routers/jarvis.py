"""Komuta ajanı (JARVIS) uçları — ana sayfadaki sohbet kutusu."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.models_jarvis import JarvisConversation, JarvisMessage
from app.services import jarvis

router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    tools: list[str]
    model: Optional[str] = None
    ok: bool


class MessageOut(BaseModel):
    id: int
    role: str
    text: str
    tools: list[str]
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    channel: str
    title: Optional[str]
    updated_at: datetime
    messages: list[MessageOut] = []


@router.get("/status")
def status(user: User = Depends(get_current_user)):
    from app.config import settings
    return {"configured": jarvis.is_configured(), "model": settings.jarvis_model}


# `def` (async değil): Claude çağrısı senkron, FastAPI bunu iş parçacığında çalıştırır.
@router.post("/chat", response_model=ChatResponse)
def chat(data: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not jarvis.is_configured():
        raise HTTPException(503, "JARVIS kapalı: sunucuda ANTHROPIC_API_KEY tanımlı değil")
    if data.conversation_id:
        conv = db.query(JarvisConversation).filter(
            JarvisConversation.id == data.conversation_id,
            JarvisConversation.channel == "web",
        ).first()
        if not conv:
            raise HTTPException(404, "Sohbet bulunamadı")
    else:
        conv = JarvisConversation(channel="web")
        db.add(conv)
        db.commit()
        db.refresh(conv)
    r = jarvis.ask(db, conv, data.message)
    return ChatResponse(conversation_id=r.conversation_id, reply=r.text,
                        tools=r.tools, model=r.model, ok=r.ok)


def _conv_out(conv: JarvisConversation, db: Session) -> ConversationOut:
    rows = (db.query(JarvisMessage)
            .filter(JarvisMessage.conversation_id == conv.id, JarvisMessage.visible == True)  # noqa: E712
            .order_by(JarvisMessage.id).all())
    return ConversationOut(
        id=conv.id, channel=conv.channel, title=conv.title, updated_at=conv.updated_at,
        messages=[MessageOut(id=m.id, role=m.role, text=m.display or "",
                             tools=m.tools or [], created_at=m.created_at) for m in rows],
    )


@router.get("/conversations/latest", response_model=Optional[ConversationOut])
def latest(channel: str = "web", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = (db.query(JarvisConversation).filter(JarvisConversation.channel == channel)
            .order_by(JarvisConversation.updated_at.desc()).first())
    return _conv_out(conv, db) if conv else None


@router.get("/conversations/{conv_id}", response_model=ConversationOut)
def get_conversation(conv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(JarvisConversation).filter(JarvisConversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Sohbet bulunamadı")
    return _conv_out(conv, db)
