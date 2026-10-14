import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './auth/store'
import { ProtectedRoute } from './components/ProtectedRoute'
import { VersionGate } from './components/VersionGate'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { StartPage } from './pages/StartPage'

export function App() {
  const hydrated = useAuthStore((state) => state.hydrated)
  const bootstrap = useAuthStore((state) => state.bootstrap)
  useEffect(() => { void bootstrap() }, [bootstrap])
  if (!hydrated) return <main className="shell"><section className="card"><p>Загрузка…</p></section></main>

  return <VersionGate><Routes>
    <Route path="/start" element={<StartPage />} />
    <Route path="/auth/login" element={<LoginPage />} />
    <Route path="/auth/register" element={<RegisterPage />} />
    <Route path="/app" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
    <Route path="*" element={<Navigate to="/start" replace />} />
  </Routes></VersionGate>
}
