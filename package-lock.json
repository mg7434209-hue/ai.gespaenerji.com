"""Workspace (iş kolu) endpoint'leri."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Workspace, User
from app.auth.dependencies import get_current_user


router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Workspace).order_by(Workspace.id).all()


@router.get("/{slug}", response_model=WorkspaceResponse)
def get_workspace(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws = db.query(Workspace).filter(Workspace.slug == slug).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace bulunamadı")
    return ws


@router.get("/{slug}/stats")
def workspace_stats(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Workspace KPI özeti — dashboard için."""
    from app.models import Lead

    ws = db.query(Workspace).filter(Workspace.slug == slug).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace bulunamadı")

    leads_q = db.query(Lead).filter(Lead.workspace_id == ws.id)
    total = leads_q.count()
    new = leads_q.filter(Lead.status == "new").count()
    contacted = leads_q.filter(Lead.status == "contacted").count()
    offered = leads_q.filter(Lead.status == "offered").count()
    won = leads_q.filter(Lead.status == "won").count()
    lost = leads_q.filter(Lead.status == "lost").count()

    return {
        "workspace": ws.slug,
        "leads": {
            "total": total,
            "new": new,
            "contacted": contacted,
            "offered": offered,
            "won": won,
            "lost": lost,
            "conversion_rate": round((won / total * 100) if total else 0, 1),
        },
    }
