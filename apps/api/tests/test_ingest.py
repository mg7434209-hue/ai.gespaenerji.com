"""Sipariş defteri: POST /api/ingest/orders + defterden okuma."""
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.models_orders import SiteOrder
from app.services import jarvis_tools, sites

TOKEN = "ingest-belirteci-0123456789abcdefghijk"


def _order(**kw):
    base = {"ref": "GSP-1", "channel": "sepet", "status": "pending",
            "createdAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "totalTL": 7200, "items": [{"id": "boost-mppt", "name": "BOOST MPPT", "qty": 1, "unitTL": 7200}]}
    base.update(kw)
    return base


@pytest.fixture()
def api(db):
    from app.database import get_db
    from app.routers import ingest
    app = FastAPI()
    app.include_router(ingest.router)
    app.dependency_overrides[get_db] = lambda: db
    with mock.patch.object(settings, "order_ingest_token", TOKEN):
        yield TestClient(app)


def test_token_required(api):
    with mock.patch.object(settings, "order_ingest_token", ""):
        assert api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": []}).status_code == 503
    assert api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": []}).status_code == 403
    r = api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": []}, headers={"X-Ingest-Token": "yanlis"})
    assert r.status_code == 403
    r = api.post("/api/ingest/orders", json={"site": "amazon", "orders": []}, headers={"X-Ingest-Token": TOKEN})
    assert r.status_code == 400


def test_upsert_is_idempotent_and_updates_status(api, db):
    h = {"X-Ingest-Token": TOKEN}
    assert api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": [_order()]}, headers=h).json()["upserted"] == 1
    api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": [_order(status="paid", paidTL=7200)]}, headers=h)
    api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": [_order(status="paid", paidTL=7200)]}, headers=h)
    rows = db.query(SiteOrder).all()
    assert len(rows) == 1 and rows[0].status == "paid" and rows[0].paid_tl == 7200
    assert rows[0].created_at.tzinfo is None  # UTC, saat dilimsiz


def test_unknown_fields_and_pii_are_dropped(api, db):
    leaky = _order(buyer={"ad": "Ayşe Gizli", "tel": "05551112233", "tckn": "12345678901"},
                   items=[{"id": "x", "name": "Panel", "qty": 1, "adres": "Gizli Sok."}])
    api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": [leaky]}, headers={"X-Ingest-Token": TOKEN})
    row = db.query(SiteOrder).one()
    dump = repr({c.name: getattr(row, c.name) for c in SiteOrder.__table__.columns})
    for leak in ("Ayşe", "0555", "12345678901", "Gizli Sok"):
        assert leak not in dump


def test_ledger_feeds_tools_even_when_site_is_down(api, db):
    api.post("/api/ingest/orders", json={"site": "gespaenerji", "orders": [
        _order(ref="GSP-A", status="paid", paidTL=7200),
        _order(ref="GSP-B", status="pending", createdAt=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat()),
    ]}, headers={"X-Ingest-Token": TOKEN})
    with mock.patch.object(settings, "order_ingest_token", TOKEN), \
         mock.patch.object(sites, "fetch_summary", return_value={"error": "siteye ulaşılamadı (ConnectError)"}):
        out = jarvis_tools.run_tool(db, "site_orders", {"site": "gespaenerji"})
        card = sites.card("gespaenerji", sites.summary_with_ledger(db, "gespaenerji"))
    assert [o["ref"] for o in out["orders"]] == ["GSP-A", "GSP-B"]
    assert "defteri" in out["source"] and out["orders"][0]["created_label"]
    assert card["ok"] is False and card["orders_30d"] == 2 and card["orders_24h"] == 1


def test_ledger_off_uses_summary(db):
    with mock.patch.object(settings, "order_ingest_token", ""), \
         mock.patch.object(sites, "fetch_summary", return_value={"orders": {"count": 9, "items": []}}):
        d = sites.summary_with_ledger(db, "gespaenerji")
    assert d["orders"]["count"] == 9
