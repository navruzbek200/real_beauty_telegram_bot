import type { Schemas } from '@/shared/api/schema'

export type SupportThread = Schemas['SupportThread'] & { messages?: SupportMessage[] }
export type SupportMessage = Schemas['SupportMessage']
export type SupportSettings = Schemas['SupportSettings']
export type SupportAdmin = Schemas['SupportAdmin']

export interface SupportListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: string | number | boolean | undefined
}
