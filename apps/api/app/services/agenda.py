"""Ajanda — yaklaşan/geçmiş hukuki süreler ve duruşmalar.

Tek hesap: /api/legal/agenda, komuta ajanı ve sabah brifingi aynı fonksiyonu
okur; iki yerde ayrı ayrı yazılırsa sayılar birbirini tutmaz.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models_legal import LegalDeadline, LegalMatter
from app.timeutil import day_label, today_tr


def deadline_dict(d: LegalDeadline, today: date) -> dict:
    return {
        "id": d.id,
        "title": d.title,
        "due_date": d.due_date,
        "due_label": day_label(d.due_date),
        "days_left": (d.due_date - today).days,
        "matter_id": d.matter_id,
        "matter_title": d.matter.title if d.matter else None,
        "basis": d.basis,
        "critical": d.critical,
        "status": d.status,
    }


def build_agenda(
    db: Session,
    days: int = 30,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> dict:
    """Açık süreler (geçmişler dahil, `end`'e kadar) + `start`..`end` duruşmaları.

    `start`/`end` verilmezse bugünden itibaren `days` gün.
    """
    today = today_tr()
    start = start or today
    end = end or (today + timedelta(days=days))

    rows = (
        db.query(LegalDeadline)
        .filter(LegalDeadline.status == "open", LegalDeadline.due_date <= end)
        .order_by(LegalDeadline.due_date)
        .all()
    )
    hearings = (
        db.query(LegalMatter)
        .filter(
            LegalMatter.next_hearing.isnot(None),
            LegalMatter.next_hearing >= start,
            LegalMatter.next_hearing <= end,
        )
        .order_by(LegalMatter.next_hearing)
        .all()
    )
    return {
        "today": today,
        "start": start,
        "end": end,
        "deadlines": rows,
        "overdue": len([d for d in rows if d.due_date < today]),
        "critical": len([d for d in rows if d.critical and d.due_date >= today]),
        "hearings": [
            {"matter_id": m.id, "title": m.title, "court": m.court,
             "date": m.next_hearing, "date_label": day_label(m.next_hearing),
             "days_left": (m.next_hearing - today).days}
            for m in hearings
        ],
    }
