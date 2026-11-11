import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore, type Me } from '../auth/store'
import { flushQueue, onQueueChange, queueCount } from './offline'
import { flushMedia, mediaQueue } from './mediaQueue'

const links = [
  { to: '/app', name: 'Сегодня', end: true },
  { to: '/app/fields', name: 'Мои поля' },
  { to: '/app/observations', name: 'Наблюдения' },
  { to: '/app/tasks', name: 'Задачи' },
  { to: '/app/work-log', name: 'Журнал работ' },
  { to: '/app/notifications', name: 'Уведомления' },
  { to: '/app/settings', name: 'Настройки' },
]

export function WorkspaceLayout() {
  const logout = useAuthStore((state) => state.logout)
  const setActiveOrg = useAuthStore((state) => state.setActiveOrg)
  const setUserId = useAuthStore((state) => state.setUserId)
  const userId = useAuthStore((state) => state.userId)
  const orgId = useAuthStore((state) => state.activeOrgId)
  const queryClient = useQueryClient()
  const [pending, setPending] = useState(0)
  const [online, setOnline] = useState(navigator.onLine)

  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => api<Me>('/me'),
  })
  useEffect(() => {
    if (me.data) {
      setActiveOrg(me.data.organization.id)
      setUserId(me.data.user.id)
    }
  }, [me.data, setActiveOrg, setUserId])

  useEffect(() => {
    if (!userId || !orgId) return
    const update = () => { void queueCount().then(setPending).catch(() => undefined) }
    const sync = () => {
      setOnline(navigator.onLine)
      void flushQueue().then(async (results) => {
        await flushMedia()
        if (results.length) void queryClient.invalidateQueries()
        update()
      }).catch(() => undefined)
    }
    const onVisibility = () => { if (document.visibilityState === 'visible') sync() }
    const unsubscribe = onQueueChange(update)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)
    document.addEventListener('visibilitychange', onVisibility)
    const interval = window.setInterval(sync, 30_000)
    sync()
    return () => {
      unsubscribe()
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
      document.removeEventListener('visibilitychange', onVisibility)
      window.clearInterval(interval)
    }
  }, [userId, orgId, queryClient])

  async function safelyLogout() {
    const queued = await queueCount().catch(() => 0)
    const photos = await mediaQueue().then((items) => items.length).catch(() => 0)
    if (queued + photos > 0 && !window.confirm('Есть неотправленные изменения. При выходе они будут удалены. Продолжить?')) return
    await logout()
  }

  if (me.isLoading) return <main className="shell"><section className="card">Загрузка хозяйства…</section></main>
  if (!me.data) return <main className="shell"><section className="card"><p className="error">Не удалось получить хозяйство.</p><button className="button secondary" onClick={() => void safelyLogout()}>Выйти</button></section></main>

  return <div className="workspace">
    <header className="workspace-header">
      <div><span className="brand">АГРОПОЛИЯ</span><span className="workspace-org">{me.data.organization.name}</span></div>
      <div className="workspace-session">
        {!online && <span className="status-note">Нет связи</span>}
        {pending > 0 && <span className="status-note">{pending} в очереди</span>}
        <button className="link-button" onClick={() => void safelyLogout()}>Выйти</button>
      </div>
    </header>
    <nav className="workspace-nav" aria-label="Разделы хозяйства">
      {links.map((link) => <NavLink key={link.to} to={link.to}
        end={link.end} className={({ isActive }) => isActive ? 'nav-link selected' : 'nav-link'}>{link.name}</NavLink>)}
    </nav>
    <main className="workspace-main"><Outlet /></main>
  </div>
}
