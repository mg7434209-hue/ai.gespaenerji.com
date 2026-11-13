import { Menu, Search, X } from 'lucide-react'
import { titleFor } from './navConfig'

interface Props {
  pathname: string
  onOpenMenu: () => void
  /** Arama yalnız onu kullanan sayfada (Inbox) görünür; genel arama ucu yok. */
  search?: { value: string; onChange: (v: string) => void; placeholder: string }
}

export function TopBar({ pathname, onOpenMenu, search }: Props) {
  return (
    <header className="sticky top-0 z-30 h-16 flex items-center gap-3 px-4 md:px-6 bg-os-nav border-b border-os-line">
      <button
        type="button"
        onClick={onOpenMenu}
        className="md:hidden grid place-items-center w-11 h-11 -ml-2 rounded-[10px] text-os-text2 hover:bg-os-raised"
        aria-label="Menüyü aç"
        aria-controls="app-nav"
      >
        <Menu className="w-5 h-5" />
      </button>
      <h1 className="text-[22px] font-bold text-os-text truncate">{titleFor(pathname)}</h1>
      <div className="flex-1" />
      {search && (
        <div className="relative w-full max-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-os-muted pointer-events-none" aria-hidden="true" />
          <input
            type="search"
            value={search.value}
            onChange={(e) => search.onChange(e.target.value)}
            placeholder={search.placeholder}
            aria-label={search.placeholder}
            className="w-full h-11 pl-9 pr-9 rounded-[10px] bg-os-panel border border-os-line text-[15px] text-os-text placeholder:text-os-muted outline-none focus:border-os-accent [&::-webkit-search-cancel-button]:hidden"
          />
          {search.value && (
            <button
              type="button"
              onClick={() => search.onChange('')}
              className="absolute right-1 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 rounded-[10px] text-os-muted hover:text-os-text"
              aria-label="Aramayı temizle"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}
    </header>
  )
}
