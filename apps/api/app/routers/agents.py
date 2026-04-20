"""AI ajan endpoint'leri."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, User
from app.auth.dependencies import get_current_user


router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentResponse(BaseModel):
    id: int
    slug: str
    name: str
    department: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    model: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Agent).order_by(Agent.id).all()


@router.post("/{slug}/toggle")
def toggle_agent(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = db.query(Agent).filter(Agent.slug == slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Ajan bulunamadı")
    agent.is_active = not agent.is_active
    db.commit()
    return {"ok": True, "slug": slug, "is_active": agent.is_active}
