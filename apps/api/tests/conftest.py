"""Test ortamı: geçici SQLite, uygulama içe aktarılmadan ÖNCE ayarlanır."""
import os
import sys
import tempfile
from pathlib import Path

_DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ENVIRONMENT"] = "test"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["WHATSAPP_APP_SECRET"] = "test-app-secret"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "ilk-sifre-123456"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app import models, models_whatsapp, models_legal  # noqa: E402,F401


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
