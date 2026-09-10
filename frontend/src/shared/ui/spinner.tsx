import { clsx } from 'clsx'

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={clsx('animate-spin text-brand-600', className)}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      role="status"
      aria-label="Yuklanmoqda"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}
