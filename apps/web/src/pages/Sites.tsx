import { Link } from 'react-router-dom'
import { ClipboardList, ShoppingBag } from 'lucide-react'
import { SiteCards } from '@/components/SiteCards'
import { PendingActions } from '@/components/PendingActions'

/** Tüm siteler tek ekranda: mağazalar, başvuru siteleri, içerik sitesi. */
export function Sites() {
  return (
    <div className="p-4 sm:p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Siteler</h1>
          <p className="text-sm text-slate-400 mt-1">
            Beş sitenin canlı durumu. Veriler sitelerden salt okunur gelir; müşteri adı ve telefonu burada tutulmaz.
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/siparisler" className="btn-ghost text-sm flex items-center gap-2"><ShoppingBag className="w-4 h-4" /> Siparişler</Link>
          <Link to="/basvurular" className="btn-ghost text-sm flex items-center gap-2"><ClipboardList className="w-4 h-4" /> Başvurular</Link>
        </div>
      </div>
      <PendingActions />
      <SiteCards title="Durum" />
    </div>
  )
}
