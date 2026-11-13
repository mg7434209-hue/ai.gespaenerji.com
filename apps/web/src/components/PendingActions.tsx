import { useEffect, useState } from 'react'
import { AlertTriangle, Check, ExternalLink, GitPullRequest, Loader2, X } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'

interface Action {
  id: number
  site: string
  kind: 'price' | 'stock'
  summary: string
  status: 'proposed' | 'pr_open' | 'failed' | 'rejected'
  warnings: string[]
  pr_url?: string | null
  error?: string | null
  created_at: string
}

/**
 * JARVIS'in önerdiği fiyat/stok değişiklikleri. Onaylanınca GitHub'da PR açılır;
 * hiçbir öneri onaysız siteye ulaşmaz. Bekleyen ya da yeni sonuçlanan yoksa hiç görünmez.
 */
export function PendingActions() {
  const [actions, setActions] = useState<Action[]>([])
  const [canApprove, setCanApprove] = useState(true)
  const [busy, setBusy] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      const { data } = await api.get<{ can_approve: boolean; actions: Action[] }>('/jarvis/actions')
      setActions(data.actions)
      setCanApprove(data.can_approve)
    } catch { /* kutu sessizce gizli kalır */ }
  }
  useEffect(() => {
    load()
    const t = setInterval(load, 30000) // sohbetten gelen yeni öneri kendiliğinden görünsün
    return () => clearInterval(t)
  }, [])

  async function act(id: number, what: 'approve' | 'reject') {
    setBusy(id); setError(null)
    try {
      await api.post(`/jarvis/actions/${id}/${what}`)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'İşlem yapılamadı.')
    } finally {
      setBusy(null)
      load()
    }
  }

  const day = 24 * 3600 * 1000
  const shown = actions.filter((a) =>
    a.status === 'proposed' || a.status === 'failed' ||
    (a.status === 'pr_open' && Date.now() - new Date(a.created_at + 'Z').getTime() < 3 * day))
  if (shown.length === 0) return null
  const waiting = shown.filter((a) => a.status === 'proposed').length

  return (
    <div className="card border-brand-500/30">
      <div className="flex items-center gap-2 mb-4">
        <GitPullRequest className="w-5 h-5 text-brand-400" />
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Onay bekleyenler</h2>
        {waiting > 0 && <span className="text-[11px] font-semibold text-amber-300 bg-amber-500/10 rounded-full px-2 py-0.5">{waiting}</span>}
      </div>
      {!canApprove && waiting > 0 && (
        <p className="text-sm text-amber-400 mb-3">Onay kapalı: sunucuda JARVIS_GITHUB_TOKEN tanımlı değil. Öneriler burada bekler.</p>
      )}
      {error && <p role="alert" className="text-sm text-red-400 mb-3">{error}</p>}
      <ul className="divide-y divide-slate-800/70">
        {shown.map((a) => (
          <li key={a.id} className="py-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <div className="min-w-0 flex-1 basis-64">
              <div className="text-slate-100 font-medium break-words">{a.summary}</div>
              <div className="text-xs text-slate-500">
                {a.site}.com · {a.kind === 'price' ? 'fiyat' : 'stok'} · öneri #{a.id}
              </div>
              {a.warnings.map((w, i) => (
                <div key={i} className="text-xs text-amber-300 flex items-start gap-1 mt-1"><AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />{w}</div>
              ))}
              {a.status === 'failed' && <div className="text-xs text-red-400 mt-1">Açılamadı: {a.error}</div>}
            </div>
            {a.status === 'pr_open' ? (
              <a href={a.pr_url || '#'} target="_blank" rel="noopener noreferrer" className="text-sm text-emerald-300 flex items-center gap-1.5 hover:text-emerald-200">
                PR açıldı: incele ve birleştir <ExternalLink className="w-4 h-4" />
              </a>
            ) : (
              <div className="flex gap-2">
                <button onClick={() => act(a.id, 'approve')} disabled={busy !== null || !canApprove}
                  className={clsx('btn-primary text-sm flex items-center gap-1.5 min-h-11')}>
                  {busy === a.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  {a.status === 'failed' ? 'Yeniden dene' : 'Onayla'}
                </button>
                <button onClick={() => act(a.id, 'reject')} disabled={busy !== null} className="btn-ghost text-sm flex items-center gap-1.5 min-h-11">
                  <X className="w-4 h-4" /> Reddet
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
