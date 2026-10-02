import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuthStore, type Me } from '../auth/store'
import { Layout } from '../components/Layout'

export function DashboardPage() {
  const logout = useAuthStore((state) => state.logout)
  const setActiveOrg = useAuthStore((state) => state.setActiveOrg)
  const query = useQuery({ queryKey: ['me'], queryFn: async () => {
    const result = await api<Me>('/me')
    setActiveOrg(result.organization.id)
    return result
  }})

  if (query.isLoading) return <Layout><section className="card"><p>Загрузка…</p></section></Layout>
  if (query.isError || !query.data) return <Layout><section className="card"><p className="error">Не удалось загрузить данные пользователя.</p><button className="button secondary" onClick={() => void logout()}>Выйти</button></section></Layout>

  const { user, organization, membership } = query.data
  return <Layout><section className="card dashboard">
    <div className="row"><div><p className="eyebrow">АГРОПОЛИЯ</p><h1>{user.name || 'Пользователь'}</h1></div><button className="link-button" onClick={() => void logout()}>Выйти</button></div>
    <dl>
      <div><dt>Телефон</dt><dd>{user.phone_masked}</dd></div>
      <div><dt>Организация</dt><dd>{organization.name}</dd></div>
      <div><dt>Тип</dt><dd>{organization.type}</dd></div>
      <div><dt>ИНН</dt><dd>{organization.inn}</dd></div>
      <div><dt>Роль</dt><dd>{membership.role}</dd></div>
    </dl>
  </section></Layout>
}
