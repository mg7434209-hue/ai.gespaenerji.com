"""Uygulama konfigürasyonu — tüm env değişkenleri buradan okunur."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dev.db"

    # Auth
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 gün

    # Admin (tek kullanıcı — başlangıçta seed edilir)
    admin_email: str = "admin@gespa.com"
    admin_password: str = "change-me"

    # AI Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

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


settings = Settings()
