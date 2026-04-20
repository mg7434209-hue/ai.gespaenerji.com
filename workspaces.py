"""Veritabanı modelleri — tek dosyada tutuyoruz, basit."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Admin kullanıcı (tek kullanıcı sistemi)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)


class Workspace(Base):
    """İş kolu / workspace — Superonline, SolarAnaliz, TrafikRehber vs."""
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(64))  # lucide icon name
    color: Mapped[Optional[str]] = mapped_column(String(32))  # hex/tailwind
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)  # workspace-özel ayarlar
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    leads: Mapped[list["Lead"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Lead(Base):
    """Lead / potansiyel müşteri — Superonline workspace için."""
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)

    # Müşteri bilgileri
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(64))

    # Lead durumu
    status: Mapped[str] = mapped_column(
        String(32),
        default="new",
        index=True,
    )  # new, contacted, offered, won, lost

    source: Mapped[Optional[str]] = mapped_column(String(64))  # web_form, whatsapp, phone, referral
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Superonline özel alanlar
    package_interest: Mapped[Optional[str]] = mapped_column(String(128))  # örn "100 Mbps Fiber"
    estimated_value: Mapped[Optional[int]] = mapped_column(Integer)  # TL/ay

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contact_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    workspace: Mapped["Workspace"] = relationship(back_populates="leads")


class Agent(Base):
    """AI ajanı tanımı — Satış Uzmanı, Email Asistanı vs."""
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str] = mapped_column(String(64))  # Satış, Teklif, Destek, İletişim...
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(64))
    color: Mapped[Optional[str]] = mapped_column(String(32))
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64), default="claude-sonnet-4-20250514")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
