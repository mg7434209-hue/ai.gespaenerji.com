"""Komuta ajanının (JARVIS) araçları — Faz 1: YALNIZ OKUMA.

Her araç veritabanından okur, hiçbir şey yazmaz. Yazma işleri (süre ekleme,
lead güncelleme…) Faz 2'de onay adımıyla gelir; buraya yazan araç EKLEME.

Araç tanımı (TOOLS) ile uygulaması (HANDLERS) aynı dosyadadır: yeni araç =
ikisine birer satır. Çıktılar kısa tutulur (model bağlamı için); tarih
hesapları Türkiye saatiyle (`today_tr`).
"""
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Lead, Workspace
from app.models_legal import LegalConsultation, LegalDeadline, LegalMatter
from app.models_whatsapp import WhatsAppConversation
from app.services import agenda as agenda_svc
from app.timeutil import today_tr

MAX_ROWS = 50

# Lead verisinin NEREDEN geldiği. Model "lead yok" ile "lead verisi bağlı
# değil"i karıştırmasın diye her lead çıktısına eklenir. Yeni kaynak
# bağlanınca (ör. tarifesec API'si) buradaki listeyi güncelle.
LEAD_SOURCE = {
    "reads": "Gespa OS'in kendi leads tablosu (Lead Yönetimi ekranından elle girilen kayıtlar)",
    "not_connected": [
        "internetbasvuru.com başvuruları",
        "tarifesec.net.tr başvuruları",
        "gespaenerji.com ve gesmarketim.com formları/siparişleri",
        "WhatsApp mesajları (gelen mesajdan otomatik lead açılmıyor)",
    ],
}


def _lead_source(db: Session) -> dict:
    return {**LEAD_SOURCE, "table_total": db.query(func.count(Lead.id)).scalar() or 0}


class ToolInputError(ValueError):
    """Modelin gönderdiği girdi geçersiz — is_error'lu tool_result olarak döner."""


# ── Girdi yardımcıları (strict şema kullanılmadığı için girdiyi biz doğrularız)

def _date(v: Any, field: str) -> Optional[date]:
    if v in (None, ""):
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        raise ToolInputError(f"{field} YYYY-AA-GG biçiminde olmalı: {v!r}")


def _int(v: Any, field: str, lo: int, hi: int, default: Optional[int] = None) -> Optional[int]:
    if v in (None, ""):
        return default
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ToolInputError(f"{field} tam sayı olmalı: {v!r}")
    if not lo <= n <= hi:
        raise ToolInputError(f"{field} {lo}..{hi} arasında olmalı: {n}")
    return n


def _choice(v: Any, field: str, allowed: set, default: Optional[str] = None) -> Optional[str]:
    if v in (None, ""):
        return default
    if v not in allowed:
        raise ToolInputError(f"{field} şunlardan biri olmalı: {sorted(allowed)}")
    return v


def _iso(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


# ── Araçlar ──────────────────────────────────────────────────

def get_agenda(db: Session, inp: dict) -> dict:
    today = today_tr()
    start = _date(inp.get("start_date"), "start_date") or today
    end = _date(inp.get("end_date"), "end_date") or (start + timedelta(days=7))
    if end < start:
        raise ToolInputError("end_date, start_date'ten önce olamaz")
    if (end - start).days > 366:
        raise ToolInputError("aralık en çok 366 gün olabilir")
    a = agenda_svc.build_agenda(db, start=start, end=end)
    # Ajandaya geçmiş (gecikmiş) açık süreler her zaman girer; aralık öncesindeki
    # gelecek süreler girmez.
    rows = [d for d in a["deadlines"] if d.due_date < today or d.due_date >= start]
    return {
        "today": today,
        "range": {"start": start, "end": end},
        "overdue_count": len([d for d in rows if d.due_date < today]),
        "deadlines": [agenda_svc.deadline_dict(d, today) for d in rows[:MAX_ROWS]],
        "hearings": a["hearings"][:MAX_ROWS],
        "note": "Süre tarihleri tahminidir; resmî/adli tatil hesaba katılmaz.",
    }


def list_deadlines(db: Session, inp: dict) -> dict:
    today = today_tr()
    status = _choice(inp.get("status"), "status", {"open", "done", "missed", "all"}, "open")
    days = _int(inp.get("days_ahead"), "days_ahead", 1, 3650)
    matter_id = _int(inp.get("matter_id"), "matter_id", 1, 10**9)
    q = db.query(LegalDeadline)
    if status != "all":
        q = q.filter(LegalDeadline.status == status)
    if matter_id:
        q = q.filter(LegalDeadline.matter_id == matter_id)
    if days:
        q = q.filter(LegalDeadline.due_date <= today + timedelta(days=days))
    rows = q.order_by(LegalDeadline.due_date).limit(MAX_ROWS).all()
    return {"today": today, "count": len(rows),
            "deadlines": [agenda_svc.deadline_dict(d, today) for d in rows]}


def list_matters(db: Session, inp: dict) -> dict:
    today = today_tr()
    status = _choice(inp.get("status"), "status", {"open", "waiting", "closed", "all"}, "open")
    text = (inp.get("query") or "").strip()
    q = db.query(LegalMatter)
    if status != "all":
        q = q.filter(LegalMatter.status == status)
    if text:
        like = f"%{text}%"
        q = q.filter(
            LegalMatter.title.ilike(like)
            | LegalMatter.counterparty.ilike(like)
            | LegalMatter.reference.ilike(like)
        )
    matters = q.order_by(LegalMatter.updated_at.desc()).limit(MAX_ROWS).all()
    open_counts = dict(
        db.query(LegalDeadline.matter_id, func.count(LegalDeadline.id))
        .filter(LegalDeadline.status == "open")
        .group_by(LegalDeadline.matter_id)
        .all()
    )
    return {
        "count": len(matters),
        "matters": [
            {
                "id": m.id, "title": m.title, "area": m.area, "status": m.status,
                "stage": m.stage, "role": m.role, "counterparty": m.counterparty,
                "court": m.court, "reference": m.reference,
                "next_hearing": m.next_hearing,
                "hearing_days_left": (m.next_hearing - today).days if m.next_hearing else None,
                "open_deadlines": open_counts.get(m.id, 0),
            }
            for m in matters
        ],
    }


def get_matter(db: Session, inp: dict) -> dict:
    today = today_tr()
    matter_id = _int(inp.get("matter_id"), "matter_id", 1, 10**9)
    if not matter_id:
        raise ToolInputError("matter_id gerekli")
    m = db.query(LegalMatter).filter(LegalMatter.id == matter_id).first()
    if not m:
        raise ToolInputError(f"{matter_id} numaralı hukuk dosyası yok")
    open_dl = [d for d in m.deadlines if d.status == "open"]
    open_dl.sort(key=lambda d: d.due_date)
    recent = (
        db.query(LegalConsultation)
        .filter(LegalConsultation.matter_id == m.id)
        .order_by(LegalConsultation.created_at.desc())
        .limit(3)
        .all()
    )
    return {
        "id": m.id, "title": m.title, "area": m.area, "status": m.status,
        "stage": m.stage, "role": m.role, "self_party": m.self_party,
        "counterparty": m.counterparty, "court": m.court, "reference": m.reference,
        "amount": m.amount, "next_hearing": m.next_hearing,
        "summary": (m.summary or "")[:1500], "notes": (m.notes or "")[:800],
        "open_deadlines": [agenda_svc.deadline_dict(d, today) for d in open_dl],
        "recent_consultations": [
            {"id": c.id, "subject": c.subject, "mode": c.mode,
             "date": c.created_at, "summary": (c.summary or "")[:600]}
            for c in recent
        ],
    }


def list_workspaces(db: Session, inp: dict) -> dict:
    counts: dict = {}
    for ws_id, status, n in (
        db.query(Lead.workspace_id, Lead.status, func.count(Lead.id))
        .group_by(Lead.workspace_id, Lead.status)
        .all()
    ):
        counts.setdefault(ws_id, {})[status] = n
    return {
        "workspaces": [
            {"slug": w.slug, "name": w.name, "description": w.description,
             "is_active": w.is_active, "leads_by_status": counts.get(w.id, {})}
            for w in db.query(Workspace).order_by(Workspace.id).all()
        ],
        "lead_data_source": _lead_source(db),
    }


def list_leads(db: Session, inp: dict) -> dict:
    slug = (inp.get("workspace_slug") or "").strip()
    status = _choice(inp.get("status"), "status",
                     {"new", "contacted", "offered", "won", "lost", "all"}, "all")
    since = _int(inp.get("since_days"), "since_days", 1, 3650)
    limit = _int(inp.get("limit"), "limit", 1, MAX_ROWS, 20)
    q = db.query(Lead, Workspace.slug).join(Workspace, Lead.workspace_id == Workspace.id)
    if slug:
        q = q.filter(Workspace.slug == slug)
    if status != "all":
        q = q.filter(Lead.status == status)
    if since:
        q = q.filter(Lead.created_at >= datetime.utcnow() - timedelta(days=since))
    rows = q.order_by(Lead.created_at.desc()).limit(limit).all()
    return {
        "data_source": _lead_source(db),
        "count": len(rows),
        "leads": [
            {"id": l.id, "workspace": ws, "name": l.full_name, "status": l.status,
             "source": l.source, "city": l.city, "interest": l.package_interest,
             "created_at": l.created_at, "last_contact_at": l.last_contact_at,
             "notes": (l.notes or "")[:300]}
            for l, ws in rows
        ],
    }


def inbox_summary(db: Session, inp: dict) -> dict:
    q = db.query(WhatsAppConversation)
    attention = (
        q.filter(WhatsAppConversation.needs_attention == True)  # noqa: E712
        .order_by(WhatsAppConversation.last_message_at.desc())
        .limit(10)
        .all()
    )
    return {
        "total_conversations": q.count(),
        "unread_conversations": q.filter(WhatsAppConversation.unread_count > 0).count(),
        "needs_attention_count": q.filter(WhatsAppConversation.needs_attention == True).count(),  # noqa: E712
        "needs_attention": [
            {"id": c.id, "name": c.contact_name or c.profile_name, "unread": c.unread_count,
             "last_message_at": c.last_message_at, "preview": c.last_message_preview}
            for c in attention
        ],
    }


def _schema(props: dict) -> dict:
    return {"type": "object", "properties": props, "additionalProperties": False}


TOOLS = [
    {
        "name": "get_agenda",
        "description": (
            "Ajanda: verilen tarih aralığındaki açık hukuki süreler ve duruşmalar. "
            "Gecikmiş (tarihi geçmiş) açık süreler her zaman dahildir. 'Bu hafta neyim var', "
            "'yarın ne var' gibi sorular için önce bunu kullan. Tarih verilmezse bugünden "
            "itibaren 7 gün."
        ),
        "input_schema": _schema({
            "start_date": {"type": "string", "description": "YYYY-AA-GG; varsayılan bugün"},
            "end_date": {"type": "string", "description": "YYYY-AA-GG; varsayılan başlangıç + 7 gün"},
        }),
    },
    {
        "name": "list_deadlines",
        "description": "Hukuki süre kayıtları; duruma, dosyaya ve kaç gün ileriye bakılacağına göre süzülür.",
        "input_schema": _schema({
            "status": {"type": "string", "enum": ["open", "done", "missed", "all"], "description": "varsayılan open"},
            "days_ahead": {"type": "integer", "description": "bugünden kaç gün ileriye kadar (gecikmişler dahil)"},
            "matter_id": {"type": "integer", "description": "yalnız bu hukuk dosyasının süreleri"},
        }),
    },
    {
        "name": "list_matters",
        "description": "Hukuk dosyaları (uyuşmazlıklar): durum, aşama, karşı taraf, sıradaki duruşma ve açık süre sayısı.",
        "input_schema": _schema({
            "status": {"type": "string", "enum": ["open", "waiting", "closed", "all"], "description": "varsayılan open"},
            "query": {"type": "string", "description": "başlık, karşı taraf veya esas no içinde arama"},
        }),
    },
    {
        "name": "get_matter",
        "description": "Tek bir hukuk dosyasının ayrıntısı: künye, özet, açık süreler ve son 3 danışmanın özeti.",
        "input_schema": {**_schema({"matter_id": {"type": "integer"}}), "required": ["matter_id"]},
    },
    {
        "name": "list_workspaces",
        "description": "İş kolları (workspace) ve her birindeki lead sayılarının duruma göre dağılımı.",
        "input_schema": _schema({}),
    },
    {
        "name": "list_leads",
        "description": (
            "Potansiyel müşteriler (lead). Durumlar: new, contacted, offered (teklif verildi), won, lost. "
            "Yalnız Gespa OS'in kendi tablosunu okur; diğer sitelerin başvuruları bağlı değildir "
            "(çıktıdaki data_source alanı)."
        ),
        "input_schema": _schema({
            "workspace_slug": {"type": "string", "description": "örn. superonline, solar"},
            "status": {"type": "string", "enum": ["new", "contacted", "offered", "won", "lost", "all"]},
            "since_days": {"type": "integer", "description": "son kaç günde oluşturulanlar"},
            "limit": {"type": "integer", "description": "en çok kaç kayıt (varsayılan 20, en çok 50)"},
        }),
    },
    {
        "name": "inbox_summary",
        "description": "WhatsApp gelen kutusu özeti: okunmamış ve dikkat bekleyen konuşmalar.",
        "input_schema": _schema({}),
    },
]

HANDLERS: dict[str, Callable[[Session, dict], dict]] = {
    "get_agenda": get_agenda,
    "list_deadlines": list_deadlines,
    "list_matters": list_matters,
    "get_matter": get_matter,
    "list_workspaces": list_workspaces,
    "list_leads": list_leads,
    "inbox_summary": inbox_summary,
}

assert {t["name"] for t in TOOLS} == set(HANDLERS), "TOOLS ve HANDLERS eşleşmeli"


def run_tool(db: Session, name: str, inp: Any) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        raise ToolInputError(f"bilinmeyen araç: {name}")
    if not isinstance(inp, dict):
        raise ToolInputError("girdi bir nesne olmalı")
    return handler(db, inp)
