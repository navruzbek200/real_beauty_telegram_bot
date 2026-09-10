import { apiClient } from '@/shared/api/client'
import type { Paginated } from '@/shared/api/types'
import type {
  Product,
  ProductListParams,
  ProductTutorialStep,
  TopProduct,
  TutorialStepListParams,
} from './model/types'

async function list(params: ProductListParams): Promise<Paginated<Product>> {
  const { data, error } = await apiClient.GET('/api/v1/products/', { params: { query: params } })
  if (error) throw error
  return data
}

async function retrieve(id: number): Promise<Product> {
  const { data, error } = await apiClient.GET('/api/v1/products/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function create(body: FormData): Promise<Product> {
  const { data, error } = await apiClient.POST('/api/v1/products/', {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body, see note in create-resource-hooks usage
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function update(id: number, body: FormData): Promise<Product> {
  const { data, error } = await apiClient.PATCH('/api/v1/products/{id}/', {
    params: { path: { id } },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function remove(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/products/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

async function addToTop(ids: number[]): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/products/add_to_top/', { body: { ids } })
  if (error) throw error
}

async function removeFromTop(ids: number[]): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/products/remove_from_top/', { body: { ids } })
  if (error) throw error
}

export const productApi = { list, retrieve, create, update, remove, addToTop, removeFromTop }

async function listTop(params: ProductListParams): Promise<Paginated<TopProduct>> {
  const { data, error } = await apiClient.GET('/api/v1/top-products/', {
    params: { query: params },
  })
  if (error) throw error
  return data
}

async function retrieveTop(id: number): Promise<TopProduct> {
  const { data, error } = await apiClient.GET('/api/v1/top-products/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function createTop(body: FormData): Promise<TopProduct> {
  const { data, error } = await apiClient.POST('/api/v1/top-products/', {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function updateTop(id: number, body: FormData): Promise<TopProduct> {
  const { data, error } = await apiClient.PATCH('/api/v1/top-products/{id}/', {
    params: { path: { id } },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function removeTop(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/top-products/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

async function reorderTop(ids: number[]): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/top-products/reorder/', { body: { ids } })
  if (error) throw error
}

export const topProductApi = {
  list: listTop,
  retrieve: retrieveTop,
  create: createTop,
  update: updateTop,
  remove: removeTop,
  reorder: reorderTop,
}

async function listTutorialSteps(
  params: TutorialStepListParams,
): Promise<Paginated<ProductTutorialStep>> {
  const { data, error } = await apiClient.GET('/api/v1/product-tutorial-steps/', {
    params: { query: params },
  })
  if (error) throw error
  return data
}

async function retrieveTutorialStep(id: number): Promise<ProductTutorialStep> {
  const { data, error } = await apiClient.GET('/api/v1/product-tutorial-steps/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
  return data
}

async function createTutorialStep(body: FormData): Promise<ProductTutorialStep> {
  const { data, error } = await apiClient.POST('/api/v1/product-tutorial-steps/', {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function updateTutorialStep(id: number, body: FormData): Promise<ProductTutorialStep> {
  const { data, error } = await apiClient.PATCH('/api/v1/product-tutorial-steps/{id}/', {
    params: { path: { id } },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- multipart body
    body: body as any,
    bodySerializer: (b) => b,
  })
  if (error) throw error
  return data
}

async function removeTutorialStep(id: number): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/product-tutorial-steps/{id}/', {
    params: { path: { id } },
  })
  if (error) throw error
}

export const tutorialStepApi = {
  list: listTutorialSteps,
  retrieve: retrieveTutorialStep,
  create: createTutorialStep,
  update: updateTutorialStep,
  remove: removeTutorialStep,
}
