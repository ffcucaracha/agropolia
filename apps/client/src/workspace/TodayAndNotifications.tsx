import { FormEvent, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Me } from '../auth/store'
import { loadCollection, onQueueChange, pendingOperations, retryOperation, submitCommand, type PendingOperation } from './offline'
import type { Field, Notice, Task } from './types'
import { taskStatuses } from './types'
import { ErrorMessage, formatDate, PageHead, StateMessage } from './ui'

export function TodayPage() {
  const me = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me') })
  const tasks = useQuery({ queryKey: ['tasks'], queryFn: () => loadCollection<Task>('/tasks') })
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const now = new Date()
  const open = (tasks.data ?? []).filter((task) => task.status !== 'done' && task.status !== 'verified')
  const overdue = open.filter((task) => !!task.due_at && new Date(task.due_at) < now)
  return <>
    <PageHead title={me.data?.user.name || 'Сегодня'} subtitle="Рабочий день вашего хозяйства" />
    <p className="muted">ИНН: {me.data?.organization.inn} · Роль: {me.data?.membership.role}</p>
    <div className="stat-row">
      <section className="stat"><span>Полей</span><strong>{fields.data?.length ?? 0}</strong></section>
      <section className="stat"><span>Открытых задач</span><strong>{open.length}</strong></section>
      <section className="stat"><span>Просроченных</span><strong>{overdue.length}</strong></section>
    </div>
    <div className="button-row">
      <Link className="button primary" to="/app/observations/new">Отметить наблюдение</Link>
      <Link className="button secondary" to="/app/tasks/new">Создать задачу</Link>
    </div>
    <section className="workspace-panel">
      <h2>Актуальные задачи</h2>
      {open.length === 0 ? <p className="muted">Нет открытых задач. Добавьте первую задачу для своего поля.</p>
        : open.slice(0, 12).map((task) => <div className="list-item" key={task.id}>
          <Link to={`/app/tasks/${task.id}`}>{task.title}</Link><span>{taskStatuses[task.status]} · {formatDate(task.due_at)}</span>
        </div>)}
      {(tasks.error || fields.error) && <ErrorMessage error={tasks.error || fields.error} />}
    </section>
    {fields.data?.length === 0 && <section className="workspace-panel">
      <h2>Начните с поля</h2><p className="muted">Добавьте поле вручную. Интеграция с «Метеомониторингом» пока недоступна.</p>
      <Link className="button primary" to="/app/fields/new">Добавить поле</Link>
    </section>}
  </>
}

export function NotificationsPage() {
  const client = useQueryClient()
  const notices = useQuery({ queryKey: ['notifications'], queryFn: () => api<Notice[]>('/notifications'), refetchInterval: 15_000 })
  const [error, setError] = useState<unknown>(null)
  async function read(notice: Notice) {
    setError(null)
    try {
      await submitCommand('notification.read', {}, notice.id)
      await client.invalidateQueries({ queryKey: ['notifications'] })
    } catch (e) { setError(e) }
  }
  return <>
    <PageHead title="Уведомления" subtitle="События по задачам вашего хозяйства" />
    {error != null && <ErrorMessage error={error} />}
    {notices.error && <ErrorMessage error={notices.error} />}
    {notices.data?.length === 0 && <StateMessage>Уведомлений пока нет.</StateMessage>}
    <div className="record-grid">{notices.data?.map((notice) => <section className="record-card" key={notice.id}>
      <span className="tag">{notice.read_at ? 'Прочитано' : 'Новое'}</span>
      <h2>{notice.title}</h2>
      <p className="muted">{formatDate(notice.created_at)}</p>
      <div className="button-row">
        {!notice.read_at && <button className="button secondary" onClick={() => void read(notice)}>Прочитано</button>}
        {notice.task_id && <Link className="button primary" to={`/app/tasks/${notice.task_id}`}>Открыть задачу</Link>}
      </div>
    </section>)}</div>
  </>
}

export function SettingsPage() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: ['notification-settings'], queryFn: () => api<{ task_events: boolean }>('/notification-settings') })
  const [enabled, setEnabled] = useState(true)
  const [pending, setPending] = useState<PendingOperation[]>([])
  const [error, setError] = useState<unknown>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (settings.data) setEnabled(settings.data.task_events) }, [settings.data])
  useEffect(() => {
    const refresh = () => { void pendingOperations().then(setPending).catch(() => undefined) }
    refresh()
    return onQueueChange(refresh)
  }, [])
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage('')
    try {
      const result = await submitCommand('notification.preference', { task_events: enabled })
      setMessage(result.queued ? 'Настройки сохранены локально; отправим при появлении сети.' : 'Настройки сохранены.')
      await client.invalidateQueries({ queryKey: ['notification-settings'] })
    } catch (e) { setError(e) }
    finally { setBusy(false) }
  }
  return <>
    <PageHead title="Настройки" subtitle="Уведомления и синхронизация web/PWA" />
    <section className="workspace-panel">
      <h2>Внутренние уведомления</h2>
      <form onSubmit={(event) => void save(event)}>
        <label className="checkbox"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />События и изменения задач</label>
        <button className="button primary" disabled={busy}>Сохранить настройки</button>
      </form>
      {message && <p role="status">{message}</p>}
      {error != null && <ErrorMessage error={error} />}
    </section>
    <section className="workspace-panel">
      <h2>Очередь синхронизации</h2>
      <p className="muted">Изменения без сети сохраняются в этом браузере. Отключение сессии очищает локальные данные.</p>
      {pending.length === 0 && <p>Все операции отправлены.</p>}
      {pending.map((item) => <div key={item.client_op_id} className="list-item">
        <span>{item.type} · {item.state === 'error' ? 'Ошибка' : 'Ожидает отправки'}</span>
        {item.error && <span className="error">{item.error}</span>}
        {item.details?.length ? <span className="muted">Локальные данные: {JSON.stringify(item.payload)}. Версия сервера: {JSON.stringify(item.details)}</span> : null}
        <button className="button secondary" type="button" onClick={() => void retryOperation(item.client_op_id)}>Повторить</button>
      </div>)}
    </section>
  </>
}
