"""Hukuk Ofisi endpoint'leri — avukat ajan serisi, danışmalar ve dosyalar."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.legal_agents import DEPARTMENTS, DISCLAIMER, LEGAL_AGENT_MAP, MODES
from app.models import User
from app.models_legal import LegalAgent, LegalConsultation, LegalMatter
from app.services.legal_ai import legal_ai


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


class ConsultRequest(BaseModel):
    agent_slug: str
    mode: str = "danisma"
    subject: str = ""
    question: str = Field(min_length=10, max_length=8000)
    context: Optional[str] = Field(default=None, max_length=60000)
    doc_type: Optional[str] = None
    matter_id: Optional[int] = None


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
    created_at: datetime


class MatterRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    counterparty: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class MatterResponse(BaseModel):
    id: int
    title: str
    counterparty: str | None = None
    reference: str | None = None
    status: str
    notes: str | None = None
    consultation_count: int = 0
    created_at: datetime
    updated_at: datetime


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

    run = legal_ai.run(
        agent={**spec, "model": agent.model},
        mode=mode,
        question=payload.question,
        context=payload.context,
        doc_type=payload.doc_type,
        subject=payload.subject,
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
    return [
        MatterResponse(
            id=m.id,
            title=m.title,
            counterparty=m.counterparty,
            reference=m.reference,
            status=m.status,
            notes=m.notes,
            consultation_count=len(m.consultations),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in rows
    ]


@router.post("/matters", response_model=MatterResponse)
def create_matter(
    payload: MatterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = LegalMatter(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return MatterResponse(
        id=m.id,
        title=m.title,
        counterparty=m.counterparty,
        reference=m.reference,
        status=m.status,
        notes=m.notes,
        consultation_count=0,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


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
    return {
        "agents_total": total,
        "agents_active": active,
        "consultations": consultations,
        "drafts": drafts,
        "open_matters": open_matters,
        "ai_configured": legal_ai.is_configured(),
    }
