import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './auth/store'
import { ProtectedRoute } from './components/ProtectedRoute'
import { VersionGate } from './components/VersionGate'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { StartPage } from './pages/StartPage'
import { WorkspaceLayout } from './workspace/WorkspaceLayout'
import { FieldDetailPage, FieldFormPage, FieldsPage } from './workspace/FieldsPages'
import { ObservationDetailPage, ObservationFormPage, ObservationsPage } from './workspace/ObservationsPages'
import { TaskDetailPage, TaskFormPage, TasksPage, WorkLogPage } from './workspace/TasksPages'
import { TodayPage, NotificationsPage, SettingsPage } from './workspace/TodayAndNotifications'

export function App() {
  const hydrated = useAuthStore((state) => state.hydrated)
  const bootstrap = useAuthStore((state) => state.bootstrap)
  useEffect(() => { void bootstrap() }, [bootstrap])
  if (!hydrated) return <main className="shell"><section className="card"><p>Загрузка…</p></section></main>

  return <VersionGate><Routes>
    <Route path="/start" element={<StartPage />} />
    <Route path="/auth/login" element={<LoginPage />} />
    <Route path="/auth/register" element={<RegisterPage />} />
    <Route path="/app" element={<ProtectedRoute><WorkspaceLayout /></ProtectedRoute>}>
      <Route index element={<TodayPage />} />
      <Route path="fields" element={<FieldsPage />} />
      <Route path="fields/new" element={<FieldFormPage />} />
      <Route path="fields/:id/edit" element={<FieldFormPage />} />
      <Route path="fields/:id" element={<FieldDetailPage />} />
      <Route path="observations" element={<ObservationsPage />} />
      <Route path="observations/new" element={<ObservationFormPage />} />
      <Route path="observations/:id" element={<ObservationDetailPage />} />
      <Route path="tasks" element={<TasksPage />} />
      <Route path="tasks/new" element={<TaskFormPage />} />
      <Route path="tasks/:id" element={<TaskDetailPage />} />
      <Route path="work-log" element={<WorkLogPage />} />
      <Route path="notifications" element={<NotificationsPage />} />
      <Route path="settings" element={<SettingsPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/start" replace />} />
  </Routes></VersionGate>
}
