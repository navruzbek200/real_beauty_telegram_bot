import { useMutation, useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query'

import type { ListParams, Paginated } from '@/shared/api/types'

export interface ResourceApi<T, TCreate, TUpdate> {
  list: (params: ListParams) => Promise<Paginated<T>>
  retrieve: (id: number) => Promise<T>
  create?: (data: TCreate) => Promise<T>
  update?: (id: number, data: TUpdate) => Promise<T>
  remove?: (id: number) => Promise<void>
}

interface WithId {
  id: number
}

/**
 * One factory backing every entity's list/detail/create/update/delete hooks,
 * so each `features/<entity>` slice only has to describe *what* it is (the
 * api + query key), not re-derive cache invalidation and optimistic-update
 * plumbing 20 times over.
 */
export function createResourceHooks<T extends WithId, TCreate = Partial<T>, TUpdate = Partial<T>>(
  queryKey: QueryKey,
  api: ResourceApi<T, TCreate, TUpdate>,
) {
  function useList(params: ListParams) {
    return useQuery({
      queryKey: [...queryKey, 'list', params],
      queryFn: () => api.list(params),
      placeholderData: (previous) => previous,
    })
  }

  function useDetail(id: number | undefined) {
    return useQuery({
      queryKey: [...queryKey, 'detail', id],
      queryFn: () => api.retrieve(id as number),
      enabled: id !== undefined,
    })
  }

  function useCreate() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: (data: TCreate) => {
        if (!api.create) throw new Error('create not supported')
        return api.create(data)
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: [...queryKey, 'list'] })
      },
    })
  }

  function useUpdate() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: ({ id, data }: { id: number; data: TUpdate }) => {
        if (!api.update) throw new Error('update not supported')
        return api.update(id, data)
      },
      onMutate: async ({ id, data }) => {
        await queryClient.cancelQueries({ queryKey })
        const previousLists = queryClient.getQueriesData<Paginated<T>>({
          queryKey: [...queryKey, 'list'],
        })
        for (const [key, page] of previousLists) {
          if (!page) continue
          queryClient.setQueryData<Paginated<T>>(key, {
            ...page,
            results: page.results.map((item) =>
              item.id === id ? { ...item, ...(data as Partial<T>) } : item,
            ),
          })
        }
        const previousDetail = queryClient.getQueryData<T>([...queryKey, 'detail', id])
        if (previousDetail) {
          queryClient.setQueryData<T>([...queryKey, 'detail', id], {
            ...previousDetail,
            ...(data as Partial<T>),
          })
        }
        return { previousLists, previousDetail, id }
      },
      onError: (_err, _vars, context) => {
        if (!context) return
        for (const [key, page] of context.previousLists) {
          queryClient.setQueryData(key, page)
        }
        if (context.previousDetail) {
          queryClient.setQueryData([...queryKey, 'detail', context.id], context.previousDetail)
        }
      },
      onSettled: () => {
        queryClient.invalidateQueries({ queryKey })
      },
    })
  }

  function useRemove() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: (id: number) => {
        if (!api.remove) throw new Error('remove not supported')
        return api.remove(id)
      },
      onMutate: async (id: number) => {
        await queryClient.cancelQueries({ queryKey: [...queryKey, 'list'] })
        const previousLists = queryClient.getQueriesData<Paginated<T>>({
          queryKey: [...queryKey, 'list'],
        })
        for (const [key, page] of previousLists) {
          if (!page) continue
          queryClient.setQueryData<Paginated<T>>(key, {
            ...page,
            count: Math.max(0, page.count - 1),
            results: page.results.filter((item) => item.id !== id),
          })
        }
        return { previousLists }
      },
      onError: (_err, _id, context) => {
        if (!context) return
        for (const [key, page] of context.previousLists) {
          queryClient.setQueryData(key, page)
        }
      },
      onSettled: () => {
        queryClient.invalidateQueries({ queryKey: [...queryKey, 'list'] })
      },
    })
  }

  return { useList, useDetail, useCreate, useUpdate, useRemove }
}
