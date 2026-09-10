import { clsx } from 'clsx'
import type { ReactNode, ThHTMLAttributes } from 'react'

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full min-w-max text-left text-sm">{children}</table>
    </div>
  )
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-400">
      <tr>{children}</tr>
    </thead>
  )
}

interface ThProps extends ThHTMLAttributes<HTMLTableCellElement> {
  sortable?: boolean
  sortDirection?: 'asc' | 'desc' | null
  onSort?: () => void
}

export function Th({ sortable, sortDirection, onSort, className, children, ...props }: ThProps) {
  if (!sortable) {
    return (
      <th className={clsx('px-3 py-2 font-medium', className)} {...props}>
        {children}
      </th>
    )
  }
  return (
    <th className={clsx('px-3 py-2 font-medium', className)} {...props}>
      <button
        type="button"
        onClick={onSort}
        className="inline-flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200"
      >
        {children}
        <span className="text-[10px]">
          {sortDirection === 'asc' ? '▲' : sortDirection === 'desc' ? '▼' : '↕'}
        </span>
      </button>
    </th>
  )
}

export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-slate-100 dark:divide-slate-800">{children}</tbody>
}

export function Tr({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <tr className={clsx('hover:bg-slate-50 dark:hover:bg-slate-800/60', className)}>{children}</tr>
  )
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={clsx('px-3 py-2 align-middle', className)}>{children}</td>
}
