import createClient, { type Middleware } from 'openapi-fetch'

import { getAuthHooks } from './auth-hooks'
import { env } from '@/shared/config/env'
import type { paths } from '@/shared/api/schema'

const RETRY_HEADER = 'X-Retried-After-Refresh'

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getAuthHooks().getAccessToken()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || request.headers.has(RETRY_HEADER)) {
      return response
    }

    const newToken = await getAuthHooks().refresh()
    if (!newToken) {
      getAuthHooks().onAuthFailure()
      return response
    }

    const retried = request.clone()
    retried.headers.set('Authorization', `Bearer ${newToken}`)
    retried.headers.set(RETRY_HEADER, '1')
    const retryResponse = await fetch(retried)
    if (retryResponse.status === 401) {
      getAuthHooks().onAuthFailure()
    }
    return retryResponse
  },
}

export const apiClient = createClient<paths>({ baseUrl: env.apiBaseUrl })
apiClient.use(authMiddleware)
