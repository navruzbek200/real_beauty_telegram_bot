import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type {
  SupportAdmin,
  SupportListParams,
  SupportSettings,
  SupportThread,
} from './model/types'

export const supportThreadApi = {
  async list(params: SupportListParams): Promise<Paginated<SupportThread>> {
    const { data, error } = await apiClient.GET('/api/v1/support-threads/', {
      params: { query: params },
    })
    if (error) throw error
    return data as Paginated<SupportThread>
  },
  async retrieve(id: number): Promise<SupportThread> {
    const { data, error } = await apiClient.GET('/api/v1/support-threads/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data as SupportThread
  },
  async remove(id: number): Promise<void> {
    const { error } = await apiClient.DELETE('/api/v1/support-threads/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
  },
}

export const supportAdminApi = {
  async list(params: SupportListParams): Promise<Paginated<SupportAdmin>> {
    const { data, error } = await apiClient.GET('/api/v1/support-admins/', {
      params: { query: params },
    })
    if (error) throw error
    return data
  },
  async retrieve(id: number): Promise<SupportAdmin> {
    const { data, error } = await apiClient.GET('/api/v1/support-admins/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data
  },
  async create(body: SupportAdmin): Promise<SupportAdmin> {
    const { data, error } = await apiClient.POST('/api/v1/support-admins/', { body })
    if (error) throw error
    return data
  },
  async update(id: number, body: Partial<SupportAdmin>): Promise<SupportAdmin> {
    const { data, error } = await apiClient.PATCH('/api/v1/support-admins/{id}/', {
      params: { path: { id } },
      body,
    })
    if (error) throw error
    return data
  },
  async remove(id: number): Promise<void> {
    const { error } = await apiClient.DELETE('/api/v1/support-admins/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
  },
}

export const supportSettingsApi = {
  async get(): Promise<SupportSettings> {
    const { data, error } = await apiClient.GET('/api/v1/settings/support/')
    if (error) throw error
    return data
  },
  async update(body: Partial<SupportSettings>): Promise<SupportSettings> {
    const { data, error } = await apiClient.PATCH('/api/v1/settings/support/', { body })
    if (error) throw error
    return data
  },
  async testConnection(): Promise<SupportSettings> {
    const { data, error } = await apiClient.POST('/api/v1/settings/support/test-connection/')
    if (error) throw error
    return data
  },
}
