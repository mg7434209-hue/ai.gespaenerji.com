import { useEffect, useMemo, useState } from 'react'
import { FileStack, Loader2, Sparkles, X } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { LegalNav } from '@/components/LegalNav'
import { LegalUploader } from '@/components/LegalUploader'
import { ResultPanel } from '@/components/LegalResult'
import type { LegalConsultation, LegalDocument, LegalMatter, LegalTemplate } from '@/types'

export function LegalTemplates() {
  const [templates, setTemplates] = useState<LegalTemplate[]>([])
  const [matters, setMatters] = useState<LegalMatter[]>([])
  const [active, setActive] = useState<LegalTemplate | null>(null)
  const [details, setDetails] = useState('')
  const [matterId, setMatterId] = useState('')
  const [docs, setDocs] = useState<LegalDocument[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [out, setOut] = useState<LegalConsultation | null>(null)
  const [category, setCategory] = useState('all')

  useEffect(() => {
    api.get<LegalTemplate[]>('/legal/templates').then(({ data }) => setTemplates(data))
    api.get<LegalMatter[]>('/legal/matters').then(({ data }) => setMatters(data))
  }, [])

  const categories = useMemo(
    () => Array.from(new Set(templates.map((t) => t.category))),
    [templates],
  )
  const visible = useMemo(
    () => (category === 'all' ? templates : templates.filter((t) => t.category === category)),
    [templates, category],
  )

  function pick(t: LegalTemplate) {
    setActive(t)
    setOut(null)
    setError(null)
    setDetails(t.fields.map((f) => `${f}: `).join('\n'))
  }

  async function draft(e: React.FormEvent) {
    e.preventDefault()
    if (!active) return
    if (details.trim().length < 5) {
      setError('Şablonun istediği bilgileri doldur.')
      return
    }
    setBusy(true)
    setError(null)
    setOut(null)
    try {
      const { data } = await api.post<LegalConsultation>(`/legal/templates/${active.id}/draft`, {
        details: details.trim(),
        matter_id: matterId ? Number(matterId) : null,
        document_ids: docs.map((d) => d.id),
      })
      setOut(data)
      if (data.status === 'error') setError(data.error || 'Taslak üretilemedi.')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Taslak üretilemedi.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <LegalNav />

      <div>
        <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <FileStack className="w-5 h-5" />
          </span>
          Şablonlar
        </h1>
        <p className="text-slate-400 mt-2">
          Sık kullanılan dilekçe ve yazışmalar. Şablonu seç, istenen bilgileri doldur — ilgili
          avukat ajanı belgeyi senin olayına göre yazar.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Chip active={category === 'all'} onClick={() => setCategory('all')}>
          Tümü ({templates.length})
        </Chip>
        {categories.map((c) => (
          <Chip key={c} active={category === c} onClick={() => setCategory(c)}>
            {c}
          </Chip>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {visible.map((t) => (
          <button
            key={t.id}
            onClick={() => pick(t)}
            className={clsx(
              'card text-left transition-colors',
              active?.id === t.id ? 'border-brand-500/60' : 'hover:border-slate-700',
            )}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="font-semibold text-slate-100">{t.name}</div>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 shrink-0">
                {t.category}
              </span>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">{t.description}</p>
            <div className="text-xs text-slate-600 mt-3">{t.fields.length} bilgi istenir</div>
          </button>
        ))}
      </div>

      {active && (
        <form onSubmit={draft} className="card space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-lg font-bold text-slate-100">{active.name}</div>
              <p className="text-sm text-slate-400 mt-1">{active.description}</p>
            </div>
            <button
              type="button"
              onClick={() => { setActive(null); setOut(null) }}
              className="text-slate-500 hover:text-slate-200"
              aria-label="Kapat"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div>
            <label className="label" htmlFor="tpl-details">
              Şablonun istediği bilgiler
            </label>
            <textarea
              id="tpl-details"
              rows={Math.max(5, active.fields.length + 2)}
              className="input resize-y font-mono text-xs"
              value={details}
              onChange={(e) => setDetails(e.target.value)}
            />
            <p className="text-xs text-slate-600 mt-1">
              Bilmediğin alanı boş bırak — ajan onu köşeli parantezle işaretler.
            </p>
          </div>

          <div>
            <label className="label" htmlFor="tpl-matter">
              Dosyaya bağla <span className="text-slate-600">(opsiyonel)</span>
            </label>
            <select
              id="tpl-matter"
              className="input"
              value={matterId}
              onChange={(e) => setMatterId(e.target.value)}
            >
              <option value="">Bağımsız</option>
              {matters.map((m) => (
                <option key={m.id} value={m.id}>{m.title}</option>
              ))}
            </select>
          </div>

          <div>
            <span className="label">İlgili belge ekle <span className="text-slate-600">(opsiyonel)</span></span>
            <LegalUploader value={docs} onChange={setDocs} title="Sözleşme, tebligat veya yazışma" />
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <button type="submit" disabled={busy} className="btn-primary inline-flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {busy ? 'Dilekçe yazılıyor...' : 'Dilekçeyi hazırla'}
          </button>
        </form>
      )}

      {out && <ResultPanel consultation={out} />}
    </div>
  )
}

function Chip({
  active, onClick, children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'px-3 py-1.5 text-xs font-medium rounded-full border transition-colors',
        active
          ? 'bg-brand-500/10 border-brand-500/40 text-brand-400'
          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-100',
      )}
    >
      {children}
    </button>
  )
}
