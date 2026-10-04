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
