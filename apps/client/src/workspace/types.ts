export type Field = {
  id: string
  name: string
  crop_name: string
  area_ha: number
  sowing_date: string | null
  source: 'manual' | 'meteo'
  version: number
  created_at: string
  pending?: boolean
}

export type Observation = {
  id: string
  field_id: string
  kind: 'disease' | 'pest' | 'weed' | 'damage' | 'crop_state' | 'other'
  text: string
  taken_at: string
  author_id: string
  visibility: 'private'
  version: number
  created_at: string
  pending?: boolean
}

export type Task = {
  id: string
  field_id: string
  observation_id: string | null
  title: string
  description: string
  priority: 'low' | 'normal' | 'high'
  due_at: string | null
  checklist: string[]
  status: 'new' | 'accepted' | 'in_progress' | 'blocked' | 'done' | 'verified'
  blocked_reason: string | null
  author_id: string
  assignee_id: string
  completed_at: string | null
  verified_at: string | null
  version: number
  created_at: string
  pending?: boolean
}

export type WorkLog = {
  id: string
  field_id: string
  task_id: string
  title: string
  performed_by: string
  performed_at: string
}

export type Notice = {
  id: string
  kind: string
  title: string
  task_id: string | null
  read_at: string | null
  created_at: string
}

export const observationKinds: Record<string, string> = {
  disease: 'Болезнь', pest: 'Вредитель', weed: 'Сорняк',
  damage: 'Повреждение', crop_state: 'Состояние посевов', other: 'Другое',
}

export const taskStatuses: Record<string, string> = {
  new: 'Новая', accepted: 'Принята', in_progress: 'В работе',
  blocked: 'Заблокирована', done: 'Выполнена', verified: 'Проверена',
}

export const taskPriorities: Record<string, string> = {
  low: 'Низкий', normal: 'Обычный', high: 'Высокий',
}
