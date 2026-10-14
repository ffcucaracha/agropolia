export interface LocalPersistence {
  get<T>(key: string): Promise<T | null>
  set<T>(key: string, value: T): Promise<void>
  remove(key: string): Promise<void>
}

export class MemoryPersistence implements LocalPersistence {
  private readonly values = new Map<string, unknown>()
  async get<T>(key: string): Promise<T | null> { return (this.values.get(key) as T | undefined) ?? null }
  async set<T>(key: string, value: T): Promise<void> { this.values.set(key, value) }
  async remove(key: string): Promise<void> { this.values.delete(key) }
}

// I-0 defines the boundary only. IndexedDB/SQLite implementations are added with offline sync,
// without leaking platform checks into application/domain code.
