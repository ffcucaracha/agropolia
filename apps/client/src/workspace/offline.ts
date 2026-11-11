import { api } from '../api/client'
import { useAuthStore } from '../auth/store'
import { IndexedDbPersistence } from '../persistence/indexeddb'

const storage = new IndexedDbPersistence()

export type CommandType =
  | 'field.create' | 'field.update' | 'observation.create'
  | 'task.create' | 'task.transition' | 'notification.read' | 'notification.preference'

export type PendingOperation = {
  client_op_id: string
  type: CommandType
  entity_id?: string
  base_version?: number
  payload: Record<string, unknown>
  state: 'queued' | 'error'
  error?: string
}

type Result = { client_op_id: string; state: 'applied' | 'duplicate' | 'rejected'; result?: unknown; code?: string; message?: string }

let syncing = false
const listeners = new Set<() => void>()

export function onQueueChange(listener: () => void): () => void {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

function changed() { listeners.forEach((listener) => listener()) }

export function uuid7(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  const ms = BigInt(Date.now())
  for (let i = 0; i < 6; i++) bytes[i] = Number((ms >> BigInt((5 - i) * 8)) & 255n)
  bytes[6] = (bytes[6] & 0x0f) | 0x70
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function scope(): string {
  const { userId, activeOrgId } = useAuthStore.getState()
  if (!userId || !activeOrgId) throw new Error('Не определён пользователь или хозяйство')
  return `${userId}:${activeOrgId}`
}

function key(suffix: string) { return `workspace:${scope()}:${suffix}` }

export async function pendingOperations(): Promise<PendingOperation[]> {
  return (await storage.get<PendingOperation[]>(key('outbox'))) ?? []
}

async function saveQueue(queue: PendingOperation[]) {
  await storage.set(key('outbox'), queue)
  changed()
}

export async function submitCommand(
  type: CommandType, payload: Record<string, unknown>,
  entityId?: string, baseVersion?: number,
): Promise<{ queued: boolean; result?: Record<string, unknown>; entityId?: string }> {
  const stableId = entityId ?? (type.endsWith('.create') ? uuid7() : undefined)
  const item: PendingOperation = {
    client_op_id: uuid7(), type, payload, entity_id: stableId,
    base_version: baseVersion, state: 'queued',
  }
  const queue = await pendingOperations()
  await saveQueue([...queue, item])
  const result = await flushQueue()
  const match = result.find((row) => row.client_op_id === item.client_op_id)
  if (match?.state === 'rejected') {
    throw new Error(match.message || 'Операция отклонена сервером')
  }
  return { queued: !match, result: match?.result as Record<string, unknown> | undefined, entityId: stableId }
}

export async function flushQueue(): Promise<Result[]> {
  if (syncing || !navigator.onLine) return []
  syncing = true
  const allResults: Result[] = []
  try {
    let queue = await pendingOperations()
    const pending = queue.filter((item) => item.state === 'queued')
    // Ordering matters for offline field → observation → task dependencies.
    for (let i = 0; i < pending.length; i += 50) {
      const batch = pending.slice(i, i + 50)
      let response: { results: Result[] }
      try {
        response = await api<{ results: Result[] }>('/sync/ops', {
          method: 'POST', body: JSON.stringify({ ops: batch.map(({ state: _state, error: _error, ...command }) => command) }),
        })
      } catch {
        break // No network or expired session: retain queue; never discard operations.
      }
      allResults.push(...response.results)
      const done = new Set(response.results.filter((r) => r.state !== 'rejected').map((r) => r.client_op_id))
      queue = queue.filter((row) => !done.has(row.client_op_id)).map((row) => {
        const rejected = response.results.find((result) => result.client_op_id === row.client_op_id && result.state === 'rejected')
        return rejected ? { ...row, state: 'error' as const, error: rejected.message } : row
      })
      await saveQueue(queue)
      if (response.results.some((r) => r.state === 'rejected')) break
    }
  } finally {
    syncing = false
  }
  return allResults
}

export async function retryOperation(clientOpId: string) {
  const queue = await pendingOperations()
  await saveQueue(queue.map((item) => item.client_op_id === clientOpId ? { ...item, state: 'queued', error: undefined } : item))
  await flushQueue()
}

export async function loadCollection<T extends { id: string }>(path: string): Promise<T[]> {
  let rows: T[]
  try {
    rows = await api<T[]>(path)
    await storage.set(key(`cache:${path}`), rows)
  } catch {
    const cached = await storage.get<T[]>(key(`cache:${path}`))
    if (!cached) throw new Error('Нет связи и сохранённых данных')
    rows = cached
  }
  // Optimistic local projections are used only in the absence of a server row.
  const pending = await pendingOperations()
  const type = path.startsWith('/fields') ? 'field'
    : path.startsWith('/observations') ? 'observation'
    : path.startsWith('/tasks') ? 'task' : null
  if (!type) return rows
  const byId = new Map<string, T>(rows.map((row) => [row.id, row]))
  for (const op of pending) {
    if (!op.type.startsWith(type + '.')) continue
    if (op.type.endsWith('.create') && op.entity_id && !byId.has(op.entity_id)) {
      const now = new Date().toISOString()
      byId.set(op.entity_id, {
        ...op.payload, id: op.entity_id, version: 1, created_at: now,
        pending: true, status: type === 'task' ? 'new' : undefined,
        source: type === 'field' ? 'manual' : undefined,
      } as unknown as T)
    }
    if ((op.type === 'field.update' || op.type === 'task.transition') && op.entity_id) {
      const current = byId.get(op.entity_id)
      if (current) byId.set(op.entity_id, { ...current, ...op.payload, pending: true })
    }
  }
  return Array.from(byId.values())
}

export async function queueCount(): Promise<number> {
  return (await pendingOperations()).length
}
