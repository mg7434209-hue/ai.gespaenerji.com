"""Lead (potansiyel müşteri) endpoint'leri."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lead, Workspace, User
from app.auth.dependencies import get_current_user


router = APIRouter(prefix="/api/leads", tags=["leads"])


ALLOWED_STATUSES = {"new", "contacted", "offered", "won", "lost"}


class LeadCreate(BaseModel):
    workspace_slug: str
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    package_interest: Optional[str] = None
    estimated_value: Optional[int] = None


class LeadUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    package_interest: Optional[str] = None
    estimated_value: Optional[int] = None


class LeadResponse(BaseModel):
    id: int
    workspace_id: int
    full_name: str
    phone: str
    email: Optional[str]
    address: Optional[str]
    city: Optional[str]
    status: str
    source: Optional[str]
    notes: Optional[str]
    package_interest: Optional[str]
    estimated_value: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_contact_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("", response_model=list[LeadResponse])
def list_leads(
    workspace: Optional[str] = Query(None, description="Workspace slug ile filtrele"),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Lead)
    if workspace:
        ws = db.query(Workspace).filter(Workspace.slug == workspace).first()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace bulunamadı")
        q = q.filter(Lead.workspace_id == ws.id)
    if status:
        q = q.filter(Lead.status == status)
    return q.order_by(Lead.created_at.desc()).limit(limit).all()


@router.post("", response_model=LeadResponse)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws = db.query(Workspace).filter(Workspace.slug == data.workspace_slug).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace bulunamadı")

    # Whitelist — workspace_slug'ı Lead modeline yazma
    lead_data = data.model_dump(exclude={"workspace_slug"}, exclude_none=True)
    lead = Lead(workspace_id=ws.id, **lead_data)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")

    update = data.model_dump(exclude_none=True)
    if "status" in update and update["status"] not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail=f"Geçersiz status. İzinli: {ALLOWED_STATUSES}")

    for k, v in update.items():
        setattr(lead, k, v)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    db.delete(lead)
    db.commit()
    return {"ok": True}
