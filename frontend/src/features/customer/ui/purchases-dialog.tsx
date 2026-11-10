import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { Button, Dialog, EmptyState, Select, Spinner } from '@/shared/ui'
import { productApi } from '@/entities/product'
import { customerApi, userProductApi, type Customer, type UserProduct } from '@/entities/customer'

interface PurchasesDialogProps {
  customer: Customer | null
  onClose: () => void
}

/**
 * Attach and detach the products a customer bought, straight from their row.
 *
 * A purchase is what the whole retention flow hangs off: attaching one is
 * what fires the "after purchase" auto-messages and hands the customer the
 * product's tutorial videos. Keeping it here, next to the customer, means a
 * seller records a sale without leaving the page they're already on.
 */
export function PurchasesDialog({ customer, onClose }: PurchasesDialogProps) {
  const queryClient = useQueryClient()
  const [productId, setProductId] = useState('')
  const [busy, setBusy] = useState(false)

  const detail = useQuery({
    queryKey: ['customers', 'detail', customer?.id],
    queryFn: () => customerApi.retrieve(customer!.id),
    enabled: customer !== null,
  })

  const products = useQuery({
    queryKey: ['products', 'all-for-select'],
    queryFn: () => productApi.list({ page_size: 200, ordering: 'name', is_active: true }),
    enabled: customer !== null,
  })

  const purchases = ((detail.data?.purchases ?? []) as UserProduct[]).filter(purchase => !purchase.is_billz)
  const billzPurchases = detail.data?.billz_purchases ?? []

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ['customers'] })
  }

  async function attach() {
    if (!customer || !productId) return
    setBusy(true)
    try {
      await userProductApi.create({ user: customer.id, product: Number(productId) })
      setProductId('')
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  async function detach(id: number) {
    setBusy(true)
    try {
      await userProductApi.remove(id)
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={customer !== null}
      title={`${customer?.full_name || 'Mijoz'} — sotib olgan mahsulotlar`}
      onClose={onClose}
    >
      {detail.isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : (
        <div className="space-y-4">
          {billzPurchases.length > 0 && (
            <section aria-label="BILLZ xaridlari">
              <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">BILLZ xaridlari</h3>
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                {billzPurchases.map((purchase) => (
                  <li key={purchase.id} className="py-2">
                    <p className="text-sm text-slate-800 dark:text-slate-200">{purchase.product_name} × {Number(purchase.quantity)}</p>
                    <p className="text-xs text-slate-400">
                      {new Date(purchase.purchased_at).toLocaleString('uz-UZ')} · Chek {purchase.order_number}
                      {purchase.cancelled ? ' · Bekor qilingan' : !purchase.active && ' · Qaytarilgan yoki faol emas'}
                    </p>
                    {!purchase.has_tutorial && (
                      <a className="text-xs text-cyan-700 underline dark:text-cyan-300" href={`/admin/billz/billzproduct/${encodeURIComponent(purchase.mapping_id)}/change/`} target="_blank" rel="noreferrer">Qo‘llanmani biriktirish</a>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Biriktirilgan mahsulotlar</h3>
          {purchases.length === 0 ? (
            <EmptyState message="Hozircha biriktirilgan mahsulot yo'q." />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {purchases.map((up) => (
                <li key={up.id} className="flex items-center justify-between py-2">
                  <div>
                    <p className="text-sm text-slate-800 dark:text-slate-200">{up.product_name}</p>
                    <p className="text-xs text-slate-400">
                      {new Date(up.purchased_at as string).toLocaleDateString('uz-UZ')}
                    </p>
                  </div>
                  <Button variant="ghost" disabled={busy} onClick={() => detach(up.id)}>
                    O'chirish
                  </Button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex items-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Mahsulot biriktirish
              </label>
              <Select value={productId} onChange={(e) => setProductId(e.target.value)}>
                <option value="">Mahsulotni tanlang...</option>
                {(products.data?.results ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <Button disabled={!productId || busy} onClick={attach}>
              Qo'shish
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  )
}
