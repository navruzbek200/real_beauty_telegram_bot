export interface Paginated<T> {
  count: number
  next?: string | null
  previous?: string | null
  results: T[]
}

export interface ListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [filterKey: string]: string | number | undefined
}
