import { describe, expect, it } from 'vitest'
import { MemoryPersistence } from './local'

describe('MemoryPersistence', () => {
  it('implements the persistence port without platform checks', async () => {
    const storage = new MemoryPersistence()
    await storage.set('key', { value: 1 })
    expect(await storage.get('key')).toEqual({ value: 1 })
    await storage.remove('key')
    expect(await storage.get('key')).toBeNull()
  })
})
