import { Button } from './button'
import { Dialog } from './dialog'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  danger?: boolean
  pending?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Ha, davom eting',
  danger,
  pending,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} title={title} onClose={onCancel} widthClassName="max-w-md">
      <div className="flex gap-3">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
            danger
              ? 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400'
              : 'bg-brand-100 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300'
          }`}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {danger ? (
              <>
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
                <path d="M12 9v4M12 17h.01" />
              </>
            ) : (
              <path d="M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z" />
            )}
          </svg>
        </div>
        <p className="pt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{message}</p>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel} disabled={pending}>
          Bekor qilish
        </Button>
        <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={pending}>
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  )
}
