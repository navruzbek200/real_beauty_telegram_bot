import { fetchMe, refreshAccessToken } from '../api'
import { useSessionStore } from './store'
import { configureAuthHooks } from '@/shared/api/auth-hooks'

let refreshInFlight: Promise<string | null> | null = null

/** Rotates the refresh token for a new access token. Shared by the http
 * client's 401 middleware and `restoreSession` so two callers racing around
 * app boot spend only one refresh-token rotation, not two. */
function refreshTokenOnly(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight

  const { refreshToken, setTokens, logout } = useSessionStore.getState()
  if (!refreshToken) return Promise.resolve(null)

  refreshInFlight = (async () => {
    try {
      const data = await refreshAccessToken(refreshToken)
      setTokens({ access: data.access, refresh: data.refresh })
      return data.access
    } catch {
      logout()
      return null
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

/** Called once at app boot: turns a persisted refresh token back into a live
 * access token + fresh `/me` profile, so a page reload doesn't bounce an
 * already-logged-in user back to the login screen. */
export async function restoreSession(): Promise<void> {
  const { refreshToken, setUser, logout } = useSessionStore.getState()
  if (!refreshToken) return
  const access = await refreshTokenOnly()
  if (!access) return
  try {
    const me = await fetchMe(access)
    setUser(me)
  } catch {
    logout()
  }
}

configureAuthHooks({
  getAccessToken: () => useSessionStore.getState().accessToken,
  refresh: refreshTokenOnly,
  onAuthFailure: () => useSessionStore.getState().logout(),
})
