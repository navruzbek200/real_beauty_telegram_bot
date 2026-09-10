import { apiClient } from '@/shared/api/client'
import type { ListParams, Paginated } from '@/shared/api/types'
import type { Order } from './model/types'

export const orderApi = {
  async list(params: ListParams): Promise<Paginated<Order>> {
    const { data, error } = await apiClient.GET('/api/v1/orders/', {
      params: { query: params },
    })
    if (error) throw error
    return data as unknown as Paginated<Order>
  },
  async retrieve(id: number): Promise<Order> {
    const { data, error } = await apiClient.GET('/api/v1/orders/{id}/', {
      params: { path: { id } },
    })
    if (error) throw error
    return data as unknown as Order
  },
  async update(id: number, body: Partial<Order>): Promise<Order> {
    const { data, error } = await apiClient.PATCH('/api/v1/orders/{id}/', {
      params: { path: { id } },
      body: body as never,
    })
    if (error) throw error
    return data as unknown as Order
  },
  async resendInvoice(id: number): Promise<Order> {
    const { data, error } = await apiClient.POST(
      '/api/v1/orders/{id}/resend_invoice/',
      { params: { path: { id } } },
    )
    if (error) throw error
    return data as unknown as Order
  },
}
