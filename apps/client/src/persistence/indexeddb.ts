import type { LocalPersistence } from './local'

const DB_NAME = 'agropolia-workspace-v1'
const STORE = 'entries'

async function db(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        request.result.createObjectStore(STORE)
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function readWrite<T>(mode: IDBTransactionMode, work: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const database = await db()
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = database.transaction(STORE, mode)
      const request = work(transaction.objectStore(STORE))
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
      transaction.onerror = () => reject(transaction.error)
    })
  } finally {
    database.close()
  }
}

export class IndexedDbPersistence implements LocalPersistence {
  async get<T>(key: string): Promise<T | null> {
    const value = await readWrite<unknown>('readonly', (store) => store.get(key))
    return (value as T | undefined) ?? null
  }
  async set<T>(key: string, value: T): Promise<void> {
    await readWrite('readwrite', (store) => store.put(value, key))
  }
  async remove(key: string): Promise<void> {
    await readWrite('readwrite', (store) => store.delete(key))
  }
}

export async function clearWorkspaceCache(): Promise<void> {
  // Used on logout: do not leave tenant-owned cache accessible to the next login.
  if (!('indexedDB' in window)) return
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DB_NAME)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
    request.onblocked = () => reject(new Error('Локальная база занята другой вкладкой'))
  })
}
