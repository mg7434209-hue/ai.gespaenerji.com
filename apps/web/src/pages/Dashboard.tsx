
import { WhiskyHourCard } from '@/components/WhiskyHourCard'
import { useEffect, useState } from 'react'
import { TrendingUp, Users, Target, Zap, ArrowUpRight, ExternalLink, Globe, Scale, AlertTriangle, CalendarClock } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { Agent, LegalAgenda, Workspace, WorkspaceStats } from '@/types'
import { Link } from 'react-router-dom'

// Dijital odanın dış kapıları — canlı siteler
const MY_SITES = [
  { name: 'internetbasvuru.com', desc: 'Turkcell Superbox başvuru', url: 'https://internetbasvuru.com', color: '#2856A5' },
  { name: 'gespaenerji.com', desc: 'Anahtar teslim GES', url: 'https://gespaenerji.com', color: '#f59e0b' },
  { name: 'gesmarketim.com', desc: 'Solar e-ticaret', url: 'https://gesmarketim.com', color: '#10b981' },
  { name: 'tarifesec.net.tr', desc: 'Tarife karşılaştırma', url: 'https://tarifesec.net.tr', color: '#8b5cf6' },
]

export function Dashboard() {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [stats, setStats] = useState<WorkspaceStats | null>(null)
  const [agenda, setAgenda] = useState<LegalAgenda | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [wsRes, agentsRes, statsRes, agendaRes] = await Promise.all([
          api.get<Workspace[]>('/workspaces'),
          api.get<Agent[]>('/agents').catch(() => null),
          api.get<WorkspaceStats>('/workspaces/superonline/stats').catch(() => null),
          api.get<LegalAgenda>('/legal/agenda', { params: { days: 30 } }).catch(() => null),
        ])
        setWorkspaces(wsRes.data)
        if (agentsRes) setAgents(agentsRes.data)
        if (statsRes) setStats(statsRes.data)
        if (agendaRes) setAgenda(agendaRes.data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const activeAgents = agents.filter((a) => a.is_active).length
  const today = new Date().toLocaleDateString('tr-TR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 6) return 'İyi geceler'
    if (h < 12) return 'Günaydın'
    if (h < 18) return 'İyi günler'
    return 'İyi akşamlar'
  })()

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-100">
          {greeting}, {user?.full_name?.split(' ')[0] || 'Mustafa'} 👋
        </h1>
        <p className="text-slate-400 mt-1">
          {today} · {workspaces.length} workspace ·{' '}
          {agents.length ? `${activeAgents}/${agents.length} ajan görevde` : 'ajanlar yükleniyor'}
        </p>
      </div>

      {/* Hukuki süreler — kaçırılırsa hak kaybı olur, en üstte durur */}
      {agenda && agenda.deadlines.length > 0 && <LegalAgendaCard agenda={agenda} />}

      {/* KPI Cards — Superonline */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Superonline Bayi (B9613) — Bugün
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KpiCard
            label="Toplam Lead"
            value={stats?.leads.total ?? '—'}
            icon={Users}
            color="text-blue-400 bg-blue-500/10"
          />
          <KpiCard
            label="Yeni Lead"
            value={stats?.leads.new ?? '—'}
            icon={TrendingUp}
            color="text-green-400 bg-green-500/10"
          />
          <KpiCard
            label="Teklif Aşamasında"
            value={stats?.leads.offered ?? '—'}
            icon={Target}
            color="text-yellow-400 bg-yellow-500/10"
          />
          <KpiCard
            label="Dönüşüm"
            value={stats ? `%${stats.leads.conversion_rate}` : '—'}
            icon={Zap}
            color="text-purple-400 bg-purple-500/10"
          />
        </div>
      </div>

      {/* Workspaces */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
            Workspace'lerim
          </h2>
          <Link to="/workspaces" className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
            Tümünü gör <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading && <div className="text-slate-500 text-sm col-span-full">Yükleniyor...</div>}
          {!loading && workspaces.map((ws) => (
            <Link
              key={ws.id}
              to={`/workspaces/${ws.slug}`}
              className="card hover:border-slate-700 transition-colors group"
            >
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold"
                  style={{ backgroundColor: `${ws.color}20`, color: ws.color || '#fbbf24' }}
                >
                  {ws.name.charAt(0)}
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-brand-400 transition-colors" />
              </div>
              <div className="font-semibold text-slate-100 mb-1">{ws.name}</div>
              <div className="text-sm text-slate-400 line-clamp-2">{ws.description}</div>
            </Link>
          ))}
        </div>
      </div>

      {/* Sitelerim — dijital odanın dış kapıları */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Sitelerim
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {MY_SITES.map((site) => (
            <a
              key={site.url}
              href={site.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card hover:border-slate-700 transition-colors group"
            >
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${site.color}20`, color: site.color }}
                >
                  <Globe className="w-4 h-4" />
                </div>
                <ExternalLink className="w-4 h-4 text-slate-600 group-hover:text-brand-400 transition-colors" />
              </div>
              <div className="font-semibold text-slate-100 text-sm mb-0.5">{site.name}</div>
              <div className="text-xs text-slate-400">{site.desc}</div>
            </a>
          ))}
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Hızlı İşlemler
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/leads" className="card hover:border-brand-500/50 transition-colors">
            <div className="font-semibold text-slate-100 mb-1">+ Yeni Lead Ekle</div>
            <div className="text-sm text-slate-400">Superonline için lead kaydet</div>
          </Link>
          <Link to="/agents" className="card hover:border-brand-500/50 transition-colors">
            <div className="font-semibold text-slate-100 mb-1">Dijital Ofisim</div>
            <div className="text-sm text-slate-400">AI ekibini yönet</div>
          </Link>
          <Link to="/settings" className="card hover:border-brand-500/50 transition-colors">
            <div className="font-semibold text-slate-100 mb-1">API Anahtarları</div>
            <div className="text-sm text-slate-400">Anthropic, OpenAI, Gemini</div>
          </Link>
        </div>
      </div>

      {/* Viski Saati 🥃 */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Mola Vakti
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <WhiskyHourCard />
        </div>
      </div>
    </div>
  )
}

function KpiCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="card">
      <div className="flex items-start justify-between mb-3">
        <div className="text-sm text-slate-400">{label}</div>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-100">{value}</div>
    </div>
  )
}


/** Yaklaşan hukuki süreler — Hukuk Ofisi takviminden. */
function LegalAgendaCard({ agenda }: { agenda: LegalAgenda }) {
  const urgent = agenda.deadlines.filter((d) => d.days_left <= 7)
  const alarm = agenda.overdue > 0
  return (
    <div
      className={clsx(
        'card border',
        alarm ? 'border-red-500/40 bg-red-500/5' : urgent.length ? 'border-amber-500/30' : '',
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          {alarm ? (
            <AlertTriangle className="w-5 h-5 text-red-400" />
          ) : (
            <Scale className="w-5 h-5 text-brand-400" />
          )}
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">
            {alarm ? `${agenda.overdue} süre geçti — hemen bak` : 'Yaklaşan hukuki süreler'}
          </h2>
        </div>
        <Link to="/hukuk/sureler" className="text-xs font-semibold text-brand-400 hover:text-brand-300">
          Tümünü gör →
        </Link>
      </div>

      <ul className="space-y-2">
        {agenda.deadlines.slice(0, 5).map((d) => (
          <li key={d.id} className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm text-slate-100 truncate">{d.title}</div>
              <div className="text-xs text-slate-500 truncate">
                {d.matter_title || 'Bağımsız'} · {d.due_date}
              </div>
            </div>
            <span
              className={clsx(
                'text-xs font-semibold px-2.5 py-1 rounded-full shrink-0',
                d.days_left < 0
                  ? 'bg-red-500/10 text-red-400'
                  : d.days_left <= 7
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-slate-800 text-slate-300',
              )}
            >
              {d.days_left < 0 ? `${Math.abs(d.days_left)} gün geçti` : `${d.days_left} gün`}
            </span>
          </li>
        ))}
      </ul>

      {agenda.hearings.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-2 text-xs text-slate-400">
          <CalendarClock className="w-3.5 h-3.5" />
          Sıradaki duruşma: {agenda.hearings[0].title} — {agenda.hearings[0].date}
          <span className="text-slate-600">({agenda.hearings[0].days_left} gün)</span>
        </div>
      )}
    </div>
  )
}
