import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { SiteOrderRow, SiteOrders } from '@/types'

const tl = (v?: number) => (v == null ? '—' : `${Math.round(v).toLocaleString('tr-TR')} ₺`)

/** İki site siparişi farklı adlarla yazar; satır tek biçime çevrilir. */
function norm(o: SiteOrderRow) {
  const paid = o.status ? o.status === 'paid' : !!o.paid
  const failed = o.status === 'failed'
  const done = o.fulfilled ?? o.done ?? null
  return {
    ref: o.ref || o.no || '—',
    when: o.created_label || (o.createdAt ? new Date(o.createdAt).toLocaleString('tr-TR') : '—'),
    channel: o.channel || o.pay || '—',
    total: o.totalTL ?? o.total,
    state: failed ? 'Başarısız' : paid ? 'Ödendi' : 'Ödeme bekliyor',
    tone: failed ? 'text-red-400 bg-red-500/10' : paid ? 'text-emerald-300 bg-emerald-500/10' : 'text-amber-300 bg-amber-500/10',
    done,
    items: (o.items || []).map((i) => `${i.qty ?? 1} × ${i.name || i.id}`).join(', ') || o.desc || '—',
  }
}

export function Orders() {
  const [sites, setSites] = useState<SiteOrders[] | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get<{ sites: SiteOrders[] }>('/jarvis/orders')
      setSites(data.sites)
    } catch {
      setSites([])
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  return (
    <div className="p-4 sm:p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Siparişler</h1>
          <p className="text-sm text-slate-400 mt-1">Son 30 gün. Alıcı bilgileri (ad, telefon, adres) sitenin yönetim panelindedir.</p>
        </div>
        <button onClick={load} disabled={loading} className="btn-ghost text-sm flex items-center gap-2">
          <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} /> Yenile
        </button>
      </div>

      {sites === null && <div className="text-slate-500 text-sm">Yükleniyor...</div>}
      {sites?.length === 0 && <div className="text-slate-500 text-sm">Siparişler alınamadı.</div>}
      {sites?.map((s) => (
        <section key={s.site} className="card !p-0 overflow-hidden">
          <header className="flex flex-wrap items-center justify-between gap-2 px-5 py-4 border-b border-slate-800">
            <h2 className="font-semibold text-slate-100">{s.label}</h2>
            <span className="text-xs text-slate-500">{s.error ? '' : `${s.count ?? 0} sipariş · ${s.source ?? ''}`}</span>
          </header>
          {s.error ? (
            <p className="px-5 py-4 text-sm text-amber-400 flex items-start gap-2"><AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> {s.error}</p>
          ) : !s.orders?.length ? (
            <p className="px-5 py-4 text-sm text-slate-500">Bu dönemde sipariş yok.</p>
          ) : (
            <>
            {/* Telefon: satır yerine kart — tutar ve durum yatay kaydırmadan görünür */}
            <ul className="sm:hidden divide-y divide-slate-800/70">
              {s.orders.map(norm).map((o, i) => (
                <li key={o.ref + i} className="px-5 py-3 space-y-1">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-slate-100">{tl(o.total)}</span>
                    <span className={clsx('text-xs font-medium rounded-full px-2 py-0.5', o.tone)}>{o.state}</span>
                  </div>
                  <div className="text-sm text-slate-300">{o.items}</div>
                  <div className="text-xs text-slate-500">{o.when} · {o.channel} · <span className="font-mono">{o.ref}</span></div>
                </li>
              ))}
            </ul>
            <div className="hidden sm:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-slate-500">
                  <tr>
                    <th className="px-5 py-2 font-medium">Tarih</th>
                    <th className="px-3 py-2 font-medium">No</th>
                    <th className="px-3 py-2 font-medium">Ürünler</th>
                    <th className="px-3 py-2 font-medium">Ödeme</th>
                    <th className="px-3 py-2 font-medium text-right">Tutar</th>
                    <th className="px-5 py-2 font-medium">Durum</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {s.orders.map(norm).map((o, i) => (
                    <tr key={o.ref + i} className="text-slate-300">
                      <td className="px-5 py-3 whitespace-nowrap text-slate-400">{o.when}</td>
                      <td className="px-3 py-3 whitespace-nowrap font-mono text-xs">{o.ref}</td>
                      <td className="px-3 py-3 max-w-xs truncate" title={o.items}>{o.items}</td>
                      <td className="px-3 py-3 whitespace-nowrap text-slate-400">{o.channel}</td>
                      <td className="px-3 py-3 whitespace-nowrap text-right font-semibold text-slate-100">{tl(o.total)}</td>
                      <td className="px-5 py-3 whitespace-nowrap">
                        <span className={clsx('text-xs font-medium rounded-full px-2 py-0.5', o.tone)}>{o.state}</span>
                        {o.done === true && <span className="ml-2 text-xs text-slate-500">tamamlandı</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </>
          )}
        </section>
      ))}
    </div>
  )
}
