import { Navigate, Link } from 'react-router-dom'
import { useAuthStore } from '../auth/store'
import { Layout } from '../components/Layout'

export function StartPage() {
  const accessToken = useAuthStore((state) => state.accessToken)
  if (accessToken) return <Navigate to="/app" replace />
  return <Layout>
    <section className="card start-card">
      <p className="eyebrow">АГРОПОЛИЯ</p>
      <h1>Цифровая рабочая среда агрария</h1>
      <p className="muted">Войдите или создайте хозяйство, чтобы начать работу.</p>
      <div className="actions">
        <Link className="button primary" to="/auth/register">Зарегистрироваться</Link>
        <Link className="button secondary" to="/auth/login">Войти</Link>
      </div>
    </section>
  </Layout>
}
