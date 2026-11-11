import { FormEvent, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { loadCollection, submitCommand } from './offline'
import type { Field, Observation, Task } from './types'
import { observationKinds, taskStatuses } from './types'
import { BackLink, ErrorMessage, PageHead, PendingTag, StateMessage } from './ui'

export function FieldsPage() {
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  return <>
    <PageHead title="Мои поля" subtitle="Поля хозяйства. Данные погоды появятся после подключения источника." action={{ to: '/app/fields/new', text: 'Добавить поле' }} />
    {fields.isError && <ErrorMessage error={fields.error} />}
    {fields.data?.length === 0 && <StateMessage>Полей пока нет. Добавьте первое поле, чтобы вести наблюдения и задачи.</StateMessage>}
    <div className="record-grid">{fields.data?.map((field) => <Link className="record-card" key={field.id} to={`/app/fields/${field.id}`}>
      <span className="tag">Поле</span><h2>{field.name}</h2>
      <p>{field.crop_name} · {field.area_ha} га</p>
      <PendingTag pending={field.pending} />
    </Link>)}</div>
  </>
}

export function FieldFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields'), enabled: !!id })
  const existing = fields.data?.find((item) => item.id === id)
  const [name, setName] = useState('')
  const [crop, setCrop] = useState('')
  const [area, setArea] = useState('')
  const [sowingDate, setSowingDate] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (existing) {
      setName(existing.name); setCrop(existing.crop_name); setArea(String(existing.area_ha))
      setSowingDate(existing.sowing_date ?? '')
    }
  }, [existing])

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError(null)
    try {
      if (id && !existing) throw new Error('Поле не найдено')
      await submitCommand(id ? 'field.update' : 'field.create', {
        name, crop_name: crop, area_ha: Number(area), sowing_date: sowingDate || null,
      }, id, existing?.version)
      await client.invalidateQueries({ queryKey: ['fields'] })
      navigate('/app/fields')
    } catch (e) { setError(e) }
    finally { setBusy(false) }
  }

  return <section className="workspace-panel">
    <BackLink to={id ? `/app/fields/${id}` : '/app/fields'} />
    <h1>{id ? 'Редактировать поле' : 'Новое поле'}</h1>
    <p className="muted">Создание без контура и без метеоданных. Культуру можно ввести вручную.</p>
    {id && fields.isLoading ? <p>Загрузка…</p> : <form onSubmit={(event) => void save(event)}>
      <label>Название поля<input value={name} onChange={(e) => setName(e.target.value)} maxLength={160} required /></label>
      <label>Культура<input value={crop} onChange={(e) => setCrop(e.target.value)} maxLength={120} required /></label>
      <label>Площадь, га<input type="number" step="0.001" min="0.001" value={area} onChange={(e) => setArea(e.target.value)} required /></label>
      <label>Дата сева (необязательно)<input type="date" value={sowingDate} onChange={(e) => setSowingDate(e.target.value)} /></label>
      {error != null && <ErrorMessage error={error} />}
      <button className="button primary" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить поле'}</button>
    </form>}
  </section>
}

export function FieldDetailPage() {
  const { id } = useParams()
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const obs = useQuery({ queryKey: ['observations'], queryFn: () => loadCollection<Observation>('/observations') })
  const tasks = useQuery({ queryKey: ['tasks'], queryFn: () => loadCollection<Task>('/tasks') })
  const item = fields.data?.find((field) => field.id === id)
  if (fields.isLoading) return <StateMessage>Загрузка поля…</StateMessage>
  if (!item) return <StateMessage>Поле не найдено или недоступно.</StateMessage>
  const recentObs = obs.data?.filter((entry) => entry.field_id === id).slice(0, 4) ?? []
  const recentTasks = tasks.data?.filter((task) => task.field_id === id).slice(0, 5) ?? []
  return <>
    <BackLink to="/app/fields" text="К списку полей" />
    <PageHead title={item.name} subtitle={`${item.crop_name} · ${item.area_ha} га`} action={{ to: `/app/fields/${id}/edit`, text: 'Изменить' }} />
    <section className="workspace-panel">
      <p className="muted">Дата сева: {item.sowing_date || 'не указана'} · Источник: {item.source === 'manual' ? 'Введено вручную' : 'Метеомониторинг'}</p>
      <PendingTag pending={item.pending} />
      <div className="button-row">
        <Link className="button primary" to={`/app/observations/new?field=${id}`}>Добавить наблюдение</Link>
        <Link className="button secondary" to={`/app/tasks/new?field=${id}`}>Создать задачу</Link>
      </div>
    </section>
    <div className="two-columns">
      <section className="workspace-panel">
        <h2>Наблюдения</h2>
        {recentObs.length === 0 ? <p className="muted">Записей пока нет.</p> : recentObs.map((entry) => <p key={entry.id}>
          <Link to={`/app/observations/${entry.id}`}>{observationKinds[entry.kind]} · {entry.text || 'Без описания'}</Link>
        </p>)}
      </section>
      <section className="workspace-panel">
        <h2>Задачи</h2>
        {recentTasks.length === 0 ? <p className="muted">Задач пока нет.</p> : recentTasks.map((task) => <p key={task.id}>
          <Link to={`/app/tasks/${task.id}`}>{task.title}</Link> · {taskStatuses[task.status]}
        </p>)}
      </section>
    </div>
  </>
}
