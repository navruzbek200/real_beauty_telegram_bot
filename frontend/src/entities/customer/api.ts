import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type { Customer, CustomerListParams, UserProduct } from './model/types'

async function list(params: CustomerListParams): Promise<Paginated<Customer>> {
  const { data, error } = await apiClient.GET('/api/v1/customers/', { params: { query: params } })
  if (error) throw error
  return data
}

async function retrieve(id: number): Promise<Customer> {
  const { data, error } = await apiClient.GET('/api/v1/customers/{id}/', { params: { path: { id } } })
  if (error) throw error
  return data
}

async function create(body: Partial<Customer>): Promise<Customer> {
  const { data, error } = await apiClient.POST('/api/v1/customers/', { body: body as Customer })
  if (error) throw error
  return data
}

async function update(id: number, body: Partial<Customer>): Promise<Customer> {
  const { data, error } = await apiClient.PATCH('/api/v1/customers/{id}/', {
    params: { path: { id } },
    body,
  })
  if (error) throw error
  return data
}

async function remove(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/customers/{id}/', { params: { path: { id } } })
  if (error) throw error
}

export const customerApi = { list, retrieve, create, update, remove }

async function listUserProducts(params: CustomerListParams): Promise<Paginated<UserProduct>> {
  const { data, error } = await apiClient.GET('/api/v1/user-products/', {
    params: { query: params },
  })
  if (error) throw error
  return data
}

async function createUserProduct(body: { user: number; product: number }): Promise<UserProduct> {
  const { data, error } = await apiClient.POST('/api/v1/user-products/', {
    body: body as UserProduct,
  })
  if (error) throw error
  return data
}

async function removeUserProduct(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/user-products/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

async function retrieveUserProduct(id: number): Promise<UserProduct> {
  const { data, error } = await apiClient.GET('/api/v1/user-products/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

export const userProductApi = {
  list: listUserProducts,
  retrieve: retrieveUserProduct,
  create: createUserProduct,
  remove: removeUserProduct,
}
