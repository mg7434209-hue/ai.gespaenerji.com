"""Hukuk Ofisi AI servisi — bir avukat ajanını çalıştırır.

ai_assistant.py (WhatsApp) ile aynı deseni izler: Claude'a ajan promptu +
kullanıcı talebi gider, JSON çıktı parse edilir. Fark: çıktı sözleşmesi
legal_agents.OUTPUT_CONTRACT'ta tanımlıdır ve her sonuç yasal uyarı taşır.
"""
import base64
import json
import logging
from typing import Optional

from anthropic import Anthropic

from app.config import settings
from app.legal_agents import DISCLAIMER, LEGAL_AGENTS, MODES, build_system_prompt
from app.services.document_text import MAX_PROMPT_CHARS


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


# ─────────────────────────────────────────────────────────────
# Triyaj — yüklenen belgeyi okuyup doğru ajana yönlendirir
# ─────────────────────────────────────────────────────────────

TRIAGE_PROMPT = """Sen Gespa OS Hukuk Ofisi'nin belge triyaj görevlisisin. Sana yüklenen
belgeyi okur, ne olduğunu anlar ve ofisteki hangi avukat ajanının bakması gerektiğine
karar verirsin. Hukuki yorum YAPMAZSIN — sadece sınıflandırır ve yönlendirirsin.

## Ofis kadrosu (slug — uzmanlık)
{roster}

## Kurallar
- Belgede yazmayan hiçbir bilgiyi uydurma. Okunamayan alanı "okunamadı" yaz.
- Belgede bir SÜRE varsa (itiraz, ödeme, cevap, dava açma süresi) mutlaka `sure_uyarisi`na yaz.
- Konu birden çok alana giriyorsa ana konuyu seç; ikincil olanı `alternatif_ajan`a koy.
- Ne olduğunu çözemezsen `agent_slug` olarak "bas-hukuk-musaviri" ver.

## Çıktı (KESİNLİKLE bu JSON, başka metin yok)
{{
  "belge_turu": "Ödeme emri | İhtarname | Kira sözleşmesi | Trafik ceza tutanağı | ...",
  "ozet": "Belgenin 1-2 cümlelik özeti: kim, kime, ne için",
  "taraflar": ["Belgede geçen taraf adları"],
  "tarihler": [{{"ne": "Tebliğ tarihi", "tarih": "01.09.2026"}}],
  "tutarlar": ["Belgede geçen tutarlar"],
  "referans": "Dosya/esas/tutanak numarası varsa",
  "sure_uyarisi": "Belgeden anlaşılan süre ve başlangıcı, yoksa bos birak",
  "agent_slug": "Kadrodan bir slug",
  "alternatif_ajan": "İkincil slug veya null",
  "onerilen_mod": "danisma|inceleme|dilekce",
  "gerekce": "Bu ajanı neden seçtin, tek cümle",
  "aciliyet": "dusuk|orta|yuksek",
  "guven": 0.0
}}"""


def _roster() -> str:
    return "\n".join(
        f"- {a['slug']} — {a['name']} ({a['title']}): {a['description']}"
        for a in LEGAL_AGENTS
    )


EMPTY_TRIAGE = {
    "belge_turu": "",
    "ozet": "",
    "taraflar": [],
    "tarihler": [],
    "tutarlar": [],
    "referans": "",
    "sure_uyarisi": "",
    "agent_slug": "bas-hukuk-musaviri",
    "alternatif_ajan": None,
    "onerilen_mod": "inceleme",
    "gerekce": "",
    "aciliyet": "orta",
    "guven": 0.0,
}


class LegalAI:
    """Avukat ajanlarını Claude üzerinden çalıştırır."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def default_model(self) -> str:
        return settings.legal_model

    def triage(self, attachments: list, note: str = "") -> dict:
        """Belgeyi okuyup hangi ajana gideceğine karar verir."""
        if not self.is_configured():
            out = dict(EMPTY_TRIAGE)
            out["gerekce"] = "ANTHROPIC_API_KEY tanımlı değil — otomatik yönlendirme yapılamadı."
            return {"ok": False, "triage": out, "error": "ANTHROPIC_API_KEY tanımlı değil."}

        model = settings.legal_triage_model or self.default_model()
        question = (
            "Ekteki belgeyi oku ve triyaj çıktısını üret."
            + (f"\n\nKullanıcı notu: {note.strip()}" if note and note.strip() else "")
        )
        content = self._build_content("inceleme", question, None, None, None, attachments)

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=2000,
                system=TRIAGE_PROMPT.format(roster=_roster()),
                messages=[{"role": "user", "content": content}],
            )
            text = response.content[0].text if response.content else ""
            data = self._loads(text)
            out = dict(EMPTY_TRIAGE)
            if isinstance(data, dict):
                out.update({k: data.get(k, EMPTY_TRIAGE[k]) for k in EMPTY_TRIAGE})
            for key in ("taraflar", "tarihler", "tutarlar"):
                if not isinstance(out.get(key), list):
                    out[key] = [out[key]] if out.get(key) else []
            if out.get("agent_slug") not in {a["slug"] for a in LEGAL_AGENTS}:
                out["agent_slug"] = "bas-hukuk-musaviri"
            if out.get("alternatif_ajan") not in {a["slug"] for a in LEGAL_AGENTS}:
                out["alternatif_ajan"] = None
            if out.get("onerilen_mod") not in MODES:
                out["onerilen_mod"] = "inceleme"
            try:
                out["guven"] = max(0.0, min(1.0, float(out.get("guven") or 0.0)))
            except (TypeError, ValueError):
                out["guven"] = 0.0
            usage = getattr(response, "usage", None)
            return {
                "ok": True,
                "triage": out,
                "error": None,
                "model": model,
                "tokens_in": getattr(usage, "input_tokens", 0) or 0,
                "tokens_out": getattr(usage, "output_tokens", 0) or 0,
            }
        except Exception as e:
            logger.exception("LegalAI triage failed: %s", e)
            out = dict(EMPTY_TRIAGE)
            out["gerekce"] = f"Otomatik yönlendirme yapılamadı: {e}"
            return {"ok": False, "triage": out, "error": str(e)}

    def run(
        self,
        agent: dict,
        mode: str,
        question: str,
        context: Optional[str] = None,
        doc_type: Optional[str] = None,
        subject: Optional[str] = None,
        model: Optional[str] = None,
        attachments: Optional[list] = None,
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
        user_content = self._build_content(
            mode, question, context, doc_type, subject, attachments or []
        )

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

    def _build_content(
        self,
        mode: str,
        question: str,
        context: Optional[str],
        doc_type: Optional[str],
        subject: Optional[str],
        attachments: list,
    ) -> list:
        """Kullanıcı mesajını blok listesi olarak kurar.

        PDF ve görseller modele doğrudan gider (Claude bunları kendisi okur);
        metni çıkarılmış belgeler talep metnine bölüm olarak eklenir.
        """
        blocks: list = []
        text_docs: list = []

        for i, att in enumerate(attachments, start=1):
            kind = att.get("kind")
            name = att.get("filename") or f"belge-{i}"
            if kind in ("pdf", "image") and att.get("data"):
                b64 = base64.standard_b64encode(att["data"]).decode("ascii")
                blocks.append({"type": "text", "text": f"[EK {i} — {name}]"})
                blocks.append(
                    {
                        "type": "document" if kind == "pdf" else "image",
                        "source": {
                            "type": "base64",
                            "media_type": att.get("media_type")
                            or ("application/pdf" if kind == "pdf" else "image/jpeg"),
                            "data": b64,
                        },
                    }
                )
            elif att.get("text"):
                body = att["text"].strip()[:MAX_PROMPT_CHARS]
                cut = "\n[... belge uzunluk sınırı nedeniyle kısaltıldı]" if len(att["text"].strip()) > MAX_PROMPT_CHARS else ""
                text_docs.append(f"[EK {i} — {name}]\n{body}{cut}")

        parts = [f"TALEP TÜRÜ: {MODES[mode]}"]
        if subject:
            parts.append(f"KONU BAŞLIĞI: {subject}")
        if doc_type:
            parts.append(f"İSTENEN BELGE: {doc_type}")
        if attachments:
            parts.append(
                f"EKLİ BELGE SAYISI: {len(attachments)} — belgeleri oku, "
                "içlerindeki taraf, tarih, tutar ve süreleri analizinde kullan. "
                "Belgede geçmeyen bilgiyi uydurma; okunamayan yeri 'okunamadı' diye belirt."
            )
        parts.append(f"\nSORU / TALEP:\n{question.strip()}")
        if context and context.strip():
            trimmed = context.strip()[:MAX_CONTEXT_CHARS]
            note = "" if len(context.strip()) <= MAX_CONTEXT_CHARS else "\n[... metin uzunluk sınırı nedeniyle kısaltıldı]"
            parts.append(f"\nOLAY / EK BİLGİ:\n{trimmed}{note}")
        for doc in text_docs:
            parts.append(f"\n{doc}")

        blocks.append({"type": "text", "text": "\n".join(parts)})
        return blocks

    def _loads(self, text: str):
        """Modelin döndürdüğü JSON'ı kod bloğu/serbest metin içinden çıkarır."""
        raw = (text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    def _parse(self, text: str) -> dict:
        """Modelin döndürdüğü JSON'ı güvenli parse eder, şemayı tamamlar."""
        data = self._loads(text)

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
