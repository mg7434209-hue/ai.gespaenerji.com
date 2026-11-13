"""Onaylı yönetim: öneri → onay → GitHub PR (ağ yok; GitHub sahte istemciyle)."""
import base64
from unittest import mock

import httpx
import pytest

from app.config import settings
from app.models_jarvis import JarvisAction
from app.services import actions, github, jarvis_tools, sites

CONFIG = '''window.GESPA = { config: {
  b2b: { stock: [ { id: "x", stock: 500, price: 1 } ] },
  packages: [
    {
      id: "kit-285w", icon: "🧰", group: "offgrid",
      price: 487.8, currency: "USD",   // ₺24.000 @ 49,2
      name: "240W Güneş Paneli Paketi",
    },
    {
      id: "boost-mppt", icon: "🔌", group: "accessory",
      // ₺7.200 NET: eski liste price: 154.47 idi
      price: 146.34, currency: "USD", noCartDiscount: true, freeShipping: true,  // ₺7.200 net @ 49,2
      name: "BOOST MPPT",
    },
    {
      id: "led-10w", group: "lighting",
      stock: 12, price: 2.64, currency: "USD", noCartDiscount: true,
      bulk: { min: 5, price: 2.4 },                     // ₺120 @ 49,2 (5+ adet)
      oldPrice: 3.1,
      name: "LED",
    },
  ],
} };
'''

SUMMARY = {"fx": {"rate": 49.2}, "catalog": {"products": [
    {"id": "kit-285w", "name": "240W Paket", "currency": "USD", "price": 487.8, "priceTL": 24000, "stock": None, "oldPrice": None},
    {"id": "boost-mppt", "name": "BOOST MPPT", "currency": "USD", "price": 146.34, "priceTL": 7200, "stock": None, "oldPrice": None},
    {"id": "led-10w", "name": "LED", "currency": "USD", "price": 2.64, "priceTL": 130, "stock": 12, "oldPrice": 3.1},
    {"id": "teklif", "name": "Teklif ürünü", "currency": "USD", "price": None, "priceTL": None, "stock": None},
]}}


@pytest.fixture()
def api(db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth.dependencies import get_current_user
    from app.database import get_db
    from app.routers import jarvis as jr
    app = FastAPI()
    app.include_router(jr.router)
    app.dependency_overrides[get_current_user] = lambda: object()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture(autouse=True)
def summary():
    with mock.patch.object(sites, "fetch_summary", return_value=SUMMARY):
        yield


# ── config.js düzenleme ──────────────────────────────────────

def test_edit_price_touches_only_that_product():
    out = actions.edit_config(CONFIG, "boost-mppt", price_usd=152.44, note="₺7.500 @ 49,2")
    assert 'price: 152.44, currency: "USD", noCartDiscount: true, freeShipping: true,  // ₺7.500 @ 49,2' in out
    assert "price: 487.8" in out and "eski liste price: 154.47 idi" in out          # komşu ürün ve yorum aynen
    assert len(out.splitlines()) == len(CONFIG.splitlines())
    assert actions.read_product(out, "boost-mppt")["price"] == 152.44
    # yalnız tek satır değişti
    diff = [i for i, (a, b) in enumerate(zip(CONFIG.splitlines(), out.splitlines())) if a != b]
    assert len(diff) == 1


def test_edit_skips_bulk_and_old_price():
    info = actions.read_product(CONFIG, "led-10w")
    assert info == {"price": 2.64, "stock": 12, "has_bulk": True, "has_old_price": True}
    out = actions.edit_config(CONFIG, "led-10w", price_usd=3)
    assert "stock: 12, price: 3, currency" in out and "bulk: { min: 5, price: 2.4 }" in out and "oldPrice: 3.1" in out


def test_edit_stock_set_insert_remove():
    assert "stock: 0, price: 2.64" in actions.edit_config(CONFIG, "led-10w", stock=0)
    out = actions.edit_config(CONFIG, "boost-mppt", stock=3)
    assert "stock: 3, price: 146.34" in out
    assert "stock: 500" in out                                   # packages dışındaki stok alanına dokunulmaz
    assert actions.read_product(out, "boost-mppt")["stock"] == 3
    out = actions.edit_config(CONFIG, "led-10w", stock=None)
    assert "      price: 2.64, currency" in out and actions.read_product(out, "led-10w")["stock"] is None
    with pytest.raises(actions.ActionError):
        actions.edit_config(CONFIG, "yok-boyle-urun", stock=1)


def test_tl_round_matches_site_rule():
    assert [actions.tl_round(v) for v in (7231, 995, 24049, 10050, 1024.9)] == [7250, 1000, 24000, 10100, 1000]


# ── Öneri ────────────────────────────────────────────────────

def test_proposal_changes_nothing_and_explains(db):
    out = jarvis_tools.run_tool(db, "propose_change", {"site": "gespaenerji", "product_id": "boost-mppt", "new_price_tl": 7500})
    assert out["applied"] is False and out["status"] == "proposed" and "₺7.200 → ₺7.500" in out["summary"]
    row = db.query(JarvisAction).one()
    assert row.payload["new"]["usd"] == 152.44 and row.payload["old"]["usd"] == 146.34 and row.status == "proposed"
    assert jarvis_tools.run_tool(db, "list_proposals", {})["pending"] == 1


def test_proposal_guards(db):
    run = lambda **kw: jarvis_tools.run_tool(db, "propose_change", {"site": "gespaenerji", **kw})  # noqa: E731
    for bad in ({"product_id": "yok", "new_stock": 1},
                {"product_id": "boost-mppt"},                                        # ne fiyat ne stok
                {"product_id": "boost-mppt", "new_price_tl": 7500, "new_stock": 1},  # ikisi birden
                {"product_id": "boost-mppt", "new_price_tl": 7200},                  # aynı fiyat
                {"product_id": "teklif", "new_price_tl": 100},                       # fiyatsız ürün
                {"product_id": "led-10w", "new_stock": 12},                          # aynı stok
                {"product_id": "led-10w", "new_stock": -1}):
        with pytest.raises(jarvis_tools.ToolInputError):
            run(**bad)
    assert db.query(JarvisAction).count() == 0
    big = run(product_id="boost-mppt", new_price_tl=72000)                           # sesle yanlış anlaşılan rakam
    assert any("Büyük değişiklik" in w for w in big["warnings"])
    zero = run(product_id="led-10w", new_stock=0)
    assert any("satışa kapanır" in w for w in zero["warnings"])
    with mock.patch.object(sites, "fetch_summary", return_value={"error": "siteye ulaşılamadı"}):
        with pytest.raises(jarvis_tools.ToolInputError):
            run(product_id="boost-mppt", new_stock=5)


# ── Onay → GitHub ────────────────────────────────────────────

class FakeGitHub:
    """GitHub API'sinin kullanılan dört ucunu taklit eder ve yazılanları saklar."""
    def __init__(self, content=CONFIG):
        self.content, self.calls, self.written = content, [], None
        self.client = httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(self.handle))

    def handle(self, req: httpx.Request) -> httpx.Response:
        import json
        path = req.url.path
        self.calls.append((req.method, path))
        if req.method == "GET" and path.endswith("/contents/assets/config.js"):
            if req.headers.get("accept") == "application/vnd.github.raw":
                return httpx.Response(200, text=self.content)
            return httpx.Response(200, json={"sha": "blobsha"})
        if req.method == "GET" and "/git/ref/heads/" in path:
            return httpx.Response(200, json={"object": {"sha": "headsha"}})
        if req.method == "GET":
            return httpx.Response(200, json={"default_branch": "yayin"})
        body = json.loads(req.content)
        if path.endswith("/git/refs"):
            self.branch = body["ref"]
            return httpx.Response(201, json={})
        if req.method == "PUT":
            self.written = base64.b64decode(body["content"]).decode("utf-8")
            self.put = body
            return httpx.Response(200, json={})
        self.pr = body
        return httpx.Response(201, json={"html_url": "https://github.com/x/y/pull/9"})


def test_approve_opens_pr_with_single_line_change(db):
    jarvis_tools.run_tool(db, "propose_change", {"site": "gespaenerji", "product_id": "boost-mppt", "new_price_tl": 7500})
    gh = FakeGitHub()
    a = actions.approve(db, db.query(JarvisAction).one(), client=gh.client)
    assert (a.status, a.pr_url, a.error) == ("pr_open", "https://github.com/x/y/pull/9", None)
    assert gh.branch.startswith("refs/heads/jarvis/") and gh.pr["base"] == "yayin" and gh.put["sha"] == "blobsha"
    assert actions.read_product(gh.written, "boost-mppt")["price"] == 152.44
    assert len([1 for x, y in zip(CONFIG.splitlines(), gh.written.splitlines()) if x != y]) == 1
    with pytest.raises(actions.ActionError):                    # ikinci kez onaylanamaz
        actions.approve(db, a, client=gh.client)


def test_approve_refuses_when_value_changed_or_bulk(db):
    run = lambda **kw: jarvis_tools.run_tool(db, "propose_change", {"site": "gespaenerji", **kw})  # noqa: E731
    run(product_id="boost-mppt", new_price_tl=7500)
    gh = FakeGitHub(CONFIG.replace("price: 146.34", "price: 150"))   # biri arada değiştirmiş
    a = actions.approve(db, db.query(JarvisAction).one(), client=gh.client)
    assert a.status == "failed" and "değişmiş" in a.error and gh.written is None
    assert not any(m in ("PUT", "POST") for m, _ in gh.calls)        # GitHub'a hiçbir şey yazılmadı
    run(product_id="led-10w", new_price_tl=150)
    b = actions.approve(db, db.query(JarvisAction).order_by(JarvisAction.id.desc()).first(), client=FakeGitHub().client)
    assert b.status == "failed" and "5'li" in b.error


def test_endpoints_need_token_and_jarvis_cannot_approve(api, db):
    jarvis_tools.run_tool(db, "propose_change", {"site": "gespaenerji", "product_id": "led-10w", "new_stock": 3})
    lst = api.get("/api/jarvis/actions").json()
    assert lst["can_approve"] is False and lst["actions"][0]["summary"] == "LED: stok 12 adet → 3 adet"
    aid = lst["actions"][0]["id"]
    with mock.patch.object(settings, "jarvis_github_token", ""):
        assert api.post(f"/api/jarvis/actions/{aid}/approve").status_code == 400     # belirteç yok
    assert api.post("/api/jarvis/actions/9999/approve").status_code == 404
    assert api.post(f"/api/jarvis/actions/{aid}/reject").json()["status"] == "rejected"
    assert api.post(f"/api/jarvis/actions/{aid}/approve").status_code == 400         # reddedilen onaylanamaz
    # JARVIS'in araç listesinde onaylayan/yazan başka araç yok
    assert not [n for n in jarvis_tools.HANDLERS if "approve" in n or "reject" in n or "merge" in n]
    assert github.configured() is False
