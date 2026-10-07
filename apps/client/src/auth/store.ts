import { create } from 'zustand'
import { api, clientPlatform, deviceId } from '../api/client'
import { refreshTokenStore } from '../persistence/tokens'

export type TokenPair = { access_token: string; refresh_token?: string | null; token_type: string; expires_in: number }
export type Me = {
  user: { id: string; name: string | null; phone_masked: string }
  organization: { id: string; type: string; inn: string; name: string }
  membership: { role: string }
}

type AuthState = {
  accessToken: string | null
  activeOrgId: string | null
  hydrated: boolean
  setTokens(tokens: TokenPair): Promise<void>
  bootstrap(): Promise<void>
  logout(): Promise<void>
  setActiveOrg(id: string | null): void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  activeOrgId: null,
  hydrated: false,
  async setTokens(tokens) {
    set({ accessToken: tokens.access_token })
    if (tokens.refresh_token) await refreshTokenStore.set(tokens.refresh_token)
  },
  async bootstrap() {
    try {
      const refresh = await refreshTokenStore.get()
      const tokens = await api<TokenPair>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refresh, device_id: deviceId() }),
      })
      await get().setTokens(tokens)
      const me = await api<Me>('/me')
      set({ activeOrgId: me.organization.id })
    } catch {
      set({ accessToken: null, activeOrgId: null })
      await refreshTokenStore.clear()
    } finally {
      set({ hydrated: true })
    }
  },
  async logout() {
    try {
      if (get().accessToken) await api<void>('/auth/logout', { method: 'POST', body: JSON.stringify({}) })
    } finally {
      await refreshTokenStore.clear()
      set({ accessToken: null, activeOrgId: null })
    }
  },
  setActiveOrg(id) { set({ activeOrgId: id }) },
}))
