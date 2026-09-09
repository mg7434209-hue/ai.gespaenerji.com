import { NavLink } from 'react-router-dom'
import { Scale, ScanSearch, FolderOpen, CalendarClock, FileStack, Users2 } from 'lucide-react'
import clsx from 'clsx'

const ITEMS = [
  { to: '/hukuk', label: 'Kadro', icon: Scale, end: true },
  { to: '/hukuk/belge', label: 'Belge Analizi', icon: ScanSearch },
  { to: '/hukuk/dosyalar', label: 'Dosyalar', icon: FolderOpen },
  { to: '/hukuk/sureler', label: 'Süreler', icon: CalendarClock },
  { to: '/hukuk/sablonlar', label: 'Şablonlar', icon: FileStack },
  { to: '/hukuk/kurul', label: 'Kurul', icon: Users2 },
]

/** Hukuk Ofisi alt gezintisi — tüm hukuk sayfalarının başında durur. */
export function LegalNav() {
  return (
    <nav className="flex flex-wrap gap-1 bg-slate-900/60 border border-slate-800 rounded-2xl p-1.5">
      {ITEMS.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              clsx(
                'inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-500/10 text-brand-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50',
              )
            }
          >
            <Icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        )
      })}
    </nav>
  )
}
