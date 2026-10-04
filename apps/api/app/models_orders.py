"""Site sipariş defteri — sitelerin gönderdiği KİŞİSEL VERİSİ AYIKLANMIŞ siparişler.

Siteler (ilk olarak gespaenerji.com) her sipariş durum değişikliğinde kaydı
`POST /api/ingest/orders` ile gönderir; burada (site, ref) TEKİLDİR ve kayıt
güncellenir. JARVIS ve ana sayfa siparişleri buradan okur — sitenin kendi
dosyası dağıtımda silinse de defter kalır. Ad, telefon, e-posta, adres,
TCKN/VKN bu tabloya HİÇ girmez (alan yok; uç bilinmeyen alanları atar).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SiteOrder(Base):
    __tablename__ = "site_orders"
    __table_args__ = (UniqueConstraint("site", "ref", name="uq_site_order_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site: Mapped[str] = mapped_column(String(32), index=True)          # gespaenerji
    ref: Mapped[str] = mapped_column(String(64))                       # sitenin sipariş no'su
    channel: Mapped[Optional[str]] = mapped_column(String(16))         # sepet | link
    status: Mapped[Optional[str]] = mapped_column(String(16), index=True)  # pending | paid | failed
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)   # UTC
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_tl: Mapped[Optional[float]] = mapped_column(Float)
    paid_tl: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    taksit: Mapped[Optional[int]] = mapped_column(Integer)
    error_code: Mapped[Optional[str]] = mapped_column(String(32))
    mail_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    items: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # [{id,name,qty,unitTL}]
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
