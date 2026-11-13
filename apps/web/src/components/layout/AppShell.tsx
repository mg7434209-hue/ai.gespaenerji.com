import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { api } from '@/lib/api'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { ShellSearchContext } from './shellContext'

const COLLAPSE_KEY = 'gespa.nav.collapsed'

function readCollapsed() {
  try { return localStorage.getItem(COLLAPSE_KEY) === '1' } catch { return false }
}

/** Menü + üst çubuk + sayfa içeriği. /jarvis tam ekran sesli ekranı kabuğun dışındadır (App.tsx). */
export function AppShell() {
  const { pathname } = useLocation()
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [unread, setUnread] = useState(0)
  const isInbox = pathname === '/inbox' || pathname.startsWith('/inbox/')

  const toggleCollapsed = useCallback(() => {
    setCollapsed((c) => {
      try { localStorage.setItem(COLLAPSE_KEY, c ? '0' : '1') } catch { /* gizli sekme */ }
      return !c
    })
  }, [])

  // Sayfa değişince çekmece kapanır, arama temizlenir
  useEffect(() => { setMobileOpen(false); setSearch('') }, [pathname])

  // Çekmece açıkken Esc kapatır ve arka plan kaymaz
  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMobileOpen(false)
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
  }, [mobileOpen])

  // Inbox rozeti: okunmamış konuşma sayısı (GET /whatsapp/stats), 30 sn'de bir
  useEffect(() => {
    let alive = true
    const load = () => api.get<{ unread_conversations: number }>('/whatsapp/stats')
      .then(({ data }) => alive && setUnread(data.unread_conversations || 0))
      .catch(() => { /* rozet sessizce gizli kalır */ })
    load()
    const t = setInterval(load, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [pathname === '/inbox'])  // Inbox'a girip çıkınca hemen tazele

  return (
    <div className="shell flex min-h-dvh bg-os-bg text-os-text">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        badges={{ inbox: unread }}
      />
      <div className="flex-1 min-w-0 flex flex-col">
        <TopBar
          pathname={pathname}
          onOpenMenu={() => setMobileOpen(true)}
          search={isInbox ? { value: search, onChange: setSearch, placeholder: 'Konuşma ara…' } : undefined}
        />
        <ShellSearchContext.Provider value={search}>
          {isInbox ? (
            // Inbox kenardan kenara; yüksekliği üst çubuğu düşerek kendisi doldurur
            <main className="flex-1 min-h-0 h-[calc(100dvh-4rem)]">
              <Outlet />
            </main>
          ) : (
            <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full">
              <Outlet />
            </main>
          )}
        </ShellSearchContext.Provider>
      </div>
    </div>
  )
}
