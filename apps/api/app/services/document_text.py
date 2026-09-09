"""Yüklenen belgeyi tanır ve modele gidecek hâle getirir.

Ek bağımlılık YOK — PDF ve görseller Claude'a doğrudan (base64 blok olarak)
gider, DOCX metni stdlib zipfile ile çıkarılır, düz metin dosyaları çözülür.
"""
import io
import re
import zipfile
from dataclasses import dataclass, field
from typing import Optional

# Tek dosya üst sınırı (base64 şişmesi ve 32 MB istek sınırı gözetilerek)
MAX_FILE_BYTES = 12 * 1024 * 1024
# Bir analizde modele gidebilecek toplam ham veri
MAX_TOTAL_ATTACH_BYTES = 15 * 1024 * 1024
# Metin belgelerde saklanan / gönderilen üst sınır
MAX_STORED_CHARS = 500_000
MAX_PROMPT_CHARS = 60_000

IMAGE_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}
TEXT_EXTS = {"txt", "md", "csv", "json", "log", "eml", "html", "htm", "xml", "rtf"}


class UnsupportedDocument(Exception):
    """Okunamayan dosya türü — kullanıcıya gösterilecek Türkçe mesaj taşır."""


@dataclass
class ExtractedDocument:
    kind: str                      # pdf | image | text
    media_type: str
    text: str = ""                 # text türünde dolu, pdf/image'de boş
    pages: Optional[int] = None
    notes: list = field(default_factory=list)


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def sniff_kind(filename: str, data: bytes) -> str:
    """Uzantı + sihirli baytlarla dosya türünü belirler."""
    ext = _ext(filename)
    if data[:5] == b"%PDF-" or ext == "pdf":
        return "pdf"
    if data[:4] == b"\x89PNG" or data[:3] == b"\xff\xd8\xff" or data[:6] in (b"GIF87a", b"GIF89a"):
        return "image"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image"
    if ext in IMAGE_TYPES:
        return "image"
    if ext == "docx" or (data[:2] == b"PK" and ext in ("docx", "")):
        return "docx"
    if ext in TEXT_EXTS:
        return "text"
    if ext == "doc":
        raise UnsupportedDocument(
            "Eski Word biçimi (.doc) okunamıyor. Dosyayı Word'de açıp .docx veya PDF olarak kaydedin."
        )
    if ext in ("xls", "xlsx"):
        raise UnsupportedDocument(
            "Excel dosyası hukuki belge olarak okunmuyor. İlgili sayfayı PDF'e aktarıp yükleyin."
        )
    # Uzantı tanınmadı: metin olarak çözülebiliyorsa metin say
    try:
        data[:4000].decode("utf-8")
        return "text"
    except UnicodeDecodeError as exc:
        raise UnsupportedDocument(
            "Dosya türü tanınamadı. PDF, DOCX, fotoğraf (JPG/PNG) veya düz metin yükleyin."
        ) from exc


def extract(filename: str, data: bytes) -> ExtractedDocument:
    """Dosyayı analiz edilebilir hâle getirir."""
    if not data:
        raise UnsupportedDocument("Dosya boş görünüyor.")
    if len(data) > MAX_FILE_BYTES:
        mb = MAX_FILE_BYTES // (1024 * 1024)
        raise UnsupportedDocument(
            f"Dosya {mb} MB sınırını aşıyor. PDF'i sıkıştırın veya bölerek yükleyin."
        )

    kind = sniff_kind(filename, data)

    if kind == "pdf":
        pages = _pdf_page_count(data)
        notes = []
        if pages and pages > 100:
            notes.append(
                f"{pages} sayfalık belge — model uzun belgelerde ilk bölümlere ağırlık verebilir."
            )
        return ExtractedDocument(kind="pdf", media_type="application/pdf", pages=pages, notes=notes)

    if kind == "image":
        media = IMAGE_TYPES.get(_ext(filename))
        if not media:
            media = (
                "image/png" if data[:4] == b"\x89PNG"
                else "image/gif" if data[:3] == b"GIF"
                else "image/webp" if data[:4] == b"RIFF"
                else "image/jpeg"
            )
        return ExtractedDocument(
            kind="image",
            media_type=media,
            notes=["Fotoğraf/tarama — okunaklı değilse analiz eksik kalabilir."],
        )

    if kind == "docx":
        text = _docx_text(data)
        if not text.strip():
            raise UnsupportedDocument(
                "Word dosyasından metin çıkarılamadı. Belgeyi PDF olarak kaydedip yükleyin."
            )
        return ExtractedDocument(
            kind="text",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            text=text[:MAX_STORED_CHARS],
        )

    text = _decode(data)
    if not text.strip():
        raise UnsupportedDocument("Dosyadan okunabilir metin çıkmadı.")
    return ExtractedDocument(kind="text", media_type="text/plain", text=text[:MAX_STORED_CHARS])


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _pdf_page_count(data: bytes) -> Optional[int]:
    """Kaba sayfa sayısı — yalnız bilgilendirme için, hata vermez."""
    try:
        hits = len(re.findall(rb"/Type\s*/Page[^s]", data))
        return hits or None
    except Exception:
        return None


# XML etiket temizliği için — DOCX metni
_P_END = re.compile(rb"</w:p>")
_BR = re.compile(rb"<w:(?:br|cr)\b[^>]*/?>")
_TAB = re.compile(rb"<w:tab\b[^>]*/?>")
_TAG = re.compile(rb"<[^>]+>")


def _docx_text(data: bytes) -> str:
    """DOCX içinden düz metin — stdlib zipfile ile, ek paket olmadan."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [n for n in ("word/document.xml",) if n in zf.namelist()]
            if not names:
                return ""
            xml = zf.read(names[0])
    except zipfile.BadZipFile as exc:
        raise UnsupportedDocument("Word dosyası açılamadı (bozuk olabilir).") from exc

    xml = _TAB.sub(b"\t", xml)
    xml = _BR.sub(b"\n", xml)
    xml = _P_END.sub(b"\n", xml)
    text = _TAG.sub(b"", xml).decode("utf-8", errors="replace")

    # XML varlıkları
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(entity, char)

    # Fazla boş satırları topla
    lines = [ln.rstrip() for ln in text.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if ln.strip():
            out.append(ln)
            blank = 0
        else:
            blank += 1
            if blank < 2:
                out.append("")
    return "\n".join(out).strip()


def preview(text: str, limit: int = 600) -> str:
    """Arayüzde gösterilecek kısa önizleme."""
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    return clean[:limit] + ("…" if len(clean) > limit else "")
