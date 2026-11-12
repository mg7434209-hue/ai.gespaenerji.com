"""Sitelerden gelen defter kayıtları — `POST /api/ingest/orders` ve `/applications`.

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
from app.models_orders import SiteApplication, SiteOrder

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

SITES = {"gespaenerji", "gesmarketim"}
APPLICATION_SITES = {"internetbasvuru"}
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
    fulfilled: Optional[bool] = None
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


def _check_token(given: Optional[str]):
    expected = settings.order_ingest_token
    if len(expected) < 32:
        raise HTTPException(503, "ORDER_INGEST_TOKEN tanımlı değil")
    if not given or not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(403, "Geçersiz belirteç")


@router.post("/orders")
def ingest_orders(data: IngestIn, x_ingest_token: Optional[str] = Header(default=None),
                  db: Session = Depends(get_db)):
    _check_token(x_ingest_token)
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
        row.fulfilled = o.fulfilled
        row.items = [i.model_dump() for i in o.items]
        row.updated_at = datetime.utcnow()
        n += 1
    db.commit()
    return {"ok": True, "upserted": n}


# ── Başvuru defteri ──────────────────────────────────────────

class ApplicationIn(BaseModel):
    model_config = {"extra": "ignore"}  # ad, telefon, adres gelse de atılır
    ref: str = Field(min_length=1, max_length=64)
    createdAt: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=60)
    district: Optional[str] = Field(default=None, max_length=60)
    package: Optional[str] = Field(default=None, max_length=120)
    monthlyTL: Optional[float] = None
    source: Optional[str] = Field(default=None, max_length=60)
    coverage: Optional[str] = Field(default=None, max_length=40)
    covered: Optional[bool] = None


class ApplicationsIn(BaseModel):
    site: str
    applications: list[ApplicationIn] = Field(max_length=100)


@router.post("/applications")
def ingest_applications(data: ApplicationsIn, x_ingest_token: Optional[str] = Header(default=None),
                        db: Session = Depends(get_db)):
    """Başvuru sitelerinden kişisel verisiz başvuru özeti. (site, ref) tekildir."""
    _check_token(x_ingest_token)
    if data.site not in APPLICATION_SITES:
        raise HTTPException(400, "Bilinmeyen site")
    n = 0
    for a in data.applications:
        row = (db.query(SiteApplication)
               .filter(SiteApplication.site == data.site, SiteApplication.ref == a.ref).first())
        if row is None:
            row = SiteApplication(site=data.site, ref=a.ref, created_at=_utc(a.createdAt) or datetime.utcnow())
            db.add(row)
        row.city, row.district, row.package = a.city, a.district, a.package
        row.monthly_tl, row.source, row.coverage, row.covered = a.monthlyTL, a.source, a.coverage, a.covered
        n += 1
    db.commit()
    return {"ok": True, "upserted": n}
