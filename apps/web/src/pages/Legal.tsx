import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Scale,
  Search,
  Users,
  Zap,
  MessageSquareQuote,
  FileCheck2,
  AlertTriangle,
  ChevronRight,
  Trash2,
  Inbox,
  ScanSearch,
  Sparkles,
  FileStack,
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { legalIcon, MODE_LABELS } from '@/lib/legalIcons'
import type { LegalAgent, LegalConsultation, LegalMeta, LegalStats } from '@/types'

type Tab = 'kadro' | 'gecmis'

export function Legal() {
  const [agents, setAgents] = useState<LegalAgent[]>([])
  const [meta, setMeta] = useState<LegalMeta | null>(null)
  const [stats, setStats] = useState<LegalStats | null>(null)
  const [history, setHistory] = useState<LegalConsultation[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('kadro')
  const [dept, setDept] = useState<string>('all')
  const [q, setQ] = useState('')

  async function load() {
    const [a, m, s] = await Promise.all([
      api.get<LegalAgent[]>('/legal/agents'),
      api.get<LegalMeta>('/legal/meta'),
      api.get<LegalStats>('/legal/stats'),
    ])
    setAgents(a.data)
    setMeta(m.data)
    setStats(s.data)
    setLoading(false)
  }

  async function loadHistory() {
    const { data } = await api.get<LegalConsultation[]>('/legal/consultations', {
      params: { limit: 50 },
    })
    setHistory(data)
  }

  useEffect(() => {
    load()
    loadHistory()
  }, [])

  async function toggle(slug: string) {
    setAgents((prev) =>
      prev.map((a) => (a.slug === slug ? { ...a, is_active: !a.is_active } : a)),
    )
    try {
      await api.post(`/legal/agents/${slug}/toggle`)
      const { data } = await api.get<LegalStats>('/legal/stats')
      setStats(data)
    } catch {
      load()
    }
  }

  async function removeConsultation(id: number) {
    setHistory((prev) => prev.filter((c) => c.id !== id))
    try {
      await api.delete(`/legal/consultations/${id}`)
      const { data } = await api.get<LegalStats>('/legal/stats')
      setStats(data)
    } catch {
      loadHistory()
    }
  }

  const departments = meta?.departments ?? []

  const visible = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase('tr')
    return agents.filter((a) => {
      if (dept !== 'all' && a.department !== dept) return false
      if (!needle) return true
      const hay = [a.name, a.title, a.description || '', ...a.expertise, ...a.documents]
        .join(' ')
        .toLocaleLowerCase('tr')
      return hay.includes(needle)
    })
  }, [agents, dept, q])

  const grouped = useMemo(() => {
    const order = departments.length
      ? departments
      : Array.from(new Set(visible.map((a) => a.department)))
    return order
      .map((d) => ({ department: d, items: visible.filter((a) => a.department === d) }))
      .filter((g) => g.items.length > 0)
  }, [visible, departments])

  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
              <Scale className="w-5 h-5" />
            </span>
            Hukuk Ofisi
          </h1>
          <p className="text-slate-400 mt-2">
            Uzmanlık alanına göre kurulmuş avukat ajan serin. Konuyu seç, ajanı çalıştır —
            değerlendirme, süreler ve dilekçe taslağı tek ekranda.
          </p>
        </div>
        <div className="inline-flex gap-1 bg-slate-900 border border-slate-800 rounded-full p-1">
          {(
            [
              ['kadro', 'Avukat Kadrosu'],
              ['gecmis', 'Danışma Geçmişi'],
            ] as [Tab, string][]
          ).map(([key, label]) => (
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
      </div>

      {/* Yasal uyarı */}
      {meta && (
        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 p-4 flex gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-sm text-amber-100/80 leading-relaxed">{meta.disclaimer}</p>
        </div>
      )}

      {/* API anahtarı yoksa uyar */}
      {meta && !meta.ai_configured && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/5 p-4 text-sm text-red-200/90">
          <span className="font-semibold">ANTHROPIC_API_KEY tanımlı değil.</span>{' '}
          Ajanlar listelenir ama çalıştırılamaz. Railway → Variables'a anahtarı ekleyin.
        </div>
      )}

      {/* Belge yükleme kısayolu — "dosyayı ver, sistem halletsin" akışı */}
      <Link
        to="/hukuk/belge"
        className="card flex flex-wrap items-center justify-between gap-4 hover:border-brand-500/50 transition-colors"
      >
        <div className="flex items-center gap-4 min-w-0">
          <span className="w-11 h-11 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center shrink-0">
            <ScanSearch className="w-5 h-5" />
          </span>
          <div className="min-w-0">
            <div className="font-semibold text-slate-100">Belgeyi yükle, sistem analiz etsin</div>
            <p className="text-sm text-slate-400 mt-0.5">
              Tebligat, ödeme emri, sözleşme veya ceza tutanağını at — hangi ajana gideceğine,
              hangi sürelerin işlediğine ve ne yapman gerektiğine sistem karar versin.
            </p>
          </div>
        </div>
        <span className="btn-primary inline-flex items-center gap-2 shrink-0">
          <Sparkles className="w-4 h-4" /> Belge Analizi
        </span>
      </Link>

      {/* Özet */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Summary icon={Users} label="Avukat Ajanı" value={stats?.agents_total ?? agents.length} tone="text-slate-300 bg-slate-700/30" />
        <Summary icon={Zap} label="Görevde" value={stats?.agents_active ?? 0} tone="text-green-400 bg-green-500/10" />
        <Summary icon={MessageSquareQuote} label="Danışma" value={stats?.consultations ?? 0} tone="text-brand-400 bg-brand-500/10" />
        <Summary icon={FileCheck2} label="Belge Taslağı" value={stats?.drafts ?? 0} tone="text-blue-400 bg-blue-500/10" />
        <Summary icon={FileStack} label="Yüklü Belge" value={stats?.documents ?? 0} tone="text-purple-400 bg-purple-500/10" />
      </div>

      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : tab === 'kadro' ? (
        <>
          {/* Filtre + arama */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Konu ara: kira, icra, kıdem tazminatı, KVKK..."
                className="input pl-9"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <DeptChip active={dept === 'all'} onClick={() => setDept('all')}>
              Tümü ({agents.length})
            </DeptChip>
            {departments.map((d) => {
              const n = agents.filter((a) => a.department === d).length
              if (!n) return null
              return (
                <DeptChip key={d} active={dept === d} onClick={() => setDept(d)}>
                  {d} ({n})
                </DeptChip>
              )
            })}
          </div>

          {/* Kadro */}
          {grouped.map((group) => (
            <section key={group.department} className="space-y-3">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
                {group.department}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {group.items.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} onToggle={() => toggle(agent.slug)} />
                ))}
              </div>
            </section>
          ))}

          {!grouped.length && (
            <div className="card text-slate-500 text-sm">
              "{q}" için ajan bulunamadı. Emin değilsen{' '}
              <Link to="/hukuk/bas-hukuk-musaviri" className="text-brand-400 hover:underline">
                Baş Hukuk Müşaviri
              </Link>{' '}
              konuyu doğru uzmana yönlendirir.
            </div>
          )}
        </>
      ) : (
        <HistoryList items={history} onDelete={removeConsultation} />
      )}
    </div>
  )
}

function AgentCard({ agent, onToggle }: { agent: LegalAgent; onToggle: () => void }) {
  const Icon = legalIcon(agent.icon)
  return (
    <div
      className={clsx(
        'card flex flex-col transition-colors',
        agent.is_active ? 'border-slate-700 hover:border-brand-500/50' : 'opacity-80 hover:border-slate-700',
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${agent.color}20`, color: agent.color || '#eab308' }}
        >
          <Icon className="w-5 h-5" />
        </div>
        <button
          onClick={onToggle}
          aria-label={`${agent.name} ${agent.is_active ? 'beklemeye al' : 'göreve al'}`}
          className={clsx(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            agent.is_active ? 'bg-brand-500' : 'bg-slate-700',
          )}
        >
          <span
            className={clsx(
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              agent.is_active ? 'translate-x-6' : 'translate-x-1',
            )}
          />
        </button>
      </div>

      <div className="font-semibold text-slate-100">{agent.name}</div>
      <div className="text-xs text-slate-500 mb-2">{agent.title}</div>
      <p className="text-sm text-slate-400 leading-relaxed">{agent.description}</p>

      {agent.expertise?.length > 0 && (
        <ul className="mt-3 space-y-1">
          {agent.expertise.slice(0, 3).map((e) => (
            <li key={e} className="text-xs text-slate-500 flex gap-2">
              <span className="text-brand-500/70">•</span>
              <span>{e}</span>
            </li>
          ))}
          {agent.expertise.length > 3 && (
            <li className="text-xs text-slate-600">+{agent.expertise.length - 3} alan daha</li>
          )}
        </ul>
      )}

      <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {agent.consult_count > 0 ? `${agent.consult_count} danışma` : 'Henüz danışma yok'}
        </span>
        <Link
          to={`/hukuk/${agent.slug}`}
          className="text-xs font-semibold text-brand-400 hover:text-brand-300 inline-flex items-center gap-1"
        >
          Görüş al <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  )
}

function HistoryList({
  items,
  onDelete,
}: {
  items: LegalConsultation[]
  onDelete: (id: number) => void
}) {
  if (!items.length) {
    return (
      <div className="card flex items-center gap-3 text-slate-500 text-sm">
        <Inbox className="w-5 h-5" />
        Henüz danışma kaydı yok. Kadrodan bir ajan seçip ilk sorunu sor.
      </div>
    )
  }
  return (
    <div className="space-y-3">
      {items.map((c) => (
        <div key={c.id} className="card py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-slate-100">
                  {c.subject || c.question.slice(0, 80)}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                  {MODE_LABELS[c.mode]?.label || c.mode}
                </span>
                {c.status === 'error' && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400">
                    hata
                  </span>
                )}
                {c.draft && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                    belge taslağı
                  </span>
                )}
                {c.document_ids?.length > 0 && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400">
                    {c.document_ids.length} belge
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-400 line-clamp-2">
                {c.status === 'error' ? c.error : c.summary}
              </p>
              <div className="text-xs text-slate-600 mt-2">
                {c.agent_name} · {new Date(c.created_at).toLocaleString('tr-TR')}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link
                to={`/hukuk/${c.agent_slug}?danisma=${c.id}`}
                className="text-xs font-semibold text-brand-400 hover:text-brand-300"
              >
                Aç
              </Link>
              <button
                onClick={() => onDelete(c.id)}
                aria-label="Danışmayı sil"
                className="text-slate-600 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function DeptChip({
  active,
  onClick,
  children,
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

function Summary({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ElementType
  label: string
  value: number
  tone: string
}) {
  return (
    <div className="card flex items-center gap-3 py-4">
      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center', tone)}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <div className="text-xl font-bold text-slate-100 leading-none">{value}</div>
        <div className="text-xs text-slate-400 mt-1">{label}</div>
      </div>
    </div>
  )
}
