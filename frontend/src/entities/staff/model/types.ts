import type { Schemas } from '@/shared/api/schema'

export type Staff = Schemas['Staff']

export interface StaffListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
}
