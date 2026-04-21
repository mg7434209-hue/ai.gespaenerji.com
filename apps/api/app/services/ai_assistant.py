"""WhatsApp mesaj analizi ve otomatik cevap servisi.

Gelen her mesajı Claude Sonnet 4 ile analiz eder:
1. Intent tespiti (solar_teklif, modem_sorgu, selam, şikayet vs.)
2. Sentiment + dil + aciliyet
3. Cevap taslağı (confidence ile)

Sonra confidence'a göre:
- %90+  ve güvenli intent → otomatik gönder
- %70-90 → taslak olarak kaydet, onay bekle
- %70 altı → sadece göster, ben yazarım
"""
import json
import logging
from typing import Optional

from anthropic import Anthropic

from app.config import settings


logger = logging.getLogger(__name__)

# Intent kategorileri
SAFE_INTENTS = {
    # AI direkt cevap verebilir (düşük risk)
    "selam", "tesekkur", "veda",
    "calisma_saati_sor", "adres_sor", "iletisim_sor",
    "genel_bilgi_sor",  # "Solar nedir?", "Modem ne zaman geliyor?"
    "fiyat_araligi_sor",  # Kesin değil, aralık cevabı
}

SENSITIVE_INTENTS = {
    # Mutlaka onay gerektir (yüksek risk)
    "kesin_teklif_iste", "odeme_sorgu", "iptal_iade",
    "sikayet", "hukuki", "garanti_sorgu", "fatura_sorgu",
    "randevu_onay", "sozlesme",
}

URGENT_INTENTS = {
    # Direkt Mustafa'ya bildir
    "acil_ariza", "yogun_sikayet", "hukuki_tehdit", "urgent",
}


SYSTEM_PROMPT_TR = """Sen Gespa adında bir WhatsApp AI asistanısın. Mustafa Göksoy'un işlerinde müşteri iletişimini yönetiyorsun.

## Mustafa'nın işleri:
- **Solar Enerji** (GespaEnerji): Güneş enerjisi sistemi kurulumu, on-grid/off-grid
  - 3 kW: ~110-140K TL, 5 kW: ~180-220K TL, 10 kW: ~320-380K TL (güncel değil, aralık)
  - Manavgat/Antalya merkezli
- **Superonline Bayi (B9613)**: Türkcell Superonline fiber internet satış
- **Türk Telekom Bayi**: Modem + internet (yeni bayilik alınıyor)
- **Taşınmaz/İhale**: UYAP ihale takip, gayrimenkul alım-satım

## Konum ve Saat:
- Manavgat, Antalya
- Çalışma saatleri: Hafta içi 09:00-18:00, Cumartesi 09:00-14:00, Pazar kapalı
- Ofis/bayi: Manavgat merkez

## Görevin:
1. Gelen mesajı analiz et: niyeti, duygu durumu, dili, aciliyeti tespit et
2. Türkçe (veya gelen dilde) sıcak, samimi ama profesyonel cevap hazırla
3. Emin olmadığın fiyat/tarih/teknik detayları ASLA uydurma
4. Kesin fiyat/tarih isterse "Detay için size dönecek birini ayarlıyorum" de
5. Müşteri profesyonel bir firmayla konuştuğunu hissetsin

## Kurallar:
- Selamlaşmada sıcak ol ama fazla resmi değil: "Merhaba", "İyi günler"
- "Abi", "kardeş" kullanma; "siz" hitabı kullan
- Emoji kullanma (mesaja yakışıyorsa max 1 tane — genelde hiç kullanma)
- Mesaj kısa tut (max 3-4 cümle). Uzun açıklama isterse "Detaylı bilgi için şu zamanda arayabilir miyim?"
- Fiyat verirken "aralık" ver, kesin rakam verme: "180-220K arasında, keşif sonrası netleşir"
- Tarih verme yetkili değilsin: "Yarın size dönüş yapılacak"
- Müşteri adresini alırsan kaydet: lead oluşturulacak

## Çıktı formatın KESINLIKLE şu JSON olmalı:
{
  "intent": "solar_teklif_talep|modem_kurulum|fiyat_araligi_sor|selam|tesekkur|sikayet|acil_ariza|...",
  "sentiment": "positive|neutral|negative|urgent",
  "language": "tr|en|ar|de|ru",
  "summary": "Müşterinin ne istediğinin 1 cümlelik özeti",
  "is_safe_to_auto_reply": true|false,
  "confidence": 0.0-1.0,
  "draft_reply": "Önerdiğin Türkçe cevap (müşteriye gönderilecek metin)",
  "requires_human": true|false,
  "notes": "Mustafa'ya not (opsiyonel, lead için bilgi)"
}

Sadece JSON döndür, başka açıklama yok."""


class AIAssistant:
    """WhatsApp mesajlarını analiz edip cevap hazırlayan AI."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.model = "claude-sonnet-4-20250514"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    async def analyze_message(
        self,
        message_text: str,
        conversation_history: Optional[list] = None,
        contact_name: Optional[str] = None,
    ) -> dict:
        """Gelen mesajı analiz et + cevap taslağı hazırla.

        Args:
            message_text: Gelen WhatsApp mesajının metni
            conversation_history: [{"role": "user"|"assistant", "content": "..."}, ...]
            contact_name: Müşterinin adı (varsa)

        Returns:
            {
                "intent": "...",
                "sentiment": "...",
                "language": "...",
                "summary": "...",
                "is_safe_to_auto_reply": bool,
                "confidence": float,
                "draft_reply": "...",
                "requires_human": bool,
                "notes": "..."
            }
        """
        if not self.is_configured():
            return self._fallback_response()

        history = conversation_history or []

        # Context oluştur
        context_parts = []
        if contact_name:
            context_parts.append(f"Müşteri adı: {contact_name}")

        user_content = message_text
        if context_parts:
            user_content = "\n".join(context_parts) + f"\n\n---\nGelen mesaj:\n{message_text}"

        try:
            # Geçmiş varsa messages dizisine ekle
            messages = []
            for msg in history[-10:]:  # son 10 mesaj yeterli
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

            messages.append({"role": "user", "content": user_content})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT_TR,
                messages=messages,
            )

            # İçerik text olarak al
            text = response.content[0].text if response.content else ""

            # JSON parse et
            result = self._parse_ai_response(text)

            # Ek güvenlik: sensitive intent ise auto_reply'i kapat
            if result.get("intent") in SENSITIVE_INTENTS:
                result["is_safe_to_auto_reply"] = False

            # Urgent ise requires_human=True
            if result.get("intent") in URGENT_INTENTS or result.get("sentiment") == "urgent":
                result["requires_human"] = True
                result["is_safe_to_auto_reply"] = False

            return result

        except Exception as e:
            logger.exception("AI analyze_message failed: %s", e)
            return self._fallback_response(text=message_text)

    def _parse_ai_response(self, text: str) -> dict:
        """Claude'un döndürdüğü JSON'ı güvenli parse et."""
        # JSON bloğu içinde olabilir (```json ... ```), temizle
        t = text.strip()
        if t.startswith("```"):
            # ```json ... ``` bloğunu kaldır
            t = t.split("```", 2)[1]
            if t.startswith("json"):
                t = t[4:].strip()
            t = t.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(t)
        except json.JSONDecodeError:
            logger.warning("AI response not valid JSON: %s", text[:200])
            return self._fallback_response()

        # Varsayılanlarla doldur
        return {
            "intent": data.get("intent", "diger"),
            "sentiment": data.get("sentiment", "neutral"),
            "language": data.get("language", "tr"),
            "summary": data.get("summary", ""),
            "is_safe_to_auto_reply": bool(data.get("is_safe_to_auto_reply", False)),
            "confidence": float(data.get("confidence", 0.5)),
            "draft_reply": data.get("draft_reply", ""),
            "requires_human": bool(data.get("requires_human", False)),
            "notes": data.get("notes", ""),
        }

    def _fallback_response(self, text: str = "") -> dict:
        """API hatası durumunda güvenli varsayılan."""
        return {
            "intent": "diger",
            "sentiment": "neutral",
            "language": "tr",
            "summary": "AI analizi yapılamadı, manuel kontrol gerekiyor",
            "is_safe_to_auto_reply": False,
            "confidence": 0.0,
            "draft_reply": "",
            "requires_human": True,
            "notes": "AI sistemi hata verdi, manuel cevaplanmalı",
        }


# Karar fonksiyonu — confidence + intent'e göre aksiyon belirler
def decide_action(analysis: dict, conversation_mode: str = "auto_draft") -> str:
    """
    AI analizine göre ne yapacağına karar verir.

    Returns:
        "auto_reply" → AI cevabı hemen gönder
        "draft_only" → Cevap taslağı oluştur, Mustafa onaylasın
        "notify_only" → Sadece Mustafa'ya bildir, cevap yok
    """
    # Mode "paused" ise hiçbir şey yapma
    if conversation_mode == "paused":
        return "notify_only"

    # Mode "manual" → sadece bildir
    if conversation_mode == "manual":
        return "notify_only"

    # Human müdahale gerekiyorsa
    if analysis.get("requires_human"):
        return "notify_only"

    intent = analysis.get("intent", "")
    confidence = analysis.get("confidence", 0.0)
    is_safe = analysis.get("is_safe_to_auto_reply", False)

    # Otomatik cevap kuralları:
    if conversation_mode == "auto_reply":
        # Tam otomatik mod — riski kullanıcı kabul etmiş
        if is_safe and confidence >= 0.75:
            return "auto_reply"
        return "draft_only"

    # Default: auto_draft — kademeli güven
    if is_safe and intent in SAFE_INTENTS and confidence >= 0.90:
        return "auto_reply"

    return "draft_only"


# Singleton
ai_assistant = AIAssistant()
