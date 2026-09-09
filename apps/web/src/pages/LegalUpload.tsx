import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  Sparkles,
  Loader2,
  AlertTriangle,
  ScanSearch,
  Clock,
  Users,
  CalendarDays,
  Coins,
  Hash,
  ArrowRight,
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { legalIcon } from '@/lib/legalIcons'
import { LegalUploader } from '@/components/LegalUploader'
import { ResultPanel } from '@/components/LegalResult'
import type { LegalAgent, LegalAnalyzeResponse, LegalDocument, LegalMeta } from '@/types'

type Phase = 'idle' | 'triage' | 'analyze'

export function LegalUpload() {
  const [docs, setDocs] = useState<LegalDocument[]>([])
  const [note, setNote] = useState('')
  const [agentSlug, setAgentSlug] = useState('')     // boş = sistem seçsin
  const [agents, setAgents] = useState<LegalAgent[]>([])
  const [meta, setMeta] = useState<LegalMeta | null>(null)

  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [out, setOut] = useState<LegalAnalyzeResponse | null>(null)

  useEffect(() => {
    api.get<LegalAgent[]>('/legal/agents').then(({ data }) => setAgents(data))
    api.get<LegalMeta>('/legal/meta').then(({ data }) => setMeta(data))
  }, [])

  async function analyze() {
    if (!docs.length) {
      setError('Önce en az bir belge yükleyin.')
      return
    }
    setError(null)
    setOut(null)
    setPhase('triage')
    // Triyaj ilk saniyelerde biter; ikinci evreyi kullanıcıya göstermek için
    const toAnalyze = setTimeout(() => setPhase('analyze'), 6000)
    try {
      const { data } = await api.post<LegalAnalyzeResponse>('/legal/documents/analyze', {
        document_ids: docs.map((d) => d.id),
        agent_slug: agentSlug || null,
        note: note.trim(),
      })
      setOut(data)
      if (data.consultation.status === 'error') {
        setError(data.consultation.error || 'Analiz tamamlanamadı.')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Analiz başarısız oldu.')
    } finally {
      clearTimeout(toAnalyze)
      setPhase('idle')
    }
  }

  const running = phase !== 'idle'

  return (
    <div className="space-y-6">
      <Link
        to="/hukuk"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100"
      >
        <ArrowLeft className="w-4 h-4" /> Hukuk Ofisi
      </Link>

      <div>
        <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <ScanSearch className="w-5 h-5" />
          </span>
          Belge Analizi
        </h1>
        <p className="text-slate-400 mt-2">
          Dosyayı yükle, gerisini sistem yapsın: belgeyi okur, ne olduğunu çıkarır, doğru avukat
          ajanına yönlendirir ve tam değerlendirmeyi üretir. Ne yapacağını sana bırakmaz.
        </p>
      </div>

      {meta && !meta.ai_configured && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/5 p-4 text-sm text-red-200/90">
          <span className="font-semibold">ANTHROPIC_API_KEY tanımlı değil.</span> Belge yüklenir
          ama analiz çalışmaz. Railway → Variables'a anahtarı ekleyin.
        </div>
      )}

      <div className="card space-y-5">
        <LegalUploader
          value={docs}
          onChange={setDocs}
          title="Dosyayı buraya bırak"
          hint="Tebligat, ödeme emri, ihtarname, sözleşme, ceza tutanağı, dava dilekçesi — PDF, Word, fotoğraf veya metin."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="upload-note">
              Ayrıca sormak istediğin <span className="text-slate-600">(opsiyonel)</span>
            </label>
            <input
              id="upload-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Örn. itiraz edersem masrafı ne olur?"
              className="input"
            />
          </div>
          <div>
            <label className="label" htmlFor="upload-agent">
              Hangi ajan baksın?
            </label>
            <select
              id="upload-agent"
              value={agentSlug}
              onChange={(e) => setAgentSlug(e.target.value)}
              className="input"
            >
              <option value="">Sistem karar versin (önerilen)</option>
              {agents.map((a) => (
                <option key={a.slug} value={a.slug}>
                  {a.name} — {a.department}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-600">
            {docs.length ? `${docs.length} belge hazır` : 'Henüz belge yüklenmedi'}
          </span>
          <button
            onClick={analyze}
            disabled={running || !docs.length}
            className="btn-primary inline-flex items-center gap-2"
          >
            {running ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {phase === 'triage' ? 'Belge okunuyor...' : 'Avukat ajanı inceliyor...'}
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Yükle ve analiz et
              </>
            )}
          </button>
        </div>
      </div>

      {running && (
        <div className="card space-y-3">
          <Step
            done={phase === 'analyze'}
            active={phase === 'triage'}
            label="Belge okunuyor — türü, taraflar, tarihler ve süreler çıkarılıyor"
          />
          <Step
            done={false}
            active={phase === 'analyze'}
            label="Uzman ajan inceliyor — değerlendirme, riskler ve gerekiyorsa dilekçe taslağı"
          />
        </div>
      )}

      {out && <TriageCard data={out} />}
      {out && <ResultPanel consultation={out.consultation} />}
    </div>
  )
}

function Step({ done, active, label }: { done: boolean; active: boolean; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={clsx(
          'w-5 h-5 rounded-full flex items-center justify-center shrink-0',
          done ? 'bg-green-500/20 text-green-400' : active ? 'bg-brand-500/20' : 'bg-slate-800',
        )}
      >
        {done ? (
          <span className="text-[11px]">✓</span>
        ) : active ? (
          <Loader2 className="w-3 h-3 animate-spin text-brand-400" />
        ) : (
          <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
        )}
      </span>
      <span className={clsx('text-sm', active || done ? 'text-slate-200' : 'text-slate-500')}>
        {label}
      </span>
    </div>
  )
}

function TriageCard({ data }: { data: LegalAnalyzeResponse }) {
  const t = data.triage
  const Icon = legalIcon(data.routed_to.icon)
  const urgency: Record<string, [string, string]> = {
    dusuk: ['Düşük aciliyet', 'bg-slate-700/40 text-slate-300'],
    orta: ['Orta aciliyet', 'bg-amber-500/10 text-amber-400'],
    yuksek: ['Yüksek aciliyet', 'bg-red-500/10 text-red-400'],
  }
  const [urgencyLabel, urgencyCls] = urgency[t.aciliyet] || urgency.orta

  return (
    <div className="card space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Belge künyesi
          </div>
          <div className="text-lg font-bold text-slate-100 mt-1">
            {t.belge_turu || 'Belge türü belirlenemedi'}
          </div>
        </div>
        <span className={clsx('text-[11px] font-semibold px-2.5 py-1 rounded-full', urgencyCls)}>
          {urgencyLabel}
        </span>
      </div>

      {t.ozet && <p className="text-sm text-slate-300 leading-relaxed">{t.ozet}</p>}

      {t.sure_uyarisi && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-2.5 flex gap-2">
          <Clock className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-red-300 uppercase tracking-wide">
              Belgeden çıkan süre
            </div>
            <p className="text-sm text-red-200/90 mt-0.5">{t.sure_uyarisi}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {t.taraflar?.length > 0 && (
          <Fact icon={Users} label="Taraflar" items={t.taraflar} />
        )}
        {t.tarihler?.length > 0 && (
          <Fact
            icon={CalendarDays}
            label="Tarihler"
            items={t.tarihler.map((d) => [d.ne, d.tarih].filter(Boolean).join(': '))}
          />
        )}
        {t.tutarlar?.length > 0 && <Fact icon={Coins} label="Tutarlar" items={t.tutarlar} />}
        {t.referans && <Fact icon={Hash} label="Dosya / referans no" items={[t.referans]} />}
      </div>

      {/* Yönlendirme */}
      <div className="rounded-xl border border-slate-800 bg-slate-800/30 px-4 py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{
              backgroundColor: `${data.routed_to.color}20`,
              color: data.routed_to.color || '#eab308',
            }}
          >
            <Icon className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <div className="text-xs text-slate-500">
              {data.auto_routed ? 'Sistem bu ajana yönlendirdi' : 'Senin seçtiğin ajan'}
            </div>
            <div className="text-sm font-semibold text-slate-100 truncate">
              {data.routed_to.name}
            </div>
            {t.gerekce && <div className="text-xs text-slate-500 mt-0.5">{t.gerekce}</div>}
          </div>
        </div>
        <Link
          to={`/hukuk/${data.routed_to.slug}`}
          className="text-xs font-semibold text-brand-400 hover:text-brand-300 inline-flex items-center gap-1 shrink-0"
        >
          Ajana git <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {t.alternatif_ajan && (
        <div className="text-xs text-slate-500">
          Konunun ikinci yüzü için{' '}
          <Link to={`/hukuk/${t.alternatif_ajan}`} className="text-brand-400 hover:underline">
            {t.alternatif_ajan}
          </Link>{' '}
          ajanına da danışabilirsin.
        </div>
      )}

      {t.guven < 0.6 && (
        <div className="flex gap-2 text-xs text-amber-300/80">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          Sistem belgeden emin olamadı (%{Math.round(t.guven * 100)}). Yönlendirmeyi kontrol et,
          gerekirse ajanı elle seçip tekrar çalıştır.
        </div>
      )}
    </div>
  )
}

function Fact({
  icon: Icon,
  label,
  items,
}: {
  icon: React.ElementType
  label: string
  items: string[]
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
        <Icon className="w-3.5 h-3.5" /> {label}
      </div>
      <ul className="space-y-1">
        {items.filter(Boolean).map((x, i) => (
          <li key={i} className="text-sm text-slate-300">
            {x}
          </li>
        ))}
      </ul>
    </div>
  )
}
