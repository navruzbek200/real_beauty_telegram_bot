import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type { Staff, StaffListParams } from './model/types'

async function list(params: StaffListParams): Promise<Paginated<Staff>> {
  const { data, error } = await apiClient.GET('/api/v1/staff/', { params: { query: params } })
  if (error) throw error
  return data
}

async function retrieve(id: number): Promise<Staff> {
  const { data, error } = await apiClient.GET('/api/v1/staff/{id}/', { params: { path: { id } } })
  if (error) throw error
  return data
}

async function create(body: Staff): Promise<Staff> {
  const { data, error } = await apiClient.POST('/api/v1/staff/', { body })
  if (error) throw error
  return data
}

async function update(id: number, body: Partial<Staff>): Promise<Staff> {
  const { data, error } = await apiClient.PATCH('/api/v1/staff/{id}/', {
    params: { path: { id } },
    body,
  })
  if (error) throw error
  return data
}

async function remove(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/staff/{id}/', { params: { path: { id } } })
  if (error) throw error
}

export const staffApi = { list, retrieve, create, update, remove }
