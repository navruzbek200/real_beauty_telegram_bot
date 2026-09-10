import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { Schemas } from '@/shared/api/schema'

export type CurrentUser = Schemas['Me']

interface SessionState {
  accessToken: string | null
  refreshToken: string | null
  user: CurrentUser | null
  setTokens: (tokens: { access: string; refresh?: string }) => void
  setUser: (user: CurrentUser) => void
  logout: () => void
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: ({ access, refresh }) =>
        set((state) => ({
          accessToken: access,
          refreshToken: refresh ?? state.refreshToken,
        })),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: 'rb-session',
      // Access tokens are short-lived and kept in memory only; persisting the
      // refresh token + cached user lets a reload skip the login screen while
      // still forcing a fresh access token through the refresh flow.
      partialize: (state) => ({ refreshToken: state.refreshToken, user: state.user }),
    },
  ),
)

export function isSuperUser(user: CurrentUser | null): boolean {
  return user?.is_superuser ?? false
}

export function hasPermission(user: CurrentUser | null, permission: string): boolean {
  if (!user) return false
  if (user.is_superuser) return true
  return user.permissions?.includes(permission) ?? false
}
