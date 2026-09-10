import type { Schemas } from '@/shared/api/schema'

export type SkinQuizResult = Schemas['SkinQuizResult']

export interface AnalyticsListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: string | number | boolean | undefined
}
