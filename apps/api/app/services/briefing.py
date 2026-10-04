"""Sabah brifingi — her gün 08:00 (Türkiye) WhatsApp'a ajanda + süreler + açık işler.

Odak: gespaenerji.com ve gesmarketim.com (siparişler, soru-cevap, ürün
uyarıları); hukuk yalnız gecikmiş/bugün dolan süre varsa tek satır.

Tetik: GitHub Actions (`.github/workflows/sabah-brifingi.yml`) 07:50'de başlar,
08:00'i bekler ve `POST /api/jarvis/briefing/run` çağırır; 08:30'da yedek
tetik vardır. Uygulama uyku modunda olsa da istek onu uyandırır; uygulama
içinde zamanlayıcı YOKTUR (uyuyan süreçte çalışmazdı).

Akış:
1. `collect()` veriyi JARVIS'in salt okunur araçlarıyla toplar (tek kaynak).
2. `compose()` tam metni JARVIS_BRIEF_MODEL (Sonnet 5.5) ile yazar; model
   yoksa ya da hata verirse `plain_text()` ile veriden düz metin kurulur.
   Şablon satırı (`summary_line`) HER ZAMAN veriden kurulur — model yazmaz.
3. `run_morning()` günde bir kez gönderir (`JarvisRun` (tür, gün) tekil):
   sahibin son 24 saatte yazdığı varsa (WhatsApp hizmet penceresi açık) tam
   metin serbest mesajla, yoksa onaylı utility şablonuyla (kısa satır +
   "Brifingi gönder" düğmesi). Düğmeye basılınca pencere açılır ve
   `send_full_to_owner()` tam metni yollar.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, time, timedelta
from typing import Optional

import anthropic
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models_jarvis import JarvisRun
from app.models_whatsapp import WhatsAppConversation, WhatsAppMessage
from app.services import jarvis, sites
from app.services import jarvis_tools as tools
from app.services.whatsapp_client import whatsapp_client
from app.timeutil import day_label, now_tr, today_tr

logger = logging.getLogger(__name__)

KIND = "morning"
# Bu saatten önce ya da sonra gelen OTOMATİK tetik gönderim yapmaz (elle gönderim serbest).
WINDOW_START = time(7, 55)
WINDOW_END = time(12, 0)
WA_LIMIT = 4096

BRIEF_SYSTEM = """Sen JARVIS'sin ve Mustafa Göksoy'a sabah brifingini yazıyorsun. Metin WhatsApp'ta okunacak.
Sana bugünün verisi JSON olarak verilecek. Yalnız bu veriye dayan; veride olmayan hiçbir şeyi ekleme.

Odak iki ticari site: gespaenerji.com ve gesmarketim.com.
Biçim:
- İlk satır: "Günaydın — <gün ay, haftanın günü>".
- Her site için kısa bir bölüm: son 24 saatteki siparişler (varsa tutar ve ürün), ödenmemiş/bekleyen siparişler, onay bekleyen soru-cevaplar, ürün uyarıları (stok, fiyat, görsel, kampanya).
- Bir sitenin verisi alınamadıysa (error) bunu tek satırla söyle; "sipariş yok" deme.
- Sonra varsa: dikkat bekleyen WhatsApp konuşmaları.
- Hukuk yalnız "legal" bölümünde gecikmiş ya da bugün dolan süre varsa tek satır (⚠ ile); yoksa hiç anma.
- Kısa maddeler; tablo ve başlık yok. En çok 1500 karakter."""

def collect(db: Session) -> dict:
    """Brifing verisi — JARVIS araçlarıyla AYNI kaynak (sayılar birbirini tutar).
    Siteler TAZE okunur (önbellek atlanır)."""
    today = today_tr()
    agenda = tools.get_agenda(db, {"start_date": str(today), "end_date": str(today)})
    return {
        "today": today,
        "sites": [sites.card(s, sites.fetch_summary(s, fresh=True)) for s in sites.SITES],
        # Hukuk ikinci planda: yalnız gecikmiş ve bugün dolan süreler
        "legal": [d for d in agenda["deadlines"] if d["due_date"] <= today],
        "inbox": tools.inbox_summary(db, {}),
    }


def counts(data: dict) -> dict:
    by = {c["site"]: c for c in data["sites"]}
    g, m = by.get("gespaenerji", {}), by.get("gesmarketim", {})
    today = data["today"]
    return {
        "gespa_ok": g.get("ok", False), "gesm_ok": m.get("ok", False),
        "gespa_orders_24h": g.get("orders_24h", 0), "gesm_orders_24h": m.get("orders_24h", 0),
        "gespa_pending": g.get("orders_pending_30d", 0), "gesm_unpaid": m.get("orders_unpaid_30d", 0),
        "qa_pending": g.get("qa_pending", 0),
        "gespa_alerts": g.get("alerts", 0), "gesm_out_of_stock": m.get("out_of_stock", 0),
        "legal_overdue": len([d for d in data["legal"] if d["due_date"] < today]),
        "legal_today": len([d for d in data["legal"] if d["due_date"] == today]),
        "attention": data["inbox"]["needs_attention_count"],
    }


def _clean_param(s: str, limit: int) -> str:
    """Meta şablon değişkeni: satır sonu/sekme yok, 4+ boşluk yok."""
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r" {2,}", " ", s).strip()
    return s[:limit]


def summary_line(data: dict) -> str:
    """Şablondaki {{2}} — veriden, tek satır."""
    c = counts(data)
    if c["gespa_ok"]:
        g = [f"{c['gespa_orders_24h']} yeni sipariş"]
        if c["gespa_pending"]:
            g.append(f"{c['gespa_pending']} bekleyen ödeme")
        if c["qa_pending"]:
            g.append(f"{c['qa_pending']} soru onay bekliyor")
        if c["gespa_alerts"]:
            g.append(f"{c['gespa_alerts']} ürün uyarısı")
        gs = "gespaenerji: " + ", ".join(g)
    else:
        gs = "gespaenerji: veri alınamadı"
    if c["gesm_ok"]:
        m = [f"{c['gesm_orders_24h']} yeni sipariş"]
        if c["gesm_unpaid"]:
            m.append(f"{c['gesm_unpaid']} ödenmemiş")
        if c["gesm_out_of_stock"]:
            m.append(f"{c['gesm_out_of_stock']} ürün stokta yok")
        ms = "gesmarketim: " + ", ".join(m)
    else:
        ms = "gesmarketim: veri alınamadı"
    parts = [gs, ms]
    if c["legal_overdue"] or c["legal_today"]:
        parts.append(f"hukuk: {c['legal_overdue'] + c['legal_today']} süre")
    return _clean_param("; ".join(parts) + ".", 300)


def date_label(data: dict) -> str:
    """Şablondaki {{1}} — "4 Eki Cmt"."""
    return _clean_param(day_label(data["today"]), 40)


def plain_text(data: dict) -> str:
    """Model olmadan da gönderilebilen, veriden kurulan tam brifing."""
    c = counts(data)
    lines = [f"Günaydın — {day_label(data['today'])}"]
    for card in data["sites"]:
        lines += ["", card["label"] + ":"]
        if not card.get("ok"):
            lines.append(f"• veri alınamadı ({card.get('error', '?')})")
            continue
        lines.append(f"• son 24 saatte {card['orders_24h']} sipariş · 30 günde {card['orders_30d']}")
        if card["site"] == "gespaenerji":
            if card["orders_pending_30d"]:
                lines.append(f"• ödemesi tamamlanmamış: {card['orders_pending_30d']}")
            if card["qa_pending"]:
                lines.append(f"• onay bekleyen soru-cevap: {card['qa_pending']}")
            for a in card.get("alert_items", [])[:5]:
                lines.append(f"• ⚠ {_alert_text(a)}")
        else:
            if card["orders_unpaid_30d"]:
                lines.append(f"• ödenmemiş sipariş: {card['orders_unpaid_30d']}")
            if card["out_of_stock"]:
                lines.append(f"• stokta olmayan ürün: {card['out_of_stock']}")
            if card["no_image"]:
                lines.append(f"• görseli olmayan ürün: {card['no_image']}")
    if c["attention"]:
        lines += ["", f"Dikkat bekleyen WhatsApp konuşması: {c['attention']}"]
    if data["legal"]:
        names = ", ".join(d["title"] for d in data["legal"][:3])
        lines += ["", f"⚠ Hukuk: {len(data['legal'])} süre geçti/bugün doluyor ({names}). Tarihler tahminidir."]
    return "\n".join(lines)


_ALERT = {
    "no_price": "fiyatı yok", "no_image": "görseli yok", "low_stock": "stok azaldı",
    "out_of_stock": "tükendi", "campaign_ending": "kampanya bitiyor",
    "old_price_without_campaign": "kampanya bitti, eski fiyat (oldPrice) duruyor",
}


def _alert_text(a: dict) -> str:
    what = _ALERT.get(a.get("type"), a.get("type", "uyarı"))
    if a.get("type") == "low_stock":
        what += f" ({a.get('stock')} adet)"
    if a.get("type") == "campaign_ending":
        return f"Kampanya bitiyor: {a.get('endsAt')}"
    return f"{a.get('name') or a.get('id')}: {what}"


def compose(data: dict, client: Optional[anthropic.Anthropic] = None) -> str:
    """Tam metin: JARVIS_BRIEF_MODEL; olmazsa düz metin."""
    if client is None:
        if not jarvis.is_configured():
            return plain_text(data)
        client = jarvis.get_client()
    payload = json.dumps(data, ensure_ascii=False, default=str)
    extra = ({"betas": [jarvis.FALLBACK_BETA], "fallbacks": "default"}
             if settings.jarvis_fallbacks else {})
    try:
        resp = client.beta.messages.create(
            model=settings.jarvis_brief_model,
            max_tokens=4000,
            system=BRIEF_SYSTEM,
            messages=[{"role": "user", "content": f"Bugünün verisi:\n{payload}"}],
            output_config={"effort": "low"},
            **extra,
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        logger.error("Brifing modeli hata verdi, düz metne düşülüyor: %s", e)
        return plain_text(data)
    if resp.stop_reason == "refusal":
        return plain_text(data)
    text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
    return text[:WA_LIMIT] if text else plain_text(data)


def owner_phone() -> str:
    return re.sub(r"\D", "", settings.jarvis_owner_phone or "")


def owner_window_open(db: Session, now: Optional[datetime] = None) -> bool:
    """WhatsApp hizmet penceresi: sahip son 24 saatte bize yazdı mı?"""
    phone = owner_phone()
    if not phone:
        return False
    since = (now or datetime.utcnow()) - timedelta(hours=24)
    return db.query(WhatsAppMessage).join(WhatsAppConversation).filter(
        WhatsAppConversation.phone == phone,
        WhatsAppMessage.direction == "inbound",
        WhatsAppMessage.created_at >= since,
    ).first() is not None


def split_text(text: str, limit: int = WA_LIMIT) -> list[str]:
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # tek satır sınırı aşarsa
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:limit])
            line = line[limit:]
        cand = f"{cur}\n{line}" if cur else line
        if len(cand) > limit:
            parts.append(cur)
            cur = line
        else:
            cur = cand
    if cur:
        parts.append(cur)
    return parts


async def _send_text(text: str):
    for part in split_text(text):
        await whatsapp_client.send_text(to=owner_phone(), body=part)


async def _send_template(data: dict):
    components = [{"type": "body", "parameters": [
        {"type": "text", "text": date_label(data)},
        {"type": "text", "text": summary_line(data)},
    ]}]
    await whatsapp_client.send_template(
        to=owner_phone(), template_name=settings.brief_template_name,
        language=settings.brief_template_lang, components=components,
    )


def _claim(db: Session, day) -> Optional[JarvisRun]:
    """Günün kaydını al: yoksa oluştur, 'failed' ise yeniden dene; 'sent' ya da
    başka bir tetik şu an gönderiyorsa None."""
    try:
        run = JarvisRun(kind=KIND, day=day, status="sending")
        db.add(run)
        db.commit()
        return run
    except IntegrityError:
        db.rollback()
    n = (db.query(JarvisRun)
         .filter(JarvisRun.kind == KIND, JarvisRun.day == day, JarvisRun.status == "failed")
         .update({"status": "sending", "error": None}, synchronize_session=False))
    db.commit()
    if n != 1:
        return None
    return db.query(JarvisRun).filter(JarvisRun.kind == KIND, JarvisRun.day == day).one()


async def run_morning(db: Session, *, manual: bool = False,
                      client: Optional[anthropic.Anthropic] = None) -> dict:
    now = now_tr()
    if not manual and not (WINDOW_START <= now.time() <= WINDOW_END):
        return {"status": "skipped", "reason": "outside_window", "now": now.isoformat()}
    if not owner_phone():
        return {"status": "error", "reason": "JARVIS_OWNER_PHONE tanımlı değil"}
    if not whatsapp_client.is_configured():
        return {"status": "error", "reason": "WhatsApp API yapılandırılmamış"}

    day = now.date()
    run = _claim(db, day)
    if run is None:
        existing = db.query(JarvisRun).filter(JarvisRun.kind == KIND, JarvisRun.day == day).one()
        if not manual:
            return {"status": "skipped", "reason": f"already_{existing.status}"}
        run = existing  # elle gönderim: aynı günün kaydını yeniden kullan

    try:
        data = collect(db)
        run.summary = summary_line(data)
        run.text = await asyncio.to_thread(compose, data, client)
        db.commit()
        if owner_window_open(db):
            await _send_text(run.text)
            run.via = "text"
        else:
            await _send_template(data)
            run.via = "template"
        run.status = "sent"
        db.commit()
        return {"status": "sent", "via": run.via, "day": str(day)}
    except Exception as e:  # noqa: BLE001
        logger.exception("Sabah brifingi gönderilemedi")
        db.rollback()
        run.status = "failed"
        run.error = f"{type(e).__name__}: {e}"[:500]
        db.commit()
        return {"status": "failed", "error": run.error}


async def send_full_to_owner(db: Session, client: Optional[anthropic.Anthropic] = None) -> str:
    """Şablondaki düğmeye basılınca (pencere açık) bugünün tam metnini gönderir."""
    day = today_tr()
    run = db.query(JarvisRun).filter(JarvisRun.kind == KIND, JarvisRun.day == day).first()
    text = run.text if run and run.text else await asyncio.to_thread(compose, collect(db), client)
    await _send_text(text)
    return text
