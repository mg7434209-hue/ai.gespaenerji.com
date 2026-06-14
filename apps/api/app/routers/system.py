"""Sistem durumu endpoint'leri.

Frontend Ayarlar sayfası için: hangi entegrasyonlar/API anahtarları
gerçekten yapılandırılmış? Sır (token/key) ASLA dönmez — sadece bool durum.
"""
from fastapi import APIRouter, Depends

from app.config import settings, APP_VERSION
from app.models import User
from app.auth.dependencies import get_current_user
from app.services.ai_assistant import ai_assistant
from app.services.whatsapp_client import whatsapp_client


router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def system_status(user: User = Depends(get_current_user)):
    """Entegrasyon ve API anahtarı durumları — sadece yapılandırılmış mı bilgisi."""
    return {
        "version": APP_VERSION,
        "environment": settings.environment,
        "database": "PostgreSQL" if settings.database_url.startswith(("postgres", "postgresql")) else "SQLite",
        "api_keys": {
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "gemini": bool(settings.gemini_api_key),
        },
        "integrations": {
            "whatsapp": {
                "configured": whatsapp_client.is_configured(),
                # Built ve canlıda — eksik olan sadece token/phone_id
                "status": "active" if whatsapp_client.is_configured() else "needs_config",
            },
            "ai_assistant": {
                "configured": ai_assistant.is_configured(),
                "status": "active" if ai_assistant.is_configured() else "needs_config",
            },
            "gmail": {"configured": False, "status": "planned"},
            "vapi": {"configured": False, "status": "planned"},
            "n8n": {"configured": False, "status": "planned"},
        },
    }
