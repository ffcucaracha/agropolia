import { Capacitor } from '@capacitor/core'
import { SecureStorage } from '@aparajita/capacitor-secure-storage'

const REFRESH_KEY = 'auth.refresh'

export interface RefreshTokenStore {
  get(): Promise<string | null>
  set(value: string): Promise<void>
  clear(): Promise<void>
}

class WebRefreshTokenStore implements RefreshTokenStore {
  // Web refresh token is HttpOnly cookie and intentionally unavailable to JS.
  async get(): Promise<string | null> { return null }
  async set(_value: string): Promise<void> { return }
  async clear(): Promise<void> { return }
}

class NativeRefreshTokenStore implements RefreshTokenStore {
  async get(): Promise<string | null> {
    const value = await SecureStorage.get(REFRESH_KEY, false)
    return typeof value === 'string' ? value : null
  }
  async set(value: string): Promise<void> {
    await SecureStorage.set(REFRESH_KEY, value)
  }
  async clear(): Promise<void> {
    await SecureStorage.remove(REFRESH_KEY)
  }
}

export const refreshTokenStore: RefreshTokenStore = Capacitor.isNativePlatform()
  ? new NativeRefreshTokenStore()
  : new WebRefreshTokenStore()
