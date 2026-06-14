import { useEffect, useState } from 'react'
import { Key, Globe, Database, Shield, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import type { SystemStatus, IntegrationStatus } from '@/types'

export function Settings() {
  const { user } = useAuth()
  const [status, setStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
    api.get<SystemStatus>('/system/status')
      .then((r) => setStatus(r.data))
      .catch(() => setStatus(null))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-100">Ayarlar</h1>
        <p className="text-slate-400 mt-1">Sistem yapılandırması ve entegrasyonlar.</p>
      </div>

      {/* Account */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-slate-100">Hesap</div>
            <div className="text-sm text-slate-400">Giriş bilgileri</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-400 mb-1">Email</div>
            <div className="text-slate-100">{user?.email}</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">İsim</div>
            <div className="text-slate-100">{user?.full_name || '—'}</div>
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-slate-100">AI API Anahtarları</div>
            <div className="text-sm text-slate-400">Railway Environment Variables'dan yönetilir</div>
          </div>
        </div>
        <div className="space-y-2 text-sm">
          <ApiKeyRow name="ANTHROPIC_API_KEY" provider="Claude Sonnet 4" ok={status?.api_keys.anthropic} />
          <ApiKeyRow name="OPENAI_API_KEY" provider="GPT-4o-mini" ok={status?.api_keys.openai} />
          <ApiKeyRow name="GEMINI_API_KEY" provider="Gemini Vision" ok={status?.api_keys.gemini} />
        </div>
        <div className="mt-4 p-3 bg-slate-800/50 rounded-lg text-xs text-slate-400">
          💡 API anahtarlarını değiştirmek için Railway → Variables sekmesini kullan. Yeşil = yapılandırılmış, kırmızı = eksik.
        </div>
      </div>

      {/* Integrations */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-slate-100">Dış Entegrasyonlar</div>
            <div className="text-sm text-slate-400">Canlı durum — gerçek yapılandırmadan okunur</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <IntegrationCard name="WhatsApp Business API" data={status?.integrations.whatsapp} />
          <IntegrationCard name="AI Asistan (Claude)" data={status?.integrations.ai_assistant} />
          <IntegrationCard name="Gmail (MCP)" data={status?.integrations.gmail} />
          <IntegrationCard name="Vapi (Sesli ajan)" data={status?.integrations.vapi} />
          <IntegrationCard name="n8n Workflows" data={status?.integrations.n8n} />
        </div>
      </div>

      {/* System */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-green-500/10 text-green-400 flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-slate-100">Sistem</div>
            <div className="text-sm text-slate-400">Deploy bilgileri</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-400 mb-1">Versiyon</div>
            <div className="text-slate-100">v{status?.version ?? '—'}</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">Ortam</div>
            <div className="text-slate-100 capitalize">{status?.environment ?? '—'}</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">Veritabanı</div>
            <div className="text-slate-100">{status?.database ?? '—'}</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">Stack</div>
            <div className="text-slate-100">FastAPI · React 18 + Vite</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ApiKeyRow({ name, provider, ok }: { name: string; provider: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg">
      <div>
        <div className="font-mono text-xs text-slate-300">{name}</div>
        <div className="text-xs text-slate-500">{provider}</div>
      </div>
      {ok === undefined ? (
        <span className="text-xs text-slate-500">—</span>
      ) : ok ? (
        <CheckCircle2 className="w-4 h-4 text-green-400" />
      ) : (
        <XCircle className="w-4 h-4 text-red-400" />
      )}
    </div>
  )
}

function IntegrationCard({ name, data }: { name: string; data?: IntegrationStatus }) {
  const status = data?.status ?? 'planned'
  const meta = {
    active: { label: '● Aktif', cls: 'text-green-400', Icon: CheckCircle2 },
    needs_config: { label: '○ Yapılandır', cls: 'text-yellow-400', Icon: Clock },
    planned: { label: '○ Planlı', cls: 'text-slate-500', Icon: Clock },
  }[status]

  return (
    <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg">
      <span className="text-sm text-slate-300">{name}</span>
      <span className={`text-xs flex items-center gap-1 ${meta.cls}`}>
        <meta.Icon className="w-3.5 h-3.5" />
        {meta.label}
      </span>
    </div>
  )
}
