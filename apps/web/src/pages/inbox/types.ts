export type AiMode = 'auto_reply' | 'auto_draft' | 'manual' | 'paused'

export interface Conversation {
  id: number
  phone: string
  contact_name?: string | null
  profile_name?: string | null
  last_message_at: string
  last_message_preview?: string | null
  unread_count: number
  ai_mode: AiMode | string
  is_vip: boolean
  needs_attention: boolean
  tags?: string[] | null
}

export interface Message {
  id: number
  direction: 'inbound' | 'outbound'
  content_type: string
  content: string
  media_url?: string | null
  ai_intent?: string | null
  ai_confidence?: number | null
  ai_draft?: string | null
  ai_auto_sent: boolean
  status: string
  sent_by: string
  created_at: string
}

/** Arayüzde üç yanıt modu gösterilir; `paused` (AI kapalı) Manuel gibi görünür. */
export type UiMode = 'auto_reply' | 'auto_draft' | 'manual'
export const toUiMode = (m: string): UiMode => (m === 'auto_reply' || m === 'auto_draft' ? m : 'manual')

export const MODE_LABEL: Record<UiMode, string> = {
  auto_reply: 'Tam Otomatik',
  auto_draft: 'Taslak',
  manual: 'Manuel',
}

export const displayName = (c: Pick<Conversation, 'contact_name' | 'profile_name' | 'phone'>) =>
  c.contact_name?.trim() || c.profile_name?.trim() || c.phone

/** Sunucu saatsiz UTC yazar (datetime.utcnow); saat dilimi yoksa UTC kabul edilir. */
export function parseTime(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
}
const TZ = 'Europe/Istanbul'
export const fmtClock = (iso: string) =>
  parseTime(iso).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', timeZone: TZ })

/** Listedeki kısa zaman: bugün saat, dün "Dün", daha eskisi gün.ay */
export function fmtListTime(iso: string): string {
  const d = parseTime(iso)
  const day = (x: Date) => x.toLocaleDateString('sv-SE', { timeZone: TZ })
  const today = new Date()
  if (day(d) === day(today)) return fmtClock(iso)
  if (day(d) === day(new Date(today.getTime() - 864e5))) return 'Dün'
  return d.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', timeZone: TZ })
}

export const norm = (s: string) => s.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[̀-ͯ]/g, '')
