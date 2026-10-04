"""İki ticari site — gespaenerji.com ve gesmarketim.com — için okuma katmanı.

Her site salt okunur `GET /api/os/summary` ucunu yayınlar (`X-OS-Token`).
JARVIS araçları, ana sayfa kartları ve sabah brifingi bu modül üzerinden okur;
siteye başka bir yoldan (veritabanı, yönetici şifresi) bağlanılmaz.

Ayarlar: GESPA_SITE_URL + GESPA_OS_TOKEN, GESM_SITE_URL + GESM_OS_TOKEN.
Token sitedeki OS_TOKEN ile AYNI değerdir. Yanıt 60 sn önbelleklenir; site
ulaşılamazsa hata sözlüğü döner, çağıran tarafı çökertmez.
"""
import logging
import time
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60
TIMEOUT = 20.0  # uyuyan servis ilk istekte birkaç saniyede uyanır

SITES = {
    "gespaenerji": {"label": "gespaenerji.com", "url": "gespa_site_url", "token": "gespa_os_token"},
    "gesmarketim": {"label": "gesmarketim.com", "url": "gesm_site_url", "token": "gesm_os_token"},
}

_cache: dict[str, tuple[float, dict]] = {}


def _conf(site: str) -> tuple[str, str]:
    s = SITES[site]
    return getattr(settings, s["url"]).rstrip("/"), getattr(settings, s["token"])


def configured(site: str) -> bool:
    url, token = _conf(site)
    return bool(url and token)


def fetch_summary(site: str, *, client: Optional[httpx.Client] = None, fresh: bool = False) -> dict:
    """Sitenin özetini döndürür. Hata durumunda {"error": "..."} — istisna atmaz."""
    if site not in SITES:
        return {"error": f"bilinmeyen site: {site}"}
    if not configured(site):
        return {"error": "bağlantı ayarlı değil (site adresi ve OS belirteci)", "configured": False}
    hit = _cache.get(site)
    if hit and not fresh and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    url, token = _conf(site)
    started = time.monotonic()
    try:
        c = client or httpx.Client(timeout=TIMEOUT)
        try:
            r = c.get(f"{url}/api/os/summary", headers={"X-OS-Token": token})
        finally:
            if client is None:
                c.close()
    except httpx.HTTPError as e:
        logger.warning("%s özeti alınamadı: %s", site, e)
        return {"error": f"siteye ulaşılamadı ({type(e).__name__})"}
    if r.status_code != 200:
        msg = {403: "belirteç reddedildi (OS_TOKEN eşleşmiyor)",
               503: "sitede OS_TOKEN tanımlı değil",
               404: "sitede /api/os/summary yok (site güncellenmemiş)"}.get(r.status_code, f"HTTP {r.status_code}")
        return {"error": msg, "status": r.status_code}
    try:
        data = r.json()
    except ValueError:
        return {"error": "geçersiz yanıt"}
    data["_fetched_ms"] = int((time.monotonic() - started) * 1000)
    _cache[site] = (time.monotonic(), data)
    return data


def clear_cache():
    _cache.clear()


def card(site: str, data: dict) -> dict:
    """Ana sayfa kartı ve brifing için kısa özet (her iki sitede aynı alanlar)."""
    base = {"site": site, "label": SITES[site]["label"]}
    if "error" in data:
        out = {**base, "ok": False, "error": data["error"]}
        if "orders" in data:  # defter: özet alınamasa da siparişler görünür
            o = data["orders"]
            out.update(orders_30d=o.get("count", 0),
                       orders_24h=_last_24h(o.get("items", []), "createdAt"),
                       orders_source=o.get("source"))
        return out
    if site == "gespaenerji":
        orders = data.get("orders", {})
        by = orders.get("byStatus", {})
        alerts = data.get("catalog", {}).get("alerts", [])
        return {
            **base, "ok": True,
            "orders_30d": orders.get("count", 0),
            "orders_paid_30d": by.get("paid", 0),
            "orders_pending_30d": by.get("pending", 0),
            "orders_24h": _last_24h(orders.get("items", []), "createdAt"),
            "orders_source": orders.get("source", "summary"),
            "mail_failed_30d": orders.get("mailFailed", 0),
            "qa_pending": data.get("qa", {}).get("pending", 0),
            "alerts": len(alerts),
            "alert_items": alerts[:10],
            "visitors_24h": data.get("visitors", {}).get("day"),
            "usd_try": data.get("fx", {}).get("rate"),
            "data_persistent": data.get("dataPersistent"),
        }
    orders = data.get("orders", {})
    cat = data.get("catalog", {})
    return {
        **base, "ok": True,
        "orders_30d": orders.get("count", 0),
        "orders_unpaid_30d": orders.get("unpaid", 0),
        "orders_open_30d": orders.get("open", 0),
        "orders_24h": _last_24h(orders.get("items", []), "createdAt"),
        "out_of_stock": len(cat.get("outOfStock", [])),
        "no_image": len(cat.get("noImage", [])),
        "alerts": len(cat.get("outOfStock", [])) + len(cat.get("noImage", [])),
        "visitors_total": data.get("visitors", {}).get("count"),
        "usd_try": data.get("kur", {}).get("usdTry"),
    }


def _last_24h(items: list, key: str) -> int:
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    n = 0
    for it in items:
        try:
            if datetime.fromisoformat(str(it.get(key, "")).replace("Z", "+00:00")) >= since:
                n += 1
        except ValueError:
            continue
    return n


# ── Sipariş defteri (Gespa OS Postgres) ─────────────────────
# gespaenerji siparişleri defter açıksa (ORDER_INGEST_TOKEN) sitenin özetinden
# DEĞİL buradan okunur: site dosyası dağıtımda silinir, defter kalır; site
# uyusa ya da özet alınamasa da siparişler görünür.
LEDGER_SITES = {"gespaenerji"}


def ledger_enabled(site: str) -> bool:
    return site in LEDGER_SITES and len(settings.order_ingest_token) >= 32


def ledger_orders(db, site: str, days: int = 30) -> dict:
    """Defterden, sitenin özetindeki `orders` ile AYNI biçim."""
    from datetime import datetime, timedelta
    from app.models_orders import SiteOrder
    since = datetime.utcnow() - timedelta(days=days)
    rows = (db.query(SiteOrder)
            .filter(SiteOrder.site == site, SiteOrder.created_at >= since)
            .order_by(SiteOrder.created_at.desc()).all())
    by: dict = {}
    for r in rows:
        by[r.status or "?"] = by.get(r.status or "?", 0) + 1
    return {
        "days": days, "count": len(rows), "byStatus": by, "source": "ledger",
        "mailFailed": sum(1 for r in rows if r.mail_failed),
        "items": [{
            "ref": r.ref, "channel": r.channel, "status": r.status,
            "createdAt": (r.created_at.isoformat() + "Z") if r.created_at else None,
            "resolvedAt": (r.resolved_at.isoformat() + "Z") if r.resolved_at else None,
            "totalTL": r.total_tl, "paidTL": r.paid_tl, "desc": r.description,
            "taksit": r.taksit, "errorCode": r.error_code, "mailFailed": r.mail_failed,
            "items": r.items or [],
        } for r in rows[:50]],
    }


def summary_with_ledger(db, site: str, **kw) -> dict:
    """Sitenin özeti; defter açıksa `orders` defterden gelir (özet alınamasa da)."""
    data = fetch_summary(site, **kw)
    if db is None or not ledger_enabled(site):
        return data
    return {**data, "orders": ledger_orders(db, site)}
