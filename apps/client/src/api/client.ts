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

export function deviceId(): string {
  const key = 'agropolia.device-id'
  const existing = localStorage.getItem(key)
  if (existing) return existing
  const value = crypto.randomUUID()
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
