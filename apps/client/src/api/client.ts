import { Capacitor } from '@capacitor/core'
import { useAuthStore } from '../auth/store'

export type ApiErrorBody = { code: string; message: string; details?: unknown[]; request_id?: string }

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly body: ApiErrorBody) {
    super(body.message)
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export function clientPlatform(): 'web' | 'android' | 'ios' {
  const platform = Capacitor.getPlatform()
  return platform === 'android' || platform === 'ios' ? platform : 'web'
}

function randomDeviceId(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()

  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'))
  return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10).join('')}`
}

export function deviceId(): string {
  const key = 'agropolia.device-id'
  const existing = localStorage.getItem(key)
  if (existing) return existing
  const value = randomDeviceId()
  localStorage.setItem(key, value)
  return value
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { accessToken, activeOrgId } = useAuthStore.getState()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  headers.set('X-Client-Platform', clientPlatform())
  headers.set('X-Client-Version', __APP_VERSION__)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  if (activeOrgId) headers.set('X-Org-Id', activeOrgId)
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' })
  if (!response.ok) {
    let body: ApiErrorBody = { code: 'HTTP_ERROR', message: 'Ошибка запроса' }
    try { body = await response.json() as ApiErrorBody } catch { /* response is not JSON */ }
    throw new ApiError(response.status, body)
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}
