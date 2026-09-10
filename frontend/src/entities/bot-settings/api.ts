import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type { Discount, DiscountListParams, GlobalSettings } from './model/types'

async function list(params: DiscountListParams): Promise<Paginated<Discount>> {
  const { data, error } = await apiClient.GET('/api/v1/discounts/', { params: { query: params } })
  if (error) throw error
  return data
}

async function retrieve(id: number): Promise<Discount> {
  const { data, error } = await apiClient.GET('/api/v1/discounts/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function create(body: Partial<Discount>): Promise<Discount> {
  const { data, error } = await apiClient.POST('/api/v1/discounts/', { body: body as Discount })
  if (error) throw error
  return data
}

async function update(id: number, body: Partial<Discount>): Promise<Discount> {
  const { data, error } = await apiClient.PATCH('/api/v1/discounts/{id}/', {
    params: { path: { id } },
    body,
  })
  if (error) throw error
  return data
}

async function remove(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/discounts/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

export const discountApi = { list, retrieve, create, update, remove }

export const globalSettingsApi = {
  async get(): Promise<GlobalSettings> {
    const { data, error } = await apiClient.GET('/api/v1/settings/global/')
    if (error) throw error
    return data
  },
  async update(body: Partial<GlobalSettings>): Promise<GlobalSettings> {
    const { data, error } = await apiClient.PATCH('/api/v1/settings/global/', { body })
    if (error) throw error
    return data
  },
}
