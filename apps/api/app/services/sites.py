"""Mustafa'nın siteleri için okuma katmanı ("Siteler" ekranı, JARVIS, brifing).

Ticari: gespaenerji.com, gesmarketim.com · başvuru: tarifesec.net.tr,
internetbasvuru.com (yalnız defter) · içerik: cezarehberi.com.
Her site salt okunur `GET /api/os/summary` ucunu yayınlar (`X-OS-Token`).
JARVIS araçları, ana sayfa kartları ve sabah brifingi bu modül üzerinden okur;
siteye başka bir yoldan (veritabanı, yönetici şifresi) bağlanılmaz.

Ayarlar: GESPA_SITE_URL + GESPA_OS_TOKEN, GESM_SITE_URL + GESM_OS_TOKEN,
TARIFESEC_SITE_URL + TARIFESEC_OS_TOKEN, CEZA_SITE_URL + CEZA_OS_TOKEN.
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

# Sipariş almayan siteler: başvuru (tarifesec) ve içerik (cezarehberi).
OTHER_SITES = {
    "tarifesec": {"label": "tarifesec.net.tr", "url": "tarifesec_site_url", "token": "tarifesec_os_token"},
    "cezarehberi": {"label": "cezarehberi.com", "url": "ceza_site_url", "token": "ceza_os_token"},
}
ALL_SITES = {**SITES, **OTHER_SITES}
# Özet ucu olmayan, yalnız başvuru defterine yazan siteler.
LEDGER_ONLY = {"internetbasvuru": {"label": "internetbasvuru.com", "url": "https://www.internetbasvuru.com"}}
KIND = {"gespaenerji": "shop", "gesmarketim": "shop", "tarifesec": "leads",
        "internetbasvuru": "leads", "cezarehberi": "content"}
# "Siteler" ekranındaki sıra
ORDER = ["gespaenerji", "gesmarketim", "tarifesec", "internetbasvuru", "cezarehberi"]

_cache: dict[str, tuple[float, dict]] = {}


def _conf(site: str) -> tuple[str, str]:
    s = ALL_SITES[site]
    return getattr(settings, s["url"]).rstrip("/"), getattr(settings, s["token"])


def configured(site: str) -> bool:
    url, token = _conf(site)
    return bool(url and token)


def fetch_summary(site: str, *, client: Optional[httpx.Client] = None, fresh: bool = False) -> dict:
    """Sitenin özetini döndürür. Hata durumunda {"error": "..."} — istisna atmaz."""
    if site not in ALL_SITES:
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
    base = {"site": site, "label": ALL_SITES[site]["label"], "kind": KIND[site], "url": _conf(site)[0]}
    if site == "tarifesec" and "error" not in data:
        return {**base, **_tarifesec_card(data)}
    if site == "cezarehberi" and "error" not in data:
        return {**base, **_ceza_card(data)}
    if "error" in data:
        out = {**base, "ok": False, "error": data["error"]}
        if data.get("configured") is False:
            out["configured"] = False
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


def _tarifesec_card(data: dict) -> dict:
    leads, prices, scraper = data.get("leads", {}), data.get("prices", {}), data.get("scraper", {})
    visitors = data.get("visitors", {})
    err = scraper.get("lastError")
    return {
        "ok": True,
        "leads_30d": leads.get("count", 0),
        "leads_24h": _last_24h(leads.get("items", []), "createdAt"),
        "leads_uncontacted": leads.get("uncontacted", 0),
        "price_pending": prices.get("pendingApproval", 0),
        "price_stale": prices.get("stale", 0),
        "packages": prices.get("packages", 0),
        "scraper_last_run": scraper.get("lastRunAt"),
        "scraper_error": ({"operator": err.get("operator"), "at": err.get("at"),
                           "message": err.get("message")} if err else None),
        "visitors_today": visitors.get("today"),
        "visitors_total": visitors.get("total"),
        "alerts": (leads.get("uncontacted", 0) or 0) + (prices.get("pendingApproval", 0) or 0)
                  + (1 if prices.get("stale") else 0),
    }


def _ceza_card(data: dict) -> dict:
    visitors, messages = data.get("visitors", {}), data.get("messages", {})
    articles, bots = data.get("articles", {}), data.get("bots", {})
    return {
        "ok": True,
        "visitors_today": visitors.get("today"),
        "views_today": visitors.get("todayViews"),
        "visitors_total": visitors.get("total"),
        "visitors_7d": sum(d.get("unique", 0) or 0 for d in visitors.get("last7", [])),
        "messages_unread": messages.get("unread", 0),
        "articles_published": articles.get("published", 0),
        "articles_drafts": articles.get("drafts", 0),
        "top_articles": articles.get("top", [])[:5],
        "petitions_7d": data.get("petitions", {}).get("last7", 0),
        "bot_hits_7d": sum(b.get("count", 0) or 0 for b in bots.get("top", [])),
        "alerts": messages.get("unread", 0) or 0,
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
LEDGER_SITES = {"gespaenerji", "gesmarketim"}


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
        # gesmarketim kartının beklediği sayılar (özetle aynı adlar)
        "unpaid": sum(1 for r in rows if r.status != "paid"),
        "open": sum(1 for r in rows if not r.fulfilled),
        "items": [{
            "ref": r.ref, "channel": r.channel, "status": r.status,
            "createdAt": (r.created_at.isoformat() + "Z") if r.created_at else None,
            "resolvedAt": (r.resolved_at.isoformat() + "Z") if r.resolved_at else None,
            "totalTL": r.total_tl, "paidTL": r.paid_tl, "desc": r.description,
            "taksit": r.taksit, "errorCode": r.error_code, "mailFailed": r.mail_failed,
            "fulfilled": r.fulfilled, "items": r.items or [],
        } for r in rows[:50]],
    }


def summary_with_ledger(db, site: str, **kw) -> dict:
    """Sitenin özeti; defter açıksa `orders` defterden gelir (özet alınamasa da)."""
    data = fetch_summary(site, **kw)
    if db is None or not ledger_enabled(site):
        return data
    from app.models_orders import SiteOrder
    # Site henüz deftere hiç yazmadıysa (güncellenmemiş site) özetteki siparişler kalır.
    if "orders" in data and db.query(SiteOrder.id).filter(SiteOrder.site == site).first() is None:
        return data
    return {**data, "orders": ledger_orders(db, site)}


# ── Başvuru defteri (internetbasvuru.com) ───────────────────

def applications(db, site: str = "internetbasvuru", days: int = 30) -> dict:
    """Başvuru defterinden kişisel verisiz başvurular (yeni → eski)."""
    from datetime import datetime, timedelta
    from app.models_orders import SiteApplication
    since = datetime.utcnow() - timedelta(days=days)
    rows = (db.query(SiteApplication)
            .filter(SiteApplication.site == site, SiteApplication.created_at >= since)
            .order_by(SiteApplication.created_at.desc()).all())

    def top(attr: str) -> list:
        c: dict = {}
        for r in rows:
            k = getattr(r, attr) or "belirtilmemiş"
            c[k] = c.get(k, 0) + 1
        return [{"name": k, "count": v} for k, v in sorted(c.items(), key=lambda x: -x[1])[:5]]

    return {
        "days": days, "count": len(rows), "source": "ledger",
        "last_24h": sum(1 for r in rows if r.created_at >= datetime.utcnow() - timedelta(hours=24)),
        "last_7d": sum(1 for r in rows if r.created_at >= datetime.utcnow() - timedelta(days=7)),
        "covered": sum(1 for r in rows if r.covered),
        "not_covered": sum(1 for r in rows if r.covered is False),
        "by_city": top("city"), "by_package": top("package"), "by_source": top("source"),
        "items": [{
            "ref": r.ref, "createdAt": r.created_at.isoformat() + "Z", "city": r.city,
            "district": r.district, "package": r.package, "monthlyTL": r.monthly_tl,
            "source": r.source, "coverage": r.coverage, "covered": r.covered,
        } for r in rows[:50]],
    }


def ledger_card(db, site: str) -> dict:
    base = {"site": site, "label": LEDGER_ONLY[site]["label"], "kind": KIND[site],
            "url": LEDGER_ONLY[site]["url"]}
    if len(settings.order_ingest_token) < 32:
        return {**base, "ok": False, "configured": False,
                "error": "başvuru defteri kapalı (ORDER_INGEST_TOKEN tanımlı değil)"}
    a = applications(db, site)
    return {**base, "ok": True, "leads_30d": a["count"], "leads_24h": a["last_24h"],
            "leads_7d": a["last_7d"], "covered": a["covered"], "not_covered": a["not_covered"],
            "by_city": a["by_city"], "by_package": a["by_package"], "alerts": 0,
            "note": "Yalnız sayılar: ad ve telefon başvuru panelinde ve Telegram bildiriminde."}


def all_cards(db, *, fresh: bool = False) -> list[dict]:
    """Beş sitenin kartı, ORDER sırasıyla. Uyuyan servisler yüzünden özetler
    PARALEL çekilir; veritabanı yalnız bu iş parçacığında kullanılır."""
    from concurrent.futures import ThreadPoolExecutor
    names = [s for s in ORDER if s in ALL_SITES]
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        list(pool.map(lambda s: fetch_summary(s, fresh=fresh), names))  # önbelleği ısıtır
    out = []
    for s in ORDER:
        if s in LEDGER_ONLY:
            out.append(ledger_card(db, s))
        else:
            c = card(s, summary_with_ledger(db, s) if s in SITES else fetch_summary(s))
            c.setdefault("kind", KIND[s])
            out.append(c)
    return out
