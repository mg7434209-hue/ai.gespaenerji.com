import { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const { user, initialized, checkAuth } = useAuth()

  useEffect(() => {
    if (!initialized) checkAuth()
  }, [initialized, checkAuth])

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="text-slate-400 text-sm">Yükleniyor...</div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" state={{ returnTo: location.pathname }} replace />

  return <>{children}</>
}
