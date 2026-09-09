"""İlk kurulum — admin kullanıcı + workspace + ajanlar + Hukuk Ofisi kadrosu."""
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models import User, Workspace, Agent

# Tablolar create_all ile oluşacağı için modellerin import edilmesi şart
from app import models_whatsapp  # noqa: F401
from app.models_legal import LegalAgent
from app.legal_agents import LEGAL_AGENTS, build_system_prompt
from app.auth.security import hash_password
from app.config import settings


# 12 AI ajanı — Mustafa'nın gerçek iş kollarına göre (dijital oda kadrosu)
DEFAULT_AGENTS = [
    {
        "slug": "satis-uzmani",
        "name": "Satış Uzmanı",
        "department": "Satış",
        "description": "Superbox ve fiber müşteri adaylarını arar, ikna eder, satışı kapatır.",
        "icon": "briefcase",
        "color": "#10b981",
    },
    {
        "slug": "superbox-takipcisi",
        "name": "Superbox Başvuru Takipçisi",
        "department": "Superonline",
        "description": "internetbasvuru.com lead'lerini izler; arama, kapsama teyidi ve kurulum takibini yönetir.",
        "icon": "wifi",
        "color": "#fbbf24",
    },
    {
        "slug": "teklif-motoru",
        "name": "Solar Teklif Motoru",
        "department": "Solar",
        "description": "Keşif verisinden anahtar teslim GES teklifi ve maliyet analizi hazırlar.",
        "icon": "sun",
        "color": "#f59e0b",
    },
    {
        "slug": "destek-uzmani",
        "name": "Destek Uzmanı",
        "department": "Destek",
        "description": "Müşteri sorunlarını çözer, memnuniyet takibini yapar.",
        "icon": "wrench",
        "color": "#3b82f6",
    },
    {
        "slug": "tahsilat-sorumlusu",
        "name": "Tahsilat Sorumlusu",
        "department": "Finans",
        "description": "Ödeme hatırlatır, tahsilat ve fatura takibini yapar.",
        "icon": "dollar-sign",
        "color": "#a855f7",
    },
    {
        "slug": "email-asistani",
        "name": "Email Asistanı",
        "department": "İletişim",
        "description": "Email yazışmalarını taslaklar, takip eder, önceliklendirir.",
        "icon": "mail",
        "color": "#6366f1",
    },
    {
        "slug": "proje-yoneticisi",
        "name": "Proje Yöneticisi",
        "department": "Proje",
        "description": "GES kurulumları ve site projelerini takip eder, haftalık rapor çıkarır.",
        "icon": "bar-chart-3",
        "color": "#f97316",
    },
    {
        "slug": "hukuk-asistani",
        "name": "Hukuk & Trafik Asistanı",
        "department": "Hukuk",
        "description": "TrafikRehber/CezaRehberi sorularını yanıtlar, dilekçe taslağı hazırlar.",
        "icon": "scale",
        "color": "#0ea5e9",
    },
    {
        "slug": "sigorta-asistani",
        "name": "Sigorta Asistanı",
        "department": "Sigorta",
        "description": "Trafik/kasko teklif karşılaştırır (SEGEM sonrası tam aktif).",
        "icon": "shield-check",
        "color": "#14b8a6",
    },
    {
        "slug": "tarife-analisti",
        "name": "Tarife Analisti",
        "department": "Analiz",
        "description": "tarifesec.net.tr için operatör tarifelerini ve rakipleri izler.",
        "icon": "line-chart",
        "color": "#8b5cf6",
    },
    {
        "slug": "icerik-yazari",
        "name": "İçerik & SEO Yazarı",
        "department": "Pazarlama",
        "description": "Siteler için rehber yazısı, kampanya metni ve SEO içeriği üretir.",
        "icon": "pen-square",
        "color": "#ec4899",
    },
    {
        "slug": "genel-asistan",
        "name": "Genel Asistan",
        "department": "Genel",
        "description": "Gündelik görevler, özetler ve hatırlatmalar.",
        "icon": "bot",
        "color": "#64748b",
    },
]

# Eski şablondan kalan, iş kollarıyla ilgisi olmayan ajanlar — seed'de silinir
LEGACY_AGENT_SLUGS = [
    "saglik-asistani",
    "egitim-danismani",
    "rezervasyon",
    "kargo-takip",
    "sesli-asistan",
]


# İlk workspace'ler — Mustafa'nın mevcut iş kolları
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


# Admin profili — değişirse her deploy'da güncellenir
ADMIN_FULL_NAME = "Mustafa Göksoy"


def seed_legal_agents(db: Session) -> None:
    """Avukat ajan serisi — legal_agents.py tek doğru kaynak, DB ona senkronlanır.

    Tanım alanları her deploy'da güncellenir; is_active kullanıcı tercihidir,
    yalnızca ajan ilk kez eklenirken belirlenir. Listeden çıkarılan ajan silinir.
    """
    added = updated = 0
    for order, spec in enumerate(LEGAL_AGENTS):
        row = db.query(LegalAgent).filter(LegalAgent.slug == spec["slug"]).first()
        fields = dict(
            name=spec["name"],
            title=spec["title"],
            department=spec["department"],
            description=spec["description"],
            icon=spec["icon"],
            color=spec["color"],
            expertise=spec["expertise"],
            documents=spec["documents"],
            keywords=spec.get("keywords", []),
            system_prompt=build_system_prompt(spec),
            model=settings.legal_model,
            sort_order=order,
        )
        if row:
            for key, value in fields.items():
                setattr(row, key, value)
            updated += 1
        else:
            db.add(LegalAgent(slug=spec["slug"], is_active=True, **fields))
            added += 1

    known = {s["slug"] for s in LEGAL_AGENTS}
    stale = db.query(LegalAgent).filter(LegalAgent.slug.notin_(known)).all()
    for row in stale:
        db.delete(row)

    if added:
        print(f"✓ {added} avukat ajanı eklendi")
    if updated:
        print(f"✓ {updated} avukat ajanı güncellendi")
    if stale:
        print(f"✓ {len(stale)} eski avukat ajanı kaldırıldı")


def seed():
    """Tablolar + ilk veri."""
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Admin user (upsert — varsa güncelle, yoksa oluştur)
        admin = db.query(User).filter(User.email == settings.admin_email.lower()).first()
        if not admin:
            admin = User(
                email=settings.admin_email.lower(),
                password_hash=hash_password(settings.admin_password),
                full_name=ADMIN_FULL_NAME,
            )
            db.add(admin)
            print(f"✓ Admin user oluşturuldu: {admin.email}")
        else:
            # İsim güncellemesi (her deploy'da senkron)
            if admin.full_name != ADMIN_FULL_NAME:
                print(f"✓ Admin ismi güncellendi: {admin.full_name} → {ADMIN_FULL_NAME}")
                admin.full_name = ADMIN_FULL_NAME
            # Şifre boşsa yeniden hashle
            if not admin.password_hash:
                admin.password_hash = hash_password(settings.admin_password)

        # Workspaces
        for ws_data in DEFAULT_WORKSPACES:
            existing = db.query(Workspace).filter(Workspace.slug == ws_data["slug"]).first()
            if not existing:
                db.add(Workspace(**ws_data))
                print(f"✓ Workspace eklendi: {ws_data['slug']}")

        # Agents — upsert: varsa tanımı güncelle (is_active korunur), yoksa ekle
        for agent_data in DEFAULT_AGENTS:
            existing = db.query(Agent).filter(Agent.slug == agent_data["slug"]).first()
            if not existing:
                db.add(Agent(**agent_data))
                print(f"✓ Ajan eklendi: {agent_data['slug']}")
            else:
                for field in ("name", "department", "description", "icon", "color"):
                    setattr(existing, field, agent_data[field])

        # Eski şablon ajanlarını kaldır
        removed = (
            db.query(Agent)
            .filter(Agent.slug.in_(LEGACY_AGENT_SLUGS))
            .delete(synchronize_session=False)
        )
        if removed:
            print(f"✓ {removed} eski şablon ajanı kaldırıldı")

        # Hukuk Ofisi — avukat ajan serisi
        seed_legal_agents(db)

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
