import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import Skeleton from './ui/Skeleton'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()
  const { pathname } = useLocation()
  const { t } = useTranslation()
  if (loading) return <div role="status" aria-label={t('common.loading')}><Skeleton className="h-10 w-full" /></div>
  if (!user) return <Navigate to="/login" replace />
  if (!user.has_company && pathname !== '/onboarding' && !(user.is_admin && (pathname.startsWith('/admin') || pathname === '/demo'))) return <Navigate to="/onboarding" replace />
  return <Outlet />
}
