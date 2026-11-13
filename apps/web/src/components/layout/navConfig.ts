import {
  LayoutDashboard, MessageSquare, Bot, Globe, ShoppingBag, ClipboardList,
  Users, Map, Briefcase, Building2, Scale, Settings,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  exact?: boolean
  /** Etiketin yanında gösterilecek sayaç anahtarı (AppShell sağlar) */
  badge?: 'inbox'
}
export interface NavGroup { title: string; items: NavItem[] }

// Menü ve üst çubuk başlığı için TEK kaynak. Route adresleri App.tsx'tedir ve değişmez.
export const NAV_GROUPS: NavGroup[] = [
  { title: 'Bugün', items: [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  ] },
  { title: 'İletişim', items: [
    { to: '/inbox', label: 'Inbox', icon: MessageSquare, badge: 'inbox' },
    { to: '/jarvis', label: 'JARVIS Sohbet', icon: Bot },
  ] },
  { title: 'Siteler', items: [
    { to: '/siteler', label: 'Siteler', icon: Globe },
    { to: '/siparisler', label: 'Siparişler', icon: ShoppingBag },
    { to: '/basvurular', label: 'Başvurular', icon: ClipboardList },
  ] },
  { title: 'Satış ve iş', items: [
    { to: '/leads', label: 'Lead Yönetimi', icon: Users },
    { to: '/roadmap', label: 'Yol Haritası', icon: Map },
    { to: '/workspaces', label: 'Workspaces', icon: Briefcase },
  ] },
  { title: 'Ofisler', items: [
    { to: '/agents', label: 'Dijital Ofis', icon: Building2 },
    { to: '/hukuk', label: 'Hukuk Ofisi', icon: Scale },
  ] },
]

export const SETTINGS_ITEM: NavItem = { to: '/settings', label: 'Ayarlar', icon: Settings }

const ALL = [...NAV_GROUPS.flatMap((g) => g.items), SETTINGS_ITEM]

export function isActive(item: NavItem, pathname: string) {
  return item.exact ? pathname === item.to : pathname === item.to || pathname.startsWith(item.to + '/')
}

/** Üst çubuktaki sayfa başlığı: menüdeki etiket; alt sayfalar bağlı oldukları maddeyi kullanır. */
export function titleFor(pathname: string) {
  return ALL.find((i) => isActive(i, pathname))?.label ?? 'Gespa OS'
}
