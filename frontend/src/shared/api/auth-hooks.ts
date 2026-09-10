/**
 * Extension point the http client calls into for auth — kept dependency-free
 * so `shared` never has to import `entities/session` (FSD forbids importing
 * upward). `entities/session` wires these in once, at app bootstrap.
 */
interface AuthHooks {
  getAccessToken: () => string | null
  refresh: () => Promise<string | null>
  onAuthFailure: () => void
}

let hooks: AuthHooks = {
  getAccessToken: () => null,
  refresh: async () => null,
  onAuthFailure: () => {},
}

export function configureAuthHooks(next: AuthHooks): void {
  hooks = next
}

export function getAuthHooks(): AuthHooks {
  return hooks
}
