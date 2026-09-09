"""Hukuk Ofisi AI servisi — bir avukat ajanını çalıştırır.

ai_assistant.py (WhatsApp) ile aynı deseni izler: Claude'a ajan promptu +
kullanıcı talebi gider, JSON çıktı parse edilir. Fark: çıktı sözleşmesi
legal_agents.OUTPUT_CONTRACT'ta tanımlıdır ve her sonuç yasal uyarı taşır.
"""
import json
import logging
from typing import Optional

from anthropic import Anthropic

from app.config import settings
from app.legal_agents import DISCLAIMER, MODES, build_system_prompt


logger = logging.getLogger(__name__)

# Cevabın iskeleti — eksik alanlar bununla tamamlanır
EMPTY_RESULT = {
    "ozet": "",
    "degerlendirme": "",
    "mevzuat": [],
    "adimlar": [],
    "sureler": [],
    "riskler": [],
    "maliyet": "",
    "belge": None,
    "eksik_bilgiler": [],
    "sonraki_ajan": None,
    "avukat_gerekli": True,
    "guven": 0.0,
    "uyari": DISCLAIMER,
}

MAX_CONTEXT_CHARS = 40_000  # sözleşme metni gibi uzun girdiler için üst sınır


class LegalAI:
    """Avukat ajanlarını Claude üzerinden çalıştırır."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def default_model(self) -> str:
        return settings.legal_model

    def run(
        self,
        agent: dict,
        mode: str,
        question: str,
        context: Optional[str] = None,
        doc_type: Optional[str] = None,
        subject: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        """Ajanı çalıştırır.

        Returns:
            {"ok": bool, "result": {...}, "error": str|None,
             "model": str, "tokens_in": int, "tokens_out": int}
        """
        if mode not in MODES:
            mode = "danisma"

        if not self.is_configured():
            return {
                "ok": False,
                "result": self._blank(
                    "ANTHROPIC_API_KEY tanımlı değil — ajan çalıştırılamadı.",
                ),
                "error": "ANTHROPIC_API_KEY tanımlı değil. Railway Variables'a ekleyin.",
                "model": model or self.default_model(),
                "tokens_in": 0,
                "tokens_out": 0,
            }

        use_model = model or agent.get("model") or self.default_model()
        system_prompt = build_system_prompt(agent, mode)
        user_content = self._build_user_message(mode, question, context, doc_type, subject)

        try:
            response = self.client.messages.create(
                model=use_model,
                max_tokens=8000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            text = response.content[0].text if response.content else ""
            result = self._parse(text)
            usage = getattr(response, "usage", None)
            return {
                "ok": True,
                "result": result,
                "error": None,
                "model": use_model,
                "tokens_in": getattr(usage, "input_tokens", 0) or 0,
                "tokens_out": getattr(usage, "output_tokens", 0) or 0,
            }
        except Exception as e:
            logger.exception("LegalAI run failed (%s/%s): %s", agent.get("slug"), mode, e)
            return {
                "ok": False,
                "result": self._blank(f"Ajan çalıştırılamadı: {e}"),
                "error": str(e),
                "model": use_model,
                "tokens_in": 0,
                "tokens_out": 0,
            }

    # ── yardımcılar ────────────────────────────────────────────

    def _build_user_message(
        self,
        mode: str,
        question: str,
        context: Optional[str],
        doc_type: Optional[str],
        subject: Optional[str],
    ) -> str:
        parts = [f"TALEP TÜRÜ: {MODES[mode]}"]
        if subject:
            parts.append(f"KONU BAŞLIĞI: {subject}")
        if doc_type:
            parts.append(f"İSTENEN BELGE: {doc_type}")
        parts.append(f"\nSORU / TALEP:\n{question.strip()}")
        if context and context.strip():
            trimmed = context.strip()[:MAX_CONTEXT_CHARS]
            note = "" if len(context.strip()) <= MAX_CONTEXT_CHARS else "\n[... metin uzunluk sınırı nedeniyle kısaltıldı]"
            parts.append(f"\nOLAY / BELGE METNİ:\n{trimmed}{note}")
        return "\n".join(parts)

    def _parse(self, text: str) -> dict:
        """Modelin döndürdüğü JSON'ı güvenli parse eder, şemayı tamamlar."""
        raw = (text or "").strip()

        # ```json ... ``` sarmalı varsa temizle
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        data = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # İlk { ... son } arasını denemek yeterli oluyor
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end > start:
                try:
                    data = json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    data = None

        if not isinstance(data, dict):
            logger.warning("LegalAI response not valid JSON: %s", (text or "")[:200])
            out = self._blank("Model yanıtı okunamadı (JSON değil).")
            out["degerlendirme"] = (text or "").strip()[:4000]
            return out

        out = dict(EMPTY_RESULT)
        out.update({k: data.get(k, EMPTY_RESULT[k]) for k in EMPTY_RESULT})

        # Tip güvenliği — model bazen tek nesne veya string gönderebilir
        for key in ("mevzuat", "adimlar", "sureler", "riskler", "eksik_bilgiler"):
            val = out.get(key)
            if val is None:
                out[key] = []
            elif isinstance(val, dict):
                out[key] = [val]
            elif isinstance(val, str):
                out[key] = [val] if val.strip() else []
            elif not isinstance(val, list):
                out[key] = []

        belge = out.get("belge")
        if isinstance(belge, str):
            belge = {"tur": "", "merci": "", "icerik": belge}
        if isinstance(belge, dict) and not (belge.get("icerik") or "").strip():
            belge = None
        out["belge"] = belge if isinstance(belge, dict) else None

        try:
            out["guven"] = max(0.0, min(1.0, float(out.get("guven") or 0.0)))
        except (TypeError, ValueError):
            out["guven"] = 0.0

        out["avukat_gerekli"] = bool(out.get("avukat_gerekli", True))
        # Yasal uyarı her koşulda sabit metinle döner — model değiştiremez
        out["uyari"] = DISCLAIMER
        return out

    def _blank(self, message: str) -> dict:
        out = dict(EMPTY_RESULT)
        out["ozet"] = message
        out["degerlendirme"] = message
        out["mevzuat"], out["adimlar"], out["sureler"] = [], [], []
        out["riskler"], out["eksik_bilgiler"] = [], []
        return out


# Singleton — ai_assistant ile aynı desen
legal_ai = LegalAI()
