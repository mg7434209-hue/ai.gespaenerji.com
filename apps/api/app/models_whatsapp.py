"""WhatsApp konuşma + mesaj + AI analiz modelleri.

Ana models.py'dan ayrı tutuyoruz, daha temiz.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WhatsAppConversation(Base):
    """Bir telefon numarası = bir konuşma."""
    __tablename__ = "whatsapp_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Kişi bilgileri
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    profile_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Durum
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    last_message_preview: Mapped[Optional[str]] = mapped_column(String(280))
    unread_count: Mapped[int] = mapped_column(Integer, default=0)

    # İlişkilendirmeler
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), nullable=True)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)

    # Etiketler
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # AI ayarları
    ai_mode: Mapped[str] = mapped_column(String(32), default="auto_draft")
    # Modlar: auto_reply | auto_draft | manual | paused

    # Güven skoru
    ai_confidence_avg: Mapped[float] = mapped_column(Float, default=0.7)

    # Durum bayrakları
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["WhatsAppMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="WhatsAppMessage.created_at",
    )


class WhatsAppMessage(Base):
    """Gelen/giden tek bir mesaj."""
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("whatsapp_conversations.id"),
        nullable=False,
        index=True,
    )

    meta_message_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)

    content_type: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    media_url: Mapped[Optional[str]] = mapped_column(Text)
    media_mime: Mapped[Optional[str]] = mapped_column(String(64))

    # AI analiz sonuçları
    ai_intent: Mapped[Optional[str]] = mapped_column(String(64))
    ai_sentiment: Mapped[Optional[str]] = mapped_column(String(16))
    ai_language: Mapped[Optional[str]] = mapped_column(String(8))
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)

    ai_draft: Mapped[Optional[str]] = mapped_column(Text)
    ai_draft_confidence: Mapped[Optional[float]] = mapped_column(Float)
    ai_auto_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    reply_to_id: Mapped[Optional[int]] = mapped_column(ForeignKey("whatsapp_messages.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    sent_by: Mapped[str] = mapped_column(String(32), default="user")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation: Mapped["WhatsAppConversation"] = relationship(back_populates="messages")


class WhatsAppWebhookLog(Base):
    """Meta'dan gelen tüm webhook payload'ları (debug + audit)."""
    __tablename__ = "whatsapp_webhook_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    event_type: Mapped[Optional[str]] = mapped_column(String(64))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
