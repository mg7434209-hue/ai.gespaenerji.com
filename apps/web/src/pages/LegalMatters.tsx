import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FolderOpen, Plus, X, AlertTriangle, CalendarClock, FileText, MessageSquareQuote } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { LegalNav } from '@/components/LegalNav'
import type { LegalMatter, LegalMeta } from '@/types'

export const STAGES = [
  'inceleme', 'ihtar', 'arabuluculuk', 'dava', 'icra', 'istinaf', 'karar', 'kapandı',
]
export const ROLES = ['davacı', 'davalı', 'alacaklı', 'borçlu', 'şikayetçi', 'şüpheli', 'üçüncü kişi']

export function LegalMatters() {
  const [matters, setMatters] = useState<LegalMatter[]>([])
  const [meta, setMeta] = useState<LegalMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    title: '', area: '', self_party: '', counterparty: '', role: '',
    court: '', reference: '', stage: 'inceleme', amount: '',
  })

  async function load() {
    const { data } = await api.get<LegalMatter[]>('/legal/matters')
    setMatters(data)
    setLoading(false)
  }

  useEffect(() => {
    load()
    api.get<LegalMeta>('/legal/meta').then(({ data }) => setMeta(data))
  }, [])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (form.title.trim().length < 2) {
      setError('Dosyaya bir başlık ver.')
      return
    }
    setError(null)
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, v.trim() || null]),
      )
      await api.post('/legal/matters', { ...payload, title: form.title.trim() })
      setShowNew(false)
      setForm({ title: '', area: '', self_party: '', counterparty: '', role: '', court: '', reference: '', stage: 'inceleme', amount: '' })
      load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Dosya oluşturulamadı.')
    }
  }

  const open = matters.filter((m) => m.status === 'open')
  const closed = matters.filter((m) => m.status !== 'open')

  return (
    <div className="space-y-6">
      <LegalNav />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
              <FolderOpen className="w-5 h-5" />
            </span>
            Dosyalar
          </h1>
          <p className="text-slate-400 mt-2">
            Bir uyuşmazlığın belgeleri, görüşleri ve süreleri tek yerde. Dosyaya bağlı sorularda
            ajan geçmişi hatırlar — ofis hafızası budur.
          </p>
        </div>
        <button onClick={() => setShowNew((v) => !v)} className="btn-primary inline-flex items-center gap-2">
          {showNew ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showNew ? 'Vazgeç' : 'Yeni dosya'}
        </button>
      </div>

      {showNew && (
        <form onSubmit={create} className="card space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Dosya başlığı" value={form.title} onChange={(v) => setForm({ ...form, title: v })}
              placeholder="Örn. X Ltd. ödeme emri itirazı" />
            <div>
              <label className="label">Hukuk alanı</label>
              <select className="input" value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })}>
                <option value="">Seçilmedi</option>
                {(meta?.departments || []).map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <Field label="Bizim taraf" value={form.self_party} onChange={(v) => setForm({ ...form, self_party: v })}
              placeholder="Gespa Enerji Ltd. Şti." />
            <Field label="Karşı taraf" value={form.counterparty} onChange={(v) => setForm({ ...form, counterparty: v })} />
            <div>
              <label className="label">Sıfatımız</label>
              <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="">Seçilmedi</option>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Aşama</label>
              <select className="input" value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })}>
                {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <Field label="Merci (mahkeme / icra dairesi)" value={form.court} onChange={(v) => setForm({ ...form, court: v })} />
            <Field label="Dosya / esas no" value={form.reference} onChange={(v) => setForm({ ...form, reference: v })} />
            <Field label="Uyuşmazlık değeri" value={form.amount} onChange={(v) => setForm({ ...form, amount: v })}
              placeholder="45.000 TL" />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button type="submit" className="btn-primary">Dosyayı oluştur</button>
        </form>
      )}

      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : matters.length === 0 ? (
        <div className="card text-slate-500 text-sm">
          Henüz dosya yok. Devam eden bir uyuşmazlığın varsa dosya aç; belgeleri ve görüşleri
          altında toplansın.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {open.map((m) => <MatterCard key={m.id} matter={m} />)}
          </div>
          {closed.length > 0 && (
            <>
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide pt-2">
                Kapanmış dosyalar
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {closed.map((m) => <MatterCard key={m.id} matter={m} />)}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}

function MatterCard({ matter }: { matter: LegalMatter }) {
  const urgent = matter.next_deadline
    ? Math.ceil((new Date(matter.next_deadline).getTime() - Date.now()) / 86400000)
    : null
  return (
    <Link
      to={`/hukuk/dosyalar/${matter.id}`}
      className={clsx(
        'card hover:border-brand-500/50 transition-colors block',
        matter.status !== 'open' && 'opacity-70',
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="min-w-0">
          <div className="font-semibold text-slate-100 truncate">{matter.title}</div>
          <div className="text-xs text-slate-500 mt-0.5">
            {[matter.area, matter.role, matter.reference].filter(Boolean).join(' · ') || 'Ayrıntı girilmedi'}
          </div>
        </div>
        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 shrink-0">
          {matter.stage}
        </span>
      </div>

      {matter.counterparty && (
        <div className="text-sm text-slate-400">Karşı taraf: {matter.counterparty}</div>
      )}

      {urgent !== null && (
        <div
          className={clsx(
            'mt-3 inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full',
            urgent < 0
              ? 'bg-red-500/10 text-red-400'
              : urgent <= 7
                ? 'bg-amber-500/10 text-amber-400'
                : 'bg-slate-800 text-slate-300',
          )}
        >
          {urgent < 0 ? <AlertTriangle className="w-3.5 h-3.5" /> : <CalendarClock className="w-3.5 h-3.5" />}
          {urgent < 0 ? `Süre ${Math.abs(urgent)} gün geçti` : `En yakın süre: ${urgent} gün`}
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-slate-800 flex gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <MessageSquareQuote className="w-3.5 h-3.5" /> {matter.consultation_count} görüş
        </span>
        <span className="inline-flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" /> {matter.document_count} belge
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CalendarClock className="w-3.5 h-3.5" /> {matter.open_deadlines} açık süre
        </span>
      </div>
    </Link>
  )
}

export function Field({
  label, value, onChange, placeholder, type = 'text',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        type={type}
        className="input"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
