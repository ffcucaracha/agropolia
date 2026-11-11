import type { PropsWithChildren } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../auth/store'

export function ProtectedRoute({ children }: PropsWithChildren) {
  const accessToken = useAuthStore((state) => state.accessToken)
  return accessToken ? children : <Navigate to="/start" replace />
}
