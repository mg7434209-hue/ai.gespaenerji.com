"""İki ticari sitenin özet okuması — services/sites.py ve JARVIS site araçları."""
from datetime import datetime, timedelta, timezone
from unittest import mock

import httpx
import pytest

from app.config import settings
from app.services import jarvis_tools, sites

NOW = datetime.now(timezone.utc)
GESPA = {
    "site": "gespaenerji.com", "dataPersistent": False,
    "orders": {"days": 30, "count": 2, "byStatus": {"paid": 1, "pending": 1}, "items": [
        {"ref": "GSP-1", "status": "paid", "createdAt": (NOW - timedelta(hours=2)).isoformat(), "totalTL": 7200,
         "items": [{"id": "boost-mppt", "name": "BOOST MPPT", "qty": 1}]},
        {"ref": "GSP-0", "status": "pending", "createdAt": (NOW - timedelta(days=3)).isoformat(), "totalTL": 1000, "items": []},
    ]},
    "qa": {"pending": 1, "items": [{"id": "a1", "text": "Soru?"}]},
    "visitors": {"total": 50, "day": 12, "online": 1},
    "fx": {"rate": 49.2}, "pay": {"card": True, "mail": True},
    "catalog": {"count": 21, "campaign": {"endsAt": None, "live": False},
                "alerts": [{"type": "low_stock", "id": "unv", "name": "UNV", "stock": 1}], "products": []},
}
GESM = {
    "orders": {"days": 30, "count": 1, "unpaid": 1, "open": 1, "items": [
        {"no": "GM1", "createdAt": (NOW - timedelta(hours=30)).isoformat(), "total": 500, "items": []}]},
    "catalog": {"count": 82, "categories": [], "outOfStock": [{"id": "a"}] * 5, "noImage": [{"id": "b"}] * 11, "overrides": []},
    "kur": {"usdTry": 41.5}, "visitors": {"count": 300},
}


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def conf():
    sites.clear_cache()
    with mock.patch.object(settings, "gespa_os_token", "t" * 40), \
         mock.patch.object(settings, "gesm_os_token", "u" * 40):
        yield
    sites.clear_cache()


def test_fetch_sends_token_and_caches():
    calls = []

    def h(req):
        calls.append(req)
        return httpx.Response(200, json=GESPA)
    c = _client(h)
    d = sites.fetch_summary("gespaenerji", client=c)
    assert d["orders"]["count"] == 2
    assert calls[0].headers["x-os-token"] == "t" * 40
    assert str(calls[0].url) == "https://www.gespaenerji.com/api/os/summary"
    sites.fetch_summary("gespaenerji", client=c)
    assert len(calls) == 1  # 60 sn önbellek
    sites.fetch_summary("gespaenerji", client=c, fresh=True)
    assert len(calls) == 2


@pytest.mark.parametrize("code,needle", [(403, "belirteç reddedildi"), (503, "OS_TOKEN tanımlı değil"),
                                         (404, "güncellenmemiş"), (500, "HTTP 500")])
def test_http_errors_are_explained(code, needle):
    d = sites.fetch_summary("gesmarketim", client=_client(lambda r: httpx.Response(code)))
    assert needle in d["error"]


def test_connection_error_does_not_raise():
    def h(req):
        raise httpx.ConnectError("yok")
    d = sites.fetch_summary("gespaenerji", client=_client(h))
    assert "ulaşılamadı" in d["error"]


def test_not_configured():
    with mock.patch.object(settings, "gesm_os_token", ""):
        d = sites.fetch_summary("gesmarketim")
    assert d["configured"] is False


def test_cards():
    g = sites.card("gespaenerji", GESPA)
    assert (g["orders_24h"], g["orders_30d"], g["orders_pending_30d"], g["qa_pending"], g["alerts"]) == (1, 2, 1, 1, 1)
    m = sites.card("gesmarketim", GESM)
    assert (m["orders_24h"], m["orders_unpaid_30d"], m["out_of_stock"], m["no_image"]) == (0, 1, 5, 11)
    e = sites.card("gesmarketim", {"error": "x"})
    assert e["ok"] is False and e["error"] == "x"


def test_tools_use_summary(db):
    def fake(site, **kw):
        return GESPA if site == "gespaenerji" else GESM
    with mock.patch.object(sites, "fetch_summary", side_effect=fake):
        ov = jarvis_tools.run_tool(db, "site_overview", {})
        assert [s["site"] for s in ov["sites"]] == ["gespaenerji", "gesmarketim"]
        orders = jarvis_tools.run_tool(db, "site_orders", {"site": "gespaenerji", "limit": 1})
        assert [o["ref"] for o in orders["orders"]] == ["GSP-1"]
        cat = jarvis_tools.run_tool(db, "site_catalog", {"site": "gesmarketim"})
        assert len(cat["out_of_stock"]) == 5
        qa = jarvis_tools.run_tool(db, "site_questions", {})
        assert qa["pending"] == 1
    with pytest.raises(jarvis_tools.ToolInputError):
        jarvis_tools.run_tool(db, "site_orders", {"site": "amazon"})


def test_site_error_reaches_model(db):
    with mock.patch.object(sites, "fetch_summary", return_value={"error": "siteye ulaşılamadı (ConnectError)"}):
        out = jarvis_tools.run_tool(db, "site_orders", {"site": "gesmarketim"})
    assert out["error"].startswith("siteye ulaşılamadı")
