import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Users2, Loader2, Sparkles, Check } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { LegalNav } from '@/components/LegalNav'
import { LegalUploader } from '@/components/LegalUploader'
import { ResultPanel } from '@/components/LegalResult'
import { legalIcon } from '@/lib/legalIcons'
import type {
  LegalAgent, LegalBoardResponse, LegalDocument, LegalMatter,
} from '@/types'

export function LegalBoard() {
  const [params] = useSearchParams()
  const [agents, setAgents] = useState<LegalAgent[]>([])
  const [matters, setMatters] = useState<LegalMatter[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [question, setQuestion] = useState('')
  const [subject, setSubject] = useState('')
  const [matterId, setMatterId] = useState(params.get('dosya') || '')
  const [docs, setDocs] = useState<LegalDocument[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [out, setOut] = useState<LegalBoardResponse | null>(null)

  useEffect(() => {
    api.get<LegalAgent[]>('/legal/agents').then(({ data }) => setAgents(data))
    api.get<LegalMatter[]>('/legal/matters').then(({ data }) => setMatters(data))
  }, [])

  const active = useMemo(() => agents.filter((a) => a.is_active), [agents])

  function toggle(slug: string) {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : prev.length >= 4 ? prev : [...prev, slug],
    )
  }

  async function convene(e: React.FormEvent) {
    e.preventDefault()
    if (question.trim().length < 10) {
      setError('Olayı biraz daha anlat (en az 10 karakter).')
      return
    }
    if (selected.length === 1) {
      setError('Kurul için en az iki ajan seç ya da hiçbirini seçme; sistem kendi kursun.')
      return
    }
    setBusy(true)
    setError(null)
    setOut(null)
    try {
      const { data } = await api.post<LegalBoardResponse>('/legal/board', {
        question: question.trim(),
        subject: subject.trim(),
        agent_slugs: selected,
        matter_id: matterId ? Number(matterId) : null,
        document_ids: docs.map((d) => d.id),
      })
      setOut(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Kurul toplanamadı.')
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
            <Users2 className="w-5 h-5" />
          </span>
          Hukuk Kurulu
        </h1>
        <p className="text-slate-400 mt-2">
          Birden çok alanı kesen olaylarda tek ajan yetmez. Kurul topla: her uzman kendi
          açısından bakar, Baş Hukuk Müşaviri görüşleri tek karara bağlar — görüş ayrılığı varsa
          gizlemez.
        </p>
      </div>

      <form onSubmit={convene} className="card space-y-4">
        <div>
          <label className="label" htmlFor="board-subject">
            Konu başlığı <span className="text-slate-600">(opsiyonel)</span>
          </label>
          <input
            id="board-subject"
            className="input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Örn. Bayilik sözleşmesi feshi ve alacak"
          />
        </div>

        <div>
          <label className="label" htmlFor="board-question">
            Olay
          </label>
          <textarea
            id="board-question"
            rows={5}
            className="input resize-y"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Taraflar, ne oldu, tarihler, elindeki belgeler ve ne istediğin..."
          />
        </div>

        <div>
          <span className="label">
            Kurul üyeleri <span className="text-slate-600">(boş bırakırsan sistem seçer · en fazla 4)</span>
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-72 overflow-y-auto pr-1">
            {active.map((a) => {
              const Icon = legalIcon(a.icon)
              const on = selected.includes(a.slug)
              return (
                <button
                  key={a.slug}
                  type="button"
                  onClick={() => toggle(a.slug)}
                  className={clsx(
                    'flex items-center gap-2.5 px-3 py-2 rounded-xl border text-left transition-colors',
                    on
                      ? 'bg-brand-500/10 border-brand-500/50'
                      : 'bg-slate-800/40 border-slate-700 hover:border-slate-600',
                  )}
                >
                  <span
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ backgroundColor: `${a.color}20`, color: a.color || '#eab308' }}
                  >
                    <Icon className="w-4 h-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm text-slate-100 truncate">{a.name}</span>
                    <span className="block text-[11px] text-slate-500 truncate">{a.department}</span>
                  </span>
                  {on && <Check className="w-4 h-4 text-brand-400 shrink-0" />}
                </button>
              )
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="board-matter">
              Dosyaya bağla <span className="text-slate-600">(opsiyonel)</span>
            </label>
            <select
              id="board-matter"
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
        </div>

        <div>
          <span className="label">Belge ekle <span className="text-slate-600">(opsiyonel)</span></span>
          <LegalUploader value={docs} onChange={setDocs} title="Sözleşme, tebligat, yazışma" />
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-600">
            {selected.length ? `${selected.length} ajan seçildi` : 'Sistem uygun ajanları seçecek'}
            {' · her üye ayrı çalışır, süre biraz uzun olabilir'}
          </span>
          <button type="submit" disabled={busy} className="btn-primary inline-flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {busy ? 'Kurul çalışıyor...' : 'Kurulu topla'}
          </button>
        </div>
      </form>

      {out && (
        <>
          <div className="card">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
              Kurul üyeleri ve görüşleri
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {out.opinions.map((o) => {
                const Icon = legalIcon(o.icon)
                return (
                  <div
                    key={o.slug}
                    className={clsx(
                      'rounded-xl border px-3 py-3',
                      o.ok ? 'border-slate-800 bg-slate-800/30' : 'border-red-500/30 bg-red-500/5',
                    )}
                  >
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <span
                        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${o.color}20`, color: o.color || '#eab308' }}
                      >
                        <Icon className="w-4 h-4" />
                      </span>
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-slate-100 truncate">{o.name}</div>
                        <div className="text-[11px] text-slate-500 truncate">{o.title}</div>
                      </div>
                    </div>
                    <p className="text-sm text-slate-400 leading-relaxed">
                      {o.ok ? o.result?.ozet : o.error || 'Görüş alınamadı.'}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
          <ResultPanel consultation={out.consultation} />
        </>
      )}
    </div>
  )
}
