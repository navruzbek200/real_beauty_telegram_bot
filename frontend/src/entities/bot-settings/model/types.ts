import type { Schemas } from '@/shared/api/schema'

export type Discount = Schemas['Discount']
export type GlobalSettings = Schemas['GlobalSettings']

export interface DiscountListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  is_active?: boolean
}
