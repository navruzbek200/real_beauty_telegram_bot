import type { Schemas } from '@/shared/api/schema'

export type MessageTemplate = Schemas['MessageTemplate']
export type AutoMessage = Schemas['AutoMessage']
export type Broadcast = Schemas['Broadcast']

export interface CampaignListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  is_active?: boolean
  [key: string]: string | number | boolean | undefined
}
