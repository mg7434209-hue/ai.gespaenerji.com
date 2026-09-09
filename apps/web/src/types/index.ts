export interface User {
  id: number
  email: string
  full_name?: string | null
}

export interface Workspace {
  id: number
  slug: string
  name: string
  description: string | null
  icon: string | null
  color: string | null
  is_active: boolean
}

export interface Lead {
  id: number
  workspace_id: number
  full_name: string
  phone: string
  email: string | null
  address: string | null
  city: string | null
  status: 'new' | 'contacted' | 'offered' | 'won' | 'lost'
  source: string | null
  notes: string | null
  package_interest: string | null
  estimated_value: number | null
  created_at: string
  updated_at: string
  last_contact_at: string | null
}

export interface Agent {
  id: number
  slug: string
  name: string
  department: string
  description: string | null
  icon: string | null
  color: string | null
  model: string
  is_active: boolean
}

export interface WorkspaceStats {
  workspace: string
  leads: {
    total: number
    new: number
    contacted: number
    offered: number
    won: number
    lost: number
    conversion_rate: number
  }
}

// ── Hukuk Ofisi (avukat ajan serisi) ──────────────────────────

export interface LegalAgent {
  id: number
  slug: string
  name: string
  title: string
  department: string
  description: string | null
  icon: string | null
  color: string | null
  expertise: string[]
  documents: string[]
  model: string
  is_active: boolean
  sort_order: number
  consult_count: number
}

export type LegalMode = 'danisma' | 'dilekce' | 'inceleme' | 'arastirma'

export interface LegalMeta {
  modes: { key: LegalMode; label: string }[]
  departments: string[]
  disclaimer: string
  ai_configured: boolean
  model: string
}

export interface LegalResult {
  ozet: string
  degerlendirme: string
  mevzuat: { kanun?: string; madde?: string; aciklama?: string; teyit?: boolean }[]
  adimlar: { sira?: number; baslik?: string; aciklama?: string; kim?: string }[]
  sureler: { is?: string; sure?: string; baslangic?: string; kritik?: boolean }[]
  riskler: { baslik?: string; seviye?: 'dusuk' | 'orta' | 'yuksek'; aciklama?: string }[]
  maliyet: string
  belge: { tur?: string; merci?: string; icerik?: string } | null
  eksik_bilgiler: string[]
  sonraki_ajan: string | null
  avukat_gerekli: boolean
  guven: number
  uyari: string
}

export interface LegalConsultation {
  id: number
  agent_slug: string
  agent_name: string
  mode: LegalMode
  subject: string | null
  question: string
  context: string | null
  doc_type: string | null
  result: LegalResult | null
  summary: string | null
  draft: string | null
  confidence: number
  needs_lawyer: boolean
  status: 'done' | 'error'
  error: string | null
  model: string | null
  matter_id: number | null
  created_at: string
}

export interface LegalStats {
  agents_total: number
  agents_active: number
  consultations: number
  drafts: number
  open_matters: number
  ai_configured: boolean
}
