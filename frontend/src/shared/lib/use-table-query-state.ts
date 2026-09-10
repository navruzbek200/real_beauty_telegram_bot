import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useDebouncedValue } from './use-debounced-value'

export interface TableQueryState {
  page: number
  pageSize: number
  search: string
  ordering: string
  filters: Record<string, string>
}

/**
 * Server-side table state (page, page size, search, ordering, arbitrary
 * filters) kept in the URL, so a link to a filtered/sorted view is shareable
 * and survives a reload. Search is debounced before it reaches the URL (and
 * therefore the query key) so typing doesn't refetch on every keystroke.
 */
export function useTableQueryState(filterKeys: readonly string[] = []) {
  const [searchParams, setSearchParams] = useSearchParams()

  const rawSearch = searchParams.get('search') ?? ''
  const debouncedSearch = useDebouncedValue(rawSearch)

  const state: TableQueryState = useMemo(() => {
    const filters: Record<string, string> = {}
    for (const key of filterKeys) {
      const value = searchParams.get(key)
      if (value) filters[key] = value
    }
    return {
      page: Number(searchParams.get('page') ?? '1') || 1,
      pageSize: Number(searchParams.get('page_size') ?? '25') || 25,
      search: debouncedSearch,
      ordering: searchParams.get('ordering') ?? '',
      filters,
    }
  }, [searchParams, debouncedSearch, filterKeys])

  const patch = useCallback(
    (next: Record<string, string | number | null | undefined>) => {
      setSearchParams(
        (prev) => {
          const params = new URLSearchParams(prev)
          for (const [key, value] of Object.entries(next)) {
            if (value === null || value === undefined || value === '') {
              params.delete(key)
            } else {
              params.set(key, String(value))
            }
          }
          return params
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  return {
    ...state,
    rawSearch,
    setPage: (page: number) => patch({ page }),
    setPageSize: (pageSize: number) => patch({ page_size: pageSize, page: 1 }),
    setSearch: (search: string) => patch({ search, page: 1 }),
    setOrdering: (ordering: string) => patch({ ordering, page: 1 }),
    setFilter: (key: string, value: string | null) => patch({ [key]: value, page: 1 }),
  }
}
