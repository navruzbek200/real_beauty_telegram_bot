export const env = {
  // Empty string in production: the SPA is served from the same origin as
  // the API (nginx fronts both), so requests can stay relative and need no
  // CORS at all. Local dev overrides this in .env (Vite on 5173, Django on
  // 8000 are different origins, hence CORS_ALLOWED_ORIGINS on the backend).
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
} as const
