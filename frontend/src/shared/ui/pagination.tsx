import { Button } from './button'

interface PaginationProps {
  page: number
  pageSize: number
  count: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, pageSize, count, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  if (count === 0) return null

  const from = (page - 1) * pageSize + 1
  const to = Math.min(count, page * pageSize)

  return (
    <div className="flex items-center justify-between border-t border-slate-200 px-3 py-2 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
      <span>
        {from}–{to} / {count}
      </span>
      <div className="flex gap-1.5">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Oldingi
        </Button>
        <span className="px-2 py-1.5 text-xs">
          {page} / {totalPages}
        </span>
        <Button
          variant="secondary"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Keyingi
        </Button>
      </div>
    </div>
  )
}
