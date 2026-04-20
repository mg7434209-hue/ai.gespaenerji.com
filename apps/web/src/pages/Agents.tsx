import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Agent } from '@/types'
import clsx from 'clsx'

export function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    const { data } = await api.get<Agent[]>('/agents')
    setAgents(data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  async function toggle(slug: string) {
    await api.post(`/agents/${slug}/toggle`)
    load()
  }

  const activeCount = agents.filter((a) => a.is_active).length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-100">AI Departmanları</h1>
        <p className="text-slate-400 mt-1">
          {activeCount} / {agents.length} ajan aktif — 7/24 çalışıyor.
        </p>
      </div>

      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div key={agent.id} className="card hover:border-slate-700 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm"
                  style={{
                    backgroundColor: `${agent.color}20`,
                    color: agent.color || '#fbbf24',
                  }}
                >
                  {agent.name.charAt(0)}
                </div>
                <button
                  onClick={() => toggle(agent.slug)}
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
              <div
                className="text-xs font-medium mb-2"
                style={{ color: agent.color || '#fbbf24' }}
              >
                {agent.department}
              </div>
              <div className="text-sm text-slate-400 line-clamp-2">{agent.description}</div>

              <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-500">{agent.model}</span>
                <span className={clsx(agent.is_active ? 'text-green-400' : 'text-slate-500')}>
                  {agent.is_active ? '● Aktif' : '○ Pasif'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
