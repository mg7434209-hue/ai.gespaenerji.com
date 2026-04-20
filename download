import { useAuth } from '@/lib/auth'
import { Key, Globe, Database, Shield, CheckCircle2 } from 'lucide-react'

export function Settings() {
  const { user } = useAuth()

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
          <ApiKeyRow name="ANTHROPIC_API_KEY" provider="Claude Sonnet 4" />
          <ApiKeyRow name="OPENAI_API_KEY" provider="GPT-4o-mini" />
          <ApiKeyRow name="GEMINI_API_KEY" provider="Gemini Vision" />
        </div>
        <div className="mt-4 p-3 bg-slate-800/50 rounded-lg text-xs text-slate-400">
          💡 API anahtarlarını değiştirmek için Railway → goksoylar-os → Variables sekmesini kullan.
        </div>
      </div>

      {/* Integrations — planned */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-slate-100">Dış Entegrasyonlar</div>
            <div className="text-sm text-slate-400">Faz 2'de gelecek</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <IntegrationCard name="WhatsApp Business API" status="planned" />
          <IntegrationCard name="Gmail (MCP)" status="planned" />
          <IntegrationCard name="Vapi (Sesli ajan)" status="planned" />
          <IntegrationCard name="n8n Workflows" status="planned" />
          <IntegrationCard name="SolarAnaliz API" status="planned" />
          <IntegrationCard name="TrafikRehber API" status="planned" />
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
            <div className="text-slate-100">v0.1.0 (Faz 1 Hafta 1)</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">Veritabanı</div>
            <div className="text-slate-100">PostgreSQL (Railway)</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">Backend</div>
            <div className="text-slate-100">FastAPI + SQLAlchemy</div>
          </div>
          <div>
            <div className="text-slate-400 mb-1">Frontend</div>
            <div className="text-slate-100">React 18 + Vite</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ApiKeyRow({ name, provider }: { name: string; provider: string }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg">
      <div>
        <div className="font-mono text-xs text-slate-300">{name}</div>
        <div className="text-xs text-slate-500">{provider}</div>
      </div>
      <CheckCircle2 className="w-4 h-4 text-green-400" />
    </div>
  )
}

function IntegrationCard({ name, status }: { name: string; status: 'active' | 'planned' }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg">
      <span className="text-sm text-slate-300">{name}</span>
      <span className={`text-xs ${status === 'active' ? 'text-green-400' : 'text-slate-500'}`}>
        {status === 'active' ? '● Aktif' : '○ Planlı'}
      </span>
    </div>
  )
}
