
import { WhiskyHourCard } from '@/components/WhiskyHourCard'
import { useEffect, useState } from 'react'
import { TrendingUp, Users, Target, Zap, ArrowUpRight } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { Workspace, WorkspaceStats } from '@/types'
import { Link } from 'react-router-dom'

export function Dashboard() {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [stats, setStats] = useState<WorkspaceStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [wsRes, statsRes] = await Promise.all([
          api.get<Workspace[]>('/workspaces'),
          api.get<WorkspaceStats>('/workspaces/superonline/stats').catch(() => null),
        ])
        setWorkspaces(wsRes.data)
        if (statsRes) setStats(statsRes.data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

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
          Bugün {workspaces.length} workspace ve 12 AI ajanı ile çalışıyorsun.
        </p>
      </div>

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
            <div className="font-semibold text-slate-100 mb-1">AI Ajanları</div>
            <div className="text-sm text-slate-400">12 departmanı yönet</div>
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
