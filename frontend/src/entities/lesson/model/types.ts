import type { Schemas } from '@/shared/api/schema'

export type LessonVideo = Schemas['LessonVideo']
export type AccessCode = Schemas['AccessCode']
export type LessonUnlock = Schemas['LessonUnlock']

export interface LessonListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  is_active?: boolean
}
