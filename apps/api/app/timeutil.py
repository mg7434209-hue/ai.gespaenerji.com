"""Türkiye saati — "bugün" her yerde buradan okunur.

Railway UTC çalışır; `date.today()` Türkiye'de 00:00-03:00 arasında bir önceki
günü verir. Süre geri sayımı, ajanda ve sabah brifingi bu yüzden
`today_tr()` / `now_tr()` kullanır.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")


def now_tr() -> datetime:
    return datetime.now(TZ)


def today_tr() -> date:
    return now_tr().date()


# ── Türkçe tarih etiketleri ──────────────────────────────────
# Gün adı HER ZAMAN buradan gelir; modele hesaplatılmaz (yanlış gün adı
# yazıyordu: "4 Ekim Pzt"). Araç çıktıları ve "şu an" satırı bunları taşır.
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AY_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
GUN_KISA = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def day_label(d: date) -> str:
    """"6 Eki Pzt" — kısa etiket."""
    return f"{d.day} {AY_KISA[d.month - 1]} {GUN_KISA[d.weekday()]}"


def day_label_long(d: date) -> str:
    """"4 Ekim 2026 Pazar"."""
    return f"{d.day} {AYLAR[d.month - 1]} {d.year} {GUNLER[d.weekday()]}"


def ts_label(value) -> str:
    """ISO zaman damgası (UTC ya da saat dilimli) → Türkiye saatiyle "4 Eki Paz 14:05".
    Saat dilimsiz değer UTC sayılır (sunucular UTC yazar). Okunamazsa ""."""
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    loc = dt.astimezone(TZ)
    return f"{day_label(loc.date())} {loc:%H:%M}"
