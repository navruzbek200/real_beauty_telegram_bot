import { clsx } from 'clsx'
import type { ButtonHTMLAttributes } from 'react'

import { Spinner } from './spinner'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    'bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800 focus-visible:ring-brand-500 disabled:bg-brand-300 disabled:shadow-none',
  secondary:
    'bg-white text-slate-700 border border-slate-300 shadow-sm hover:bg-slate-50 active:bg-slate-100 focus-visible:ring-brand-500 disabled:text-slate-400 disabled:shadow-none dark:bg-slate-800 dark:text-slate-100 dark:border-slate-600 dark:hover:bg-slate-700',
  danger:
    'bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800 focus-visible:ring-red-500 disabled:bg-red-300 disabled:shadow-none',
  ghost:
    'bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 active:bg-slate-200 focus-visible:ring-brand-500 disabled:text-slate-300 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100',
}

const SIZE_CLASSES: Record<Size, string> = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-3.5 py-2 text-sm',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'relative inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-transparent',
        'disabled:cursor-not-allowed',
        SIZE_CLASSES[size],
        VARIANT_CLASSES[variant],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <Spinner className={clsx('h-4 w-4', variant === 'secondary' || variant === 'ghost' ? 'text-current' : 'text-white')} />
      )}
      {children}
    </button>
  )
}
