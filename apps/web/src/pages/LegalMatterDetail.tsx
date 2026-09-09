import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, Save, CalendarClock, FileText, MessageSquareQuote, Plus,
  AlertTriangle, CheckCircle2, Trash2, Users2, ScanSearch,
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { LegalNav } from '@/components/LegalNav'
import { LegalUploader } from '@/components/LegalUploader'
import { ResultPanel } from '@/components/LegalResult'
import { MODE_LABELS } from '@/lib/legalIcons'
import { Field, ROLES, STAGES } from './LegalMatters'
import type {
  LegalConsultation, LegalDeadline, LegalDocument, LegalMatter, LegalMeta,
} from '@/types'

type Tab = 'ozet' | 'gorusler' | 'belgeler' | 'sureler'

export function LegalMatterDetail() {
  const { id = '' } = useParams()
  const [matter, setMatter] = useState<LegalMatter | null>(null)
  const [meta, setMeta] = useState<LegalMeta | null>(null)
  const [consultations, setConsultations] = useState<LegalConsultation[]>([])
  const [documents, setDocuments] = useState<LegalDocument[]>([])
  const [deadlines, setDeadlines] = useState<LegalDeadline[]>([])
  const [open, setOpen] = useState<LegalConsultation | null>(null)
  const [tab, setTab] = useState<Tab>('ozet')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [newDl, setNewDl] = useState({ title: '', due_date: '', basis: '' })

  const load = useCallback(async () => {
    try {
      const [m, cs, ds, dl] = await Promise.all([
        api.get<LegalMatter>(`/legal/matters/${id}`),
        api.get<LegalConsultation[]>('/legal/consultations', { params: { matter_id: id, limit: 100 } }),
        api.get<LegalDocument[]>('/legal/documents', { params: { matter_id: id } }),
        api.get<LegalDeadline[]>('/legal/deadlines', { params: { matter_id: id } }),
      ])
      setMatter(m.data)
      setConsultations(cs.data)
      setDocuments(ds.data)
      setDeadlines(dl.data)
    } catch {
      setNotFound(true)
    }
  }, [id])

  useEffect(() => {
    load()
    api.get<LegalMeta>('/legal/meta').then(({ data }) => setMeta(data))
  }, [load])

  async function save() {
    if (!matter) return
    setSaving(true)
    try {
      const { data } = await api.patch<LegalMatter>(`/legal/matters/${id}`, {
        title: matter.title, area: matter.area, self_party: matter.self_party,
        counterparty: matter.counterparty, role: matter.role, court: matter.court,
        reference: matter.reference, stage: matter.stage, status: matter.status,
        amount: matter.amount, next_hearing: matter.next_hearing || null,
        summary: matter.summary, notes: matter.notes,
      })
      setMatter(data)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  async function addDocuments(docs: LegalDocument[]) {
    const fresh = docs.filter((d) => !documents.some((x) => x.id === d.id))
    setDocuments(docs)
    if (fresh.length) {
      await api.post(`/legal/matters/${id}/attach`, { document_ids: fresh.map((d) => d.id) })
      load()
    }
  }

  async function addDeadline(e: React.FormEvent) {
    e.preventDefault()
    if (!newDl.title.trim() || !newDl.due_date) return
    await api.post('/legal/deadlines', {
      title: newDl.title.trim(), due_date: newDl.due_date,
      basis: newDl.basis.trim() || null, matter_id: Number(id), source: 'manual',
    })
    setNewDl({ title: '', due_date: '', basis: '' })
    load()
  }

  async function toggleDeadline(d: LegalDeadline) {
    await api.patch(`/legal/deadlines/${d.id}`, { status: d.status === 'open' ? 'done' : 'open' })
    load()
  }

  async function removeDeadline(deadlineId: number) {
    await api.delete(`/legal/deadlines/${deadlineId}`)
    load()
  }

  if (notFound) {
    return (
      <div className="card">
        <p className="text-slate-300">Dosya bulunamadı.</p>
        <Link to="/hukuk/dosyalar" className="text-brand-400 hover:underline text-sm mt-2 inline-block">
          ← Dosyalara dön
        </Link>
      </div>
    )
  }
  if (!matter) return <div className="text-slate-500">Yükleniyor...</div>

  const openDeadlines = deadlines.filter((d) => d.status === 'open')
  const set = (patch: Partial<LegalMatter>) => setMatter({ ...matter, ...patch })

  return (
    <div className="space-y-6">
      <LegalNav />

      <Link to="/hukuk/dosyalar" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100">
        <ArrowLeft className="w-4 h-4" /> Dosyalar
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-slate-100">{matter.title}</h1>
          <p className="text-sm text-slate-500 mt-1">
            {[matter.area, matter.role, matter.court, matter.reference].filter(Boolean).join(' · ') ||
              'Ayrıntılar aşağıdan doldurulabilir'}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/hukuk/belge?dosya=${matter.id}`} className="btn-ghost inline-flex items-center gap-2 text-sm py-2">
            <ScanSearch className="w-4 h-4" /> Belge analizi
          </Link>
          <Link to={`/hukuk/kurul?dosya=${matter.id}`} className="btn-ghost inline-flex items-center gap-2 text-sm py-2">
            <Users2 className="w-4 h-4" /> Kurul topla
          </Link>
        </div>
      </div>

      {/* Kritik süre bandı */}
      {openDeadlines.some((d) => d.days_left <= 7) && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-4 flex gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-red-300">Bu dosyada süre yaklaşıyor</div>
            <ul className="mt-1 space-y-0.5">
              {openDeadlines.filter((d) => d.days_left <= 7).map((d) => (
                <li key={d.id} className="text-sm text-red-200/90">
                  {d.title} — {d.due_date} ({d.days_left < 0 ? `${Math.abs(d.days_left)} gün geçti` : `${d.days_left} gün kaldı`})
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="inline-flex gap-1 bg-slate-900 border border-slate-800 rounded-full p-1">
        {([
          ['ozet', 'Künye'],
          ['gorusler', `Görüşler (${consultations.length})`],
          ['belgeler', `Belgeler (${documents.length})`],
          ['sureler', `Süreler (${openDeadlines.length})`],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={clsx(
              'px-4 py-1.5 text-xs font-semibold rounded-full transition-colors',
              tab === key ? 'bg-brand-500 text-slate-950' : 'text-slate-400 hover:text-slate-100',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'ozet' && (
        <div className="card space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Dosya başlığı" value={matter.title} onChange={(v) => set({ title: v })} />
            <div>
              <label className="label">Hukuk alanı</label>
              <select className="input" value={matter.area || ''} onChange={(e) => set({ area: e.target.value })}>
                <option value="">Seçilmedi</option>
                {(meta?.departments || []).map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <Field label="Bizim taraf" value={matter.self_party || ''} onChange={(v) => set({ self_party: v })} />
            <Field label="Karşı taraf" value={matter.counterparty || ''} onChange={(v) => set({ counterparty: v })} />
            <div>
              <label className="label">Sıfatımız</label>
              <select className="input" value={matter.role || ''} onChange={(e) => set({ role: e.target.value })}>
                <option value="">Seçilmedi</option>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Aşama</label>
              <select className="input" value={matter.stage} onChange={(e) => set({ stage: e.target.value })}>
                {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <Field label="Merci" value={matter.court || ''} onChange={(v) => set({ court: v })} />
            <Field label="Dosya / esas no" value={matter.reference || ''} onChange={(v) => set({ reference: v })} />
            <Field label="Uyuşmazlık değeri" value={matter.amount || ''} onChange={(v) => set({ amount: v })} />
            <Field label="Sıradaki duruşma" type="date" value={matter.next_hearing || ''} onChange={(v) => set({ next_hearing: v })} />
            <div>
              <label className="label">Durum</label>
              <select className="input" value={matter.status} onChange={(e) => set({ status: e.target.value })}>
                <option value="open">Açık</option>
                <option value="waiting">Beklemede</option>
                <option value="closed">Kapandı</option>
              </select>
            </div>
          </div>
          <div>
            <label className="label">Dosya özeti — ajanlar bunu bağlam olarak okur</label>
            <textarea
              className="input resize-y" rows={3}
              value={matter.summary || ''}
              onChange={(e) => set({ summary: e.target.value })}
              placeholder="Olayın kısa hikâyesi: ne oldu, nerede kaldık?"
            />
          </div>
          <div className="flex items-center gap-3">
            <button onClick={save} disabled={saving} className="btn-primary inline-flex items-center gap-2">
              <Save className="w-4 h-4" /> {saving ? 'Kaydediliyor...' : 'Kaydet'}
            </button>
            {saved && <span className="text-sm text-green-400">Kaydedildi</span>}
          </div>
        </div>
      )}

      {tab === 'gorusler' && (
        <div className="space-y-3">
          {consultations.length === 0 && (
            <div className="card text-sm text-slate-500">
              Bu dosyada henüz görüş yok. Belge analizi yap ya da bir ajana danış; dosyayı seçmen
              yeterli.
            </div>
          )}
          {consultations.map((c) => (
            <div key={c.id} className="card py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-slate-100">{c.subject}</span>
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                      {MODE_LABELS[c.mode]?.label || c.mode}
                    </span>
                    {c.review && (
                      <span className={clsx(
                        'text-[11px] px-2 py-0.5 rounded-full',
                        c.review.verdict === 'temiz' ? 'bg-green-500/10 text-green-400'
                          : c.review.verdict === 'riskli' ? 'bg-red-500/10 text-red-400'
                            : 'bg-amber-500/10 text-amber-400',
                      )}>
                        denetlendi
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-400 mt-1 line-clamp-2">{c.summary}</p>
                  <div className="text-xs text-slate-600 mt-2">
                    {c.agent_name} · {new Date(c.created_at).toLocaleString('tr-TR')}
                    {c.message_count > 0 && ` · ${c.message_count} mesaj`}
                  </div>
                </div>
                <button
                  onClick={() => setOpen(open?.id === c.id ? null : c)}
                  className="text-xs font-semibold text-brand-400 hover:text-brand-300 shrink-0"
                >
                  {open?.id === c.id ? 'Kapat' : 'Aç'}
                </button>
              </div>
            </div>
          ))}
          {open && <ResultPanel consultation={open} onReview={() => load()} />}
        </div>
      )}

      {tab === 'belgeler' && (
        <div className="card">
          <p className="text-sm text-slate-400 mb-4">
            Bu dosyaya yüklenen belgeler ajanlara bağlam olarak verilir.
          </p>
          <LegalUploader value={documents} onChange={addDocuments} title="Dosyaya belge ekle" />
        </div>
      )}

      {tab === 'sureler' && (
        <div className="space-y-4">
          <form onSubmit={addDeadline} className="card space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field label="Süre / iş" value={newDl.title} onChange={(v) => setNewDl({ ...newDl, title: v })}
                placeholder="Örn. Cevap dilekçesi" />
              <Field label="Son gün" type="date" value={newDl.due_date} onChange={(v) => setNewDl({ ...newDl, due_date: v })} />
              <Field label="Dayanak" value={newDl.basis} onChange={(v) => setNewDl({ ...newDl, basis: v })}
                placeholder="tebliğden 2 hafta" />
            </div>
            <button type="submit" className="btn-primary inline-flex items-center gap-2 text-sm py-2">
              <Plus className="w-4 h-4" /> Süre ekle
            </button>
          </form>

          {deadlines.length === 0 ? (
            <div className="card text-sm text-slate-500">
              Bu dosyada süre kaydı yok. Bir analizin sonucundaki "Süreleri takvime yaz" düğmesiyle
              toplu ekleyebilirsin.
            </div>
          ) : (
            <div className="space-y-2">
              {deadlines.map((d) => (
                <DeadlineRow key={d.id} deadline={d} onToggle={() => toggleDeadline(d)} onDelete={() => removeDeadline(d.id)} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function DeadlineRow({
  deadline: d, onToggle, onDelete, showMatter = false,
}: {
  deadline: LegalDeadline
  onToggle: () => void
  onDelete: () => void
  showMatter?: boolean
}) {
  const done = d.status !== 'open'
  const late = !done && d.days_left < 0
  const soon = !done && d.days_left >= 0 && d.days_left <= 7
  return (
    <div
      className={clsx(
        'card py-3 flex items-center gap-3',
        late ? 'border-red-500/30' : soon ? 'border-amber-500/30' : '',
        done && 'opacity-60',
      )}
    >
      <button
        onClick={onToggle}
        aria-label={done ? 'Tekrar aç' : 'Tamamlandı işaretle'}
        className={clsx(
          'w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors',
          done ? 'border-green-500 bg-green-500/20 text-green-400' : 'border-slate-600 hover:border-brand-500',
        )}
      >
        {done && <CheckCircle2 className="w-3 h-3" />}
      </button>

      <div className="min-w-0 flex-1">
        <div className={clsx('text-sm font-medium', done ? 'text-slate-500 line-through' : 'text-slate-100')}>
          {d.title}
          {d.critical && !done && <span className="ml-2 text-[11px] text-red-400">kritik</span>}
        </div>
        <div className="text-xs text-slate-500">
          {d.due_date}
          {d.basis ? ` · ${d.basis}` : ''}
          {showMatter && d.matter_title ? ` · ${d.matter_title}` : ''}
          {d.source === 'analiz' && ' · analizden'}
        </div>
      </div>

      <span
        className={clsx(
          'text-xs font-semibold px-2.5 py-1 rounded-full shrink-0',
          done ? 'bg-slate-800 text-slate-400'
            : late ? 'bg-red-500/10 text-red-400'
              : soon ? 'bg-amber-500/10 text-amber-400'
                : 'bg-slate-800 text-slate-300',
        )}
      >
        {done ? 'tamam' : late ? `${Math.abs(d.days_left)} gün geçti` : `${d.days_left} gün`}
      </span>

      <button onClick={onDelete} aria-label="Sil" className="text-slate-600 hover:text-red-400 shrink-0">
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  )
}
