import type { Schemas } from '@/shared/api/schema'

export type LoyaltySettings = Schemas['LoyaltySettings']
export type Reward = Schemas['Reward']

export interface RewardListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  is_active?: boolean
}
