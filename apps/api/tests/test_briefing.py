"""Adım 2: sabah brifingi — pencere, günde bir kez, şablon/serbest metin, belirteç."""
import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from unittest import mock

import anthropic
import httpx
import pytest
from anthropic.types.beta import BetaMessage
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import timeutil
from app.config import settings
from app.models_jarvis import JarvisRun
from app.models_legal import LegalDeadline, LegalMatter
from app.models_whatsapp import WhatsAppConversation, WhatsAppMessage
from app.services import briefing, sites
from test_sites import GESM, GESPA

OWNER = "905551234567"


def _at(h, m=0):
    """Bugün Türkiye saatiyle h:m."""
    n = timeutil.now_tr()
    return n.replace(hour=h, minute=m, second=0, microsecond=0)


@pytest.fixture(autouse=True)
def site_data():
    """Siteler ağa çıkmadan, sabit özetle okunur."""
    with mock.patch.object(sites, "fetch_summary",
                           side_effect=lambda s, **k: GESPA if s == "gespaenerji" else GESM):
        yield


@pytest.fixture()
def wa():
    with mock.patch.object(settings, "jarvis_owner_phone", "+90 555 123 45 67"), \
         mock.patch.object(settings, "anthropic_api_key", ""), \
         mock.patch.object(briefing.whatsapp_client, "is_configured", return_value=True), \
         mock.patch.object(briefing.whatsapp_client, "send_text", new=mock.AsyncMock(return_value={})) as st, \
         mock.patch.object(briefing.whatsapp_client, "send_template", new=mock.AsyncMock(return_value={})) as tp:
        yield {"text": st, "template": tp}


@pytest.fixture()
def data(db):
    t = timeutil.today_tr()
    m = LegalMatter(title="Kira davası", next_hearing=t + timedelta(days=3))
    db.add(m)
    db.flush()
    db.add_all([
        LegalDeadline(title="İstinaf dilekçesi", due_date=t - timedelta(days=1), matter_id=m.id),
        LegalDeadline(title="Ödeme emrine itiraz", due_date=t + timedelta(days=2)),
    ])
    db.commit()


def run(coro):
    return asyncio.run(coro)


def test_summary_line_is_single_line_template_param(db, data):
    d = briefing.collect(db)
    line = briefing.summary_line(d)
    assert "\n" not in line and "\t" not in line and "    " not in line
    assert line == ("gespaenerji: 1 yeni sipariş, 1 bekleyen ödeme, 1 soru onay bekliyor, 1 ürün uyarısı; "
                    "gesmarketim: 0 yeni sipariş, 1 ödenmemiş, 5 ürün stokta yok; hukuk: 1 süre.")
    assert len(line) <= 300
    assert "\n" not in briefing.date_label(d)


def test_plain_text_is_site_first_legal_one_line(db, data):
    text = briefing.plain_text(briefing.collect(db))
    assert text.index("gespaenerji.com:") < text.index("gesmarketim.com:") < text.index("⚠ Hukuk")
    assert "UNV: stok azaldı (1 adet)" in text and "stokta olmayan ürün: 5" in text
    # Gelecek süreler ve duruşmalar brifinge girmez; yalnız geçen/bugün dolan
    assert "Ödeme emrine itiraz" not in text and "Kira davası" not in text
    assert "İstinaf dilekçesi" in text


def test_site_error_is_reported_not_zero(db):
    with mock.patch.object(sites, "fetch_summary", return_value={"error": "siteye ulaşılamadı (ConnectError)"}):
        d = briefing.collect(db)
    assert "veri alınamadı" in briefing.summary_line(d)
    assert "veri alınamadı (siteye ulaşılamadı" in briefing.plain_text(d)


def test_outside_window_skips(db, data, wa):
    with mock.patch.object(briefing, "now_tr", return_value=_at(7, 30)):
        r = run(briefing.run_morning(db))
    assert r["status"] == "skipped" and r["reason"] == "outside_window"
    wa["template"].assert_not_awaited()


def test_template_when_window_closed_then_once_per_day(db, data, wa):
    with mock.patch.object(briefing, "now_tr", return_value=_at(8, 0)):
        r1 = run(briefing.run_morning(db))
        r2 = run(briefing.run_morning(db))  # 08:30 yedek tetik
    assert r1 == {"status": "sent", "via": "template", "day": str(timeutil.today_tr())}
    assert r2["status"] == "skipped" and r2["reason"] == "already_sent"
    assert wa["template"].await_count == 1
    kw = wa["template"].await_args.kwargs
    assert kw["to"] == OWNER and kw["template_name"] == settings.brief_template_name
    params = kw["components"][0]["parameters"]
    assert [p["type"] for p in params] == ["text", "text"]
    row = db.query(JarvisRun).one()
    assert row.status == "sent" and row.via == "template" and "İstinaf" in row.text


def test_full_text_when_owner_wrote_in_last_24h(db, data, wa):
    conv = WhatsAppConversation(phone=OWNER)
    db.add(conv)
    db.flush()
    db.add(WhatsAppMessage(conversation_id=conv.id, direction="inbound", content_type="text",
                           content="selam", created_at=datetime.utcnow() - timedelta(hours=3)))
    db.commit()
    with mock.patch.object(briefing, "now_tr", return_value=_at(8, 1)):
        r = run(briefing.run_morning(db))
    assert r["via"] == "text"
    wa["template"].assert_not_awaited()
    assert "Günaydın" in wa["text"].await_args.kwargs["body"]


def test_failed_send_is_retried_by_backup_trigger(db, data, wa):
    wa["template"].side_effect = [RuntimeError("meta 500"), {}]
    with mock.patch.object(briefing, "now_tr", return_value=_at(8, 0)):
        r1 = run(briefing.run_morning(db))
    assert r1["status"] == "failed" and db.query(JarvisRun).one().status == "failed"
    with mock.patch.object(briefing, "now_tr", return_value=_at(8, 30)):
        r2 = run(briefing.run_morning(db))
    assert r2["status"] == "sent"
    db.expire_all()
    assert db.query(JarvisRun).one().status == "sent"


def test_missing_owner_phone(db, data):
    with mock.patch.object(settings, "jarvis_owner_phone", ""), \
         mock.patch.object(briefing, "now_tr", return_value=_at(8, 0)):
        r = run(briefing.run_morning(db))
    assert r["status"] == "error"


def test_compose_uses_brief_model_and_falls_back(db, data):
    d = briefing.collect(db)
    ok = mock.Mock()
    ok.beta.messages.create.return_value = BetaMessage.model_validate({
        "id": "m", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5",
        "content": [{"type": "text", "text": "Günaydın — model metni"}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1}})
    assert briefing.compose(d, ok) == "Günaydın — model metni"
    kw = ok.beta.messages.create.call_args.kwargs
    assert kw["model"] == settings.jarvis_brief_model == "claude-sonnet-5-5"
    assert "tools" not in kw  # brifing modeli veritabanına erişmez, veri hazır verilir

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    bad = mock.Mock()
    bad.beta.messages.create.side_effect = anthropic.InternalServerError(
        "x", response=httpx.Response(500, request=req), body=None)
    assert briefing.compose(d, bad) == briefing.plain_text(d)


def test_split_text_respects_limit():
    parts = briefing.split_text("a" * 50 + "\n" + "b" * 50, limit=60)
    assert parts == ["a" * 50, "b" * 50]
    assert all(len(p) <= 60 for p in briefing.split_text("x" * 130, limit=60))


# ── Uçlar ────────────────────────────────────────────────────

@pytest.fixture()
def api(db):
    from app.auth.dependencies import get_current_user
    from app.database import get_db
    from app.routers import jarvis as jr

    app = FastAPI()
    app.include_router(jr.router)
    app.dependency_overrides[get_current_user] = lambda: object()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_run_endpoint_token(api, db, data, wa):
    with mock.patch.object(settings, "brief_cron_token", ""):
        assert api.post("/api/jarvis/briefing/run").status_code == 503
    with mock.patch.object(settings, "brief_cron_token", "gizli-belirtec"):
        assert api.post("/api/jarvis/briefing/run").status_code == 403
        assert api.post("/api/jarvis/briefing/run", headers={"X-Brief-Token": "yanlis"}).status_code == 403
        with mock.patch.object(briefing, "now_tr", return_value=_at(8, 0)):
            r = api.post("/api/jarvis/briefing/run", headers={"X-Brief-Token": "gizli-belirtec"})
    assert r.status_code == 200 and r.json()["status"] == "sent"


def test_preview_endpoint(api, db, data):
    r = api.get("/api/jarvis/briefing/preview").json()
    assert len(r["template_params"]) == 2 and "Günaydın" in r["text"]


# ── Sahibin düğmesi (webhook) ────────────────────────────────

def _sig(body: bytes) -> str:
    return "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()


def test_owner_button_sends_full_briefing_not_customer_ai(db, data, wa):
    from app.routers import whatsapp as wh

    app = FastAPI()
    app.include_router(wh.router)
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    payload = {"entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": OWNER, "profile": {"name": "Mustafa"}}],
        "messages": [{"from": OWNER, "id": "wamid.btn", "type": "button",
                      "button": {"text": "Brifingi gönder", "payload": "brifing"}}],
    }}]}]}
    body = json.dumps(payload).encode()
    with mock.patch.object(wh, "SessionLocal", return_value=db), \
         mock.patch.object(db, "close"), \
         mock.patch.object(wh.whatsapp_client, "mark_as_read", new=mock.AsyncMock()), \
         mock.patch.object(wh, "_run_ai_analysis", new=mock.AsyncMock()) as ai:
        r = TestClient(app).post("/api/whatsapp/webhook", content=body,
                                 headers={"x-hub-signature-256": _sig(body)})
    assert r.status_code == 200
    ai.assert_not_awaited()
    assert "Günaydın" in wa["text"].await_args.kwargs["body"]
    assert db.query(WhatsAppMessage).one().content == "Brifingi gönder"
