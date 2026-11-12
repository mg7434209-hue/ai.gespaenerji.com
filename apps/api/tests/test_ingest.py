"""Sipariş defteri: POST /api/ingest/orders + defterden okuma."""
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.models_orders import SiteApplication, SiteOrder
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


# ── gesmarketim siparişleri ve başvuru defteri ───────────────

def test_gesmarketim_orders_and_empty_ledger_fallback(api, db):
    summary = {"orders": {"count": 4, "unpaid": 2, "open": 3, "items": []}, "catalog": {}, "kur": {}, "visitors": {}}
    with mock.patch.object(sites, "fetch_summary", return_value=summary):
        # Site deftere henüz hiç yazmadıysa özetteki siparişler kalır
        assert sites.summary_with_ledger(db, "gesmarketim")["orders"]["count"] == 4
        api.post("/api/ingest/orders", json={"site": "gesmarketim", "orders": [
            _order(ref="GM1", channel="havale", status="pending", fulfilled=False),
            _order(ref="GM2", channel="kart", status="paid", paidTL=7200, fulfilled=True),
        ]}, headers={"X-Ingest-Token": TOKEN})
        card = sites.card("gesmarketim", sites.summary_with_ledger(db, "gesmarketim"))
    assert (card["orders_30d"], card["orders_unpaid_30d"], card["orders_open_30d"], card["orders_24h"]) == (2, 1, 1, 2)


def test_applications_ledger_has_no_pii(api, db):
    h = {"X-Ingest-Token": TOKEN}
    app_ = {"ref": "abc123def456", "createdAt": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            "city": "Antalya", "district": "Manavgat", "package": "Superbox 100 GB", "monthlyTL": 899,
            "source": "hero", "coverage": "covered", "covered": True,
            "name": "Ayşe Gizli", "phone": "05551112233", "address": "Gizli Sok. 1"}
    assert api.post("/api/ingest/applications", json={"site": "amazon", "applications": []}, headers=h).status_code == 400
    assert api.post("/api/ingest/applications", json={"site": "internetbasvuru", "applications": [app_]}).status_code == 403
    for _ in range(2):  # aynı başvuru iki kez gelirse tek kayıt
        r = api.post("/api/ingest/applications", json={"site": "internetbasvuru", "applications": [app_]}, headers=h)
        assert r.status_code == 200
    row = db.query(SiteApplication).one()
    dump = repr({c.name: getattr(row, c.name) for c in SiteApplication.__table__.columns})
    for leak in ("Ayşe", "0555", "Gizli Sok"):
        assert leak not in dump
    with mock.patch.object(settings, "order_ingest_token", TOKEN):
        card = sites.ledger_card(db, "internetbasvuru")
        out = jarvis_tools.run_tool(db, "site_applications", {"site": "internetbasvuru"})
    assert (card["ok"], card["leads_24h"], card["leads_30d"], card["covered"]) == (True, 1, 1, 1)
    assert card["by_city"] == [{"name": "Antalya", "count": 1}]
    assert out["count"] == 1 and out["applications"][0]["district"] == "Manavgat" and out["applications"][0]["created_label"]
