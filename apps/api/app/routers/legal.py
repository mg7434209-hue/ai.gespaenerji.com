"""Hukuk Ofisi endpoint'leri — avukat ajan serisi, danışmalar ve dosyalar."""
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.legal_agents import (
    DEPARTMENTS,
    DISCLAIMER,
    LEGAL_AGENT_MAP,
    MODES,
    TEMPLATE_MAP,
    TEMPLATES,
)
from app.models import User
from app.models_legal import (
    LegalAgent,
    LegalConsultation,
    LegalDeadline,
    LegalDocument,
    LegalMatter,
    LegalMessage,
    LegalReview,
)
from app.services import document_text, legal_dates
from app.services.document_text import UnsupportedDocument
from app.services.legal_ai import legal_ai
from app.services.legal_export import build_docx, safe_filename


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/legal", tags=["legal"])


# ─────────────────────────────────────────────────────────────
# Şemalar
# ─────────────────────────────────────────────────────────────

class LegalAgentResponse(BaseModel):
    id: int
    slug: str
    name: str
    title: str
    department: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    expertise: list = []
    documents: list = []
    model: str
    is_active: bool
    sort_order: int
    consult_count: int

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: int
    consultation_id: int
    verdict: str
    score: float
    findings: list = []
    summary: str | None = None
    model: str | None = None
    error: str | None = None
    created_at: datetime


class ConsultRequest(BaseModel):
    agent_slug: str
    mode: str = "danisma"
    subject: str = ""
    question: str = Field(min_length=10, max_length=8000)
    context: Optional[str] = Field(default=None, max_length=60000)
    doc_type: Optional[str] = None
    matter_id: Optional[int] = None
    document_ids: list[int] = []


class ConsultationResponse(BaseModel):
    id: int
    agent_slug: str
    agent_name: str
    mode: str
    subject: str | None = None
    question: str
    context: str | None = None
    doc_type: str | None = None
    result: dict | None = None
    summary: str | None = None
    draft: str | None = None
    confidence: float
    needs_lawyer: bool
    status: str
    error: str | None = None
    model: str | None = None
    matter_id: int | None = None
    document_ids: list[int] = []
    triage: dict | None = None
    message_count: int = 0
    review: ReviewResponse | None = None
    created_at: datetime


class MatterRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    area: Optional[str] = None
    self_party: Optional[str] = None
    counterparty: Optional[str] = None
    role: Optional[str] = None
    court: Optional[str] = None
    reference: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[str] = None
    next_hearing: Optional[date] = None
    summary: Optional[str] = None
    notes: Optional[str] = None


class MatterResponse(BaseModel):
    id: int
    title: str
    area: str | None = None
    self_party: str | None = None
    counterparty: str | None = None
    role: str | None = None
    court: str | None = None
    reference: str | None = None
    stage: str
    status: str
    amount: str | None = None
    next_hearing: date | None = None
    summary: str | None = None
    notes: str | None = None
    consultation_count: int = 0
    document_count: int = 0
    open_deadlines: int = 0
    next_deadline: date | None = None
    created_at: datetime
    updated_at: datetime


class DeadlineRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    due_date: date
    matter_id: Optional[int] = None
    consultation_id: Optional[int] = None
    basis: Optional[str] = None
    start_date: Optional[date] = None
    critical: bool = True
    notes: Optional[str] = None
    source: str = "manual"


class DeadlinePatch(BaseModel):
    title: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    critical: Optional[bool] = None
    notes: Optional[str] = None
    matter_id: Optional[int] = None


class DeadlineResponse(BaseModel):
    id: int
    title: str
    due_date: date
    days_left: int
    matter_id: int | None = None
    matter_title: str | None = None
    consultation_id: int | None = None
    basis: str | None = None
    start_date: date | None = None
    critical: bool
    status: str
    notes: str | None = None
    source: str
    created_at: datetime


class CaptureDeadlinesRequest(BaseModel):
    """Analizdeki süre satırlarını takvime yazar."""
    start_date: date                       # sürenin başladığı gün (ör. tebliğ tarihi)
    matter_id: Optional[int] = None
    indexes: Optional[list[int]] = None    # boşsa hepsi


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=6000)
    document_ids: list[int] = []


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    document_ids: list[int] = []
    created_at: datetime


class BoardRequest(BaseModel):
    question: str = Field(min_length=10, max_length=8000)
    subject: str = ""
    agent_slugs: list[str] = Field(default_factory=list)   # boşsa sistem seçer
    context: Optional[str] = None
    document_ids: list[int] = []
    matter_id: Optional[int] = None


class AttachRequest(BaseModel):
    document_ids: list[int] = []
    consultation_ids: list[int] = []


class TemplateDraftRequest(BaseModel):
    details: str = Field(min_length=5, max_length=8000)
    matter_id: Optional[int] = None
    document_ids: list[int] = []


class DocumentResponse(BaseModel):
    id: int
    filename: str
    kind: str
    media_type: str
    size: int
    pages: int | None = None
    char_count: int
    preview: str = ""
    notes: list = []
    matter_id: int | None = None
    created_at: datetime


class AnalyzeRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1)
    agent_slug: Optional[str] = None      # boşsa sistem kendi seçer
    mode: Optional[str] = None            # boşsa triyajın önerdiği mod
    note: str = ""                        # "şunu da sor" notu
    matter_id: Optional[int] = None


def _document_out(d: LegalDocument) -> DocumentResponse:
    return DocumentResponse(
        id=d.id,
        filename=d.filename,
        kind=d.kind,
        media_type=d.media_type,
        size=d.size,
        pages=d.pages,
        char_count=d.char_count,
        preview=document_text.preview(d.text or ""),
        notes=d.notes or [],
        matter_id=d.matter_id,
        created_at=d.created_at,
    )


def _load_attachments(db: Session, ids: list[int]) -> tuple[list[dict], list[LegalDocument]]:
    """Belge kayıtlarını modele gidecek ek listesine çevirir."""
    if not ids:
        return [], []
    rows = db.query(LegalDocument).filter(LegalDocument.id.in_(ids)).all()
    found = {d.id: d for d in rows}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadı: {missing}")

    ordered = [found[i] for i in ids]
    total = sum(d.size or 0 for d in ordered)
    if total > document_text.MAX_TOTAL_ATTACH_BYTES:
        mb = document_text.MAX_TOTAL_ATTACH_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Seçilen belgeler toplam {mb} MB sınırını aşıyor. Daha az belgeyle deneyin.",
        )

    attachments = [
        {
            "kind": d.kind,
            "media_type": d.media_type,
            "filename": d.filename,
            "data": d.content,
            "text": d.text,
        }
        for d in ordered
    ]
    return attachments, ordered


def _matter_out(m: LegalMatter, db: Session) -> MatterResponse:
    open_dl = [d for d in m.deadlines if d.status == "open"]
    doc_count = db.query(LegalDocument).filter(LegalDocument.matter_id == m.id).count()
    return MatterResponse(
        id=m.id, title=m.title, area=m.area, self_party=m.self_party,
        counterparty=m.counterparty, role=m.role, court=m.court, reference=m.reference,
        stage=m.stage, status=m.status, amount=m.amount, next_hearing=m.next_hearing,
        summary=m.summary, notes=m.notes,
        consultation_count=len(m.consultations),
        document_count=doc_count,
        open_deadlines=len(open_dl),
        next_deadline=min((d.due_date for d in open_dl), default=None),
        created_at=m.created_at, updated_at=m.updated_at,
    )


def _deadline_out(d: LegalDeadline) -> DeadlineResponse:
    return DeadlineResponse(
        id=d.id, title=d.title, due_date=d.due_date,
        days_left=legal_dates.days_left(d.due_date),
        matter_id=d.matter_id, matter_title=d.matter.title if d.matter else None,
        consultation_id=d.consultation_id, basis=d.basis, start_date=d.start_date,
        critical=d.critical, status=d.status, notes=d.notes, source=d.source,
        created_at=d.created_at,
    )


def _review_out(r: LegalReview) -> ReviewResponse:
    return ReviewResponse(
        id=r.id, consultation_id=r.consultation_id, verdict=r.verdict, score=r.score,
        findings=r.findings or [], summary=r.summary, model=r.model, error=r.error,
        created_at=r.created_at,
    )


def _matter_context(m: Optional[LegalMatter], db: Session, skip_consultation: Optional[int] = None) -> Optional[str]:
    """Dosyanın hafızası — ajana bağlam olarak verilir."""
    if not m:
        return None
    lines = [f"Dosya: {m.title}"]
    for label, value in (
        ("Hukuk alanı", m.area), ("Bizim taraf", m.self_party), ("Karşı taraf", m.counterparty),
        ("Sıfatımız", m.role), ("Merci", m.court), ("Dosya/esas no", m.reference),
        ("Aşama", m.stage), ("Uyuşmazlık değeri", m.amount),
    ):
        if value:
            lines.append(f"{label}: {value}")
    if m.next_hearing:
        lines.append(f"Sıradaki duruşma: {m.next_hearing.isoformat()}")
    if m.summary:
        lines.append(f"Dosya özeti: {m.summary}")

    open_dl = [d for d in m.deadlines if d.status == "open"]
    if open_dl:
        lines.append("Açık süreler:")
        for d in sorted(open_dl, key=lambda x: x.due_date)[:8]:
            lines.append(f"  - {d.title}: son gün {d.due_date.isoformat()} ({d.basis or 'dayanak yok'})")

    prev = [c for c in m.consultations if c.id != skip_consultation and c.status == "done"]
    prev.sort(key=lambda c: c.created_at, reverse=True)
    if prev:
        lines.append("Bu dosyada daha önce verilen görüşler:")
        for c in prev[:5]:
            who = c.agent.name if c.agent else "ajan"
            lines.append(f"  - [{who} · {c.created_at.date().isoformat()}] {(c.summary or '')[:300]}")

    docs = db.query(LegalDocument).filter(LegalDocument.matter_id == m.id).all()
    if docs:
        lines.append("Dosyadaki belgeler: " + ", ".join(d.filename for d in docs[:15]))
    return "\n".join(lines)


def _consultation_out(c: LegalConsultation) -> ConsultationResponse:
    return ConsultationResponse(
        id=c.id,
        agent_slug=c.agent.slug if c.agent else "",
        agent_name=c.agent.name if c.agent else "",
        mode=c.mode,
        subject=c.subject,
        question=c.question,
        context=c.context,
        doc_type=c.doc_type,
        result=c.result or None,
        summary=c.summary,
        draft=c.draft,
        confidence=c.confidence,
        needs_lawyer=c.needs_lawyer,
        status=c.status,
        error=c.error,
        model=c.model,
        matter_id=c.matter_id,
        document_ids=c.document_ids or [],
        triage=c.triage or None,
        message_count=len(c.messages),
        review=_review_out(c.reviews[-1]) if c.reviews else None,
        created_at=c.created_at,
    )


# ─────────────────────────────────────────────────────────────
# Ajanlar
# ─────────────────────────────────────────────────────────────

@router.get("/meta")
def legal_meta(user: User = Depends(get_current_user)):
    """Arayüzün ihtiyaç duyduğu sabitler — modlar, departman sırası, uyarı metni."""
    return {
        "modes": [{"key": k, "label": v} for k, v in MODES.items()],
        "departments": DEPARTMENTS,
        "disclaimer": DISCLAIMER,
        "ai_configured": legal_ai.is_configured(),
        "model": legal_ai.default_model(),
    }


@router.get("/agents", response_model=list[LegalAgentResponse])
def list_legal_agents(
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(LegalAgent)
    if department:
        q = q.filter(LegalAgent.department == department)
    return q.order_by(LegalAgent.sort_order, LegalAgent.id).all()


@router.get("/agents/{slug}", response_model=LegalAgentResponse)
def get_legal_agent(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = db.query(LegalAgent).filter(LegalAgent.slug == slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Avukat ajanı bulunamadı")
    return agent


@router.post("/agents/{slug}/toggle")
def toggle_legal_agent(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = db.query(LegalAgent).filter(LegalAgent.slug == slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Avukat ajanı bulunamadı")
    agent.is_active = not agent.is_active
    db.commit()
    return {"ok": True, "slug": slug, "is_active": agent.is_active}


# ─────────────────────────────────────────────────────────────
# Danışma
# ─────────────────────────────────────────────────────────────

@router.post("/consult", response_model=ConsultationResponse)
def consult(
    payload: ConsultRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seçilen avukat ajanını çalıştırır ve sonucu kaydeder.

    Senkron tanımlı: Anthropic istemcisi bloklayıcı olduğu için FastAPI bunu
    threadpool'da çalıştırsın, event loop kilitlenmesin.
    """
    agent = db.query(LegalAgent).filter(LegalAgent.slug == payload.agent_slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Avukat ajanı bulunamadı")
    if not agent.is_active:
        raise HTTPException(status_code=400, detail=f"{agent.name} şu an beklemede. Önce göreve alın.")

    mode = payload.mode if payload.mode in MODES else "danisma"

    if payload.matter_id is not None:
        exists = db.query(LegalMatter).filter(LegalMatter.id == payload.matter_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    # Prompt tanımı kod tarafında (legal_agents.py) — DB'deki kopya yalnız görüntü içindir
    spec = LEGAL_AGENT_MAP.get(agent.slug, {
        "slug": agent.slug,
        "name": agent.name,
        "title": agent.title,
        "role": agent.description or "",
    })

    attachments, _docs = _load_attachments(db, payload.document_ids)
    matter = (
        db.query(LegalMatter).filter(LegalMatter.id == payload.matter_id).first()
        if payload.matter_id is not None else None
    )

    run = legal_ai.run(
        agent={**spec, "model": agent.model},
        mode=mode,
        question=payload.question,
        context=payload.context,
        doc_type=payload.doc_type,
        subject=payload.subject,
        attachments=attachments,
        matter_context=_matter_context(matter, db),
    )
    result = run["result"]
    belge = result.get("belge") or {}

    consultation = LegalConsultation(
        agent_id=agent.id,
        matter_id=payload.matter_id,
        mode=mode,
        subject=(payload.subject or payload.question[:120]).strip(),
        question=payload.question,
        context=payload.context,
        doc_type=payload.doc_type,
        document_ids=payload.document_ids or [],
        result=result,
        summary=result.get("ozet") or "",
        draft=(belge.get("icerik") or None) if isinstance(belge, dict) else None,
        confidence=float(result.get("guven") or 0.0),
        needs_lawyer=bool(result.get("avukat_gerekli", True)),
        status="done" if run["ok"] else "error",
        error=run.get("error"),
        model=run.get("model"),
        tokens_in=run.get("tokens_in", 0),
        tokens_out=run.get("tokens_out", 0),
    )
    db.add(consultation)
    agent.consult_count = (agent.consult_count or 0) + 1
    db.commit()
    db.refresh(consultation)

    if not run["ok"]:
        logger.warning("Legal consult error (%s): %s", agent.slug, run.get("error"))

    return _consultation_out(consultation)


@router.get("/consultations", response_model=list[ConsultationResponse])
def list_consultations(
    agent: Optional[str] = None,
    matter_id: Optional[int] = None,
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(LegalConsultation)
    if agent:
        q = q.join(LegalAgent).filter(LegalAgent.slug == agent)
    if matter_id is not None:
        q = q.filter(LegalConsultation.matter_id == matter_id)
    rows = q.order_by(LegalConsultation.created_at.desc()).limit(limit).all()
    return [_consultation_out(c) for c in rows]


@router.get("/consultations/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    return _consultation_out(c)


@router.delete("/consultations/{consultation_id}")
def delete_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    db.delete(c)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# Dosyalar
# ─────────────────────────────────────────────────────────────

@router.get("/matters", response_model=list[MatterResponse])
def list_matters(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.query(LegalMatter).order_by(LegalMatter.updated_at.desc()).all()
    return [_matter_out(m, db) for m in rows]


@router.post("/matters", response_model=MatterResponse)
def create_matter(
    payload: MatterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    m = LegalMatter(**data)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _matter_out(m, db)


@router.delete("/matters/{matter_id}")
def delete_matter(
    matter_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.query(LegalMatter).filter(LegalMatter.id == matter_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    db.delete(m)
    db.commit()
    return {"ok": True}




@router.get("/matters/{matter_id}", response_model=MatterResponse)
def get_matter(
    matter_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.query(LegalMatter).filter(LegalMatter.id == matter_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return _matter_out(m, db)


@router.patch("/matters/{matter_id}", response_model=MatterResponse)
def update_matter(
    matter_id: int,
    payload: MatterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.query(LegalMatter).filter(LegalMatter.id == matter_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(m, key, value)
    db.commit()
    db.refresh(m)
    return _matter_out(m, db)


@router.post("/matters/{matter_id}/attach")
def attach_to_matter(
    matter_id: int,
    payload: AttachRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Var olan belge ve danışmaları dosyaya bağlar."""
    m = db.query(LegalMatter).filter(LegalMatter.id == matter_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    moved_docs = (
        db.query(LegalDocument).filter(LegalDocument.id.in_(payload.document_ids)).all()
        if payload.document_ids else []
    )
    for d in moved_docs:
        d.matter_id = matter_id
    moved_cons = (
        db.query(LegalConsultation).filter(LegalConsultation.id.in_(payload.consultation_ids)).all()
        if payload.consultation_ids else []
    )
    for c in moved_cons:
        c.matter_id = matter_id
    db.commit()
    return {"ok": True, "documents": len(moved_docs), "consultations": len(moved_cons)}


# ─────────────────────────────────────────────────────────────
# Süre takvimi — hak düşürücü süreler
# ─────────────────────────────────────────────────────────────

@router.get("/deadlines", response_model=list[DeadlineResponse])
def list_deadlines(
    status: Optional[str] = None,
    matter_id: Optional[int] = None,
    days: Optional[int] = Query(default=None, ge=1, le=3650),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(LegalDeadline)
    if status:
        q = q.filter(LegalDeadline.status == status)
    if matter_id is not None:
        q = q.filter(LegalDeadline.matter_id == matter_id)
    if days is not None:
        from datetime import timedelta
        q = q.filter(LegalDeadline.due_date <= date.today() + timedelta(days=days))
    rows = q.order_by(LegalDeadline.due_date).all()
    return [_deadline_out(d) for d in rows]


@router.post("/deadlines", response_model=DeadlineResponse)
def create_deadline(
    payload: DeadlineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = LegalDeadline(**payload.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return _deadline_out(d)


@router.patch("/deadlines/{deadline_id}", response_model=DeadlineResponse)
def update_deadline(
    deadline_id: int,
    payload: DeadlinePatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.query(LegalDeadline).filter(LegalDeadline.id == deadline_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Süre kaydı bulunamadı")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(d, key, value)
    db.commit()
    db.refresh(d)
    return _deadline_out(d)


@router.delete("/deadlines/{deadline_id}")
def delete_deadline(
    deadline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.query(LegalDeadline).filter(LegalDeadline.id == deadline_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Süre kaydı bulunamadı")
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.post("/consultations/{consultation_id}/deadlines", response_model=list[DeadlineResponse])
def capture_deadlines(
    consultation_id: int,
    payload: CaptureDeadlinesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analizde çıkan süre satırlarını gerçek tarihe çevirip takvime yazar.

    Hesap tahminîdir: başlangıç gününe süre eklenir; resmî/adli tatil ve özel
    tebligat kuralları hesaba katılmaz.
    """
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")

    rows = (c.result or {}).get("sureler") or []
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=400, detail="Bu danışmada kaydedilecek süre yok.")

    matter_id = payload.matter_id if payload.matter_id is not None else c.matter_id
    if matter_id is not None and not db.query(LegalMatter).filter(LegalMatter.id == matter_id).first():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    created: list[LegalDeadline] = []
    skipped: list[str] = []
    for i, row in enumerate(rows):
        if payload.indexes is not None and i not in payload.indexes:
            continue
        if not isinstance(row, dict):
            continue
        period = str(row.get("sure") or "")
        due = legal_dates.compute_due(payload.start_date, period)
        if not due:
            skipped.append(str(row.get("is") or period))
            continue
        d = LegalDeadline(
            matter_id=matter_id,
            consultation_id=c.id,
            title=(str(row.get("is") or "Süre"))[:255],
            due_date=due,
            basis=f"{period} — {row.get('baslangic') or 'başlangıç belirtilmedi'}"[:255],
            start_date=payload.start_date,
            critical=bool(row.get("kritik", True)),
            source="analiz",
        )
        db.add(d)
        created.append(d)

    if not created:
        raise HTTPException(
            status_code=400,
            detail="Süre metinlerinden tarih çıkarılamadı: " + ", ".join(skipped[:5]),
        )
    db.commit()
    for d in created:
        db.refresh(d)
    return [_deadline_out(d) for d in created]


@router.get("/agenda")
def legal_agenda(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard için: yaklaşan ve geçmiş süreler + duruşmalar."""
    from datetime import timedelta
    horizon = date.today() + timedelta(days=days)
    rows = (
        db.query(LegalDeadline)
        .filter(LegalDeadline.status == "open", LegalDeadline.due_date <= horizon)
        .order_by(LegalDeadline.due_date)
        .all()
    )
    overdue = [d for d in rows if d.due_date < date.today()]
    hearings = (
        db.query(LegalMatter)
        .filter(
            LegalMatter.next_hearing.isnot(None),
            LegalMatter.next_hearing >= date.today(),
            LegalMatter.next_hearing <= horizon,
        )
        .order_by(LegalMatter.next_hearing)
        .all()
    )
    return {
        "deadlines": [_deadline_out(d) for d in rows],
        "overdue": len(overdue),
        "critical": len([d for d in rows if d.critical and d.due_date >= date.today()]),
        "hearings": [
            {"matter_id": m.id, "title": m.title, "court": m.court,
             "date": m.next_hearing, "days_left": legal_dates.days_left(m.next_hearing)}
            for m in hearings
        ],
    }


# ─────────────────────────────────────────────────────────────
# Devam sohbeti — danışmanın üstüne konuşma
# ─────────────────────────────────────────────────────────────

@router.get("/consultations/{consultation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    consultation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    return [
        MessageResponse(id=m.id, role=m.role, content=m.content,
                        document_ids=m.document_ids or [], created_at=m.created_at)
        for m in c.messages
    ]


@router.post("/consultations/{consultation_id}/messages", response_model=list[MessageResponse])
def send_message(
    consultation_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ajanla konuşmayı sürdürür; kullanıcı ve ajan mesajını birlikte döner."""
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    agent = c.agent
    if not agent:
        raise HTTPException(status_code=404, detail="Danışmanın ajanı bulunamadı")

    attachments, docs = _load_attachments(db, payload.document_ids)
    spec = LEGAL_AGENT_MAP.get(agent.slug, {
        "slug": agent.slug, "name": agent.name, "title": agent.title,
        "role": agent.description or "",
    })
    history = [{"role": m.role, "content": m.content} for m in c.messages]

    user_msg = LegalMessage(
        consultation_id=c.id, role="user", content=payload.message.strip(),
        document_ids=[d.id for d in docs],
    )
    db.add(user_msg)

    out = legal_ai.chat(
        agent={**spec, "model": agent.model},
        base={"subject": c.subject, "question": c.question, "result": c.result or {}},
        history=history,
        question=payload.message.strip(),
        attachments=attachments,
        matter_context=_matter_context(c.matter, db, skip_consultation=c.id),
    )
    agent_msg = LegalMessage(
        consultation_id=c.id, role="assistant", content=out["reply"], model=out.get("model"),
    )
    db.add(agent_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(agent_msg)

    if not out["ok"]:
        logger.warning("Legal chat error (%s): %s", agent.slug, out.get("error"))

    return [
        MessageResponse(id=m.id, role=m.role, content=m.content,
                        document_ids=m.document_ids or [], created_at=m.created_at)
        for m in (user_msg, agent_msg)
    ]


# ─────────────────────────────────────────────────────────────
# İkinci okuma — Hukuk Denetçisi
# ─────────────────────────────────────────────────────────────

@router.post("/consultations/{consultation_id}/review", response_model=ReviewResponse)
def review_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Çıktıyı denetler: uydurma madde, süre hatası, eksik yol, dilekçe kusuru."""
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    if not c.result:
        raise HTTPException(status_code=400, detail="Denetlenecek çıktı yok.")

    out = legal_ai.review(
        agent_name=c.agent.name if c.agent else "ajan",
        mode=c.mode,
        question=c.question,
        result=c.result,
    )
    data = out["review"]
    review = LegalReview(
        consultation_id=c.id,
        verdict=data.get("karar") or "hata",
        score=float(data.get("puan") or 0.0),
        findings=data.get("bulgular") or [],
        summary=data.get("ozet") or "",
        model=out.get("model"),
        error=out.get("error"),
    )
    # Doğrulanması gerekenler bulgu listesinin sonuna eklenir
    for item in data.get("dogrulanmasi_gerekenler") or []:
        review.findings = (review.findings or []) + [
            {"tur": "dogrulama", "agirlik": "orta", "alan": "Teyit",
             "sorun": str(item), "duzeltme": "Resmî kaynaktan doğrulayın."}
        ]
    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_out(review)


@router.get("/consultations/{consultation_id}/reviews", response_model=list[ReviewResponse])
def list_reviews(
    consultation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    return [_review_out(r) for r in c.reviews]


# ─────────────────────────────────────────────────────────────
# Kurul görüşü — birden çok ajan aynı olaya bakar
# ─────────────────────────────────────────────────────────────

@router.post("/board")
def board_opinion(
    payload: BoardRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seçilen ajanlar ayrı ayrı görüş verir, Baş Müşavir tek karara bağlar."""
    attachments, docs = _load_attachments(db, payload.document_ids)
    matter = (
        db.query(LegalMatter).filter(LegalMatter.id == payload.matter_id).first()
        if payload.matter_id is not None else None
    )
    if payload.matter_id is not None and not matter:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    context = _matter_context(matter, db)

    slugs = payload.agent_slugs
    if not slugs:
        # Sistem seçsin: triyaj hangi ajanı işaret ederse o + alternatifi
        tri = legal_ai.triage(attachments, note=payload.question)["triage"]
        slugs = [s for s in (tri.get("agent_slug"), tri.get("alternatif_ajan")) if s]
        slugs.append("dava-stratejisti")
    slugs = list(dict.fromkeys(slugs))[:4]

    agents = (
        db.query(LegalAgent)
        .filter(LegalAgent.slug.in_(slugs), LegalAgent.is_active == True)  # noqa: E712
        .all()
    )
    if len(agents) < 2:
        raise HTTPException(
            status_code=400,
            detail="Kurul için görevde olan en az iki ajan gerekir.",
        )

    opinions = []
    for agent in agents:
        spec = LEGAL_AGENT_MAP.get(agent.slug, {
            "slug": agent.slug, "name": agent.name, "title": agent.title,
            "role": agent.description or "",
        })
        run = legal_ai.run(
            agent={**spec, "model": agent.model},
            mode="kurul",
            question=payload.question,
            context=payload.context,
            doc_type=None,
            subject=payload.subject,
            attachments=attachments,
            matter_context=context,
        )
        opinions.append({
            "slug": agent.slug, "name": agent.name, "title": agent.title,
            "icon": agent.icon, "color": agent.color,
            "ok": run["ok"], "error": run.get("error"), "result": run["result"],
        })
        agent.consult_count = (agent.consult_count or 0) + 1

    usable = [o for o in opinions if o["ok"]]
    if not usable:
        db.commit()
        raise HTTPException(status_code=503, detail=opinions[0].get("error") or "Kurul çalıştırılamadı.")

    synth = legal_ai.board_synthesis(payload.question, usable, matter_context=context)
    result = synth["result"]
    result["kurul_gorusleri"] = [
        {"slug": o["slug"], "name": o["name"], "title": o["title"],
         "icon": o["icon"], "color": o["color"],
         "ozet": (o["result"] or {}).get("ozet", ""), "ok": o["ok"]}
        for o in opinions
    ]

    chair = db.query(LegalAgent).filter(LegalAgent.slug == "bas-hukuk-musaviri").first() or agents[0]
    belge = result.get("belge") or {}
    consultation = LegalConsultation(
        agent_id=chair.id,
        matter_id=payload.matter_id,
        mode="kurul",
        subject=(payload.subject or payload.question[:120]).strip(),
        question=payload.question,
        context=payload.context,
        document_ids=[d.id for d in docs],
        triage={"kurul": [o["slug"] for o in opinions]},
        result=result,
        summary=result.get("ozet") or "",
        draft=(belge.get("icerik") or None) if isinstance(belge, dict) else None,
        confidence=float(result.get("guven") or 0.0),
        needs_lawyer=bool(result.get("avukat_gerekli", True)),
        status="done" if synth["ok"] else "error",
        error=synth.get("error"),
        model=synth.get("model"),
        tokens_in=synth.get("tokens_in", 0),
        tokens_out=synth.get("tokens_out", 0),
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return {
        "consultation": _consultation_out(consultation),
        "opinions": [
            {k: o[k] for k in ("slug", "name", "title", "icon", "color", "ok", "error", "result")}
            for o in opinions
        ],
    }


# ─────────────────────────────────────────────────────────────
# Şablon kütüphanesi
# ─────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(user: User = Depends(get_current_user)):
    return TEMPLATES


@router.post("/templates/{template_id}/draft", response_model=ConsultationResponse)
def draft_from_template(
    template_id: str,
    payload: TemplateDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Şablonu, verilen bilgilerle gerçek dilekçeye çevirir."""
    tpl = TEMPLATE_MAP.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Şablon bulunamadı")
    agent = db.query(LegalAgent).filter(LegalAgent.slug == tpl["agent"]).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Şablonun ajanı bulunamadı")
    if not agent.is_active:
        raise HTTPException(status_code=400, detail=f"{agent.name} beklemede. Önce göreve alın.")

    attachments, docs = _load_attachments(db, payload.document_ids)
    matter = (
        db.query(LegalMatter).filter(LegalMatter.id == payload.matter_id).first()
        if payload.matter_id is not None else None
    )
    if payload.matter_id is not None and not matter:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    spec = LEGAL_AGENT_MAP.get(agent.slug, {
        "slug": agent.slug, "name": agent.name, "title": agent.title,
        "role": agent.description or "",
    })
    question = (
        f"'{tpl['name']}' hazırla. Şablonun beklediği bilgiler: "
        + "; ".join(tpl["fields"])
        + f"\n\nVerilen bilgiler:\n{payload.details.strip()}\n\n"
        "Eksik bırakılan her alanı köşeli parantezle işaretle ve eksik_bilgiler listesine yaz."
    )
    run = legal_ai.run(
        agent={**spec, "model": agent.model},
        mode="dilekce",
        question=question,
        context=None,
        doc_type=tpl["name"],
        subject=tpl["name"],
        attachments=attachments,
        matter_context=_matter_context(matter, db),
    )
    result = run["result"]
    belge = result.get("belge") or {}
    consultation = LegalConsultation(
        agent_id=agent.id, matter_id=payload.matter_id, mode="dilekce",
        subject=tpl["name"], question=question, doc_type=tpl["name"],
        document_ids=[d.id for d in docs], result=result,
        summary=result.get("ozet") or "",
        draft=(belge.get("icerik") or None) if isinstance(belge, dict) else None,
        confidence=float(result.get("guven") or 0.0),
        needs_lawyer=bool(result.get("avukat_gerekli", True)),
        status="done" if run["ok"] else "error",
        error=run.get("error"), model=run.get("model"),
        tokens_in=run.get("tokens_in", 0), tokens_out=run.get("tokens_out", 0),
    )
    db.add(consultation)
    agent.consult_count = (agent.consult_count or 0) + 1
    db.commit()
    db.refresh(consultation)
    return _consultation_out(consultation)


# ─────────────────────────────────────────────────────────────
# Word çıktısı
# ─────────────────────────────────────────────────────────────

@router.get("/consultations/{consultation_id}/export")
def export_consultation(
    consultation_id: int,
    part: str = Query(default="belge", pattern="^(belge|rapor)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dilekçe taslağını veya tam raporu .docx olarak indirir."""
    c = db.query(LegalConsultation).filter(LegalConsultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Danışma kaydı bulunamadı")
    result = c.result or {}

    if part == "belge":
        if not c.draft:
            raise HTTPException(status_code=400, detail="Bu danışmada indirilecek belge taslağı yok.")
        belge = result.get("belge") or {}
        title = belge.get("tur") or c.doc_type or "Dilekçe"
        content = c.draft
    else:
        title = f"Hukuki Değerlendirme — {c.subject or ''}".strip(" —")
        lines = [f"Hazırlayan: {c.agent.name if c.agent else 'Hukuk Ofisi'}",
                 f"Tarih: {c.created_at.date().isoformat()}", ""]
        if result.get("ozet"):
            lines += ["## Özet", result["ozet"], ""]
        if result.get("degerlendirme"):
            lines += ["## Hukuki değerlendirme", str(result["degerlendirme"]), ""]
        if result.get("sureler"):
            lines.append("## Süreler")
            for x in result["sureler"]:
                if isinstance(x, dict):
                    lines.append(f"- **{x.get('is','')}**: {x.get('sure','')} ({x.get('baslangic') or 'başlangıç belirtilmedi'})")
            lines.append("")
        if result.get("adimlar"):
            lines.append("## Yapılacaklar")
            for x in result["adimlar"]:
                if isinstance(x, dict):
                    lines.append(f"- {x.get('sira','')}. {x.get('baslik','')} — {x.get('aciklama','')}")
            lines.append("")
        if result.get("riskler"):
            lines.append("## Riskler")
            for x in result["riskler"]:
                if isinstance(x, dict):
                    lines.append(f"- [{x.get('seviye','')}] **{x.get('baslik','')}**: {x.get('aciklama','')}")
            lines.append("")
        if result.get("mevzuat"):
            lines.append("## İlgili mevzuat")
            for x in result["mevzuat"]:
                if isinstance(x, dict):
                    teyit = " (teyit edilmeli)" if x.get("teyit") else ""
                    lines.append(f"- {x.get('kanun','')} {x.get('madde','')}{teyit} — {x.get('aciklama','')}")
            lines.append("")
        if c.draft:
            lines += ["## Belge taslağı", c.draft, ""]
        content = "\n".join(lines)

    data = build_docx(title, content, footer_note=DISCLAIMER)
    filename = safe_filename(f"{title}-{c.id}", "docx")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────
# Belgeler — yükle, sistem okusun ve analiz etsin
# ─────────────────────────────────────────────────────────────

@router.post("/documents", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    matter_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Tek dosya yükler; türünü tanır, metnini çıkarır, kaydeder.

    PDF ve görseller ham hâliyle saklanır ve analiz sırasında modele doğrudan
    gider; DOCX/metin dosyalarının metni çıkarılıp saklanır.
    """
    raw = file.file.read()
    try:
        extracted = document_text.extract(file.filename or "belge", raw)
    except UnsupportedDocument as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        file.file.close()

    if matter_id is not None and not db.query(LegalMatter).filter(LegalMatter.id == matter_id).first():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    doc = LegalDocument(
        filename=(file.filename or "belge")[:255],
        kind=extracted.kind,
        media_type=extracted.media_type,
        size=len(raw),
        pages=extracted.pages,
        # Metni çıkarılan belgede ham veriyi tutmaya gerek yok
        content=raw if extracted.kind in ("pdf", "image") else None,
        text=extracted.text or None,
        char_count=len(extracted.text or ""),
        notes=extracted.notes,
        matter_id=matter_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _document_out(doc)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    matter_id: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(LegalDocument)
    if matter_id is not None:
        q = q.filter(LegalDocument.matter_id == matter_id)
    rows = q.order_by(LegalDocument.created_at.desc()).limit(limit).all()
    return [_document_out(d) for d in rows]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.query(LegalDocument).filter(LegalDocument.id == document_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Belge bulunamadı")
    return _document_out(d)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.query(LegalDocument).filter(LegalDocument.id == document_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Belge bulunamadı")
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.post("/documents/analyze")
def analyze_documents(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Yüklenen belgeleri okur, doğru avukat ajanını seçer ve analizi üretir.

    İki kademe: önce triyaj (belge nedir, kime gider, süre var mı), sonra
    seçilen ajanın tam analizi. agent_slug verilirse triyaj yönlendirmesi
    o ajanla ezilir ama belge künyesi yine çıkarılır.
    """
    attachments, docs = _load_attachments(db, payload.document_ids)

    if payload.matter_id is not None and not db.query(LegalMatter).filter(
        LegalMatter.id == payload.matter_id
    ).first():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    matter = (
        db.query(LegalMatter).filter(LegalMatter.id == payload.matter_id).first()
        if payload.matter_id is not None else None
    )

    # 1) Triyaj
    triage_run = legal_ai.triage(attachments, note=payload.note)
    triage = triage_run["triage"]
    if not triage_run["ok"] and payload.agent_slug is None:
        raise HTTPException(
            status_code=503,
            detail=triage_run.get("error") or "Belge okunamadı, otomatik yönlendirme yapılamadı.",
        )

    slug = payload.agent_slug or triage.get("agent_slug") or "bas-hukuk-musaviri"
    agent = db.query(LegalAgent).filter(LegalAgent.slug == slug).first()
    if not agent:
        agent = db.query(LegalAgent).filter(LegalAgent.slug == "bas-hukuk-musaviri").first()
    if not agent:
        raise HTTPException(status_code=500, detail="Hukuk Ofisi kadrosu yüklenmemiş.")
    if not agent.is_active:
        raise HTTPException(status_code=400, detail=f"{agent.name} beklemede. Önce göreve alın.")

    mode = payload.mode or triage.get("onerilen_mod") or "inceleme"
    if mode not in MODES:
        mode = "inceleme"

    # 2) Seçilen ajanın tam analizi
    spec = LEGAL_AGENT_MAP.get(agent.slug, {
        "slug": agent.slug, "name": agent.name, "title": agent.title,
        "role": agent.description or "",
    })
    question = (
        "Ekteki belgeleri incele ve tam değerlendirmeni yap: belge ne diyor, "
        "benim için ne anlama geliyor, hangi süreler işliyor, ne yapmalıyım."
    )
    if payload.note.strip():
        question += f"\n\nAyrıca şunu da yanıtla: {payload.note.strip()}"

    subject = (triage.get("belge_turu") or docs[0].filename)[:255]
    run = legal_ai.run(
        agent={**spec, "model": agent.model},
        mode=mode,
        question=question,
        context=None,
        doc_type=None,
        subject=subject,
        attachments=attachments,
        matter_context=_matter_context(matter, db),
    )
    result = run["result"]
    belge = result.get("belge") or {}

    consultation = LegalConsultation(
        agent_id=agent.id,
        matter_id=payload.matter_id,
        mode=mode,
        subject=subject,
        question=question,
        context=None,
        doc_type=None,
        document_ids=[d.id for d in docs],
        triage=triage,
        result=result,
        summary=result.get("ozet") or "",
        draft=(belge.get("icerik") or None) if isinstance(belge, dict) else None,
        confidence=float(result.get("guven") or 0.0),
        needs_lawyer=bool(result.get("avukat_gerekli", True)),
        status="done" if run["ok"] else "error",
        error=run.get("error"),
        model=run.get("model"),
        tokens_in=run.get("tokens_in", 0) + triage_run.get("tokens_in", 0),
        tokens_out=run.get("tokens_out", 0) + triage_run.get("tokens_out", 0),
    )
    db.add(consultation)
    agent.consult_count = (agent.consult_count or 0) + 1
    db.commit()
    db.refresh(consultation)

    return {
        "triage": triage,
        "routed_to": {
            "slug": agent.slug,
            "name": agent.name,
            "title": agent.title,
            "icon": agent.icon,
            "color": agent.color,
        },
        "auto_routed": payload.agent_slug is None,
        "consultation": _consultation_out(consultation),
        "documents": [_document_out(d) for d in docs],
    }


# ─────────────────────────────────────────────────────────────
# Özet
# ─────────────────────────────────────────────────────────────

@router.get("/stats")
def legal_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.query(LegalAgent).count()
    active = db.query(LegalAgent).filter(LegalAgent.is_active == True).count()  # noqa: E712
    consultations = db.query(LegalConsultation).count()
    drafts = db.query(LegalConsultation).filter(LegalConsultation.draft.isnot(None)).count()
    open_matters = db.query(LegalMatter).filter(LegalMatter.status == "open").count()
    documents = db.query(LegalDocument).count()
    open_deadlines = db.query(LegalDeadline).filter(LegalDeadline.status == "open").count()
    overdue = (
        db.query(LegalDeadline)
        .filter(LegalDeadline.status == "open", LegalDeadline.due_date < date.today())
        .count()
    )
    return {
        "agents_total": total,
        "agents_active": active,
        "consultations": consultations,
        "drafts": drafts,
        "open_matters": open_matters,
        "documents": documents,
        "open_deadlines": open_deadlines,
        "overdue_deadlines": overdue,
        "templates": len(TEMPLATES),
        "ai_configured": legal_ai.is_configured(),
    }
