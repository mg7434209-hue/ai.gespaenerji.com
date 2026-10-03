"""Adım 1: komuta ajanı — araçlar, tool use döngüsü, hafıza ve uç."""
import json
from datetime import timedelta
from unittest import mock

import anthropic
import httpx
import pytest
from anthropic.types.beta import BetaMessage
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.models import Lead, Workspace
from app.models_jarvis import JarvisConversation, JarvisMessage
from app.models_legal import LegalDeadline, LegalMatter
from app.services import jarvis, jarvis_tools
from app.timeutil import today_tr


def _msg(content, stop="end_turn", mid="m"):
    return BetaMessage.model_validate({
        "id": mid, "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": content, "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 20},
    })


class FakeClient:
    """client.beta.messages.create yerine sıralı yanıtlar döndürür, çağrıları kaydeder."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = mock.Mock()
        self.beta.messages.create.side_effect = self._create

    def _create(self, **kw):
        # Liste sonradan değişse de çağrı anındaki hâli kaydedilsin
        self.calls.append(json.loads(json.dumps(kw, default=str)))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture()
def data(db):
    today = today_tr()
    m = LegalMatter(title="Kira tahliye davası", counterparty="Ahmet Y.",
                    next_hearing=today + timedelta(days=3), status="open")
    db.add(m)
    db.flush()
    db.add_all([
        LegalDeadline(title="İstinaf dilekçesi", due_date=today - timedelta(days=2), matter_id=m.id),
        LegalDeadline(title="Ödeme emrine itiraz", due_date=today + timedelta(days=2), critical=True),
        LegalDeadline(title="Uzak süre", due_date=today + timedelta(days=40)),
        LegalDeadline(title="Kapanmış", due_date=today, status="done"),
    ])
    ws = Workspace(slug="solar", name="Solar Enerji")
    db.add(ws)
    db.flush()
    db.add_all([
        Lead(workspace_id=ws.id, full_name="Ayşe K.", phone="905550000001", status="new"),
        Lead(workspace_id=ws.id, full_name="Veli T.", phone="905550000002", status="offered"),
    ])
    db.commit()
    return {"matter": m, "today": today}


def _conv(db, channel="web"):
    c = JarvisConversation(channel=channel)
    db.add(c)
    db.commit()
    return c


# ── Araçlar ──────────────────────────────────────────────────

def test_get_agenda_default_week_includes_overdue(db, data):
    out = jarvis_tools.get_agenda(db, {})
    titles = [d["title"] for d in out["deadlines"]]
    assert titles == ["İstinaf dilekçesi", "Ödeme emrine itiraz"]
    assert out["overdue_count"] == 1
    assert out["hearings"][0]["title"] == "Kira tahliye davası"


def test_get_agenda_future_range_keeps_overdue_drops_earlier(db, data):
    t = data["today"]
    out = jarvis_tools.get_agenda(db, {"start_date": str(t + timedelta(days=30)),
                                       "end_date": str(t + timedelta(days=45))})
    titles = [d["title"] for d in out["deadlines"]]
    assert titles == ["İstinaf dilekçesi", "Uzak süre"]  # 2 gün sonraki süre aralık dışı
    assert out["hearings"] == []


def test_tool_input_validation(db, data):
    with pytest.raises(jarvis_tools.ToolInputError):
        jarvis_tools.run_tool(db, "get_agenda", {"start_date": "yarın"})
    with pytest.raises(jarvis_tools.ToolInputError):
        jarvis_tools.run_tool(db, "list_leads", {"status": "silindi"})
    with pytest.raises(jarvis_tools.ToolInputError):
        jarvis_tools.run_tool(db, "drop_table", {})


def test_matter_and_workspace_tools(db, data):
    mid = data["matter"].id
    m = jarvis_tools.get_matter(db, {"matter_id": mid})
    assert m["title"] == "Kira tahliye davası" and len(m["open_deadlines"]) == 1
    ms = jarvis_tools.list_matters(db, {"query": "tahliye"})
    assert ms["matters"][0]["open_deadlines"] == 1
    ws = jarvis_tools.list_workspaces(db, {})
    assert ws["workspaces"][0]["leads_by_status"] == {"new": 1, "offered": 1}
    leads = jarvis_tools.list_leads(db, {"status": "offered"})
    assert [l["name"] for l in leads["leads"]] == ["Veli T."]


def test_every_tool_is_read_only(db, data):
    """Faz 1 kuralı: hiçbir araç veritabanına yazmaz."""
    from sqlalchemy import event

    writes = []
    listener = lambda *a, **k: writes.append(1)  # noqa: E731
    event.listen(db, "before_flush", listener)
    try:
        for name in jarvis_tools.HANDLERS:
            inp = {"matter_id": data["matter"].id} if name == "get_matter" else {}
            jarvis_tools.run_tool(db, name, inp)
            db.flush()
        assert not db.new and not db.dirty and not db.deleted
    finally:
        event.remove(db, "before_flush", listener)


# ── Tool use döngüsü ─────────────────────────────────────────

def test_week_question_runs_tools_and_answers(db, data):
    client = FakeClient([
        _msg([
            {"type": "thinking", "thinking": "", "signature": "s1"},
            {"type": "tool_use", "id": "t1", "name": "get_agenda", "input": {}},
            {"type": "tool_use", "id": "t2", "name": "list_leads", "input": {"status": "new"}},
        ], stop="tool_use", mid="m1"),
        _msg([{"type": "text", "text": "Bu hafta: 1 gecikmiş süre, 1 duruşma."}], mid="m2"),
    ])
    conv = _conv(db)
    r = jarvis.ask(db, conv, "Bu hafta neyim var?", client=client)

    assert r.ok and r.text == "Bu hafta: 1 gecikmiş süre, 1 duruşma."
    assert r.tools == ["get_agenda", "list_leads"]

    first, second = client.calls
    # Sabit sistem promptu + araçlar, önbellek ve yedekleme ayarları
    assert first["system"] == second["system"] == jarvis.SYSTEM_PROMPT
    assert first["model"] == settings.jarvis_model
    assert first["output_config"] == {"effort": settings.jarvis_effort}
    assert first["cache_control"] == {"type": "ephemeral"}
    assert first["betas"] == [jarvis.FALLBACK_BETA] and first["fallbacks"] == "default"
    assert "tool_choice" not in first
    # "Şu an" bilgisi kullanıcı mesajında, sistem promptunda değil
    assert first["messages"][0]["content"][0]["text"].startswith("[Şu an: ")

    # İkinci çağrı: asistan blokları AYNEN geri gider (thinking imzası dahil),
    # iki araç sonucu TEK kullanıcı mesajında
    assert second["messages"][1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "s1"}
    results = second["messages"][2]["content"]
    assert [x["tool_use_id"] for x in results] == ["t1", "t2"]
    agenda = json.loads(results[0]["content"])
    assert [d["title"] for d in agenda["deadlines"]] == ["İstinaf dilekçesi", "Ödeme emrine itiraz"]

    rows = db.query(JarvisMessage).filter_by(conversation_id=conv.id).order_by(JarvisMessage.id).all()
    assert [x.role for x in rows] == ["user", "assistant", "user", "assistant"]
    assert [x.visible for x in rows] == [True, False, False, True]
    assert rows[0].display == "Bu hafta neyim var?"


def test_follow_up_replays_history_append_only(db, data):
    conv = _conv(db)
    c1 = FakeClient([_msg([{"type": "text", "text": "Merhaba."}])])
    jarvis.ask(db, conv, "Selam", client=c1)
    c2 = FakeClient([_msg([{"type": "text", "text": "Tamam."}])])
    jarvis.ask(db, conv, "Dosyalarım?", client=c2)
    msgs = c2.calls[0]["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[1]["content"] == [{"type": "text", "text": "Merhaba."}]


def test_fallbacks_can_be_disabled(db, data):
    client = FakeClient([_msg([{"type": "text", "text": "ok"}])])
    with mock.patch.object(settings, "jarvis_fallbacks", False):
        jarvis.ask(db, _conv(db), "selam", client=client)
    assert "fallbacks" not in client.calls[0] and "betas" not in client.calls[0]


def test_bad_tool_input_returns_error_result(db, data):
    client = FakeClient([
        _msg([{"type": "tool_use", "id": "t1", "name": "get_agenda",
               "input": {"start_date": "geçen salı"}}], stop="tool_use"),
        _msg([{"type": "text", "text": "Tarihi anlayamadım."}]),
    ])
    jarvis.ask(db, _conv(db), "Geçen salıdan beri ne var?", client=client)
    res = client.calls[1]["messages"][-1]["content"][0]
    assert res["is_error"] is True and "YYYY-AA-GG" in res["content"]


def test_api_error_closes_turn_and_keeps_alternation(db, data):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.InternalServerError("boom", response=httpx.Response(500, request=req), body=None)
    conv = _conv(db)
    r = jarvis.ask(db, conv, "Bugün ne var?", client=FakeClient([err]))
    assert not r.ok and "API 500" in r.text
    roles = [m.role for m in db.query(JarvisMessage).filter_by(conversation_id=conv.id).order_by(JarvisMessage.id)]
    assert roles == ["user", "assistant"]


def test_refusal_is_not_shown_as_answer(db, data):
    r = jarvis.ask(db, _conv(db), "x", client=FakeClient([_msg([], stop="refusal")]))
    assert not r.ok and "yanıt veremiyorum" in r.text


def test_step_limit(db, data):
    loop = [_msg([{"type": "tool_use", "id": f"t{i}", "name": "inbox_summary", "input": {}}],
                 stop="tool_use") for i in range(settings.jarvis_max_steps)]
    conv = _conv(db)
    r = jarvis.ask(db, conv, "döngü", client=FakeClient(loop))
    assert not r.ok and "adım sınırı" in r.text
    roles = [m.role for m in db.query(JarvisMessage).filter_by(conversation_id=conv.id).order_by(JarvisMessage.id)]
    assert roles[-1] == "assistant" and roles[-2] == "user"


# ── Uç ───────────────────────────────────────────────────────

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


def test_chat_endpoint_503_without_key(api):
    with mock.patch.object(settings, "anthropic_api_key", ""):
        r = api.post("/api/jarvis/chat", json={"message": "selam"})
    assert r.status_code == 503


def test_chat_endpoint_and_latest(api, db, data):
    fake = FakeClient([_msg([{"type": "text", "text": "Merhaba Mustafa."}])])
    with mock.patch.object(settings, "anthropic_api_key", "k"), \
         mock.patch.object(jarvis, "get_client", return_value=fake):
        r = api.post("/api/jarvis/chat", json={"message": "selam"})
    assert r.status_code == 200 and r.json()["reply"] == "Merhaba Mustafa."
    latest = api.get("/api/jarvis/conversations/latest").json()
    assert [m["text"] for m in latest["messages"]] == ["selam", "Merhaba Mustafa."]
