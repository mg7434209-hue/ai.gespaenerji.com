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
  document_ids: number[]
  triage: LegalTriage | null
  message_count: number
  review: LegalReview | null
  created_at: string
}

export interface LegalStats {
  agents_total: number
  agents_active: number
  consultations: number
  drafts: number
  open_matters: number
  documents: number
  open_deadlines: number
  overdue_deadlines: number
  templates: number
  ai_configured: boolean
}

export interface LegalDocument {
  id: number
  filename: string
  kind: 'pdf' | 'image' | 'text'
  media_type: string
  size: number
  pages: number | null
  char_count: number
  preview: string
  notes: string[]
  matter_id: number | null
  created_at: string
}

/** Belge triyajı — sistem belgeyi okuyup hangi ajana gideceğine karar verir. */
export interface LegalTriage {
  belge_turu: string
  ozet: string
  taraflar: string[]
  tarihler: { ne?: string; tarih?: string }[]
  tutarlar: string[]
  referans: string
  sure_uyarisi: string
  agent_slug: string
  alternatif_ajan: string | null
  onerilen_mod: LegalMode
  gerekce: string
  aciliyet: 'dusuk' | 'orta' | 'yuksek'
  guven: number
}

export interface LegalAnalyzeResponse {
  triage: LegalTriage
  routed_to: { slug: string; name: string; title: string; icon: string | null; color: string | null }
  auto_routed: boolean
  consultation: LegalConsultation
  documents: LegalDocument[]
}


// ── Dosya, süre, sohbet, denetim, kurul ───────────────────────

export interface LegalMatter {
  id: number
  title: string
  area: string | null
  self_party: string | null
  counterparty: string | null
  role: string | null
  court: string | null
  reference: string | null
  stage: string
  status: string
  amount: string | null
  next_hearing: string | null
  summary: string | null
  notes: string | null
  consultation_count: number
  document_count: number
  open_deadlines: number
  next_deadline: string | null
  created_at: string
  updated_at: string
}

export interface LegalDeadline {
  id: number
  title: string
  due_date: string
  days_left: number
  matter_id: number | null
  matter_title: string | null
  consultation_id: number | null
  basis: string | null
  start_date: string | null
  critical: boolean
  status: 'open' | 'done' | 'missed'
  notes: string | null
  source: string
  created_at: string
}

export interface LegalMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  document_ids: number[]
  created_at: string
}

export interface LegalReviewFinding {
  tur?: string
  agirlik?: 'dusuk' | 'orta' | 'yuksek'
  alan?: string
  sorun?: string
  duzeltme?: string
}

export interface LegalReview {
  id: number
  consultation_id: number
  verdict: 'temiz' | 'duzeltme_gerekli' | 'riskli' | 'hata' | string
  score: number
  findings: LegalReviewFinding[]
  summary: string | null
  model: string | null
  error: string | null
  created_at: string
}

export interface LegalTemplate {
  id: string
  name: string
  agent: string
  category: string
  description: string
  fields: string[]
}

export interface LegalBoardOpinion {
  slug: string
  name: string
  title: string
  icon: string | null
  color: string | null
  ok: boolean
  error: string | null
  result: LegalResult | null
}

export interface LegalBoardResponse {
  consultation: LegalConsultation
  opinions: LegalBoardOpinion[]
}

export interface LegalAgenda {
  deadlines: LegalDeadline[]
  overdue: number
  critical: number
  hearings: {
    matter_id: number
    title: string
    court: string | null
    date: string
    days_left: number
  }[]
}
