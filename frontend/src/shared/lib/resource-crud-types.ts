import type { ReactNode } from 'react'
import type { z } from 'zod'

export interface ResourceColumn<T> {
  key: string
  header: string
  sortField?: string
  render: (item: T) => ReactNode
}

export type FieldType = 'text' | 'textarea' | 'number' | 'checkbox' | 'select' | 'file' | 'date'

export interface ResourceFormField {
  name: string
  label: string
  type: FieldType
  options?: { value: string; label: string }[]
  help?: string
}

export interface ResourcePermissions {
  add?: string
  change?: string
  delete?: string
}

export interface ResourceFormConfig<TFormValues extends Record<string, unknown>> {
  fields: ResourceFormField[]
  schema: z.ZodType<TFormValues>
  defaultValues: TFormValues
  /** Populate the form when editing an existing row. */
  toFormValues: (item: Record<string, unknown>) => TFormValues
}
