import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { api } from '@/lib/api'
import type { Workspace } from '@/types'

export function Workspaces() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<Workspace[]>('/workspaces')
      .then(r => setWorkspaces(r.data))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-100">Workspaces</h1>
        <p className="text-slate-400 mt-1">Tüm iş kollarınız tek yerde.</p>
      </div>

      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workspaces.map((ws) => (
            <Link
              key={ws.id}
              to={`/workspaces/${ws.slug}`}
              className="card hover:border-brand-500/30 transition-colors group"
            >
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold"
                  style={{ backgroundColor: `${ws.color}20`, color: ws.color || '#fbbf24' }}
                >
                  {ws.name.charAt(0)}
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-brand-400 transition-colors" />
              </div>
              <div className="font-semibold text-slate-100 mb-1">{ws.name}</div>
              <div className="text-sm text-slate-400 line-clamp-2">{ws.description}</div>
              <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${ws.is_active ? 'bg-green-400' : 'bg-slate-600'}`} />
                <span className="text-xs text-slate-500">
                  {ws.is_active ? 'Aktif' : 'Pasif'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
