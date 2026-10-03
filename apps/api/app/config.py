"""Uygulama konfigürasyonu — tüm env değişkenleri buradan okunur."""
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_JWT_SECRET = "dev-secret-change-in-production"
DEFAULT_ADMIN_PASSWORD = "change-me"


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dev.db"

    # Auth
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 gün

    # Admin (tek kullanıcı — başlangıçta seed edilir)
    admin_email: str = "admin@gespa.com"
    admin_password: str = DEFAULT_ADMIN_PASSWORD

    # AI Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Hukuk Ofisi ajanlarının modeli (LEGAL_MODEL env ile değiştirilebilir)
    legal_model: str = "claude-opus-5"
    # Belge triyajı (hangi ajana gidecek) — boşsa legal_model kullanılır
    legal_triage_model: str = ""
    # İkinci okuma / denetim modeli — boşsa legal_model kullanılır
    legal_review_model: str = ""

    # WhatsApp Business API (Meta Cloud)
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_webhook_verify_token: str = "gespa-wh-verify-token-change-me"
    whatsapp_app_secret: str = ""

    # Environment
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def production_problems(self) -> list[str]:
        """Üretimde varsayılan/zayıf gizli değerle açılmayı engelleyen denetim.

        Repo herkese açık olmuş, varsayılanlar herkesçe biliniyor: JWT_SECRET
        varsayılanda kalırsa herkes geçerli oturum belirteci üretebilir.
        """
        if not self.is_production:
            return []
        problems = []
        if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET varsayılan ya da 32 karakterden kısa")
        if self.admin_password == DEFAULT_ADMIN_PASSWORD or len(self.admin_password) < 12:
            problems.append("ADMIN_PASSWORD varsayılan ya da 12 karakterden kısa")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL tanımlı değil (SQLite'a düşüyor)")
        return problems


settings = Settings()
