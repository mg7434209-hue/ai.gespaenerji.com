import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Menu, Sparkles } from 'lucide-react'
import { Sidebar } from './Sidebar'

export function Layout() {
  // Telefonda (lg altı) menü çekmecedir; masaüstünde her zaman açık sütun
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  // Sayfa değişince çekmece kapanır
  useEffect(() => setMenuOpen(false), [location.pathname])

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMenuOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <main className="flex-1 min-w-0 overflow-x-hidden">
        {/* Mobil üst çubuk */}
        <div className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 h-14 bg-slate-950/90 backdrop-blur border-b border-slate-800">
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 -ml-2 rounded-lg text-slate-300 hover:bg-slate-800/60"
            aria-label="Menüyü aç"
            aria-expanded={menuOpen}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-slate-950" />
          </div>
          <span className="font-bold text-slate-100">Gespa OS</span>
        </div>
        <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
