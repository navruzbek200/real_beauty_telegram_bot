import { useState, type ReactNode } from 'react'

import type { ResourceApi } from '@/shared/lib/create-resource-hooks'
import { createResourceHooks } from '@/shared/lib/create-resource-hooks'
import { useTableQueryState } from '@/shared/lib/use-table-query-state'
import { Button, ConfirmDialog, EmptyState, Input, PageHeader, Pagination, Spinner, Table, TableBody, TableHead, Td, Th, Tr } from '@/shared/ui'
import { hasPermission, useSessionStore } from '@/entities/session'
import type {
  ResourceColumn,
  ResourceFormConfig,
  ResourcePermissions,
} from '@/shared/lib/resource-crud-types'
import { ResourceFormDialog } from './resource-form-dialog'

interface WithId {
  id: number
}

// Turn a DRF error body ({field: ["msg", ...]} or {detail: "..."}) into one
// readable line, so the dialog says *which* field is wrong instead of a blanket
// "check the fields". Falls back to a generic note for network/other errors.
function formatServerError(error: unknown): string {
  const generic = "Saqlashda xatolik yuz berdi. Maydonlarni tekshiring."
  if (!error || typeof error !== 'object') return generic
  const body = error as Record<string, unknown>
  if (typeof body.detail === 'string') return body.detail
  const parts: string[] = []
  for (const [field, value] of Object.entries(body)) {
    const msg = Array.isArray(value) ? value.join(' ') : String(value)
    parts.push(field === 'non_field_errors' ? msg : `${field}: ${msg}`)
  }
  return parts.length ? parts.join('\n') : generic
}

interface ResourcePageProps<
  T extends WithId,
  TFormValues extends Record<string, unknown>,
  TCreate,
  TUpdate,
> {
  title: string
  api: ResourceApi<T, TCreate, TUpdate>
  queryKey: string[]
  columns: ResourceColumn<T>[]
  filterKeys?: string[]
  searchPlaceholder?: string
  permissions?: ResourcePermissions
  formConfig?: ResourceFormConfig<TFormValues>
  toCreatePayload?: (values: TFormValues) => TCreate
  toUpdatePayload?: (values: TFormValues) => TUpdate
  filterBar?: (helpers: ReturnType<typeof useTableQueryState>) => ReactNode
  rowActions?: (item: T) => ReactNode
  createLabel?: string
}

export function ResourcePage<
  T extends WithId,
  TFormValues extends Record<string, unknown> = Record<string, unknown>,
  TCreate = Partial<T>,
  TUpdate = Partial<T>,
>({
  title,
  api,
  queryKey,
  columns,
  filterKeys = [],
  searchPlaceholder = 'Qidirish...',
  permissions,
  formConfig,
  toCreatePayload,
  toUpdatePayload,
  filterBar,
  rowActions,
  createLabel = '+ Qo\'shish',
}: ResourcePageProps<T, TFormValues, TCreate, TUpdate>) {
  const user = useSessionStore((s) => s.user)
  const hooks = createResourceHooks<T, TCreate, TUpdate>(queryKey, api)
  const tableState = useTableQueryState(filterKeys)
  const [editing, setEditing] = useState<T | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<T | null>(null)
  const [formError, setFormError] = useState<string>()

  const listQuery = hooks.useList({
    page: tableState.page,
    page_size: tableState.pageSize,
    search: tableState.search || undefined,
    ordering: tableState.ordering || undefined,
    ...tableState.filters,
  })
  const createMutation = hooks.useCreate()
  const updateMutation = hooks.useUpdate()
  const removeMutation = hooks.useRemove()

  const canAdd = permissions?.add ? hasPermission(user, permissions.add) : false
  const canChange = permissions?.change ? hasPermission(user, permissions.change) : false
  const canDelete = permissions?.delete ? hasPermission(user, permissions.delete) : false

  function toggleSort(field: string) {
    const current = tableState.ordering
    if (current === field) tableState.setOrdering(`-${field}`)
    else if (current === `-${field}`) tableState.setOrdering('')
    else tableState.setOrdering(field)
  }

  function sortDirection(field: string): 'asc' | 'desc' | null {
    if (tableState.ordering === field) return 'asc'
    if (tableState.ordering === `-${field}`) return 'desc'
    return null
  }

  async function handleCreate(values: TFormValues) {
    if (!toCreatePayload) return
    setFormError(undefined)
    try {
      await createMutation.mutateAsync(toCreatePayload(values))
      setCreating(false)
    } catch (error) {
      setFormError(formatServerError(error))
    }
  }

  async function handleUpdate(values: TFormValues) {
    if (!editing || !toUpdatePayload) return
    setFormError(undefined)
    try {
      await updateMutation.mutateAsync({ id: editing.id, data: toUpdatePayload(values) })
      setEditing(null)
    } catch (error) {
      setFormError(formatServerError(error))
    }
  }

  async function handleDelete() {
    if (!deleting) return
    await removeMutation.mutateAsync(deleting.id)
    setDeleting(null)
  }

  const addButton =
    canAdd && formConfig ? <Button onClick={() => setCreating(true)}>{createLabel}</Button> : null

  return (
    <div className="space-y-4">
      {(title || addButton) && (
        <PageHeader
          title={title}
          count={listQuery.data?.count}
          actions={addButton}
        />
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative max-w-xs flex-1">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <Input
            placeholder={searchPlaceholder}
            value={tableState.rawSearch}
            onChange={(e) => tableState.setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        {filterBar?.(tableState)}
      </div>

      {listQuery.isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : listQuery.isError ? (
        <EmptyState
          tone="error"
          message="Ma'lumotlarni yuklab bo'lmadi."
          hint="Internet aloqasini tekshirib, sahifani yangilang."
          action={
            <Button variant="secondary" onClick={() => listQuery.refetch()}>
              Qayta urinish
            </Button>
          }
        />
      ) : listQuery.data && listQuery.data.results.length === 0 ? (
        <EmptyState
          message={tableState.search ? 'Qidiruv bo\'yicha natija topilmadi.' : "Hozircha yozuvlar yo'q."}
          hint={tableState.search ? 'Boshqa so\'z bilan urinib ko\'ring.' : undefined}
          action={!tableState.search ? addButton : undefined}
        />
      ) : listQuery.data ? (
        <Table>
          <TableHead>
            {columns.map((col) => (
              <Th
                key={col.key}
                sortable={Boolean(col.sortField)}
                sortDirection={col.sortField ? sortDirection(col.sortField) : null}
                onSort={col.sortField ? () => toggleSort(col.sortField as string) : undefined}
              >
                {col.header}
              </Th>
            ))}
            {(canChange || canDelete || rowActions) && <Th>Amallar</Th>}
          </TableHead>
          <TableBody>
            {listQuery.data.results.map((item) => (
              <Tr key={item.id}>
                {columns.map((col) => (
                  <Td key={col.key}>{col.render(item)}</Td>
                ))}
                {(canChange || canDelete || rowActions) && (
                  <Td>
                    <div className="flex flex-wrap items-center gap-1">
                      {canChange && formConfig && (
                        <Button variant="ghost" size="sm" onClick={() => setEditing(item)}>
                          Tahrirlash
                        </Button>
                      )}
                      {canDelete && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-900/30"
                          onClick={() => setDeleting(item)}
                        >
                          O'chirish
                        </Button>
                      )}
                      {rowActions?.(item)}
                    </div>
                  </Td>
                )}
              </Tr>
            ))}
          </TableBody>
        </Table>
      ) : null}

      {listQuery.data && (
        <Pagination
          page={tableState.page}
          pageSize={tableState.pageSize}
          count={listQuery.data.count}
          onPageChange={tableState.setPage}
        />
      )}

      {formConfig && (
        <>
          <ResourceFormDialog
            open={creating}
            title={`Yangi ${title.toLowerCase()}`}
            config={formConfig}
            pending={createMutation.isPending}
            serverError={formError}
            onSubmit={handleCreate}
            onClose={() => {
              setCreating(false)
              setFormError(undefined)
            }}
          />
          <ResourceFormDialog
            open={editing !== null}
            title={`${title} — tahrirlash`}
            config={formConfig}
            currentItem={editing as Record<string, unknown> | undefined}
            initialValues={editing ? formConfig.toFormValues(editing as Record<string, unknown>) : undefined}
            pending={updateMutation.isPending}
            serverError={formError}
            onSubmit={handleUpdate}
            onClose={() => {
              setEditing(null)
              setFormError(undefined)
            }}
          />
        </>
      )}

      <ConfirmDialog
        open={deleting !== null}
        title="O'chirishni tasdiqlang"
        message="Bu yozuvni o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi."
        danger
        pending={removeMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  )
}
