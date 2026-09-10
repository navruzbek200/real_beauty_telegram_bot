import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { hasPermission, isSuperUser, useSessionStore } from '@/entities/session'
import { AppShell } from '@/widgets/app-shell'

interface ProtectedRouteProps {
  children: ReactNode
  permission?: string
  superuserOnly?: boolean
}

export function ProtectedRoute({ children, permission, superuserOnly }: ProtectedRouteProps) {
  const user = useSessionStore((s) => s.user)
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  if (superuserOnly && !isSuperUser(user)) {
    return <Navigate to="/" replace />
  }
  if (permission && !hasPermission(user, permission)) {
    return <Navigate to="/" replace />
  }

  return <AppShell>{children}</AppShell>
}
