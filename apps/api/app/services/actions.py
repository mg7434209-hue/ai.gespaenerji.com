"""Onaylı yönetim: JARVIS önerir → Mustafa onaylar → GitHub'da PR açılır.

Kapsam (ilk sürüm): gespaenerji.com ürün FİYATI ve STOK adedi. İkisi de
`assets/config.js` içindeki `packages[]` satırlarıdır; PR yalnız o dosyayı
değiştirir, sitenin kendi derleme iş akışı çıktıyı üretir.

Güvenlik kuralları:
- JARVIS'in tek yazma aracı `propose_change`'tir ve YALNIZ `jarvis_actions`
  tablosuna öneri yazar. Onay ucu oturum ister; JARVIS onaylayamaz.
- Onay anında dosya YENİDEN okunur; öneri anındaki eski değer hâlâ
  geçerli değilse (biri arada değiştirdiyse) PR açılmaz.
- Fiyat USD tutulur (site kuralı). ₺ verilirse o anki site kuruyla çevrilir.
"""
import math
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models_jarvis import JarvisAction
from app.services import github, sites
from app.timeutil import now_tr

CONFIG_PATH = "assets/config.js"
REPOS = {"gespaenerji": "gespa_repo"}
MAX_CHANGE_PCT = 60        # bundan büyük fiyat farkı "büyük değişiklik" diye işaretlenir
MAX_OPEN = 20              # onay bekleyen öneri sınırı (yanlış anlaşılan sesli komut seli olmasın)
UNSET = object()


class ActionError(ValueError):
    """Kullanıcıya gösterilebilir öneri/onay hatası."""


def tl_round(v: float) -> int:
    """gespaenerji kur.js `tlRound` ile AYNI kademeli yuvarlama."""
    step = 100 if v >= 10000 else 50 if v >= 1000 else 10
    return int(math.floor(v / step + 0.5) * step)  # JS Math.round gibi: yarım YUKARI (Python round() çifte yuvarlar)


def tl(v: Optional[float]) -> str:
    return "—" if v is None else "₺" + f"{int(round(v)):,}".replace(",", ".")


# ── config.js düzenleme (saf işlev; ağ yok) ──────────────────

_ID_LINE = re.compile(r'^\s*id:\s*"([^"]+)"', re.M)
_PRICE = re.compile(r'(?<![A-Za-z])price:\s*(null|[0-9]+(?:\.[0-9]+)?)')
_STOCK = re.compile(r'(?<![A-Za-z])stock:\s*(null|[0-9]+)\s*,?[ \t]*')


def _block(src: str, product_id: str) -> tuple[int, int]:
    """Ürünün `id: "…"` satırından bir sonraki ürünün id satırına kadar olan aralık."""
    start = src.find("packages: [")
    if start < 0:
        raise ActionError("config.js içinde packages listesi bulunamadı")
    ids = [m for m in _ID_LINE.finditer(src, start)]
    for i, m in enumerate(ids):
        if m.group(1) == product_id:
            end = ids[i + 1].start() if i + 1 < len(ids) else len(src)
            return m.start(), end
    raise ActionError(f"config.js içinde '{product_id}' ürünü bulunamadı")


def _top_price(block: str) -> re.Match:
    """Ürünün KENDİ fiyatı: `bulk: { … price: … }` içindeki ve yorum satırlarındaki değil."""
    for m in _PRICE.finditer(block):
        line_start = block.rfind("\n", 0, m.start()) + 1
        before = block[line_start:m.start()]
        if "//" in before:
            continue
        if before.count("{") > before.count("}"):
            continue
        return m
    raise ActionError("ürün satırında fiyat alanı bulunamadı")


def read_product(src: str, product_id: str) -> dict:
    a, b = _block(src, product_id)
    block = src[a:b]
    pm = _top_price(block)
    sm = next((m for m in _STOCK.finditer(block)
               if "//" not in block[block.rfind("\n", 0, m.start()) + 1:m.start()]), None)
    return {
        "price": None if pm.group(1) == "null" else float(pm.group(1)),
        "stock": None if sm is None or sm.group(1) == "null" else int(sm.group(1)),
        "has_bulk": bool(re.search(r'(?<![A-Za-z])bulk:\s*\{', block)),
        "has_old_price": bool(re.search(r'(?<![A-Za-z])oldPrice:\s*[0-9]', block)),
    }


def edit_config(src: str, product_id: str, *, price_usd: Any = UNSET, stock: Any = UNSET,
                note: str = "") -> str:
    """config.js metninde TEK ürünün fiyatını ve/veya stok adedini değiştirir."""
    a, b = _block(src, product_id)
    block = src[a:b]
    if price_usd is not UNSET:
        m = _top_price(block)
        line_end = block.find("\n", m.end())
        line_end = len(block) if line_end < 0 else line_end
        tail = block[m.end():line_end]
        # Satır sonundaki eski "₺… @ kur" notu artık yanlış olur: yenisiyle değiştir
        tail = re.sub(r'\s*//.*$', '', tail) + (f"  // {note}" if note else "")
        block = block[:m.start()] + f"price: {price_usd:g}" + tail + block[line_end:]
    if stock is not UNSET:
        m = next((x for x in _STOCK.finditer(block)
                  if "//" not in block[block.rfind("\n", 0, x.start()) + 1:x.start()]), None)
        if stock is None:
            if m:
                block = block[:m.start()] + block[m.end():]
        elif m:
            block = block[:m.start()] + f"stock: {int(stock)}, " + block[m.end():]
        else:
            p = _top_price(block)
            block = block[:p.start()] + f"stock: {int(stock)}, " + block[p.start():]
    return src[:a] + block + src[b:]


# ── Öneri ────────────────────────────────────────────────────

def _product(site: str, product_id: str) -> tuple[dict, float]:
    data = sites.fetch_summary(site)
    if "error" in data:
        raise ActionError(f"{site} şu an okunamıyor: {data['error']}")
    products = data.get("catalog", {}).get("products", [])
    p = next((x for x in products if x.get("id") == product_id), None)
    if not p:
        raise ActionError(f"'{product_id}' kimlikli ürün yok. Ürün kimliğini site_catalog aracıyla "
                          "(include_products) bul.")
    rate = float(data.get("fx", {}).get("rate") or 0)
    return p, rate


def propose(db: Session, inp: dict, channel: str = "web") -> dict:
    site = inp.get("site") or "gespaenerji"
    if site not in REPOS:
        raise ActionError("Şimdilik yalnız gespaenerji için değişiklik önerilebilir")
    product_id = str(inp.get("product_id") or "").strip()
    if not product_id:
        raise ActionError("product_id gerekli")
    has_price = inp.get("new_price_tl") not in (None, "") or inp.get("new_price_usd") not in (None, "")
    has_stock = "new_stock" in inp and inp.get("new_stock") != ""
    if has_price == has_stock:
        raise ActionError("Tek öneride ya fiyat ya stok değişir (ikisi için iki ayrı öneri)")
    if db.query(JarvisAction).filter(JarvisAction.status == "proposed").count() >= MAX_OPEN:
        raise ActionError("Onay bekleyen çok öneri var; önce onları onayla ya da reddet")

    p, rate = _product(site, product_id)
    name = p.get("name") or product_id
    warnings: list[str] = []

    if has_price:
        if p.get("price") is None:
            raise ActionError("Bu ürün 'teklif alın' ürünü (fiyatı yok); ilk fiyat repodan elle girilir")
        if p.get("currency") != "USD" or rate <= 0:
            raise ActionError("Ürün USD tabanlı değil ya da site kuru okunamadı")
        try:
            if inp.get("new_price_usd") not in (None, ""):
                usd = round(float(inp["new_price_usd"]), 2)
            else:
                usd = round(float(inp["new_price_tl"]) / rate, 2)
        except (TypeError, ValueError):
            raise ActionError("Fiyat sayı olmalı")
        if not 0.5 <= usd <= 100000:
            raise ActionError("Fiyat makul aralıkta değil")
        old_usd, old_tl = float(p["price"]), p.get("priceTL")
        new_tl = tl_round(usd * rate)
        if abs(usd - old_usd) < 0.005:
            raise ActionError("Fiyat zaten bu değerde")
        pct = (usd - old_usd) / old_usd * 100
        if abs(pct) > MAX_CHANGE_PCT:
            warnings.append(f"Büyük değişiklik: %{pct:+.0f}. Rakamı doğru anladığımdan emin ol.")
        if p.get("oldPrice"):
            warnings.append("Üründe indirim (eski fiyat) tanımlı; yeni fiyat eski fiyatın altında kalmalı.")
        kind = "price"
        payload = {"old": {"usd": old_usd, "tl": old_tl}, "new": {"usd": usd, "tl": new_tl},
                   "usd_try": rate, "pct": round(pct, 1)}
        summary = f"{name}: {tl(old_tl)} → {tl(new_tl)} (%{pct:+.1f})"
    else:
        raw = inp.get("new_stock")
        if raw is None:
            new_stock = None
        else:
            try:
                new_stock = int(raw)
            except (TypeError, ValueError):
                raise ActionError("Stok tam sayı olmalı (sınırsız/genel rozet için null)")
            if not 0 <= new_stock <= 100000:
                raise ActionError("Stok 0 ile 100.000 arasında olmalı")
        old_stock = p.get("stock")
        if new_stock == old_stock:
            raise ActionError("Stok zaten bu değerde")
        if new_stock == 0:
            warnings.append("Stok 0 olunca ürün satışa kapanır (sepete eklenemez).")
        kind = "stock"
        payload = {"old": {"stock": old_stock}, "new": {"stock": new_stock}}
        show = lambda v: "belirtilmemiş" if v is None else f"{v} adet"  # noqa: E731
        summary = f"{name}: stok {show(old_stock)} → {show(new_stock)}"

    payload["warnings"] = warnings
    row = JarvisAction(site=site, kind=kind, product_id=product_id, product_name=name[:255],
                       payload=payload, summary=summary, channel=channel)
    db.add(row)
    db.commit()
    return {"proposal_id": row.id, "status": "proposed", "summary": summary, "warnings": warnings,
            "applied": False,
            "next": "Henüz HİÇBİR ŞEY değişmedi. Mustafa Gespa OS'te 'Onay bekleyenler'den onaylayınca "
                    "GitHub'da PR açılır; PR birleşince site güncellenir."}


def out(a: JarvisAction) -> dict:
    return {"id": a.id, "site": a.site, "kind": a.kind, "product_id": a.product_id,
            "product_name": a.product_name, "summary": a.summary, "status": a.status,
            "warnings": (a.payload or {}).get("warnings", []), "pr_url": a.pr_url, "error": a.error,
            "channel": a.channel, "created_at": a.created_at}


# ── Onay / ret (yalnız oturumlu uçtan çağrılır) ──────────────

def reject(db: Session, a: JarvisAction) -> JarvisAction:
    if a.status not in ("proposed", "failed"):
        raise ActionError("Bu öneri artık reddedilemez")
    a.status, a.updated_at = "rejected", datetime.utcnow()
    db.commit()
    return a


def approve(db: Session, a: JarvisAction, *, client=None) -> JarvisAction:
    if a.status not in ("proposed", "failed"):
        raise ActionError("Bu öneri zaten işlendi")
    if not github.configured() and client is None:
        raise ActionError("JARVIS_GITHUB_TOKEN tanımlı değil; öneri onaylanamıyor")
    repo = getattr(settings, REPOS[a.site])
    old, new = a.payload["old"], a.payload["new"]
    day = now_tr().strftime("%d.%m.%Y")

    def edit(src: str) -> str:
        cur = read_product(src, a.product_id)
        if a.kind == "price":
            if cur["has_bulk"]:
                raise ActionError("Üründe 5'li adet fiyatı var; tekli fiyatla birlikte elle güncellenmeli")
            if cur["price"] is None or abs(cur["price"] - old["usd"]) > 0.005:
                raise ActionError("Fiyat öneriden sonra değişmiş; öneriyi reddedip yeniden iste")
            note = f"{tl(new['tl'])} @ {a.payload['usd_try']:g} (JARVIS önerisi #{a.id}, {day})"
            return edit_config(src, a.product_id, price_usd=new["usd"], note=note)
        if cur["stock"] != old["stock"]:
            raise ActionError("Stok öneriden sonra değişmiş; öneriyi reddedip yeniden iste")
        return edit_config(src, a.product_id, stock=new["stock"])

    body = (f"**{a.summary}**\n\nGespa OS'te onaylanan JARVIS önerisi #{a.id}. Yalnız `{CONFIG_PATH}` "
            f"içinde `{a.product_id}` ürününün {'fiyatı' if a.kind == 'price' else 'stok adedi'} değişir.\n\n"
            + ("Fiyat USD tutulur: "
               f"{old['usd']:g} → {new['usd']:g} USD (kur {a.payload['usd_try']:g}).\n\n" if a.kind == "price" else "")
            + "Derleme çıktısı (dil sayfaları, ürün akışı) bu dalda iş akışıyla üretilir; "
              "birleştirmeden önce farkı kontrol edin.")
    try:
        a.pr_url = github.open_file_pr(
            repo, CONFIG_PATH, f"jarvis/{a.id}-{a.kind}-{a.product_id}"[:80], edit,
            title=f"JARVIS: {a.summary}"[:120], body=body,
            message=f"{a.summary}\n\nGespa OS'te onaylanan JARVIS önerisi #{a.id}.", client=client)
        a.status, a.error = "pr_open", None
    except (ActionError, ValueError, github.GitHubError) as e:
        a.status, a.error = "failed", str(e)[:500]
    a.updated_at = datetime.utcnow()
    db.commit()
    return a
