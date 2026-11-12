import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { SiteApplications } from '@/types'

export function Applications() {
  const [sites, setSites] = useState<SiteApplications[] | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get<{ sites: SiteApplications[] }>('/jarvis/applications')
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
          <h1 className="text-2xl font-bold text-slate-100">Başvurular</h1>
          <p className="text-sm text-slate-400 mt-1">Son 30 gün. Ad ve telefon burada tutulmaz; aramak için sitenin kendi panelini kullan.</p>
        </div>
        <button onClick={load} disabled={loading} className="btn-ghost text-sm flex items-center gap-2">
          <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} /> Yenile
        </button>
      </div>

      {sites === null && <div className="text-slate-500 text-sm">Yükleniyor...</div>}
      {sites?.length === 0 && <div className="text-slate-500 text-sm">Başvurular alınamadı.</div>}
      {sites?.map((s) => (
        <section key={s.site} className="card !p-0 overflow-hidden">
          <header className="flex flex-wrap items-center justify-between gap-2 px-5 py-4 border-b border-slate-800">
            <h2 className="font-semibold text-slate-100">{s.label}</h2>
            <span className="text-xs text-slate-500">
              {s.error ? '' : `${s.count ?? 0} başvuru`}
              {s.uncontacted ? <span className="text-amber-300"> · {s.uncontacted} aranmamış</span> : null}
            </span>
          </header>
          {s.error ? (
            <p className="px-5 py-4 text-sm text-amber-400 flex items-start gap-2"><AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> {s.error}</p>
          ) : !s.applications?.length ? (
            <p className="px-5 py-4 text-sm text-slate-500">Bu dönemde başvuru yok.</p>
          ) : (
            <>
              {(s.by_city?.length || s.by_package?.length) ? (
                <p className="px-5 pt-4 text-xs text-slate-400">
                  {s.by_city?.length ? <>İl: {s.by_city.map((x) => `${x.name} (${x.count})`).join(' · ')}</> : null}
                  {s.by_city?.length && s.by_package?.length ? <br /> : null}
                  {s.by_package?.length ? <>Paket: {s.by_package.map((x) => `${x.name} (${x.count})`).join(' · ')}</> : null}
                </p>
              ) : null}
              <ul className="sm:hidden divide-y divide-slate-800/70">
                {s.applications.map((a, i) => (
                  <li key={(a.ref ?? a.id ?? i).toString()} className="px-5 py-3 space-y-1">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-100">{[a.city, a.district].filter(Boolean).join(' / ') || '—'}</span>
                      {a.contacted != null && <span className={clsx('text-xs font-medium rounded-full px-2 py-0.5', a.contacted ? 'text-emerald-300 bg-emerald-500/10' : 'text-amber-300 bg-amber-500/10')}>{a.contacted ? 'Arandı' : 'Aranmadı'}</span>}
                      {a.covered != null && <span className={clsx('text-xs font-medium rounded-full px-2 py-0.5', a.covered ? 'text-emerald-300 bg-emerald-500/10' : 'text-slate-400 bg-slate-700/40')}>{a.covered ? 'Kapsamada' : 'Kapsama dışı'}</span>}
                    </div>
                    <div className="text-sm text-slate-300">{a.package || a.packageInterest || '—'}</div>
                    <div className="text-xs text-slate-500">{a.created_label || '—'}{a.source ? ` · ${a.source}` : ''}</div>
                  </li>
                ))}
              </ul>
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs text-slate-500">
                    <tr>
                      <th className="px-5 py-2 font-medium">Tarih</th>
                      <th className="px-3 py-2 font-medium">Konum</th>
                      <th className="px-3 py-2 font-medium">Paket</th>
                      <th className="px-3 py-2 font-medium">Kaynak</th>
                      <th className="px-5 py-2 font-medium">Durum</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70">
                    {s.applications.map((a, i) => (
                      <tr key={(a.ref ?? a.id ?? i).toString()} className="text-slate-300">
                        <td className="px-5 py-3 whitespace-nowrap text-slate-400">{a.created_label || '—'}</td>
                        <td className="px-3 py-3 whitespace-nowrap">{[a.city, a.district].filter(Boolean).join(' / ') || '—'}</td>
                        <td className="px-3 py-3 max-w-xs truncate">
                          {a.package || a.packageInterest || '—'}
                          {a.monthlyTL ? <span className="text-slate-500"> · {a.monthlyTL.toLocaleString('tr-TR')} ₺/ay</span> : null}
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap text-slate-400">{a.source || '—'}</td>
                        <td className="px-5 py-3 whitespace-nowrap text-xs">
                          {a.contacted != null && (
                            <span className={clsx('font-medium rounded-full px-2 py-0.5', a.contacted ? 'text-emerald-300 bg-emerald-500/10' : 'text-amber-300 bg-amber-500/10')}>
                              {a.contacted ? 'Arandı' : 'Aranmadı'}
                            </span>
                          )}
                          {a.covered != null && (
                            <span className={clsx('font-medium rounded-full px-2 py-0.5', a.covered ? 'text-emerald-300 bg-emerald-500/10' : 'text-slate-400 bg-slate-700/40')}>
                              {a.covered ? 'Kapsamada' : 'Kapsama dışı'}
                            </span>
                          )}
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
