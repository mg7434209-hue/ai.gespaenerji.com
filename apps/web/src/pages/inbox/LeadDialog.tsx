import { useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { api } from '@/lib/api'
import type { Workspace } from '@/types'
import { displayName, type Conversation } from './types'

const tail = (p: string) => p.replace(/\D/g, '').slice(-10)

/** Konuşmadan lead açar (POST /leads). Çalışma alanını konuşma bilmediği için seçilir;
 *  aynı telefonla lead varsa çift kayıt açılmaz. */
export function LeadDialog({ conv, onClose, onCreated }: {
  conv: Conversation; onClose: () => void; onCreated: (name: string) => void
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null)
  const [existing, setExisting] = useState<string | null>(null)
  const [slug, setSlug] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    Promise.all([
      api.get<Workspace[]>('/workspaces'),
      api.get<{ full_name: string; phone: string }[]>('/leads', { params: { limit: 500 } }),
    ]).then(([ws, leads]) => {
      if (!alive) return
      const active = ws.data.filter((w) => w.is_active !== false)
      setWorkspaces(active)
      if (active.length === 1) setSlug(active[0].slug)
      const hit = leads.data.find((l) => tail(l.phone || '') === tail(conv.phone))
      setExisting(hit ? hit.full_name : null)
    }).catch(() => alive && setError('Çalışma alanları yüklenemedi.'))
    return () => { alive = false }
  }, [conv.phone])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function create() {
    setBusy(true); setError(null)
    try {
      const name = displayName(conv)
      await api.post('/leads', { workspace_slug: slug, full_name: name, phone: conv.phone, source: 'whatsapp' })
      onCreated(name)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Lead oluşturulamadı.')
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center p-4 bg-black/60" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="lead-title"
        className="w-full max-w-sm rounded-[14px] bg-os-panel border border-os-line2 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 mb-4">
          <h2 id="lead-title" className="text-lg font-bold text-os-text">Lead'e dönüştür</h2>
          <button type="button" onClick={onClose} className="grid place-items-center w-11 h-11 -mt-2 -mr-2 rounded-[10px] text-os-muted hover:bg-os-raised" aria-label="Kapat">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-[14px] text-os-text2 mb-4"><strong className="text-os-text">{displayName(conv)}</strong> · {conv.phone}</p>

        {existing ? (
          <p className="text-[14px] text-os-urgentfg mb-4" role="status">Bu numara için zaten lead var: {existing}.</p>
        ) : !workspaces && !error ? (
          <div className="flex items-center gap-2 text-sm text-os-muted mb-4"><Loader2 className="w-4 h-4 animate-spin" /> Yükleniyor…</div>
        ) : workspaces && (
          <label className="block mb-4">
            <span className="block text-[13px] text-os-muted mb-1.5">Çalışma alanı</span>
            <select value={slug} onChange={(e) => setSlug(e.target.value)}
              className="w-full min-h-[44px] rounded-[10px] bg-os-bg border border-os-line px-3 text-[15px] text-os-text outline-none focus:border-os-accent">
              <option value="">Seçiniz…</option>
              {workspaces.map((w) => <option key={w.slug} value={w.slug}>{w.name}</option>)}
            </select>
          </label>
        )}
        {error && <p role="alert" className="text-[14px] text-os-urgentfg mb-4">{error}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="min-h-[44px] px-4 rounded-[10px] border border-os-line text-os-text2 font-medium hover:bg-os-raised">Vazgeç</button>
          <button type="button" onClick={create} disabled={!slug || busy || !!existing}
            className="min-h-[44px] px-4 rounded-[10px] bg-os-accent text-os-onaccent font-semibold disabled:opacity-50 flex items-center gap-2">
            {busy && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />} Lead oluştur
          </button>
        </div>
      </div>
    </div>
  )
}
