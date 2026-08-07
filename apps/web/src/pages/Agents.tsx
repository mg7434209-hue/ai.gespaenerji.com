import { useEffect, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import type { Agent } from '@/types'
import clsx from 'clsx'
import {
  Briefcase,
  Wifi,
  Sun,
  Wrench,
  DollarSign,
  Mail,
  BarChart3,
  Scale,
  ShieldCheck,
  LineChart,
  PenSquare,
  Bot,
  Users,
  Zap,
  PauseCircle,
} from 'lucide-react'

// seed'deki icon adları → lucide bileşenleri
const ICONS: Record<string, React.ElementType> = {
  briefcase: Briefcase,
  wifi: Wifi,
  sun: Sun,
  wrench: Wrench,
  'dollar-sign': DollarSign,
  mail: Mail,
  'bar-chart-3': BarChart3,
  scale: Scale,
  'shield-check': ShieldCheck,
  'line-chart': LineChart,
  'pen-square': PenSquare,
  bot: Bot,
}

type Filter = 'all' | 'active' | 'passive'

export function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<Filter>('all')

  async function load() {
    const { data } = await api.get<Agent[]>('/agents')
    setAgents(data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  async function toggle(slug: string) {
    // İyimser güncelleme — bekleme hissini kaldırır
    setAgents((prev) =>
      prev.map((a) => (a.slug === slug ? { ...a, is_active: !a.is_active } : a)),
    )
    try {
      await api.post(`/agents/${slug}/toggle`)
    } catch {
      load()
    }
  }

  const activeCount = agents.filter((a) => a.is_active).length

  const visible = useMemo(() => {
    if (filter === 'active') return agents.filter((a) => a.is_active)
    if (filter === 'passive') return agents.filter((a) => !a.is_active)
    return agents
  }, [agents, filter])

  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Dijital Ofisim</h1>
          <p className="text-slate-400 mt-1">
            İş kollarına göre kurulmuş AI ekibin — görevde olanlar 7/24 çalışır.
          </p>
        </div>
        {/* Filtre */}
        <div className="inline-flex gap-1 bg-slate-900 border border-slate-800 rounded-full p-1">
          {(
            [
              ['all', 'Tümü'],
              ['active', 'Görevde'],
              ['passive', 'Beklemede'],
            ] as [Filter, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={clsx(
                'px-4 py-1.5 text-xs font-semibold rounded-full transition-colors',
                filter === key
                  ? 'bg-brand-500 text-slate-950'
                  : 'text-slate-400 hover:text-slate-100',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Özet şeridi */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SummaryCard
          icon={Users}
          label="Toplam Ajan"
          value={agents.length}
          tone="text-slate-300 bg-slate-700/30"
        />
        <SummaryCard
          icon={Zap}
          label="Görevde"
          value={activeCount}
          tone="text-green-400 bg-green-500/10"
        />
        <SummaryCard
          icon={PauseCircle}
          label="Beklemede"
          value={agents.length - activeCount}
          tone="text-slate-400 bg-slate-500/10"
        />
      </div>

      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visible.map((agent) => {
            const Icon = ICONS[agent.icon || ''] || Bot
            return (
              <div
                key={agent.id}
                className={clsx(
                  'card transition-colors',
                  agent.is_active
                    ? 'border-slate-700 hover:border-brand-500/50'
                    : 'hover:border-slate-700 opacity-90',
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{
                      backgroundColor: `${agent.color}20`,
                      color: agent.color || '#fbbf24',
                    }}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <button
                    onClick={() => toggle(agent.slug)}
                    aria-label={`${agent.name} ${agent.is_active ? 'durdur' : 'göreve al'}`}
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

                <div className="font-semibold text-slate-100 mb-1">{agent.name}</div>
                <span
                  className="inline-block text-[11px] font-semibold px-2 py-0.5 rounded-full mb-2"
                  style={{
                    backgroundColor: `${agent.color}1a`,
                    color: agent.color || '#fbbf24',
                  }}
                >
                  {agent.department}
                </span>
                <div className="text-sm text-slate-400 line-clamp-2">{agent.description}</div>

                <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-500">{agent.model}</span>
                  <span
                    className={clsx(
                      'inline-flex items-center gap-1.5',
                      agent.is_active ? 'text-green-400' : 'text-slate-500',
                    )}
                  >
                    {agent.is_active && (
                      <span className="relative inline-flex w-2 h-2">
                        <span className="absolute inset-0 rounded-full bg-green-400 animate-ping opacity-60" />
                        <span className="relative inline-block w-2 h-2 rounded-full bg-green-400" />
                      </span>
                    )}
                    {agent.is_active ? 'Görevde' : 'Beklemede'}
                  </span>
                </div>
              </div>
            )
          })}
          {!visible.length && (
            <div className="text-slate-500 text-sm col-span-full">
              Bu filtrede ajan yok.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SummaryCard({
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
