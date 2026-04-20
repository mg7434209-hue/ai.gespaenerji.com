"""İlk kurulum — admin kullanıcı + default workspace + 12 ajan seed."""
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models import User, Workspace, Agent
from app.auth.security import hash_password
from app.config import settings


# 12 AI ajanı — Chatpilots tarzı
DEFAULT_AGENTS = [
    {
        "slug": "satis-uzmani",
        "name": "Satış Uzmanı",
        "department": "Satış",
        "description": "Müşteri adaylarını ikna eder, satış kapatır.",
        "icon": "briefcase",
        "color": "#10b981",
    },
    {
        "slug": "teklif-motoru",
        "name": "Teklif Motoru",
        "department": "Teklif",
        "description": "İhtiyacı analiz eder, teklif hazırlar.",
        "icon": "clipboard-list",
        "color": "#06b6d4",
    },
    {
        "slug": "destek-uzmani",
        "name": "Destek Uzmanı",
        "department": "Destek",
        "description": "Sorunları çözer, memnuniyet sağlar.",
        "icon": "wrench",
        "color": "#3b82f6",
    },
    {
        "slug": "tahsilat-sorumlusu",
        "name": "Tahsilat Sorumlusu",
        "department": "Tahsilat",
        "description": "Ödeme hatırlatır, tahsilat yapar.",
        "icon": "dollar-sign",
        "color": "#a855f7",
    },
    {
        "slug": "email-asistani",
        "name": "Email Asistanı",
        "department": "İletişim",
        "description": "Email yazışmaları ve takibi yapar.",
        "icon": "mail",
        "color": "#6366f1",
    },
    {
        "slug": "proje-yoneticisi",
        "name": "Proje Yöneticisi",
        "department": "Proje",
        "description": "Proje takibi ve raporlama yapar.",
        "icon": "bar-chart-3",
        "color": "#f59e0b",
    },
    {
        "slug": "saglik-asistani",
        "name": "Sağlık Asistanı",
        "department": "Sağlık",
        "description": "Hasta bilgi toplar, yönlendirir.",
        "icon": "plus-square",
        "color": "#ec4899",
    },
    {
        "slug": "egitim-danismani",
        "name": "Eğitim Danışmanı",
        "department": "Eğitim",
        "description": "Kurs bilgisi verir, kayıt alır.",
        "icon": "graduation-cap",
        "color": "#14b8a6",
    },
    {
        "slug": "rezervasyon",
        "name": "Rezervasyon",
        "department": "Rezervasyon",
        "description": "Konaklama ve mekan rezervasyonu alır.",
        "icon": "building",
        "color": "#0ea5e9",
    },
    {
        "slug": "kargo-takip",
        "name": "Kargo Takip",
        "department": "Lojistik",
        "description": "Kargo durumu sorgular, bildirir.",
        "icon": "package",
        "color": "#f97316",
    },
    {
        "slug": "sesli-asistan",
        "name": "Sesli Asistan",
        "department": "Ses",
        "description": "Sesli görüşme ve çağrı yönetimi.",
        "icon": "mic",
        "color": "#d946ef",
    },
    {
        "slug": "genel-asistan",
        "name": "Genel Asistan",
        "department": "Genel",
        "description": "Her türlü genel görevi üstlenir.",
        "icon": "bot",
        "color": "#64748b",
    },
]


# İlk workspace'ler — Göksoylar'ın mevcut iş kolları
DEFAULT_WORKSPACES = [
    {
        "slug": "superonline",
        "name": "Superonline Bayi (B9613)",
        "description": "Türkcell Superonline fiber satış ve müşteri yönetimi",
        "icon": "wifi",
        "color": "#fbbf24",
    },
    {
        "slug": "solar",
        "name": "Solar Enerji",
        "description": "SolarAnaliz + GespaEnerji + GesMarketim",
        "icon": "sun",
        "color": "#f59e0b",
    },
    {
        "slug": "legal",
        "name": "Hukuk & Trafik",
        "description": "TrafikRehber + CezaRehberi + HakBul",
        "icon": "scale",
        "color": "#3b82f6",
    },
    {
        "slug": "insurance",
        "name": "Sigorta Platformu",
        "description": "TrafikHızı + PoliçeHızı (SEGEM sonrası aktif)",
        "icon": "shield-check",
        "color": "#10b981",
    },
    {
        "slug": "compare",
        "name": "tarifesec.net.tr",
        "description": "İnternet/mobil paket karşılaştırma",
        "icon": "scale-3d",
        "color": "#8b5cf6",
    },
    {
        "slug": "tourism",
        "name": "Turizm & Sağlık",
        "description": "Manavgat turlar + sağlık turizmi",
        "icon": "plane",
        "color": "#14b8a6",
    },
]


def seed():
    """Tablolar + ilk veri."""
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Admin user
        admin = db.query(User).filter(User.email == settings.admin_email.lower()).first()
        if not admin:
            admin = User(
                email=settings.admin_email.lower(),
                password_hash=hash_password(settings.admin_password),
                full_name="Mustafa Göksoylar",
            )
            db.add(admin)
            print(f"✓ Admin user oluşturuldu: {admin.email}")
        else:
            # Şifre env'de değiştiyse güncelle
            if not admin.password_hash:
                admin.password_hash = hash_password(settings.admin_password)

        # Workspaces
        for ws_data in DEFAULT_WORKSPACES:
            existing = db.query(Workspace).filter(Workspace.slug == ws_data["slug"]).first()
            if not existing:
                db.add(Workspace(**ws_data))
                print(f"✓ Workspace eklendi: {ws_data['slug']}")

        # Agents
        for agent_data in DEFAULT_AGENTS:
            existing = db.query(Agent).filter(Agent.slug == agent_data["slug"]).first()
            if not existing:
                db.add(Agent(**agent_data))
                print(f"✓ Ajan eklendi: {agent_data['slug']}")

        db.commit()
        print("✓ Seed tamamlandı.")
    except Exception as e:
        db.rollback()
        print(f"✗ Seed hatası: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
