"""Hukuk Ofisi endpoint'leri — avukat ajan serisi, danışmalar ve dosyalar."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.legal_agents import DEPARTMENTS, DISCLAIMER, LEGAL_AGENT_MAP, MODES
from app.models import User
from app.models_legal import LegalAgent, LegalConsultation, LegalDocument, LegalMatter
from app.services import document_text
from app.services.document_text import UnsupportedDocument
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

    run = legal_ai.run(
        agent={**spec, "model": agent.model},
        mode=mode,
        question=payload.question,
        context=payload.context,
        doc_type=payload.doc_type,
        subject=payload.subject,
        attachments=attachments,
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
    return {
        "agents_total": total,
        "agents_active": active,
        "consultations": consultations,
        "drafts": drafts,
        "open_matters": open_matters,
        "documents": documents,
        "ai_configured": legal_ai.is_configured(),
    }
