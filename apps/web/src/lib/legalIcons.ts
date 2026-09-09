import {
  Gavel,
  FileText,
  BookOpen,
  CalendarClock,
  Target,
  ShieldAlert,
  ShoppingBag,
  Landmark,
  Banknote,
  FileSignature,
  Building2,
  HardHat,
  ShieldCheck,
  Copyright,
  HeartHandshake,
  ScrollText,
  Home,
  CarFront,
  TrafficCone,
  Receipt,
  Building,
  Sun,
  Scale,
} from 'lucide-react'

/** legal_agents.py'daki icon adları → lucide bileşenleri. */
export const LEGAL_ICONS: Record<string, React.ElementType> = {
  gavel: Gavel,
  'file-text': FileText,
  'book-open': BookOpen,
  'calendar-clock': CalendarClock,
  target: Target,
  'shield-alert': ShieldAlert,
  'shopping-bag': ShoppingBag,
  landmark: Landmark,
  banknote: Banknote,
  'file-signature': FileSignature,
  'building-2': Building2,
  'hard-hat': HardHat,
  'shield-check': ShieldCheck,
  copyright: Copyright,
  'heart-handshake': HeartHandshake,
  'scroll-text': ScrollText,
  home: Home,
  'car-front': CarFront,
  'traffic-cone': TrafficCone,
  receipt: Receipt,
  building: Building,
  sun: Sun,
}

export function legalIcon(name?: string | null): React.ElementType {
  return LEGAL_ICONS[name || ''] || Scale
}

/** Danışma modu → arayüz etiketi ve kısa açıklaması. */
export const MODE_LABELS: Record<string, { label: string; hint: string }> = {
  danisma: { label: 'Danışma', hint: 'Durumu değerlendir, yol haritası çıkar' },
  dilekce: { label: 'Dilekçe', hint: 'Dilekçe / ihtarname taslağı yaz' },
  inceleme: { label: 'Belge İncele', hint: 'Sözleşme veya belgedeki riskleri bul' },
  arastirma: { label: 'Mevzuat', hint: 'İlgili kanun ve maddeleri derle' },
}
