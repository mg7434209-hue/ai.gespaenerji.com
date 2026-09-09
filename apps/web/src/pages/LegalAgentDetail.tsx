import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  Send,
  Loader2,
  AlertTriangle,
  Clock,
  ListChecks,
  BookOpen,
  ShieldAlert,
  FileText,
  Copy,
  Check,
  HelpCircle,
  Wallet,
  History,
  ArrowRight,
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { legalIcon, MODE_LABELS } from '@/lib/legalIcons'
import { ResultPanel } from '@/components/LegalResult'
import { LegalUploader } from '@/components/LegalUploader'
import type { LegalAgent, LegalConsultation, LegalDocument, LegalMeta, LegalMode } from '@/types'

const MODE_ORDER: LegalMode[] = ['danisma', 'dilekce', 'inceleme', 'arastirma']

export function LegalAgentDetail() {
  const { slug = '' } = useParams()
  const [params, setParams] = useSearchParams()

  const [agent, setAgent] = useState<LegalAgent | null>(null)
  const [meta, setMeta] = useState<LegalMeta | null>(null)
  const [history, setHistory] = useState<LegalConsultation[]>([])
  const [notFound, setNotFound] = useState(false)

  const [mode, setMode] = useState<LegalMode>('danisma')
  const [subject, setSubject] = useState('')
  const [question, setQuestion] = useState('')
  const [context, setContext] = useState('')
  const [docType, setDocType] = useState('')
  const [docs, setDocs] = useState<LegalDocument[]>([])

  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<LegalConsultation | null>(null)

  const loadHistory = useCallback(async () => {
    const { data } = await api.get<LegalConsultation[]>('/legal/consultations', {
      params: { agent: slug, limit: 20 },
    })
    setHistory(data)
  }, [slug])

  useEffect(() => {
    let cancelled = false
    setNotFound(false)
    setActive(null)
    ;(async () => {
      try {
        const [a, m] = await Promise.all([
          api.get<LegalAgent>(`/legal/agents/${slug}`),
          api.get<LegalMeta>('/legal/meta'),
        ])
        if (cancelled) return
        setAgent(a.data)
        setMeta(m.data)
      } catch {
        if (!cancelled) setNotFound(true)
      }
    })()
    loadHistory()
    return () => {
      cancelled = true
    }
  }, [slug, loadHistory])

  // ?danisma=<id> ile geçmiş bir danışmayı aç
  const openId = params.get('danisma')
  useEffect(() => {
    if (!openId) return
    api
      .get<LegalConsultation>(`/legal/consultations/${openId}`)
      .then(({ data }) => {
        setActive(data)
        setMode(data.mode)
        setSubject(data.subject || '')
        setQuestion(data.question)
        setContext(data.context || '')
        setDocType(data.doc_type || '')
        if (data.document_ids?.length) {
          Promise.all(
            data.document_ids.map((id) =>
              api.get<LegalDocument>(`/legal/documents/${id}`).then((r) => r.data),
            ),
          )
            .then(setDocs)
            .catch(() => setDocs([]))
        } else {
          setDocs([])
        }
      })
      .catch(() => setError('Danışma kaydı açılamadı.'))
  }, [openId])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (question.trim().length < 10) {
      setError('Soruyu biraz daha açar mısın? (en az 10 karakter)')
      return
    }
    setError(null)
    setRunning(true)
    setActive(null)
    if (openId) {
      params.delete('danisma')
      setParams(params, { replace: true })
    }
    try {
      const { data } = await api.post<LegalConsultation>('/legal/consult', {
        agent_slug: slug,
        mode,
        subject: subject.trim(),
        question: question.trim(),
        context: context.trim() || null,
        doc_type: docType.trim() || null,
        document_ids: docs.map((d) => d.id),
      })
      setActive(data)
      if (data.status === 'error') setError(data.error || 'Ajan çalıştırılamadı.')
      loadHistory()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'İstek başarısız oldu.')
    } finally {
      setRunning(false)
    }
  }

  const Icon = useMemo(() => legalIcon(agent?.icon), [agent])

  if (notFound) {
    return (
      <div className="card">
        <p className="text-slate-300">Bu avukat ajanı bulunamadı.</p>
        <Link to="/hukuk" className="text-brand-400 hover:underline text-sm mt-2 inline-block">
          ← Hukuk Ofisi'ne dön
        </Link>
      </div>
    )
  }

  if (!agent) return <div className="text-slate-500">Yükleniyor...</div>

  return (
    <div className="space-y-6">
      <Link
        to="/hukuk"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100"
      >
        <ArrowLeft className="w-4 h-4" /> Hukuk Ofisi
      </Link>

      {/* Ajan kimliği */}
      <div className="card">
        <div className="flex items-start gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
            style={{ backgroundColor: `${agent.color}20`, color: agent.color || '#eab308' }}
          >
            <Icon className="w-6 h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-100">{agent.name}</h1>
              <span
                className={clsx(
                  'text-[11px] font-semibold px-2 py-0.5 rounded-full',
                  agent.is_active
                    ? 'bg-green-500/10 text-green-400'
                    : 'bg-slate-700/40 text-slate-400',
                )}
              >
                {agent.is_active ? 'Görevde' : 'Beklemede'}
              </span>
            </div>
            <div className="text-sm text-slate-500">
              {agent.title} · {agent.department}
            </div>
            <p className="text-sm text-slate-400 mt-2 leading-relaxed">{agent.description}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 pt-6 border-t border-slate-800">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Uzmanlık alanları
            </div>
            <ul className="space-y-1.5">
              {agent.expertise?.map((e) => (
                <li key={e} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-brand-500/70">•</span>
                  <span>{e}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Hazırlayabildiği belgeler
            </div>
            <div className="flex flex-wrap gap-2">
              {agent.documents?.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => {
                    setMode('dilekce')
                    setDocType(d)
                  }}
                  className="text-xs px-2.5 py-1 rounded-full bg-slate-800/70 border border-slate-700 text-slate-300 hover:border-brand-500/50 hover:text-brand-300 transition-colors"
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {!agent.is_active && (
        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 p-4 text-sm text-amber-100/80">
          Bu ajan beklemede. Çalıştırmak için Hukuk Ofisi kartındaki anahtarı aç.
        </div>
      )}

      {/* Talep formu */}
      <form onSubmit={submit} className="card space-y-4">
        <div>
          <span className="label">Ne yapmasını istiyorsun?</span>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {MODE_ORDER.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={clsx(
                  'text-left px-3 py-2.5 rounded-lg border transition-colors',
                  mode === m
                    ? 'bg-brand-500/10 border-brand-500/50'
                    : 'bg-slate-800/40 border-slate-700 hover:border-slate-600',
                )}
              >
                <div
                  className={clsx(
                    'text-sm font-semibold',
                    mode === m ? 'text-brand-400' : 'text-slate-200',
                  )}
                >
                  {MODE_LABELS[m].label}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                  {MODE_LABELS[m].hint}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="legal-subject">
              Konu başlığı <span className="text-slate-600">(opsiyonel)</span>
            </label>
            <input
              id="legal-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Örn. Manavgat şubesi kira tahliyesi"
              className="input"
            />
          </div>
          {mode === 'dilekce' && (
            <div>
              <label className="label" htmlFor="legal-doc">
                İstenen belge
              </label>
              <input
                id="legal-doc"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                placeholder={agent.documents?.[0] || 'Örn. İhtarname'}
                className="input"
              />
            </div>
          )}
        </div>

        <div>
          <label className="label" htmlFor="legal-question">
            Sorun / talebin
          </label>
          <textarea
            id="legal-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={5}
            placeholder="Olayı anlat: taraflar kim, ne oldu, tarihler neler, elinde hangi belgeler var?"
            className="input resize-y"
          />
        </div>

        <div>
          <label className="label" htmlFor="legal-context">
            {mode === 'inceleme'
              ? 'İncelenecek belge / sözleşme metni'
              : 'Ek bilgi, belge metni veya yazışma'}{' '}
            <span className="text-slate-600">(opsiyonel)</span>
          </label>
          <textarea
            id="legal-context"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={mode === 'inceleme' ? 10 : 4}
            placeholder="Sözleşme metnini, ihtarnameyi veya yazışmayı buraya yapıştır."
            className="input resize-y font-mono text-xs"
          />
        </div>

        <div>
          <span className="label">
            Belge ekle <span className="text-slate-600">(opsiyonel)</span>
          </span>
          <p className="text-xs text-slate-500 mb-2">
            Tebligat, sözleşme veya fotoğrafı yükle — {agent.name} belgeyi kendisi okur.
            Belgeyi kime göndereceğine sistemin karar vermesini istiyorsan{' '}
            <Link to="/hukuk/belge" className="text-brand-400 hover:underline">
              Belge Analizi
            </Link>{' '}
            ekranını kullan.
          </p>
          <LegalUploader value={docs} onChange={setDocs} />
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-600">
            {meta?.model ? `Model: ${meta.model}` : ''}
          </span>
          <button
            type="submit"
            disabled={running || !agent.is_active}
            className="btn-primary inline-flex items-center gap-2"
          >
            {running ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> {agent.name} çalışıyor...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" /> Görüş al
              </>
            )}
          </button>
        </div>
      </form>

      {running && (
        <div className="card text-sm text-slate-400 flex items-center gap-3">
          <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
          Dosya inceleniyor — mevzuat, süreler ve riskler çıkarılıyor. Bu 30 saniyeyi bulabilir.
        </div>
      )}

      {active && <ResultPanel consultation={active} />}

      {/* Bu ajanla geçmiş */}
      {history.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            <History className="w-4 h-4" /> Bu ajanla geçmiş danışmalar
          </div>
          <ul className="divide-y divide-slate-800">
            {history.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => {
                    params.set('danisma', String(c.id))
                    setParams(params, { replace: true })
                  }}
                  className="w-full text-left py-3 hover:bg-slate-800/30 px-2 -mx-2 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-200 truncate">
                      {c.subject || c.question.slice(0, 70)}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 shrink-0">
                      {MODE_LABELS[c.mode]?.label || c.mode}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 mt-1">
                    {new Date(c.created_at).toLocaleString('tr-TR')}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
