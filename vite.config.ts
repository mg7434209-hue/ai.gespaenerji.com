import { FormEvent, useEffect, useState } from 'react'
import { Plus, Phone, MapPin, X, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { Lead, Workspace } from '@/types'
import clsx from 'clsx'

const STATUS_LABELS: Record<string, string> = {
  new: 'Yeni',
  contacted: 'Arandı',
  offered: 'Teklif',
  won: 'Kazanıldı',
  lost: 'Kaybedildi',
}

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  contacted: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  offered: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  won: 'bg-green-500/10 text-green-400 border-green-500/20',
  lost: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export function Leads() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [filterWorkspace, setFilterWorkspace] = useState<string>('superonline')
  const [filterStatus, setFilterStatus] = useState<string>('')

  async function load() {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (filterWorkspace) params.workspace = filterWorkspace
      if (filterStatus) params.status = filterStatus

      const [leadsRes, wsRes] = await Promise.all([
        api.get<Lead[]>('/leads', { params }),
        workspaces.length ? Promise.resolve({ data: workspaces }) : api.get<Workspace[]>('/workspaces'),
      ])
      setLeads(leadsRes.data)
      setWorkspaces(wsRes.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterWorkspace, filterStatus])

  async function updateStatus(leadId: number, status: string) {
    await api.patch(`/leads/${leadId}`, { status })
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Lead Yönetimi</h1>
          <p className="text-slate-400 mt-1">Potansiyel müşterileri takip et, satışa dönüştür.</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Yeni Lead
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterWorkspace}
          onChange={(e) => setFilterWorkspace(e.target.value)}
          className="input max-w-xs"
        >
          <option value="">Tüm Workspaces</option>
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.slug}>{ws.name}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="input max-w-xs"
        >
          <option value="">Tüm Durumlar</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {/* Leads list */}
      {loading ? (
        <div className="text-slate-500">Yükleniyor...</div>
      ) : leads.length === 0 ? (
        <div className="card text-center py-12">
          <div className="text-slate-400 mb-2">Henüz lead yok</div>
          <button onClick={() => setShowModal(true)} className="text-brand-400 text-sm hover:underline">
            İlk lead'i ekle
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {leads.map((lead) => (
            <div key={lead.id} className="card hover:border-slate-700 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="font-semibold text-slate-100">{lead.full_name}</div>
                    <span
                      className={clsx(
                        'text-xs px-2 py-0.5 rounded-full border',
                        STATUS_COLORS[lead.status],
                      )}
                    >
                      {STATUS_LABELS[lead.status]}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm text-slate-400">
                    <a href={`tel:${lead.phone}`} className="flex items-center gap-1.5 hover:text-brand-400">
                      <Phone className="w-3.5 h-3.5" />
                      {lead.phone}
                    </a>
                    {lead.city && (
                      <span className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5" />
                        {lead.city}
                      </span>
                    )}
                    {lead.package_interest && (
                      <span className="text-brand-400">{lead.package_interest}</span>
                    )}
                  </div>
                  {lead.notes && (
                    <div className="text-sm text-slate-500 mt-2 line-clamp-2">{lead.notes}</div>
                  )}
                </div>
                <select
                  value={lead.status}
                  onChange={(e) => updateStatus(lead.id, e.target.value)}
                  className="input text-xs py-1.5 max-w-[140px]"
                >
                  {Object.entries(STATUS_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <LeadModal
          workspaces={workspaces}
          defaultWorkspace={filterWorkspace}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            load()
          }}
        />
      )}
    </div>
  )
}

function LeadModal({
  workspaces,
  defaultWorkspace,
  onClose,
  onSuccess,
}: {
  workspaces: Workspace[]
  defaultWorkspace: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [form, setForm] = useState({
    workspace_slug: defaultWorkspace || 'superonline',
    full_name: '',
    phone: '',
    email: '',
    city: '',
    package_interest: '',
    notes: '',
    source: 'web_form',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.post('/leads', form)
      onSuccess()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kayıt başarısız')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="card max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-100">Yeni Lead</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Workspace *</label>
            <select
              required
              value={form.workspace_slug}
              onChange={(e) => setForm({ ...form, workspace_slug: e.target.value })}
              className="input"
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.slug}>{ws.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Ad Soyad *</label>
              <input
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="label">Telefon *</label>
              <input
                required
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="input"
                placeholder="05xx xxx xx xx"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="label">Şehir</label>
              <input
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
                className="input"
                placeholder="Antalya"
              />
            </div>
          </div>

          <div>
            <label className="label">İlgilendiği Paket</label>
            <input
              value={form.package_interest}
              onChange={(e) => setForm({ ...form, package_interest: e.target.value })}
              className="input"
              placeholder="100 Mbps Fiber"
            />
          </div>

          <div>
            <label className="label">Notlar</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="input min-h-[80px]"
            />
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">
              İptal
            </button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2">
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {saving ? 'Kaydediliyor...' : 'Kaydet'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
