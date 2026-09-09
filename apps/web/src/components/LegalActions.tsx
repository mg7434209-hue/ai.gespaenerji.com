import { useEffect, useRef, useState } from 'react'
import {
  Download,
  ShieldCheck,
  CalendarPlus,
  Loader2,
  Send,
  MessageSquare,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileDown,
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { LegalConsultation, LegalDeadline, LegalMessage, LegalReview } from '@/types'

/** Danışma sonucunun altındaki eylem şeridi: indir, denetle, süreleri yaz. */
export function LegalActions({
  consultation,
  onReview,
}: {
  consultation: LegalConsultation
  onReview?: (r: LegalReview) => void
}) {
  const [review, setReview] = useState<LegalReview | null>(consultation.review)
  const [reviewing, setReviewing] = useState(false)
  const [showCapture, setShowCapture] = useState(false)
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [capturing, setCapturing] = useState(false)
  const [captured, setCaptured] = useState<LegalDeadline[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setReview(consultation.review)
    setCaptured(null)
    setShowCapture(false)
    setError(null)
  }, [consultation.id, consultation.review])

  const sureler = consultation.result?.sureler || []

  async function runReview() {
    setReviewing(true)
    setError(null)
    try {
      const { data } = await api.post<LegalReview>(`/legal/consultations/${consultation.id}/review`)
      setReview(data)
      onReview?.(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Denetim yapılamadı.')
    } finally {
      setReviewing(false)
    }
  }

  async function capture() {
    setCapturing(true)
    setError(null)
    try {
      const { data } = await api.post<LegalDeadline[]>(
        `/legal/consultations/${consultation.id}/deadlines`,
        { start_date: startDate, matter_id: consultation.matter_id },
      )
      setCaptured(data)
      setShowCapture(false)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Süreler kaydedilemedi.')
    } finally {
      setCapturing(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="card py-4">
        <div className="flex flex-wrap items-center gap-2">
          {consultation.draft && (
            <a
              href={`/api/legal/consultations/${consultation.id}/export?part=belge`}
              className="btn-primary inline-flex items-center gap-2 text-sm py-2"
            >
              <Download className="w-4 h-4" /> Dilekçeyi Word indir
            </a>
          )}
          <a
            href={`/api/legal/consultations/${consultation.id}/export?part=rapor`}
            className="btn-ghost inline-flex items-center gap-2 text-sm py-2"
          >
            <FileDown className="w-4 h-4" /> Tam raporu indir
          </a>
          {sureler.length > 0 && (
            <button
              onClick={() => setShowCapture((v) => !v)}
              className="btn-ghost inline-flex items-center gap-2 text-sm py-2"
            >
              <CalendarPlus className="w-4 h-4" /> Süreleri takvime yaz
            </button>
          )}
          <button
            onClick={runReview}
            disabled={reviewing}
            className="btn-ghost inline-flex items-center gap-2 text-sm py-2"
          >
            {reviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            {review ? 'Yeniden denetle' : 'İkinci okuma (denetle)'}
          </button>
        </div>

        {showCapture && (
          <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
            <div>
              <label className="label" htmlFor="capture-start">
                Süre hangi gün başladı? (tebliğ / öğrenme tarihi)
              </label>
              <input
                id="capture-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input max-w-xs"
              />
            </div>
            <ul className="space-y-1">
              {sureler.map((s, i) => (
                <li key={i} className="text-xs text-slate-400">
                  • {s.is} — <span className="text-slate-200">{s.sure}</span>{' '}
                  {s.kritik && <span className="text-red-400">(kritik)</span>}
                </li>
              ))}
            </ul>
            <p className="text-xs text-amber-400/80">
              Hesap tahminîdir: başlangıç gününe süre eklenir; resmî/adli tatil ve özel tebligat
              kuralları hesaba katılmaz. Tarihi avukatınla teyit et.
            </p>
            <button onClick={capture} disabled={capturing} className="btn-primary text-sm py-2">
              {capturing ? 'Yazılıyor...' : 'Takvime yaz'}
            </button>
          </div>
        )}

        {captured && (
          <div className="mt-4 pt-4 border-t border-slate-800">
            <div className="text-sm text-green-400 font-semibold mb-2">
              {captured.length} süre takvime yazıldı
            </div>
            <ul className="space-y-1">
              {captured.map((d) => (
                <li key={d.id} className="text-sm text-slate-300">
                  {d.title} — <span className="font-semibold">{d.due_date}</span>{' '}
                  <span className="text-slate-500">({d.days_left} gün)</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && <p className="text-sm text-red-400 mt-3">{error}</p>}
      </div>

      {review && <ReviewPanel review={review} />}
    </div>
  )
}

function ReviewPanel({ review }: { review: LegalReview }) {
  const map: Record<string, [string, string, React.ElementType]> = {
    temiz: ['Denetimden temiz geçti', 'text-green-400 border-green-500/30 bg-green-500/5', CheckCircle2],
    duzeltme_gerekli: ['Düzeltme gerekiyor', 'text-amber-400 border-amber-500/30 bg-amber-500/5', AlertTriangle],
    riskli: ['Riskli — kullanmadan önce düzelt', 'text-red-400 border-red-500/30 bg-red-500/5', XCircle],
  }
  const [label, cls, Icon] = map[review.verdict] || [
    'Denetim tamamlanamadı',
    'text-slate-400 border-slate-700 bg-slate-800/30',
    AlertTriangle,
  ]

  return (
    <div className={clsx('card border', cls.split(' ').slice(1).join(' '))}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className={clsx('flex items-center gap-2 font-semibold', cls.split(' ')[0])}>
          <Icon className="w-5 h-5" /> {label}
        </div>
        <span className="text-xs text-slate-500">
          Hukuk Denetçisi · puan %{Math.round((review.score || 0) * 100)}
        </span>
      </div>

      {review.summary && <p className="text-sm text-slate-300 mb-3">{review.summary}</p>}

      {review.findings?.length > 0 ? (
        <ul className="space-y-2">
          {review.findings.map((f, i) => (
            <li key={i} className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-100">{f.alan || 'Bulgu'}</span>
                {f.tur && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                    {f.tur}
                  </span>
                )}
                {f.agirlik && (
                  <span
                    className={clsx(
                      'text-[11px] px-2 py-0.5 rounded-full',
                      f.agirlik === 'yuksek'
                        ? 'bg-red-500/10 text-red-400'
                        : f.agirlik === 'orta'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-slate-700/40 text-slate-300',
                    )}
                  >
                    {f.agirlik}
                  </span>
                )}
              </div>
              {f.sorun && <p className="text-sm text-slate-400 mt-1">{f.sorun}</p>}
              {f.duzeltme && (
                <p className="text-sm text-slate-300 mt-1">
                  <span className="text-slate-500">Düzeltme: </span>
                  {f.duzeltme}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-400">Denetçi somut bir kusur bulmadı.</p>
      )}
      {review.error && <p className="text-sm text-red-400 mt-3">{review.error}</p>}
    </div>
  )
}

/** Danışmanın altındaki devam sohbeti — avukatla konuşmayı sürdürür. */
export function LegalChat({
  consultationId,
  agentName,
}: {
  consultationId: number
  agentName: string
}) {
  const [messages, setMessages] = useState<LegalMessage[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api
      .get<LegalMessage[]>(`/legal/consultations/${consultationId}/messages`)
      .then(({ data }) => setMessages(data))
      .catch(() => setMessages([]))
  }, [consultationId])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages.length])

  async function send(e: React.FormEvent) {
    e.preventDefault()
    const body = text.trim()
    if (body.length < 2) return
    setSending(true)
    setError(null)
    setText('')
    try {
      const { data } = await api.post<LegalMessage[]>(
        `/legal/consultations/${consultationId}/messages`,
        { message: body },
      )
      setMessages((prev) => [...prev, ...data])
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Mesaj gönderilemedi.')
      setText(body)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="w-4 h-4 text-brand-400" />
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">
          {agentName} ile konuş
        </h3>
      </div>

      {messages.length === 0 && (
        <p className="text-sm text-slate-500 mb-4">
          Anlamadığın yeri sor, belge iste, "peki ya şu olursa" de — ajan dosyayı hatırlayarak
          cevaplar.
        </p>
      )}

      <div className="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
        {messages.map((m) => (
          <div
            key={m.id}
            className={clsx('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}
          >
            <div
              className={clsx(
                'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
                m.role === 'user'
                  ? 'bg-brand-500/10 text-slate-100 rounded-br-sm'
                  : 'bg-slate-800/60 text-slate-200 rounded-bl-sm',
              )}
            >
              {m.content}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-slate-800/60 rounded-2xl rounded-bl-sm px-4 py-2.5">
              <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {error && <p className="text-sm text-red-400 mt-3">{error}</p>}

      <form onSubmit={send} className="flex gap-2 mt-4">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Sorunu yaz..."
          className="input flex-1"
          disabled={sending}
        />
        <button type="submit" disabled={sending || text.trim().length < 2} className="btn-primary px-4">
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  )
}
