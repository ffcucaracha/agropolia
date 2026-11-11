import { api } from '../api/client'
import { useAuthStore } from '../auth/store'
import { IndexedDbPersistence } from '../persistence/indexeddb'
import { uuid7 } from './offline'

type OwnerType = 'observation' | 'task'

type QueuedMedia = {
  client_media_id: string
  owner_type: OwnerType
  owner_id: string
  file_name: string
  blob: Blob
  state: 'queued' | 'error'
  error?: string
}

const db = new IndexedDbPersistence()
let sending = false

function key(): string {
  const { userId, activeOrgId } = useAuthStore.getState()
  if (!userId || !activeOrgId) throw new Error('Не выбран контекст хозяйства')
  return `workspace:${userId}:${activeOrgId}:media-outbox`
}

export async function mediaQueue(): Promise<QueuedMedia[]> {
  return (await db.get<QueuedMedia[]>(key())) ?? []
}

async function saveQueue(items: QueuedMedia[]) {
  await db.set(key(), items)
}

export async function enqueuePhotos(ownerType: OwnerType, ownerId: string, files: File[]) {
  if (!files.length) return
  const existing = await mediaQueue()
  const forOwner = existing.filter((f) => f.owner_type === ownerType && f.owner_id === ownerId)
  if (files.length + forOwner.length > 10) throw new Error('Не более 10 фото на одну запись')
  for (const file of files) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Разрешены JPEG, PNG и WebP')
    if (file.size > 12 * 1024 * 1024) throw new Error('Фото превышает 12 МБ')
  }
  await saveQueue([...existing, ...files.map((file) => ({
    client_media_id: uuid7(), owner_type: ownerType, owner_id: ownerId,
    file_name: file.name, blob: file, state: 'queued' as const,
  }))])
  await flushMedia()
}

export async function flushMedia() {
  if (sending || !navigator.onLine) return
  sending = true
  try {
    const queue = await mediaQueue()
    for (const item of queue.filter((row) => row.state === 'queued')) {
      const form = new FormData()
      form.set('client_media_id', item.client_media_id)
      form.set('file', item.blob, item.file_name)
      try {
        await api(`/media/${item.owner_type}/${item.owner_id}`, { method: 'POST', body: form })
        const current = await mediaQueue()
        await saveQueue(current.filter((row) => row.client_media_id !== item.client_media_id))
      } catch (error) {
        if (!navigator.onLine) break
        const status = typeof error === 'object' && error && 'status' in error ? Number(error.status) : null
        if (status === 404 || status === 503 || status === 401) break // parent operation pending, outage or expired session
        if (status === 413 || status === 422 || status === 409) {
          const current = await mediaQueue()
          await saveQueue(current.map((row) => row.client_media_id === item.client_media_id
            ? { ...row, state: 'error', error: error instanceof Error ? error.message : 'Ошибка фото' }
            : row))
          continue
        }
        break
      }
    }
  } finally { sending = false }
}

export async function pendingMedia(ownerType: OwnerType, ownerId: string) {
  const items = await mediaQueue()
  return items.filter((item) => item.owner_type === ownerType && item.owner_id === ownerId)
}
