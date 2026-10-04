"""Komuta ajanı (JARVIS) sohbet hafızası.

Her satır, API'ye gönderilen `messages` dizisinin BİREBİR bir elemanıdır:
kullanıcı metni, asistanın tüm içerik blokları (thinking + tool_use + text)
ve araç sonuçları. Geçmiş YALNIZ EKLENİR, düzenlenmez: Opus 5.5 "preserved
thinking" kuralıyla düşünme bloklarını üreten sohbete bağlar; geçmişte bir
satırı değiştirmek ya da silmek sonraki istekleri bozar. Uzayan sohbet
budanmaz, yeni sohbet açılır (web'de "Yeni sohbet", WhatsApp'ta her gün).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JarvisConversation(Base):
    __tablename__ = "jarvis_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(16), default="web", index=True)  # web | whatsapp
    title: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["JarvisMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="JarvisMessage.id",
    )


class JarvisMessage(Base):
    __tablename__ = "jarvis_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("jarvis_conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16))          # user | assistant (API rolü)
    content: Mapped[list] = mapped_column(JSON)            # API içerik blokları, olduğu gibi
    # Arayüzde gösterilecek metin; araç sonucu satırlarında boştur (gizli)
    display: Mapped[Optional[str]] = mapped_column(Text)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    tools: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # bu turda kullanılan araçlar
    model: Mapped[Optional[str]] = mapped_column(String(64))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["JarvisConversation"] = relationship(back_populates="messages")
