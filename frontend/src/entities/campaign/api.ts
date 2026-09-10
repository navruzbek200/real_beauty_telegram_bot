import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type {
  AutoMessage,
  Broadcast,
  CampaignListParams,
  MessageTemplate,
} from './model/types'

function makeApi<T extends { id: number }>(basePath: string) {
  return {
    async list(params: CampaignListParams): Promise<Paginated<T>> {
      const { data, error } = await apiClient.GET(basePath as '/api/v1/message-templates/', {
        params: { query: params },
      })
      if (error) throw error
      return data as unknown as Paginated<T>
    },
    async retrieve(id: number): Promise<T> {
      const { data, error } = await apiClient.GET(
        `${basePath}{id}/` as '/api/v1/message-templates/{id}/',
        { params: { path: { id } } },
      )
      if (error) throw error
      return data as unknown as T
    },
  }
}

export const messageTemplateApi = {
  ...makeApi<MessageTemplate>('/api/v1/message-templates/'),
  async update(id: number, body: Partial<MessageTemplate>): Promise<MessageTemplate> {
    const { data, error } = await apiClient.PATCH('/api/v1/message-templates/{id}/', {
      params: { path: { id } },
      body,
    })
    if (error) throw error
    return data
  },
}


export const autoMessageApi = {
  ...makeApi<AutoMessage>('/api/v1/auto-messages/'),
  async create(body: AutoMessage): Promise<AutoMessage> {
    const { data, error } = await apiClient.POST('/api/v1/auto-messages/', { body })
    if (error) throw error
    return data
  },
  async update(id: number, body: Partial<AutoMessage>): Promise<AutoMessage> {
    const { data, error } = await apiClient.PATCH('/api/v1/auto-messages/{id}/', {
      params: { path: { id } },
      body,
    })
    if (error) throw error
    return data
  },
  async remove(id: number): Promise<void> {
    const { error } = await apiClient.DELETE('/api/v1/auto-messages/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
  },
  async testToMe(id: number): Promise<{ detail: string }> {
    const { data, error } = await apiClient.POST('/api/v1/auto-messages/{id}/test_to_me/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data
  },
}

export const broadcastApi = {
  ...makeApi<Broadcast>('/api/v1/broadcasts/'),
  async create(body: Partial<Broadcast>): Promise<Broadcast> {
    const { data, error } = await apiClient.POST('/api/v1/broadcasts/', { body: body as Broadcast })
    if (error) throw error
    return data
  },
  async update(id: number, body: Partial<Broadcast>): Promise<Broadcast> {
    const { data, error } = await apiClient.PATCH('/api/v1/broadcasts/{id}/', {
      params: { path: { id } },
      body,
    })
    if (error) throw error
    return data
  },
  async remove(id: number): Promise<void> {
    const { error } = await apiClient.DELETE('/api/v1/broadcasts/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
  },
  async testToMe(id: number): Promise<{ detail: string }> {
    const { data, error } = await apiClient.POST('/api/v1/broadcasts/{id}/test_to_me/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data
  },
  async sendNow(id: number): Promise<{ detail: string }> {
    const { data, error } = await apiClient.POST('/api/v1/broadcasts/{id}/send_now/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data
  },
}
