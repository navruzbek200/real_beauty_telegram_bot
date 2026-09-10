import createClient from 'openapi-fetch'

import { env } from '@/shared/config/env'
import type { paths } from '@/shared/api/schema'

// Unauthenticated client — used only for login/refresh, which must not go
// through the main client's auth-header/401-retry middleware (that would be
// circular: refreshing needs its own unauthenticated call).
const authClient = createClient<paths>({ baseUrl: env.apiBaseUrl })

export async function login(username: string, password: string) {
  const { data, error } = await authClient.POST('/api/v1/auth/login/', {
    body: { username, password },
  })
  if (error) throw error
  return data
}

export async function refreshAccessToken(refresh: string) {
  const { data, error } = await authClient.POST('/api/v1/auth/refresh/', {
    body: { refresh },
  })
  if (error) throw error
  return data
}

export async function fetchMe(accessToken: string) {
  const { data, error } = await authClient.GET('/api/v1/auth/me/', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (error) throw error
  return data
}
