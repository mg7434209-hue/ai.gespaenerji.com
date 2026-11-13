import { NavLink, useLocation } from 'react-router-dom'
import { LogOut, PanelLeftClose, PanelLeftOpen, X } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '@/lib/auth'
import { NAV_GROUPS, SETTINGS_ITEM, isActive, type NavItem } from './navConfig'

interface Props {
  collapsed: boolean
  onToggleCollapsed: () => void
  mobileOpen: boolean
  onCloseMobile: () => void
  badges: { inbox: number }
}

export function Sidebar({ collapsed, onToggleCollapsed, mobileOpen, onCloseMobile, badges }: Props) {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const name = user?.full_name?.trim() || 'Kullanıcı'
  // Daraltma yalnız masaüstünde (md+); çekmece her zaman tam genişliktir.
  const hide = collapsed && 'md:hidden'

  return (
    <>
      <div
        className={clsx('fixed inset-0 z-40 bg-black/60 md:hidden transition-opacity',
          mobileOpen ? 'opacity-100' : 'opacity-0 pointer-events-none')}
        onClick={onCloseMobile}
        aria-hidden="true"
      />
      <aside
        id="app-nav"
        aria-label="Ana menü"
        className={clsx(
          'bg-os-nav border-r border-os-line flex flex-col h-dvh w-[248px] shrink-0',
          'fixed inset-y-0 left-0 z-50 transition-transform duration-200 md:transition-[width]',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          'md:sticky md:top-0 md:translate-x-0 md:z-auto',
          collapsed ? 'md:w-[76px]' : 'md:w-[248px]',
        )}
      >
        {/* Logo + daralt */}
        <div className={clsx('h-16 flex items-center gap-2 px-4 border-b border-os-line', collapsed && 'md:justify-center md:px-0')}>
          <div className={clsx('min-w-0 flex-1', hide)}>
            <div className="font-bold text-os-text leading-tight">Gespa OS</div>
            <div className="text-xs text-os-muted">v0.5.0</div>
          </div>
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="hidden md:grid place-items-center w-11 h-11 rounded-[10px] text-os-text2 hover:bg-os-raised"
            aria-label={collapsed ? 'Menüyü genişlet' : 'Menüyü daralt'}
            title={collapsed ? 'Menüyü genişlet' : 'Menüyü daralt'}
            aria-expanded={!collapsed}
          >
            {collapsed ? <PanelLeftOpen className="w-5 h-5" /> : <PanelLeftClose className="w-5 h-5" />}
          </button>
          <button
            type="button"
            onClick={onCloseMobile}
            className="md:hidden grid place-items-center w-11 h-11 rounded-[10px] text-os-text2 hover:bg-os-raised"
            aria-label="Menüyü kapat"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Gruplar */}
        <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
          {NAV_GROUPS.map((g) => (
            <div key={g.title}>
              <div className={clsx('px-3 mb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-os-faint', hide)}>
                {g.title}
              </div>
              {collapsed && <div className="hidden md:block mx-3 mb-1.5 border-t border-os-line" aria-hidden="true" />}
              <ul className="space-y-0.5">
                {g.items.map((item) => (
                  <li key={item.to}>
                    <Item item={item} active={isActive(item, pathname)} collapsed={collapsed}
                      count={item.badge ? badges[item.badge] : 0} onNavigate={onCloseMobile} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Alt: Ayarlar + kullanıcı */}
        <div className="border-t border-os-line px-3 py-3 space-y-1">
          <Item item={SETTINGS_ITEM} active={isActive(SETTINGS_ITEM, pathname)} collapsed={collapsed} count={0} onNavigate={onCloseMobile} />
          <div className={clsx('flex items-center gap-3 px-2 min-h-[52px]', collapsed && 'md:flex-col md:gap-1 md:py-2')}>
            <div className="w-9 h-9 shrink-0 rounded-full bg-os-raised text-os-accent grid place-items-center font-semibold" aria-hidden="true">
              {name.charAt(0).toLocaleUpperCase('tr-TR')}
            </div>
            <div className={clsx('min-w-0 flex-1 text-sm font-medium text-os-text truncate', hide)}>{name}</div>
            <button
              type="button"
              onClick={() => logout()}
              className="grid place-items-center w-11 h-11 rounded-[10px] text-os-muted hover:text-os-urgentfg hover:bg-os-raised"
              aria-label="Çıkış yap"
              title="Çıkış yap"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}

function Item({ item, active, collapsed, count, onNavigate }: {
  item: NavItem; active: boolean; collapsed: boolean; count: number; onNavigate: () => void
}) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      end={item.exact}
      onClick={onNavigate}
      aria-label={collapsed ? item.label : undefined}
      aria-current={active ? 'page' : undefined}
      title={item.label}
      className={clsx(
        'relative flex items-center gap-3 min-h-[44px] px-3 rounded-[10px] text-[15px] transition-colors',
        collapsed && 'md:justify-center md:px-0',
        active ? 'bg-os-raised text-os-accent font-semibold' : 'text-os-text2 font-medium hover:bg-os-raised/60',
      )}
    >
      <Icon className="w-5 h-5 shrink-0" strokeWidth={1.75} />
      <span className={clsx('flex-1 truncate', collapsed && 'md:hidden')}>{item.label}</span>
      {count > 0 && (
        <span
          className={clsx(
            'min-w-[22px] h-[22px] px-1.5 rounded-full bg-os-accent text-os-onaccent text-xs font-bold grid place-items-center',
            collapsed && 'md:absolute md:top-1 md:right-2 md:min-w-[18px] md:h-[18px] md:text-[10px] md:px-1',
          )}
          aria-label={`${count} okunmamış`}
        >
          {count > 99 ? '99+' : count}
        </span>
      )}
    </NavLink>
  )
}
