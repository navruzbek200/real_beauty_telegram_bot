import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type { AccessCode, LessonListParams, LessonUnlock, LessonVideo } from './model/types'

/* ------------------------------------------------------------------ videos */

async function listVideos(params: LessonListParams): Promise<Paginated<LessonVideo>> {
  const { data, error } = await apiClient.GET('/api/v1/lesson-videos/', {
    params: { query: params },
  })
  if (error) throw error
  return data
}

async function retrieveVideo(id: number): Promise<LessonVideo> {
  const { data, error } = await apiClient.GET('/api/v1/lesson-videos/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function createVideo(body: FormData): Promise<LessonVideo> {
  const { data, error } = await apiClient.POST('/api/v1/lesson-videos/', {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function updateVideo(id: number, body: FormData): Promise<LessonVideo> {
  const { data, error } = await apiClient.PATCH('/api/v1/lesson-videos/{id}/', {
    params: { path: { id } },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function removeVideo(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/lesson-videos/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

export const lessonVideoApi = {
  list: listVideos,
  retrieve: retrieveVideo,
  create: createVideo,
  update: updateVideo,
  remove: removeVideo,
}

/* ------------------------------------------------------------------- codes */

async function listCodes(params: LessonListParams): Promise<Paginated<AccessCode>> {
  const { data, error } = await apiClient.GET('/api/v1/access-codes/', {
    params: { query: params },
  })
  if (error) throw error
  return data
}

async function retrieveCode(id: number): Promise<AccessCode> {
  const { data, error } = await apiClient.GET('/api/v1/access-codes/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function createCode(body: Record<string, unknown>): Promise<AccessCode> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- shared JSON body shape
  const { data, error } = await apiClient.POST('/api/v1/access-codes/', { body: body as any })
  if (error) throw error
  return data
}

async function updateCode(id: number, body: Record<string, unknown>): Promise<AccessCode> {
  const { data, error } = await apiClient.PATCH('/api/v1/access-codes/{id}/', {
    params: { path: { id } },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- shared JSON body shape
    body: body as any,
  })
  if (error) throw error
  return data
}

async function removeCode(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/access-codes/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

async function issueCodes(count: number): Promise<string[]> {
  const { data, error } = await apiClient.POST('/api/v1/access-codes/issue/', {
    body: { count },
  })
  if (error) throw error
  return data.codes
}

export const accessCodeApi = {
  list: listCodes,
  retrieve: retrieveCode,
  create: createCode,
  update: updateCode,
  remove: removeCode,
  issue: issueCodes,
}

/* ----------------------------------------------------------------- unlocks */

async function listUnlocks(params: LessonListParams): Promise<Paginated<LessonUnlock>> {
  const { data, error } = await apiClient.GET('/api/v1/lesson-unlocks/', {
    params: { query: params },
  })
  if (error) throw error
  return data
}

async function createUnlock(body: Record<string, unknown>): Promise<LessonUnlock> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- shared JSON body shape
  const { data, error } = await apiClient.POST('/api/v1/lesson-unlocks/', { body: body as any })
  if (error) throw error
  return data
}

async function removeUnlock(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/lesson-unlocks/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

export const lessonUnlockApi = {
  list: listUnlocks,
  // The resource page expects a retrieve; unlocks are never edited, so the
  // list row it already holds is the whole record.
  retrieve: async (id: number) => ({ id }) as unknown as LessonUnlock,
  create: createUnlock,
  update: async () => {
    throw new Error('Ochilgan darsni tahrirlab bo‘lmaydi')
  },
  remove: removeUnlock,
}
