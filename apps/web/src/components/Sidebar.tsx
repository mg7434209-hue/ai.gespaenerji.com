import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Briefcase,
  Users,
  Bot,
  Settings,
  LogOut,
  Sparkles,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '@/lib/auth'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/workspaces', label: 'Workspaces', icon: Briefcase },
  { to: '/leads', label: 'Lead Yönetimi', icon: Users },
  { to: '/agents', label: 'AI Ajanlar', icon: Bot },
  { to: '/settings', label: 'Ayarlar', icon: Settings },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <aside className="w-64 bg-slate-900/80 border-r border-slate-800 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <div className="font-bold text-slate-100">Gespa OS</div>
            <div className="text-xs text-slate-400">v0.1.0</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = item.exact
            ? location.pathname === item.to
            : location.pathname.startsWith(item.to)

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-500/10 text-brand-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50',
              )}
            >
              <Icon className="w-5 h-5 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-slate-800">
        <div className="px-3 py-2 mb-2">
          <div className="text-sm font-medium text-slate-100 truncate">
            {user?.full_name || user?.email}
          </div>
          <div className="text-xs text-slate-500 truncate">{user?.email}</div>
        </div>
        <button
          onClick={() => logout()}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/5 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>Çıkış Yap</span>
        </button>
      </div>
    </aside>
  )
}
