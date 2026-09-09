"""Hukuk Ofisi modelleri — avukat ajan serisi, dosyalar ve danışmalar.

models.py'daki genel Agent tablosundan ayrı tutuluyor: avukat ajanlarının
uzmanlık alanı, ürettiği belge tipleri ve dosya/danışma geçmişi var.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LegalAgent(Base):
    """Bir avukat ajanı — uzmanlık alanı + kendi system prompt'u."""
    __tablename__ = "legal_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(128))          # "İcra & İflas Avukatı"
    department: Mapped[str] = mapped_column(String(64), index=True)  # "İcra & Alacak"
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(64))
    color: Mapped[Optional[str]] = mapped_column(String(32))

    expertise: Mapped[Optional[list]] = mapped_column(JSON, default=list)   # uzmanlık maddeleri
    documents: Mapped[Optional[list]] = mapped_column(JSON, default=list)   # üretebildiği belgeler
    keywords: Mapped[Optional[list]] = mapped_column(JSON, default=list)    # yönlendirme için

    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64), default="claude-opus-5")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    consult_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    consultations: Mapped[list["LegalConsultation"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )


class LegalMatter(Base):
    """Hukuk dosyası — birden çok danışmayı tek konu altında toplar."""
    __tablename__ = "legal_matters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    counterparty: Mapped[Optional[str]] = mapped_column(String(255))  # karşı taraf
    reference: Mapped[Optional[str]] = mapped_column(String(128))     # esas no / dosya no
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)  # open, waiting, closed
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consultations: Mapped[list["LegalConsultation"]] = relationship(
        back_populates="matter",
        cascade="all, delete-orphan",
    )


class LegalConsultation(Base):
    """Tek bir danışma / belge talebi ve AI çıktısı."""
    __tablename__ = "legal_consultations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("legal_agents.id"), nullable=False, index=True)
    matter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("legal_matters.id"), nullable=True, index=True)

    mode: Mapped[str] = mapped_column(String(32), default="danisma", index=True)
    # danisma | dilekce | inceleme | arastirma

    subject: Mapped[str] = mapped_column(String(255))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text)      # olay örgüsü / sözleşme metni
    doc_type: Mapped[Optional[str]] = mapped_column(String(128))  # istenen belge tipi

    # AI çıktısı
    result: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    draft: Mapped[Optional[str]] = mapped_column(Text)        # belge taslağı (markdown)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    needs_lawyer: Mapped[bool] = mapped_column(Boolean, default=True)

    status: Mapped[str] = mapped_column(String(32), default="done", index=True)  # done, error
    error: Mapped[Optional[str]] = mapped_column(Text)
    model: Mapped[Optional[str]] = mapped_column(String(64))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    agent: Mapped["LegalAgent"] = relationship(back_populates="consultations")
    matter: Mapped[Optional["LegalMatter"]] = relationship(back_populates="consultations")
