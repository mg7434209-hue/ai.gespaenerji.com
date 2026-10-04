"""Adım 0: saat dilimi, ajanda, webhook imzası, admin şifre senkronu, üretim koruması."""
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app import timeutil
from app.config import Settings, settings
from app.models import User
from app.models_legal import LegalDeadline, LegalMatter
from app.models_whatsapp import WhatsAppMessage
from app.routers import whatsapp as wa
from app.services import agenda


# ── Saat dilimi ──────────────────────────────────────────────

def test_today_tr_is_istanbul_after_utc_midnight():
    # UTC 22:30 = Türkiye 01:30 → Türkiye'de ertesi gün
    utc = datetime(2026, 10, 3, 22, 30, tzinfo=timeutil.ZoneInfo("UTC"))
    with mock.patch.object(timeutil, "now_tr", return_value=utc.astimezone(timeutil.TZ)):
        assert timeutil.today_tr() == date(2026, 10, 4)


# ── Ajanda ───────────────────────────────────────────────────

def test_agenda_counts_overdue_and_hearings(db):
    today = timeutil.today_tr()
    m = LegalMatter(title="Kira davası", next_hearing=today + timedelta(days=3))
    db.add(m)
    db.flush()
    db.add_all([
        LegalDeadline(title="geçmiş", due_date=today - timedelta(days=1), matter_id=m.id),
        LegalDeadline(title="yakın", due_date=today + timedelta(days=2), critical=True),
        LegalDeadline(title="uzak", due_date=today + timedelta(days=60)),
        LegalDeadline(title="bitti", due_date=today, status="done"),
    ])
    db.commit()
    a = agenda.build_agenda(db, days=7)
    assert [d.title for d in a["deadlines"]] == ["geçmiş", "yakın"]
    assert a["overdue"] == 1 and a["critical"] == 1
    assert a["hearings"][0]["days_left"] == 3


# ── Webhook imzası ───────────────────────────────────────────

def _sig(body: bytes, secret="test-app-secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signature_valid_and_invalid():
    body = b'{"entry":[]}'
    assert wa.verify_signature(body, _sig(body))
    assert not wa.verify_signature(body, _sig(body, "baska"))
    assert not wa.verify_signature(body, None)
    assert not wa.verify_signature(body + b" ", _sig(body))


def test_missing_secret_rejected_in_production():
    with mock.patch.object(settings, "whatsapp_app_secret", ""), \
         mock.patch.object(settings, "environment", "production"):
        assert not wa.verify_signature(b"{}", None)


def _client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(wa.router)
    return TestClient(app)


def _inbound(text="Merhaba", wamid="wamid.1", frm="905551112233"):
    return {"entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": frm, "profile": {"name": "Test"}}],
        "messages": [{"from": frm, "id": wamid, "type": "text", "text": {"body": text}}],
    }}]}]}


def test_webhook_rejects_bad_signature(db):
    body = json.dumps(_inbound()).encode()
    r = _client().post("/api/whatsapp/webhook", content=body,
                       headers={"x-hub-signature-256": _sig(body, "yanlis")})
    assert r.status_code == 403
    assert db.query(WhatsAppMessage).count() == 0


def test_webhook_stores_then_runs_background(db):
    body = json.dumps(_inbound()).encode()
    calls = []

    async def fake_after(mid):
        calls.append(mid)

    with mock.patch.object(wa, "_after_inbound", fake_after):
        r = _client().post("/api/whatsapp/webhook", content=body,
                           headers={"x-hub-signature-256": _sig(body)})
    assert r.status_code == 200
    db.expire_all()
    msg = db.query(WhatsAppMessage).one()
    assert msg.content == "Merhaba" and calls == [msg.id]

    # Aynı wamid ikinci kez gelirse yeni iş açılmaz
    calls.clear()
    with mock.patch.object(wa, "_after_inbound", fake_after):
        _client().post("/api/whatsapp/webhook", content=body,
                       headers={"x-hub-signature-256": _sig(body)})
    assert calls == [] and db.query(WhatsAppMessage).count() == 1


# ── Admin şifresi ────────────────────────────────────────────

def test_admin_password_follows_env(db):
    from app import seed as seed_mod
    from app.auth.security import verify_password

    seed_mod.seed()
    db.expire_all()
    admin = db.query(User).filter(User.email == "admin@test.local").one()
    assert verify_password("ilk-sifre-123456", admin.password_hash)

    with mock.patch.object(settings, "admin_password", "yeni-sifre-987654"):
        seed_mod.seed()
    db.expire_all()
    admin = db.query(User).filter(User.email == "admin@test.local").one()
    assert verify_password("yeni-sifre-987654", admin.password_hash)
    assert not verify_password("ilk-sifre-123456", admin.password_hash)


def test_old_admin_deactivated_when_email_changes(db):
    from app import seed as seed_mod

    seed_mod.seed()
    with mock.patch.object(settings, "admin_email", "yeni@test.local"):
        seed_mod.seed()
    db.expire_all()
    old = db.query(User).filter(User.email == "admin@test.local").one()
    new = db.query(User).filter(User.email == "yeni@test.local").one()
    assert old.is_active is False and new.is_active is True


# ── Üretim koruması ──────────────────────────────────────────

def test_production_refuses_defaults():
    from app.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_JWT_SECRET
    s = Settings(environment="production", _env_file=None,
                 database_url="sqlite:///x.db", jwt_secret=DEFAULT_JWT_SECRET,
                 admin_password=DEFAULT_ADMIN_PASSWORD)
    problems = s.production_problems()
    assert len(problems) == 3


def test_production_accepts_strong_values():
    s = Settings(environment="production", _env_file=None,
                 database_url="postgresql://u:p@h/db",
                 jwt_secret="x" * 64, admin_password="cok-guclu-bir-sifre")
    assert s.production_problems() == []


def test_development_has_no_guard():
    assert Settings(environment="development", _env_file=None).production_problems() == []


# ── Healthcheck ──────────────────────────────────────────────

def test_health_ok_and_db_failure_returns_503():
    import main
    c = TestClient(main.app)
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

    class Broken:
        def connect(self):
            raise RuntimeError("db yok")
    with mock.patch.object(main, "engine", Broken()):
        r = c.get("/api/health")
    assert r.status_code == 503 and r.json()["status"] == "db_error"


def test_railway_json_healthcheck():
    import json as _j
    from pathlib import Path
    cfg = _j.loads((Path(__file__).resolve().parents[3] / "railway.json").read_text())
    assert cfg["deploy"]["healthcheckPath"] == "/api/health"
    assert cfg["build"]["builder"] == "DOCKERFILE"


# ── Türkçe tarih etiketleri (gün adı modele hesaplatılmaz) ──────

def test_day_labels_known_dates():
    assert timeutil.day_label(date(2026, 10, 4)) == "4 Eki Paz"
    assert timeutil.day_label(date(2026, 10, 5)) == "5 Eki Pzt"
    assert timeutil.day_label_long(date(2026, 10, 4)) == "4 Ekim 2026 Pazar"
    # UTC 22:30 → Türkiye ertesi gün 01:30
    assert timeutil.ts_label("2026-10-03T22:30:00Z") == "4 Eki Paz 01:30"
    assert timeutil.ts_label("2026-10-03T22:30:00") == "4 Eki Paz 01:30"  # saat dilimsiz = UTC
    assert timeutil.ts_label("bozuk") == ""


def test_now_line_carries_weekday_and_week_bounds():
    from app.services import jarvis
    fixed = datetime(2026, 10, 4, 14, 5, tzinfo=timeutil.TZ)
    with mock.patch.object(jarvis, "now_tr", return_value=fixed):
        line = jarvis.now_line("web")
    assert line.startswith("[Şu an: 4 Ekim 2026 Pazar, saat 14:05")
    assert "dün: 3 Eki Cmt" in line and "yarın: 5 Eki Pzt" in line
    assert "bu hafta: 28 Eyl Pzt – 4 Eki Paz" in line
    assert "ASLA kendin hesaplama" in jarvis.SYSTEM_PROMPT


def test_agenda_outputs_carry_labels(db):
    t = timeutil.today_tr()
    db.add(LegalDeadline(title="x", due_date=t + timedelta(days=1)))
    db.commit()
    d = agenda.deadline_dict(agenda.build_agenda(db, days=3)["deadlines"][0], t)
    assert d["due_label"] == timeutil.day_label(t + timedelta(days=1))
