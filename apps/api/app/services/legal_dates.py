"""Süre metinlerini gerçek son tarihe çevirir.

"Tebliğden itibaren 7 gün" gibi ifadelerden takvime yazılacak tarih üretir.
Hesap TAHMİNÎDİR: resmî/adli tatil, tebligat usulü ve özel kanun istisnaları
dikkate alınmaz — arayüz bunu açıkça söyler.
"""
import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional, Tuple

# Türkçe sayı sözcükleri (küçük sayılar süre metinlerinde sık geçer)
WORD_NUMBERS = {
    "bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4, "beş": 5, "bes": 5,
    "altı": 6, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
    "onbeş": 15, "onbes": 15, "onbeşgün": 15, "yirmi": 20, "otuz": 30,
    "kırk": 40, "kirk": 40, "elli": 50, "altmış": 60, "altmis": 60, "doksan": 90,
}

MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}

TENS = {
    "on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "kirk": 40, "elli": 50,
    "altmış": 60, "altmis": 60, "yetmiş": 70, "yetmis": 70, "seksen": 80, "doksan": 90,
}
UNITS = {
    "bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4, "beş": 5, "bes": 5,
    "altı": 6, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9,
}
_COMPOUND = re.compile(
    r"\b(" + "|".join(TENS) + r")\s+(" + "|".join(UNITS) + r")\b", re.IGNORECASE
)


def normalize_numbers(text: str) -> str:
    """'on beş' → '15'; birleşik Türkçe sayıları rakama çevirir."""
    return _COMPOUND.sub(
        lambda m: str(TENS[m[1].lower()] + UNITS[m[2].lower()]), text or ""
    )


_PERIOD = re.compile(
    r"(?P<num>\d{1,4}|[a-zçğıöşü]+)\s*(?P<unit>iş\s*günü|is\s*gunu|gün|gun|hafta|ay|yıl|yil|sene)",
    re.IGNORECASE,
)


def parse_period(text: str) -> Optional[Tuple[int, str]]:
    """'7 gün' → (7, 'gun'). Bulamazsa None."""
    if not text:
        return None
    m = _PERIOD.search(normalize_numbers(text.lower()))
    if not m:
        return None
    raw = m.group("num")
    if raw.isdigit():
        amount = int(raw)
    else:
        amount = WORD_NUMBERS.get(raw.replace(" ", ""))
        if not amount:
            return None
    unit = m.group("unit").replace(" ", "")
    if unit in ("işgünü", "isgunu"):
        unit = "isgunu"
    elif unit in ("gün", "gun"):
        unit = "gun"
    elif unit in ("yıl", "yil", "sene"):
        unit = "yil"
    return amount, unit


def add_months(start: date, months: int) -> date:
    """Ay ekler; ayın son günü taşmasını kırpar (31 Ocak + 1 ay = 28/29 Şubat)."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, monthrange(year, month)[1])
    return date(year, month, day)


def add_business_days(start: date, days: int) -> date:
    """Hafta sonlarını atlar (resmî tatiller hesaba katılmaz)."""
    current = start
    left = days
    while left > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            left -= 1
    return current


def compute_due(start: date, period_text: str) -> Optional[date]:
    """Başlangıç günü + süre metninden son tarihi hesaplar."""
    parsed = parse_period(period_text)
    if not parsed or not start:
        return None
    amount, unit = parsed
    if unit == "gun":
        return start + timedelta(days=amount)
    if unit == "isgunu":
        return add_business_days(start, amount)
    if unit == "hafta":
        return start + timedelta(weeks=amount)
    if unit == "ay":
        return add_months(start, amount)
    if unit == "yil":
        return add_months(start, amount * 12)
    return None


_DOTTED = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_WORDED = re.compile(r"\b(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})\b", re.IGNORECASE)


def parse_date(text: str) -> Optional[date]:
    """Metinden '01.09.2026' veya '1 Eylül 2026' biçiminde tarih çıkarır."""
    if not text:
        return None
    m = _DOTTED.search(text)
    if m:
        try:
            return date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
    m = _WORDED.search(text.lower())
    if m:
        month = MONTHS.get(m[2])
        if month:
            try:
                return date(int(m[3]), month, int(m[1]))
            except ValueError:
                return None
    return None


def days_left(due: date, today: Optional[date] = None) -> int:
    return (due - (today or date.today())).days
