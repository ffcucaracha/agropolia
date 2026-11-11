import { FormEvent, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { loadCollection, submitCommand } from './offline'
import { enqueuePhotos } from './mediaQueue'
import { MediaGallery } from './MediaGallery'
import type { Field, Observation, Task, WorkLog } from './types'
import { taskPriorities, taskStatuses } from './types'
import { BackLink, ErrorMessage, formatDate, PageHead, PendingTag, StateMessage } from './ui'

export function TasksPage() {
  const tasks = useQuery({ queryKey: ['tasks'], queryFn: () => loadCollection<Task>('/tasks') })
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const [status, setStatus] = useState('')
  const [fieldId, setFieldId] = useState('')
  const fieldsById = new Map(fields.data?.map((f) => [f.id, f.name]) ?? [])
  const entries = (tasks.data ?? []).filter((task) => (!status || task.status === status) && (!fieldId || task.field_id === fieldId))
  return <>
    <PageHead title="Задачи" subtitle="Планирование и выполнение работ" action={{ to: '/app/tasks/new', text: 'Создать задачу' }} />
    <div className="filters">
      <label>Поле<select value={fieldId} onChange={(e) => setFieldId(e.target.value)}><option value="">Все поля</option>{fields.data?.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
      <label>Статус<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Все статусы</option>{Object.entries(taskStatuses).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label>
    </div>
    {tasks.error && <ErrorMessage error={tasks.error} />}
    {entries.length === 0 && <StateMessage>Задач пока нет.</StateMessage>}
    <div className="record-grid">{entries.map((task) => <Link className="record-card" key={task.id} to={`/app/tasks/${task.id}`}>
      <span className="tag">{taskStatuses[task.status]}</span>
      <h2>{task.title}</h2>
      <p>{fieldsById.get(task.field_id) ?? 'Поле'} · {taskPriorities[task.priority]}</p>
      <p className="muted">Срок: {formatDate(task.due_at)}</p>
      <PendingTag pending={task.pending} />

    </Link>)}</div>
  </>
}

export function TaskFormPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const obs = useQuery({ queryKey: ['observations'], queryFn: () => loadCollection<Observation>('/observations') })
  const [fieldId, setFieldId] = useState(params.get('field') ?? '')
  useEffect(() => { if (!fieldId && fields.data?.length === 1) setFieldId(fields.data[0].id) }, [fieldId, fields.data])
  const observationId = params.get('observation')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [due, setDue] = useState('')
  const [priority, setPriority] = useState<Task['priority']>('normal')
  const [checklist, setChecklist] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const source = obs.data?.find((item) => item.id === observationId)

  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null)
    try {
      await submitCommand('task.create', {
        field_id: fieldId, observation_id: observationId ?? null,
        title, description, due_at: due ? new Date(due).toISOString() : null,
        priority, checklist: checklist.split('\n').map((v) => v.trim()).filter(Boolean),
      })
      await client.invalidateQueries({ queryKey: ['tasks'] })
      navigate('/app/tasks')
    } catch (e) { setError(e) }
    finally { setBusy(false) }
  }

  return <section className="workspace-panel">
    <BackLink to="/app/tasks" />
    <h1>Новая задача</h1>
    {source && <p className="muted">По наблюдению: {source.text || 'Без описания'}</p>}
    {fields.data?.length === 0 && <p className="error">Сначала добавьте поле. <Link to="/app/fields/new">Добавить поле</Link></p>}
    <form onSubmit={(event) => void save(event)}>
      <label>Поле<select value={fieldId} onChange={(e) => setFieldId(e.target.value)} required><option value="">Выберите поле</option>{fields.data?.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
      <label>Задача<input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} placeholder="Например, проверить посевы" /></label>
      <label>Описание<textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} maxLength={10000} /></label>
      <label>Срок<input type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} /></label>
      <label>Приоритет<select value={priority} onChange={(e) => setPriority(e.target.value as Task['priority'])}>{Object.entries(taskPriorities).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
      <label>Чек-лист (один пункт на строку)<textarea rows={3} value={checklist} onChange={(e) => setChecklist(e.target.value)} /></label>
      {error != null && <ErrorMessage error={error} />}
      <button className="button primary" disabled={busy || !fieldId}>{busy ? 'Сохраняем…' : 'Создать задачу'}</button>
    </form>
  </section>
}

const transitions: Record<Task['status'], Array<{ next: Task['status']; label: string }>> = {
  new: [{ next: 'accepted', label: 'Принять' }, { next: 'blocked', label: 'Заблокировать' }],
  accepted: [{ next: 'in_progress', label: 'Начать работу' }, { next: 'blocked', label: 'Заблокировать' }],
  in_progress: [{ next: 'done', label: 'Отметить выполненной' }, { next: 'blocked', label: 'Заблокировать' }],
  blocked: [{ next: 'accepted', label: 'Возобновить' }],
  done: [{ next: 'verified', label: 'Проверить выполнение' }],
  verified: [],
}

export function TaskDetailPage() {
  const { id } = useParams()
  const client = useQueryClient()
  const tasks = useQuery({ queryKey: ['tasks'], queryFn: () => loadCollection<Task>('/tasks') })
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const task = tasks.data?.find((item) => item.id === id)
  const [reason, setReason] = useState('')
  const [photos, setPhotos] = useState<File[]>([])
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  async function transition(status: Task['status']) {
    if (!task) return
    setBusy(true); setError(null)
    try {
      await submitCommand('task.transition', { status, blocked_reason: status === 'blocked' ? reason : null }, task.id, task.version)
      if (status === 'done' && photos.length) await enqueuePhotos('task', task.id, photos)
      await client.invalidateQueries({ queryKey: ['tasks'] })
      await client.invalidateQueries({ queryKey: ['work-log'] })
    } catch (e) { setError(e) }
    finally { setBusy(false) }
  }
  if (tasks.isLoading) return <StateMessage>Загрузка задачи…</StateMessage>
  if (!task) return <StateMessage>Задача не найдена.</StateMessage>
  const field = fields.data?.find((item) => item.id === task.field_id)
  return <section className="workspace-panel">
    <BackLink to="/app/tasks" />
    <span className="tag">{taskStatuses[task.status]}</span>
    <h1>{task.title}</h1>
    <p><strong>Поле:</strong> <Link to={`/app/fields/${task.field_id}`}>{field?.name ?? 'Поле'}</Link></p>
    <p><strong>Приоритет:</strong> {taskPriorities[task.priority]}</p>
    <p><strong>Срок:</strong> {formatDate(task.due_at)}</p>
    <p className="observation-text">{task.description || 'Без описания'}</p>
    {task.observation_id && <p><Link to={`/app/observations/${task.observation_id}`}>Исходное наблюдение</Link></p>}
    {task.checklist?.length > 0 && <div><h2>Чек-лист</h2><ul>{task.checklist.map((item, i) => <li key={i}>{item}</li>)}</ul></div>}
    {task.blocked_reason && <p className="error">Причина блокировки: {task.blocked_reason}</p>}
    {task.completed_at && <p>Выполнена: {formatDate(task.completed_at)}</p>}
    <PendingTag pending={task.pending} />
    <MediaGallery ownerType="task" ownerId={task.id} />
    {task.status === 'in_progress' && <label>Фото подтверждения выполнения<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => setPhotos(Array.from(e.target.files ?? []).slice(0, 10))} /></label>}
    {transitions[task.status].some((item) => item.next === 'blocked') && <label className="block-reason">Причина блокировки<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Обязательно при блокировке" maxLength={1000} /></label>}
    {error != null && <ErrorMessage error={error} />}
    <div className="button-row">{transitions[task.status].map(({ next, label }) => <button key={next} type="button"
      className={next === 'blocked' ? 'button secondary' : 'button primary'}
      onClick={() => void transition(next)} disabled={busy || (next === 'blocked' && !reason.trim())}>{label}</button>)}</div>
  </section>
}

export function WorkLogPage() {
  const entries = useQuery({ queryKey: ['work-log'], queryFn: () => loadCollection<WorkLog>('/work-log') })
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const [fieldId, setFieldId] = useState('')
  const fieldNames = new Map(fields.data?.map((item) => [item.id, item.name]) ?? [])
  const rows = (entries.data ?? []).filter((item) => !fieldId || item.field_id === fieldId)
  return <>
    <PageHead title="Журнал работ" subtitle="Фактически выполненные операции" />
    <div className="filters"><label>Поле<select value={fieldId} onChange={(e) => setFieldId(e.target.value)}><option value="">Все поля</option>{fields.data?.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label></div>
    {entries.error && <ErrorMessage error={entries.error} />}
    {rows.length === 0 && <StateMessage>Выполненных работ ещё нет.</StateMessage>}
    <div className="record-grid">{rows.map((entry) => <Link className="record-card" key={entry.id} to={`/app/tasks/${entry.task_id}`}>
      <span className="tag">Выполнено</span><h2>{entry.title}</h2><p>{fieldNames.get(entry.field_id) ?? 'Поле'}</p>
      <p className="muted">{formatDate(entry.performed_at)}</p>
    </Link>)}</div>
  </>
}
