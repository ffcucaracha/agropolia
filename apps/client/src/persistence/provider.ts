import type { LocalPersistence } from './local'
import { MemoryPersistence } from './local'
import { IndexedDbPersistence } from './indexeddb'

// Application/sync code depends on LocalPersistence, not a specific adapter.
// Native SQLite can replace IndexedDB after the separate mobile-readiness gate.
export const workspacePersistence: LocalPersistence =
  typeof indexedDB === 'undefined' ? new MemoryPersistence() : new IndexedDbPersistence()
