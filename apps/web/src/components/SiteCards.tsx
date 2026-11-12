import { useEffect, useState } from 'react'
import { AlertTriangle, ExternalLink, RefreshCw, ShoppingCart, Store } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { SiteCard } from '@/types'

const URLS: Record<SiteCard['site'], string> = {
  gespaenerji: 'https://www.gespaenerji.com',
  gesmarketim: 'https://www.gesmarketim.com',
}

const ALERT_TEXT: Record<string, string> = {
  no_price: 'fiyatı yok',
  no_image: 'görseli yok',
  low_stock: 'stok azaldı',
  out_of_stock: 'tükendi',
  campaign_ending: 'kampanya bitiyor',
  old_price_without_campaign: 'kampanya bitti, eski fiyat duruyor',
}

/** gespaenerji.com + gesmarketim.com durum kartları (salt okunur /api/os/summary). */
export function SiteCards() {
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

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Sitelerim — durum</h2>
        <button onClick={() => load(true)} disabled={loading}
          className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 disabled:opacity-50">
          <RefreshCw className={clsx('w-3 h-3', loading && 'animate-spin')} /> Yenile
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cards === null && <div className="text-slate-500 text-sm">Yükleniyor...</div>}
        {cards?.map((c) => (
          <div key={c.site} className={clsx('card', !c.ok && 'border-amber-500/30')}>
            <div className="flex items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2 min-w-0">
                {c.site === 'gespaenerji' ? <Store className="w-5 h-5 text-amber-400" /> : <ShoppingCart className="w-5 h-5 text-emerald-400" />}
                <span className="font-semibold text-slate-100 truncate">{c.label}</span>
              </div>
              <a href={URLS[c.site]} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-brand-400" aria-label={`${c.label} sitesini aç`}>
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>

            {!c.ok ? (
              <p className="text-sm text-amber-400 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> Veri alınamadı: {c.error}
              </p>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <Stat label="Sipariş (24 sa)" value={c.orders_24h ?? 0} />
                  <Stat label="Sipariş (30 gün)" value={c.orders_30d ?? 0} />
                  {c.site === 'gespaenerji'
                    ? <Stat label="Soru onayı" value={c.qa_pending ?? 0} warn={!!c.qa_pending} />
                    : <Stat label="Ödenmemiş" value={c.orders_unpaid_30d ?? 0} warn={!!c.orders_unpaid_30d} />}
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
                {c.usd_try ? <p className="text-[11px] text-slate-600 mt-3">Kur: {c.usd_try.toLocaleString('tr-TR')} ₺</p> : null}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-lg bg-slate-800/40 px-3 py-2">
      <div className="text-[11px] text-slate-500 leading-tight">{label}</div>
      <div className={clsx('text-xl font-bold', warn ? 'text-amber-300' : 'text-slate-100')}>{value}</div>
    </div>
  )
}
