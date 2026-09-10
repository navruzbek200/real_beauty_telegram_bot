import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type { AnalyticsListParams, SkinQuizResult } from './model/types'

export const skinQuizResultApi = {
  async list(params: AnalyticsListParams): Promise<Paginated<SkinQuizResult>> {
    const { data, error } = await apiClient.GET('/api/v1/skin-quiz-results/', {
      params: { query: params },
    })
    if (error) throw error
    return data
  },
  async retrieve(id: number): Promise<SkinQuizResult> {
    const { data, error } = await apiClient.GET('/api/v1/skin-quiz-results/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data
  },
}
