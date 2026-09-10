import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, type Resolver } from 'react-hook-form'

import type { ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Button, Dialog, FieldError, Input, Label, Select, Textarea } from '@/shared/ui'

interface ResourceFormDialogProps<TFormValues extends Record<string, unknown>> {
  open: boolean
  title: string
  config: ResourceFormConfig<TFormValues>
  initialValues?: TFormValues
  // The raw record being edited, used to preview an existing image next to a
  // file input (a file field can't hold the saved URL, so it would otherwise
  // look empty — "nega rasmi yo'q").
  currentItem?: Record<string, unknown>
  pending?: boolean
  serverError?: string
  onSubmit: (values: TFormValues) => void
  onClose: () => void
}

export function ResourceFormDialog<TFormValues extends Record<string, unknown>>({
  open,
  title,
  config,
  initialValues,
  currentItem,
  pending,
  serverError,
  onSubmit,
  onClose,
}: ResourceFormDialogProps<TFormValues>) {
  const {
    control,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<TFormValues>({
    resolver: zodResolver(config.schema) as Resolver<TFormValues>,
    values: initialValues ?? config.defaultValues,
  })

  useEffect(() => {
    if (open) {
      reset(initialValues ?? config.defaultValues)
    }
  }, [open, initialValues, reset, config.defaultValues])

  if (!open) return null

  return (
    <Dialog
      open={open}
      title={title}
      onClose={() => {
        reset()
        onClose()
      }}
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        encType={config.fields.some((f) => f.type === 'file') ? 'multipart/form-data' : undefined}
      >
        {config.fields.map((field) => (
          <div key={field.name}>
            <Label htmlFor={field.name}>{field.label}</Label>
            <Controller
              name={field.name as never}
              control={control}
              render={({ field: rhf }) => {
                if (field.type === 'textarea') {
                  return <Textarea id={field.name} {...rhf} value={(rhf.value as string) ?? ''} />
                }
                if (field.type === 'checkbox') {
                  return (
                    <input
                      id={field.name}
                      type="checkbox"
                      checked={Boolean(rhf.value)}
                      onChange={(e) => rhf.onChange(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                  )
                }
                if (field.type === 'select') {
                  return (
                    <Select id={field.name} {...rhf} value={(rhf.value as string) ?? ''}>
                      <option value="">—</option>
                      {field.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </Select>
                  )
                }
                if (field.type === 'date') {
                  // Native date picker — the value is always YYYY-MM-DD, so the
                  // server's DateField never sees a malformed string.
                  return (
                    <Input
                      id={field.name}
                      type="date"
                      {...rhf}
                      value={(rhf.value as string) ?? ''}
                    />
                  )
                }
                if (field.type === 'file') {
                  const existing = currentItem?.[field.name]
                  const previewUrl =
                    typeof existing === 'string' && existing ? existing : undefined
                  const picked = (rhf.value as unknown) instanceof File ? (rhf.value as File) : undefined
                  const shownUrl = picked ? URL.createObjectURL(picked) : previewUrl
                  return (
                    <div className="space-y-2">
                      {shownUrl && (
                        <img
                          src={shownUrl}
                          alt=""
                          className="h-24 w-24 rounded-lg border border-slate-200 object-cover dark:border-slate-700"
                        />
                      )}
                      <input
                        id={field.name}
                        type="file"
                        accept="image/*"
                        onChange={(e) => rhf.onChange(e.target.files?.[0])}
                        className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm dark:text-slate-300 dark:file:bg-slate-700"
                      />
                    </div>
                  )
                }
                return (
                  <Input
                    id={field.name}
                    type={field.type === 'number' ? 'number' : 'text'}
                    {...rhf}
                    value={(rhf.value as string | number) ?? ''}
                  />
                )
              }}
            />
            {field.help && <p className="mt-1 text-xs text-slate-400">{field.help}</p>}
            <FieldError message={(errors[field.name as keyof TFormValues]?.message as string) ?? undefined} />
          </div>
        ))}
        {serverError && (
          <div className="whitespace-pre-line rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
            {serverError}
          </div>
        )}
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
          <Button type="button" variant="secondary" onClick={onClose} disabled={pending}>
            Bekor qilish
          </Button>
          <Button type="submit" loading={pending}>
            {pending ? 'Saqlanmoqda...' : 'Saqlash'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
