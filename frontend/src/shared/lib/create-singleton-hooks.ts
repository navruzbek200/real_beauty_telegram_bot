import { useMutation, useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query'

export interface SingletonApi<T> {
  get: () => Promise<T>
  update: (data: Partial<T>) => Promise<T>
}

/** Backs settings-style singleton pages (GlobalSettings, LoyaltySettings,
 * SupportSettings) — no list, no id, just GET + PATCH one object. */
export function createSingletonHooks<T>(queryKey: QueryKey, api: SingletonApi<T>) {
  function useSettings() {
    return useQuery({ queryKey, queryFn: api.get })
  }

  function useUpdateSettings() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: (data: Partial<T>) => api.update(data),
      onSuccess: (data) => {
        queryClient.setQueryData(queryKey, data)
      },
    })
  }

  return { useSettings, useUpdateSettings }
}
