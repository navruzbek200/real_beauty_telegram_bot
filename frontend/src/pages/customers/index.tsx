import { useState } from 'react'

import { ResourcePage } from '@/widgets/resource-crud'
import { Button, Select } from '@/shared/ui'
import { customerApi, type Customer } from '@/entities/customer'
import {
  customerColumns,
  customerFormConfig,
  PurchasesDialog,
  type CustomerFormValues,
} from '@/features/customer'

// Django's DateField wants a real date or null — never "". An empty
// birth_date left blank must become null, not sent as-is, or the API 400s.
function toCustomerPayload(values: CustomerFormValues): Partial<Customer> {
  return { ...values, birth_date: values.birth_date || null }
}

export function CustomersPage() {
  const [purchasesFor, setPurchasesFor] = useState<Customer | null>(null)

  return (
    <>
      <ResourcePage<Customer, CustomerFormValues, Partial<Customer>, Partial<Customer>>
        title="Xaridorlar"
        api={customerApi}
        queryKey={['customers']}
        columns={customerColumns}
        filterKeys={['is_active', 'source', 'face_condition']}
        searchPlaceholder="Ism yoki telefon..."
        permissions={{
          add: 'users.add_telegramuser',
          change: 'users.change_telegramuser',
          delete: 'users.delete_telegramuser',
        }}
        formConfig={customerFormConfig}
        toCreatePayload={toCustomerPayload}
        toUpdatePayload={toCustomerPayload}
        filterBar={(state) => (
          <Select
            value={state.filters.source ?? ''}
            onChange={(e) => state.setFilter('source', e.target.value || null)}
            className="max-w-40"
          >
            <option value="">Barcha manbalar</option>
            <option value="self">O'zi</option>
            <option value="admin">Admin</option>
            <option value="app">Mobil ilova</option>
          </Select>
        )}
        rowActions={(customer) => (
          <Button variant="ghost" onClick={() => setPurchasesFor(customer)}>
            Mahsulotlar
          </Button>
        )}
      />
      <PurchasesDialog customer={purchasesFor} onClose={() => setPurchasesFor(null)} />
    </>
  )
}
