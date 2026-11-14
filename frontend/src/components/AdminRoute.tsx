import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function AdminRoute() {
  const { user } = useAuth()
  return user?.is_admin ? <Outlet /> : <Navigate to="/" replace />
}
