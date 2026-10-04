"""Sabah brifingi — her gün 08:00 (Türkiye) WhatsApp'a ajanda + süreler + açık işler.

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
from app.services import jarvis
from app.services import jarvis_tools as tools
from app.services.whatsapp_client import whatsapp_client
from app.timeutil import now_tr, today_tr

logger = logging.getLogger(__name__)

KIND = "morning"
# Bu saatten önce ya da sonra gelen OTOMATİK tetik gönderim yapmaz (elle gönderim serbest).
WINDOW_START = time(7, 55)
WINDOW_END = time(12, 0)
WA_LIMIT = 4096

BRIEF_SYSTEM = """Sen JARVIS'sin ve Mustafa Göksoy'a sabah brifingini yazıyorsun. Metin WhatsApp'ta okunacak.
Sana bugünün verisi JSON olarak verilecek. Yalnız bu veriye dayan; veride olmayan hiçbir şeyi ekleme.

Biçim:
- İlk satır: "Günaydın — <gün ay, haftanın günü>".
- Sonra en önemli şeyler önce: tarihi geçmiş süreler (⚠ ile), bugünkü ve önümüzdeki 7 gündeki süreler, duruşmalar, yeni lead'ler, dikkat bekleyen WhatsApp konuşmaları.
- Kısa maddeler; tablo ve başlık yok. Tarihleri "6 Eki Pzt (2 gün)" gibi yaz.
- Boş bölümü tek satırla geç ("Önümüzdeki 7 günde duruşma yok" gibi). Lead verisi boşsa "lead yok" deme: Gespa OS'te kayıtlı lead olmadığını ve diğer sitelerin bağlı olmadığını söyle.
- Hak düşürücü süre varsa en sonda tek satır: süre tarihleri tahminidir, resmî/adli tatil hesaba katılmaz.
- En çok 1500 karakter."""

_AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
_GUN = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def _d(v) -> str:
    return f"{v.day} {_AY[v.month - 1]} {_GUN[v.weekday()]}"


def collect(db: Session) -> dict:
    """Brifing verisi — JARVIS araçlarıyla AYNI kaynak (sayılar birbirini tutar)."""
    today = today_tr()
    until = today + timedelta(days=7)
    return {
        "today": today,
        "until": until,
        "agenda": tools.get_agenda(db, {"start_date": str(today), "end_date": str(until)}),
        "matters": tools.list_matters(db, {"status": "open"}),
        "new_leads": tools.list_leads(db, {"status": "new", "since_days": 7}),
        "inbox": tools.inbox_summary(db, {}),
    }


def counts(data: dict) -> dict:
    a = data["agenda"]
    today = data["today"]
    dl = a["deadlines"]
    return {
        "overdue": len([d for d in dl if d["due_date"] < today]),
        "today": len([d for d in dl if d["due_date"] == today]),
        "upcoming": len([d for d in dl if d["due_date"] > today]),
        "hearings": len(a["hearings"]),
        "open_matters": data["matters"]["count"],
        "new_leads": data["new_leads"]["count"],
        "lead_table_total": data["new_leads"]["data_source"]["table_total"],
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
    parts = []
    if c["overdue"]:
        parts.append(f"{c['overdue']} süre geçti")
    if c["today"]:
        parts.append(f"bugün {c['today']} süre doluyor")
    if c["upcoming"]:
        parts.append(f"7 gün içinde {c['upcoming']} süre")
    if c["hearings"]:
        parts.append(f"{c['hearings']} duruşma")
    if c["new_leads"]:
        parts.append(f"{c['new_leads']} yeni lead")
    if c["attention"]:
        parts.append(f"{c['attention']} WhatsApp konuşması dikkat bekliyor")
    line = ", ".join(parts) + "." if parts else "önümüzdeki 7 gün için kayıtlı süre ve duruşma yok."
    return _clean_param(line, 300)


def date_label(data: dict) -> str:
    """Şablondaki {{1}} — "4 Eki Cmt"."""
    return _clean_param(_d(data["today"]), 40)


def plain_text(data: dict) -> str:
    """Model olmadan da gönderilebilen, veriden kurulan tam brifing."""
    today = data["today"]
    a = data["agenda"]
    c = counts(data)
    lines = [f"Günaydın — {_d(today)}", ""]
    dl = a["deadlines"]
    if dl:
        lines.append("Süreler:")
        for d in dl:
            left = d["days_left"]
            when = f"{abs(left)} gün geçti" if left < 0 else ("bugün" if left == 0 else f"{left} gün")
            mark = "⚠ " if left < 0 else ""
            lines.append(f"• {mark}{d['title']} — {_d(d['due_date'])} ({when})")
    else:
        lines.append("Önümüzdeki 7 günde açık süre yok.")
    if a["hearings"]:
        lines.append("Duruşmalar:")
        for h in a["hearings"]:
            lines.append(f"• {h['title']} — {_d(h['date'])} ({h['days_left']} gün)")
    else:
        lines.append("Önümüzdeki 7 günde duruşma yok.")
    lines.append(f"Açık hukuk dosyası: {c['open_matters']}")
    if c["new_leads"]:
        lines.append(f"Son 7 günde yeni lead: {c['new_leads']}")
    elif c["lead_table_total"] == 0:
        lines.append("Gespa OS'te kayıtlı lead yok (diğer sitelerin başvuruları bağlı değil).")
    else:
        lines.append("Son 7 günde Gespa OS'e yeni lead girilmedi.")
    if c["attention"]:
        lines.append(f"Dikkat bekleyen WhatsApp konuşması: {c['attention']}")
    if dl:
        lines += ["", "Süre tarihleri tahminidir; resmî/adli tatil hesaba katılmaz."]
    return "\n".join(lines)


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
