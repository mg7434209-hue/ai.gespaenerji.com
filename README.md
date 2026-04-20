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
