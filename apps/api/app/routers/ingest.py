"""Sitelerden gelen sipariş defteri kayıtları — `POST /api/ingest/orders`.

Oturum değil `X-Ingest-Token` ister (ORDER_INGEST_TOKEN, ≥32 karakter; sitedeki
OS_INGEST_TOKEN ile aynı). Tanımlı değilse 503. Kayıt (site, ref) ile güncellenir
(idempotent: aynı kayıt tekrar gelirse yalnız alanlar tazelenir). İzin listesi
dışındaki alanlar ATILIR — bir site yanlışlıkla kişisel veri gönderse bile
tabloya girmez.
"""
import hmac
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models_orders import SiteOrder

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

SITES = {"gespaenerji"}
STATUSES = {"pending", "paid", "failed"}


class OrderItem(BaseModel):
    model_config = {"extra": "ignore"}
    id: Optional[str] = Field(default=None, max_length=64)
    name: Optional[str] = Field(default=None, max_length=200)
    qty: Optional[float] = None
    unitTL: Optional[float] = None


class OrderIn(BaseModel):
    model_config = {"extra": "ignore"}  # izin listesi dışı alan (ör. buyer) atılır
    ref: str = Field(min_length=1, max_length=64)
    channel: Optional[str] = Field(default=None, max_length=16)
    status: Optional[str] = Field(default=None, max_length=16)
    createdAt: Optional[str] = None
    resolvedAt: Optional[str] = None
    totalTL: Optional[float] = None
    paidTL: Optional[float] = None
    desc: Optional[str] = Field(default=None, max_length=300)
    taksit: Optional[int] = None
    errorCode: Optional[str] = Field(default=None, max_length=32)
    mailFailed: bool = False
    items: list[OrderItem] = Field(default_factory=list, max_length=100)


class IngestIn(BaseModel):
    site: str
    orders: list[OrderIn] = Field(max_length=100)


def _utc(v: Optional[str]) -> Optional[datetime]:
    """ISO → saat dilimsiz UTC (tablo UTC tutar)."""
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


@router.post("/orders")
def ingest_orders(data: IngestIn, x_ingest_token: Optional[str] = Header(default=None),
                  db: Session = Depends(get_db)):
    expected = settings.order_ingest_token
    if len(expected) < 32:
        raise HTTPException(503, "ORDER_INGEST_TOKEN tanımlı değil")
    if not x_ingest_token or not hmac.compare_digest(x_ingest_token.encode(), expected.encode()):
        raise HTTPException(403, "Geçersiz belirteç")
    if data.site not in SITES:
        raise HTTPException(400, "Bilinmeyen site")
    n = 0
    for o in data.orders:
        row = db.query(SiteOrder).filter(SiteOrder.site == data.site, SiteOrder.ref == o.ref).first()
        if row is None:
            row = SiteOrder(site=data.site, ref=o.ref)
            db.add(row)
        row.channel = o.channel
        row.status = o.status if o.status in STATUSES else (o.status or None)
        row.created_at = _utc(o.createdAt) or row.created_at
        row.resolved_at = _utc(o.resolvedAt)
        row.total_tl, row.paid_tl = o.totalTL, o.paidTL
        row.description, row.taksit, row.error_code = o.desc, o.taksit, o.errorCode
        row.mail_failed = o.mailFailed
        row.items = [i.model_dump() for i in o.items]
        row.updated_at = datetime.utcnow()
        n += 1
    db.commit()
    return {"ok": True, "upserted": n}
