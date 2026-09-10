import type { Schemas } from '@/shared/api/schema'

export type Product = Schemas['Product']
export type ProductTutorialStep = Schemas['ProductTutorialStep']
export type TopProduct = Schemas['TopProduct']

export interface ProductListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  is_active?: boolean
  is_top?: boolean
}

export interface TutorialStepListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  product?: number
}
