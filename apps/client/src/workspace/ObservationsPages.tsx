import { FormEvent, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { loadCollection, submitCommand } from './offline'
import type { Field, Observation } from './types'
import { observationKinds } from './types'
import { BackLink, ErrorMessage, formatDate, PageHead, PendingTag, StateMessage } from './ui'

export function ObservationsPage() {
  const { data, error } = useQuery({ queryKey: ['observations'], queryFn: () => loadCollection<Observation>('/observations') })
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const [fieldId, setFieldId] = useState('')
  const [kind, setKind] = useState('')
  const [search, setSearch] = useState('')
  const fieldNames = new Map(fields.data?.map((f) => [f.id, f.name]) ?? [])
  const entries = (data ?? []).filter((x) => (!fieldId || x.field_id === fieldId) && (!kind || x.kind === kind) && x.text.toLowerCase().includes(search.toLowerCase()))
  return <>
    <PageHead title="Журнал наблюдений" subtitle="Приватные записи вашего хозяйства" action={{ to: '/app/observations/new', text: 'Отметить' }} />
    <div className="filters">
      <label>Поле<select value={fieldId} onChange={(e) => setFieldId(e.target.value)}><option value="">Все поля</option>{fields.data?.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
      <label>Тип<select value={kind} onChange={(e) => setKind(e.target.value)}><option value="">Все типы</option>{Object.entries(observationKinds).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <label>Поиск<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Описание" /></label>
    </div>
    {error && <ErrorMessage error={error} />}
    {entries.length === 0 && <StateMessage>Наблюдений по выбранным фильтрам нет.</StateMessage>}
    <div className="record-grid">{entries.map((entry) => <Link className="record-card" key={entry.id} to={`/app/observations/${entry.id}`}>
      <span className="tag">{observationKinds[entry.kind]}</span>
      <h2>{fieldNames.get(entry.field_id) ?? 'Поле'}</h2>
      <p>{entry.text || 'Без описания'}</p>
      <p className="muted">{formatDate(entry.taken_at)}</p>
      <PendingTag pending={entry.pending} />
    </Link>)}</div>
  </>
}

export function ObservationFormPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const [fieldId, setFieldId] = useState(params.get('field') ?? '')
  const [kind, setKind] = useState<Observation['kind']>('crop_state')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null)
    try {
      await submitCommand('observation.create', { field_id: fieldId, kind, text: description })
      await client.invalidateQueries({ queryKey: ['observations'] })
      navigate('/app/observations')
    } catch (e) { setError(e) }
    finally { setBusy(false) }
  }
  return <section className="workspace-panel">
    <BackLink to="/app/observations" />
    <h1>Новое наблюдение</h1>
    <p className="muted">Запись видна только вашему хозяйству. Без связи она сохраняется локально.</p>
    {fields.data?.length === 0 && <p className="error">Сначала добавьте поле. <Link to="/app/fields/new">Добавить поле</Link></p>}
    <form onSubmit={(event) => void save(event)}>
      <label>Поле<select required value={fieldId} onChange={(e) => setFieldId(e.target.value)}><option value="">Выберите поле</option>{fields.data?.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
      <label>Тип наблюдения<select value={kind} onChange={(e) => setKind(e.target.value as Observation['kind'])}>{Object.entries(observationKinds).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
      <label>Описание<textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={5} maxLength={10000} placeholder="Что вы заметили на поле?" /></label>
      {error && <ErrorMessage error={error} />}
      <button className="button primary" disabled={busy || !fieldId}>{busy ? 'Сохраняем…' : 'Сохранить наблюдение'}</button>
    </form>
  </section>
}

export function ObservationDetailPage() {
  const { id } = useParams()
  const entries = useQuery({ queryKey: ['observations'], queryFn: () => loadCollection<Observation>('/observations') })
  const fields = useQuery({ queryKey: ['fields'], queryFn: () => loadCollection<Field>('/fields') })
  const entry = entries.data?.find((item) => item.id === id)
  const field = fields.data?.find((item) => item.id === entry?.field_id)
  if (entries.isLoading) return <StateMessage>Загрузка наблюдения…</StateMessage>
  if (!entry) return <StateMessage>Наблюдение не найдено.</StateMessage>
  return <section className="workspace-panel">
    <BackLink to="/app/observations" />
    <h1>{observationKinds[entry.kind]}</h1>
    <p><strong>Поле:</strong> {field?.name ?? 'Неизвестное поле'}</p>
    <p><strong>Когда:</strong> {formatDate(entry.taken_at)}</p>
    <p className="observation-text">{entry.text || 'Нет описания'}</p>
    <PendingTag pending={entry.pending} />
    <div className="button-row">
      <Link className="button primary" to={`/app/tasks/new?field=${entry.field_id}&observation=${entry.id}`}>Создать задачу</Link>
      <Link className="button secondary" to={`/app/fields/${entry.field_id}`}>К полю</Link>
    </div>
  </section>
}
