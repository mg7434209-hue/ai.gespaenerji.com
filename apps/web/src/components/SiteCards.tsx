import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ExternalLink, FileText, Newspaper, PlugZap, RefreshCw, ShoppingCart, Store, Wifi } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { SiteCard, SiteKey } from '@/types'

const ICONS: Record<SiteKey, { icon: typeof Store; color: string }> = {
  gespaenerji: { icon: Store, color: 'text-amber-400' },
  gesmarketim: { icon: ShoppingCart, color: 'text-emerald-400' },
  tarifesec: { icon: FileText, color: 'text-sky-400' },
  internetbasvuru: { icon: Wifi, color: 'text-violet-400' },
  cezarehberi: { icon: Newspaper, color: 'text-rose-400' },
}

const ALERT_TEXT: Record<string, string> = {
  no_price: 'fiyatı yok',
  no_image: 'görseli yok',
  low_stock: 'stok azaldı',
  out_of_stock: 'tükendi',
  campaign_ending: 'kampanya bitiyor',
  old_price_without_campaign: 'kampanya bitti, eski fiyat duruyor',
}

const num = (v?: number | null) => (v ?? 0).toLocaleString('tr-TR')

/**
 * Site durum kartları (salt okunur /api/os/summary + Gespa OS defterleri).
 * `only`: ana sayfada yalnız mağazalar gösterilir; Siteler sayfası hepsini gösterir.
 */
export function SiteCards({ only, title = 'Sitelerim — durum' }: { only?: SiteCard['kind'][]; title?: string }) {
  const [cards, setCards] = useState<SiteCard[] | null>(null)
  const [loading, setLoading] = useState(false)

  async function load(fresh = false) {
    setLoading(true)
    try {
      const { data } = await api.get<{ sites: SiteCard[] }>('/jarvis/sites', { params: { fresh } })
      setCards(data.sites)
    } catch {
      setCards([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const shown = cards?.filter((c) => !only || only.includes(c.kind))

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">{title}</h2>
        <div className="flex items-center gap-4">
          {only && <Link to="/siteler" className="text-xs text-slate-400 hover:text-brand-300">Tüm siteler →</Link>}
          <button onClick={() => load(true)} disabled={loading}
            className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 disabled:opacity-50">
            <RefreshCw className={clsx('w-3 h-3', loading && 'animate-spin')} /> Yenile
          </button>
        </div>
      </div>
      <div className={clsx('grid grid-cols-1 gap-4', only ? 'md:grid-cols-2' : 'md:grid-cols-2 xl:grid-cols-3')}>
        {cards === null && <div className="text-slate-500 text-sm">Yükleniyor...</div>}
        {cards?.length === 0 && <div className="text-slate-500 text-sm">Site durumu alınamadı.</div>}
        {shown?.map((c) => <Card key={c.site} c={c} />)}
      </div>
    </div>
  )
}

function Card({ c }: { c: SiteCard }) {
  const { icon: Icon, color } = ICONS[c.site]
  const offline = !c.ok && c.configured === false
  return (
    <div className={clsx('card', !c.ok && (offline ? 'border-slate-700 border-dashed' : 'border-amber-500/30'))}>
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className={clsx('w-5 h-5 shrink-0', color)} />
          <span className="font-semibold text-slate-100 truncate">{c.label}</span>
          {c.ok && !!c.alerts && (
            <span className="shrink-0 whitespace-nowrap text-[11px] font-semibold text-amber-300 bg-amber-500/10 rounded-full px-2 py-0.5">{c.alerts} iş</span>
          )}
        </div>
        {c.url && (
          <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-brand-400" aria-label={`${c.label} sitesini aç`}>
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      {!c.ok && (
        offline ? (
          <p className="text-sm text-slate-400 flex items-start gap-2">
            <PlugZap className="w-4 h-4 mt-0.5 shrink-0" /> Henüz bağlı değil: {c.error}
          </p>
        ) : (
          <p className="text-sm text-amber-400 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> Veri alınamadı: {c.error}
          </p>
        )
      )}
      {/* Özet alınamasa da defterdeki siparişler görünür */}
      {!c.ok && c.orders_30d != null && (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <Stat label="Sipariş (24 sa)" value={c.orders_24h} />
          <Stat label="Sipariş (30 gün)" value={c.orders_30d} />
        </div>
      )}

      {c.ok && c.kind === 'shop' && <Shop c={c} />}
      {c.ok && c.kind === 'leads' && <Leads c={c} />}
      {c.ok && c.kind === 'content' && <Content c={c} />}
    </div>
  )
}

function Shop({ c }: { c: SiteCard }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-2 mb-4">
        <Stat label="Sipariş (24 sa)" value={c.orders_24h} />
        <Stat label="Sipariş (30 gün)" value={c.orders_30d} />
        {c.site === 'gespaenerji'
          ? <Stat label="Soru onayı" value={c.qa_pending} warn={!!c.qa_pending} />
          : <Stat label="Ödenmemiş" value={c.orders_unpaid_30d} warn={!!c.orders_unpaid_30d} />}
      </div>
      {c.site === 'gespaenerji' ? (
        c.alert_items && c.alert_items.length > 0 ? (
          <ul className="space-y-1">
            {c.alert_items.slice(0, 4).map((a, i) => (
              <li key={i} className="text-xs text-amber-300/90 flex gap-1.5">
                <span>⚠</span>
                <span className="truncate">
                  {a.type === 'campaign_ending' ? `Kampanya bitiyor: ${a.endsAt}` : `${a.name || a.id}: ${ALERT_TEXT[a.type] || a.type}${a.stock != null ? ` (${a.stock} adet)` : ''}`}
                </span>
              </li>
            ))}
          </ul>
        ) : <p className="text-xs text-slate-500">Ürün uyarısı yok.</p>
      ) : (
        <p className="text-xs text-slate-400">
          Stokta yok: <span className={clsx(c.out_of_stock ? 'text-amber-300' : 'text-slate-300')}>{c.out_of_stock ?? 0}</span>
          {' · '}Görselsiz: <span className={clsx(c.no_image ? 'text-amber-300' : 'text-slate-300')}>{c.no_image ?? 0}</span>
        </p>
      )}
      <p className="text-[11px] text-slate-600 mt-3">
        {c.usd_try ? `Kur: ${c.usd_try.toLocaleString('tr-TR')} ₺` : ''}
        {c.usd_try && c.orders_source === 'ledger' ? ' · ' : ''}
        {c.orders_source === 'ledger' ? 'Siparişler kalıcı defterden' : ''}
      </p>
    </>
  )
}

function Leads({ c }: { c: SiteCard }) {
  const tarife = c.site === 'tarifesec'
  return (
    <>
      <div className="grid grid-cols-3 gap-2 mb-4">
        <Stat label="Başvuru (24 sa)" value={c.leads_24h} />
        <Stat label="Başvuru (30 gün)" value={c.leads_30d} />
        {tarife
          ? <Stat label="Aranmamış" value={c.leads_uncontacted} warn={!!c.leads_uncontacted} />
          : <Stat label="Kapsamada" value={c.covered} />}
      </div>
      {tarife ? (
        <ul className="space-y-1 text-xs">
          <li className={clsx(c.price_pending ? 'text-amber-300' : 'text-slate-400')}>Onay bekleyen fiyat değişikliği: {c.price_pending ?? 0}</li>
          <li className={clsx(c.price_stale ? 'text-amber-300' : 'text-slate-400')}>Güncellenmemiş paket: {c.price_stale ?? 0}</li>
          {c.scraper_error && (
            <li className="text-amber-300/90 truncate">⚠ Son tarama hatası{c.scraper_error.operator ? ` (${c.scraper_error.operator})` : ''}: {c.scraper_error.message}</li>
          )}
        </ul>
      ) : (
        <p className="text-xs text-slate-400">
          {c.by_city && c.by_city.length > 0
            ? <>En çok: {c.by_city.slice(0, 3).map((x) => `${x.name} (${x.count})`).join(' · ')}</>
            : 'Henüz kayıtlı başvuru yok.'}
        </p>
      )}
      {c.visitors_today != null && <p className="text-[11px] text-slate-600 mt-3">Bugün {num(c.visitors_today)} ziyaretçi</p>}
    </>
  )
}

function Content({ c }: { c: SiteCard }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-2 mb-4">
        <Stat label="Ziyaretçi (bugün)" value={c.visitors_today} />
        <Stat label="Ziyaretçi (7 gün)" value={c.visitors_7d} />
        <Stat label="Yeni mesaj" value={c.messages_unread} warn={!!c.messages_unread} />
      </div>
      {c.top_articles && c.top_articles.length > 0 && (
        <ul className="space-y-1">
          {c.top_articles.slice(0, 3).map((a) => (
            <li key={a.slug} className="text-xs text-slate-400 flex justify-between gap-3">
              <span className="truncate">{a.title}</span>
              <span className="text-slate-500 shrink-0">{num(a.views)}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-[11px] text-slate-600 mt-3">
        Yayında {num(c.articles_published)} yazı · 7 günde {num(c.petitions_7d)} dilekçe · {num(c.bot_hits_7d)} bot ziyareti
      </p>
    </>
  )
}

function Stat({ label, value, warn }: { label: string; value?: number | null; warn?: boolean }) {
  return (
    <div className="rounded-lg bg-slate-800/40 px-2.5 py-2 min-w-0">
      <div className="text-[11px] text-slate-500 leading-tight break-words">{label}</div>
      <div className={clsx('text-xl font-bold', warn ? 'text-amber-300' : 'text-slate-100')}>{num(value)}</div>
    </div>
  )
}
