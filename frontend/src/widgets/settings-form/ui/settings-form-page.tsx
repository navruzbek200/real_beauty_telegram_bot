import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { Controller, useForm, type Resolver } from 'react-hook-form'

import type { SingletonApi } from '@/shared/lib/create-singleton-hooks'
import { createSingletonHooks } from '@/shared/lib/create-singleton-hooks'
import type { ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Button, FieldError, Input, Label, Select, Spinner, Textarea } from '@/shared/ui'

interface SettingsFormPageProps<T extends Record<string, unknown>> {
  title: string
  queryKey: string[]
  api: SingletonApi<T>
  config: ResourceFormConfig<T>
  canEdit: boolean
}

export function SettingsFormPage<T extends Record<string, unknown>>({
  title,
  queryKey,
  api,
  config,
  canEdit,
}: SettingsFormPageProps<T>) {
  const hooks = createSingletonHooks<T>(queryKey, api)
  const query = hooks.useSettings()
  const mutation = hooks.useUpdateSettings()

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<T>({
    resolver: zodResolver(config.schema) as Resolver<T>,
    defaultValues: config.defaultValues as never,
  })

  useEffect(() => {
    if (query.data) reset(config.toFormValues(query.data as Record<string, unknown>))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.data])

  if (query.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="max-w-xl space-y-4">
      {title && (
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
      )}
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
      >
        {config.fields.map((field) => (
          <div key={field.name}>
            <Label htmlFor={field.name}>{field.label}</Label>
            <Controller
              name={field.name as never}
              control={control}
              render={({ field: rhf }) => {
                if (field.type === 'textarea') {
                  return (
                    <Textarea id={field.name} disabled={!canEdit} {...rhf} value={(rhf.value as string) ?? ''} />
                  )
                }
                if (field.type === 'checkbox') {
                  return (
                    <input
                      id={field.name}
                      type="checkbox"
                      disabled={!canEdit}
                      checked={Boolean(rhf.value)}
                      onChange={(e) => rhf.onChange(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                  )
                }
                if (field.type === 'select') {
                  return (
                    <Select id={field.name} disabled={!canEdit} {...rhf} value={(rhf.value as string) ?? ''}>
                      {field.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </Select>
                  )
                }
                return (
                  <Input
                    id={field.name}
                    type={field.type === 'number' ? 'number' : 'text'}
                    disabled={!canEdit}
                    {...rhf}
                    value={(rhf.value as string | number) ?? ''}
                  />
                )
              }}
            />
            {field.help && <p className="mt-1 text-xs text-slate-400">{field.help}</p>}
            <FieldError message={(errors[field.name as keyof T]?.message as string) ?? undefined} />
          </div>
        ))}
        {canEdit && (
          <Button type="submit" disabled={!isDirty || mutation.isPending}>
            {mutation.isPending ? 'Saqlanmoqda...' : 'Saqlash'}
          </Button>
        )}
        {mutation.isSuccess && <p className="text-sm text-emerald-600">Saqlandi.</p>}
        {mutation.isError && <p className="text-sm text-red-600">Saqlashda xatolik.</p>}
      </form>
    </div>
  )
}
