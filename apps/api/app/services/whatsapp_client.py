"""Meta WhatsApp Cloud API wrapper.

Meta Graph API üzerinden mesaj gönderme ve medya indirme.
https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import logging
from typing import Optional

import httpx

from app.config import settings


logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v21.0"


class WhatsAppClient:
    """Meta WhatsApp Cloud API ile konuşan client."""

    def __init__(self):
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.base_url = f"{META_GRAPH_URL}/{self.phone_number_id}"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        """API erişimi yapılandırılmış mı?"""
        return bool(self.access_token and self.phone_number_id)

    async def send_text(self, to: str, body: str, reply_to: Optional[str] = None) -> dict:
        """Text mesaj gönder.

        Args:
            to: Alıcı numarası (örn. 905551234567, başında + yok)
            body: Mesaj içeriği (4096 karakter max)
            reply_to: Yanıtlanan mesajın wamid'i (opsiyonel)

        Returns:
            Meta API response dict (messages[0].id → wamid)
        """
        if not self.is_configured():
            raise RuntimeError("WhatsApp API yapılandırılmamış (token/phone_id eksik)")

        # Numaradaki + ve boşlukları temizle
        to = to.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body[:4096], "preview_url": True},
        }

        if reply_to:
            payload["context"] = {"message_id": reply_to}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                headers=self._headers,
                json=payload,
            )

            if resp.status_code >= 400:
                logger.error("WhatsApp send_text failed: %s %s", resp.status_code, resp.text)
                resp.raise_for_status()

            return resp.json()

    async def send_template(self, to: str, template_name: str, language: str = "tr",
                            components: Optional[list] = None) -> dict:
        """Onaylı template mesaj gönder (24 saat dışı konuşmalar için gerekli)."""
        if not self.is_configured():
            raise RuntimeError("WhatsApp API yapılandırılmamış")

        to = to.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }

        if components:
            payload["template"]["components"] = components

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code >= 400:
                logger.error("WhatsApp send_template failed: %s %s", resp.status_code, resp.text)
                resp.raise_for_status()
            return resp.json()

    async def mark_as_read(self, message_id: str) -> dict:
        """Gelen mesajı 'okundu' işaretle (mavi tik)."""
        if not self.is_configured():
            return {}

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._headers,
                    json=payload,
                )
                return resp.json() if resp.status_code < 400 else {}
            except Exception as e:
                logger.warning("mark_as_read failed: %s", e)
                return {}

    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Medya ID'sinden indirilebilir URL al (geçici, 5 dakika)."""
        if not self.is_configured():
            return None

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{META_GRAPH_URL}/{media_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code >= 400:
                logger.error("get_media_url failed: %s", resp.text)
                return None
            return resp.json().get("url")

    async def download_media(self, media_url: str) -> Optional[bytes]:
        """Medya URL'inden binary içerik indir."""
        if not self.access_token:
            return None

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code >= 400:
                return None
            return resp.content


# Singleton instance
whatsapp_client = WhatsAppClient()
