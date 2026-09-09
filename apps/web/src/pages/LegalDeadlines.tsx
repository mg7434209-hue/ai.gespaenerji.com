import { useCallback, useEffect, useState } from 'react'
import { CalendarClock, AlertTriangle, Gavel, Plus } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { LegalNav } from '@/components/LegalNav'
import { DeadlineRow } from './LegalMatterDetail'
import { Field } from './LegalMatters'
import type { LegalAgenda, LegalDeadline, LegalMatter } from '@/types'

type Filter = 'open' | 'done' | 'all'

export function LegalDeadlines() {
  const [items, setItems] = useState<LegalDeadline[]>([])
  const [agenda, setAgenda] = useState<LegalAgenda | null>(null)
  const [matters, setMatters] = useState<LegalMatter[]>([])
  const [filter, setFilter] = useState<Filter>('open')
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ title: '', due_date: '', basis: '', matter_id: '' })
  const [showNew, setShowNew] = useState(false)

  const load = useCallback(async () => {
    const [dl, ag, ms] = await Promise.all([
      api.get<LegalDeadline[]>('/legal/deadlines', {
        params: filter === 'all' ? {} : { status: filter },
      }),
      api.get<LegalAgenda>('/legal/agenda', { params: { days: 60 } }),
      api.get<LegalMatter[]>('/legal/matters'),
    ])
    setItems(dl.data)
    setAgenda(ag.data)
    setMatters(ms.data)
    setLoading(false)
  }, [filter])

  useEffect(() => {
    load()
  }, [load])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    if (!form.title.trim() || !form.due_date) return
    await api.post('/legal/deadlines', {
      title: form.title.trim(),
      due_date: form.due_date,
      basis: form.basis.trim() || null,
      matter_id: form.matter_id ? Number(form.matter_id) : null,
      source: 'manual',
    })
    setForm({ title: '', due_date: '', basis: '', matter_id: '' })
    setShowNew(false)
    load()
  }

  async function toggle(d: LegalDeadline) {
    await api.patch(`/legal/deadlines/${d.id}`, { status: d.status === 'open' ? 'done' : 'open' })
    load()
  }

  async function remove(id: number) {
    await api.delete(`/legal/deadlines/${id}`)
    load()
  }

  const overdue = items.filter((d) => d.status === 'open' && d.days_left < 0)
  const week = items.filter((d) => d.status === 'open' && d.days_left >= 0 && d.days_left <= 7)
  const month = items.filter((d) => d.status === 'open' && d.days_left > 7 && d.days_left <= 30)
  const later = items.filter((d) => d.status === 'open' && d.days_left > 30)
  const done = items.filter((d) => d.status !== 'open')

  return (
    <div className="space-y-6">
      <LegalNav />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
              <CalendarClock className="w-5 h-5" />
            </span>
            Süreler
          </h1>
          <p className="text-slate-400 mt-2">
            Hukukta kaybedilen davaların çoğu esastan değil süreden kaybedilir. Analizlerden çıkan
            süreler buraya yazılır ve geri sayar.
          </p>
        </div>
        <button onClick={() => setShowNew((v) => !v)} className="btn-primary inline-flex items-center gap-2">
          <Plus className="w-4 h-4" /> Süre ekle
        </button>
      </div>

      <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 p-4 flex gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-sm text-amber-100/80 leading-relaxed">
          Tarihler tahminîdir — başlangıç gününe süre eklenerek hesaplanır; resmî tatil, adli tatil
          ve özel tebligat kuralları hesaba katılmaz. Kritik süreleri avukatınla teyit et.
        </p>
      </div>

      {showNew && (
        <form onSubmit={add} className="card space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Field label="Süre / iş" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
            <Field label="Son gün" type="date" value={form.due_date} onChange={(v) => setForm({ ...form, due_date: v })} />
            <Field label="Dayanak" value={form.basis} onChange={(v) => setForm({ ...form, basis: v })} placeholder="tebliğden 15 gün" />
            <div>
              <label className="label">Dosya</label>
              <select className="input" value={form.matter_id} onChange={(e) => setForm({ ...form, matter_id: e.target.value })}>
                <option value="">Bağımsız</option>
                {matters.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
              </select>
            </div>
          </div>
          <button type="submit" className="btn-primary">Kaydet</button>
        </form>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Geçmiş süre" value={overdue.length} tone={overdue.length ? 'text-red-400 bg-red-500/10' : 'text-slate-400 bg-slate-700/30'} />
        <Stat label="Bu hafta" value={week.length} tone="text-amber-400 bg-amber-500/10" />
        <Stat label="Bu ay" value={month.length} tone="text-brand-400 bg-brand-500/10" />
        <Stat label="Duruşma (60 gün)" value={agenda?.hearings.length ?? 0} tone="text-blue-400 bg-blue-500/10" />
      </div>

      {agenda && agenda.hearings.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Gavel className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Duruşmalar</h3>
          </div>
          <ul className="space-y-2">
            {agenda.hearings.map((h) => (
              <li key={h.matter_id} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-200 truncate">
                  {h.title}
                  {h.court && <span className="text-slate-500"> · {h.court}</span>}
                </span>
                <span className="text-slate-400 shrink-0">
                  {h.date} <span className="text-slate-600">({h.days_left} gün)</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="inline-flex gap-1 bg-slate-900 border border-slate-800 rounded-full p-1">
        {([['open', 'Açık'], ['done', 'Tamamlanan'], ['all', 'Tümü']] as [Filter, string][]).map(([k, l]) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            className={clsx(
              'px-4 py-1.5 text-xs font-semibold rounded-full transition-colors',
              filter === k ? 'bg-brand-500 text-slate-950' : 'text-slate-400 hover:text-slate-100',
            )}
          >
            {l}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="card text-sm text-slate-500">
          Bu filtrede süre yok. Bir analiz sonucundaki "Süreleri takvime yaz" düğmesi, belgeden
          çıkan süreleri buraya taşır.
        </div>
      ) : (
        <div className="space-y-6">
          <Group title="Süresi geçmiş" items={overdue} onToggle={toggle} onDelete={remove} tone="text-red-400" />
          <Group title="Bu hafta" items={week} onToggle={toggle} onDelete={remove} tone="text-amber-400" />
          <Group title="Bu ay" items={month} onToggle={toggle} onDelete={remove} />
          <Group title="Daha sonra" items={later} onToggle={toggle} onDelete={remove} />
          <Group title="Tamamlanan" items={done} onToggle={toggle} onDelete={remove} />
        </div>
      )}
    </div>
  )
}

function Group({
  title, items, onToggle, onDelete, tone = 'text-slate-400',
}: {
  title: string
  items: LegalDeadline[]
  onToggle: (d: LegalDeadline) => void
  onDelete: (id: number) => void
  tone?: string
}) {
  if (!items.length) return null
  return (
    <section className="space-y-2">
      <h2 className={clsx('text-sm font-semibold uppercase tracking-wide', tone)}>
        {title} ({items.length})
      </h2>
      {items.map((d) => (
        <DeadlineRow key={d.id} deadline={d} showMatter onToggle={() => onToggle(d)} onDelete={() => onDelete(d.id)} />
      ))}
    </section>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="card flex items-center gap-3 py-4">
      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center', tone)}>
        <CalendarClock className="w-4 h-4" />
      </div>
      <div>
        <div className="text-xl font-bold text-slate-100 leading-none">{value}</div>
        <div className="text-xs text-slate-400 mt-1">{label}</div>
      </div>
    </div>
  )
}
