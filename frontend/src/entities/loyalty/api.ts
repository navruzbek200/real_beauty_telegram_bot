import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type { LoyaltySettings, Reward, RewardListParams } from './model/types'

export const loyaltySettingsApi = {
  async get(): Promise<LoyaltySettings> {
    const { data, error } = await apiClient.GET('/api/v1/settings/rewards/')
    if (error) throw error
    return data
  },
  async update(body: Partial<LoyaltySettings>): Promise<LoyaltySettings> {
    const { data, error } = await apiClient.PATCH('/api/v1/settings/rewards/', { body })
    if (error) throw error
    return data
  },
}

async function list(params: RewardListParams): Promise<Paginated<Reward>> {
  const { data, error } = await apiClient.GET('/api/v1/rewards/', { params: { query: params } })
  if (error) throw error
  return data
}

async function retrieve(id: number): Promise<Reward> {
  const { data, error } = await apiClient.GET('/api/v1/rewards/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function create(body: Partial<Reward>): Promise<Reward> {
  const { data, error } = await apiClient.POST('/api/v1/rewards/', { body: body as Reward })
  if (error) throw error
  return data
}

async function update(id: number, body: Partial<Reward>): Promise<Reward> {
  const { data, error } = await apiClient.PATCH('/api/v1/rewards/{id}/', {
    params: { path: { id } },
    body,
  })
  if (error) throw error
  return data
}

async function remove(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/rewards/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

export const rewardApi = { list, retrieve, create, update, remove }
