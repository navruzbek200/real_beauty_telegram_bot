import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { ResourcePage } from '@/widgets/resource-crud'
import { Alert, Button, ConfirmDialog, Select } from '@/shared/ui'
import { orderApi, type Order, type OrderStatus } from '@/entities/order'
import { ORDER_STATUS, orderColumns, orderFormConfig, type OrderFormValues } from '@/features/order'

type Notice = { tone: 'success' | 'error'; text: string }

const STATUS_FILTER: { value: string; label: string }[] = [
  { value: '', label: 'Barcha holatlar' },
  { value: 'new', label: '🆕 Yangi' },
  { value: 'confirmed', label: '☎️ Tasdiqlangan' },
  { value: 'shipped', label: "🚚 Yo'lda" },
  { value: 'delivered', label: '✅ Yetkazildi' },
  { value: 'cancelled', label: '❌ Bekor qilingan' },
]

export function OrdersPage() {
  const queryClient = useQueryClient()
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [notice, setNotice] = useState<Notice>()
  const [cancelling, setCancelling] = useState<Order | null>(null)

  async function resendInvoice(order: Order) {
    setPendingId(order.id)
    setNotice(undefined)
    try {
      await orderApi.resendInvoice(order.id)
      await queryClient.invalidateQueries({ queryKey: ['orders'] })
      setNotice({
        tone: 'success',
        text: `Buyurtma #${order.id} — to'lov cheki mijozga qayta yuborildi.`,
      })
    } catch (error) {
      const detail = (error as { detail?: string })?.detail
      setNotice({ tone: 'error', text: detail ?? "Hisob yuborilmadi." })
    } finally {
      setPendingId(null)
    }
  }

  async function setStatus(order: Order, status: OrderStatus) {
    setPendingId(order.id)
    setNotice(undefined)
    try {
      await orderApi.update(order.id, { status })
      await queryClient.invalidateQueries({ queryKey: ['orders'] })
      setNotice({
        tone: 'success',
        text: `Buyurtma #${order.id} → ${ORDER_STATUS[status].label}`,
      })
    } catch {
      setNotice({ tone: 'error', text: "Holatni o'zgartirib bo'lmadi. Qayta urinib ko'ring." })
    } finally {
      setPendingId(null)
    }
  }

  return (
    <div className="space-y-3">
      <Alert tone="info">
        Buyurtmalar Mini Appdagi 🛒 savatchadan tushadi va Telegram guruhga ham boradi.
        Ish tartibi: mijozga qo'ng'iroq qiling → <b>Tasdiqlash</b> → jo'natgach{' '}
        <b>Yo'lga chiqdi</b> → qo'lga tekkach <b>Yetkazildi</b>.
      </Alert>
      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(undefined)}>
          {notice.text}
        </Alert>
      )}
      <ResourcePage<Order, OrderFormValues, Partial<Order>, Partial<Order>>
        title="Buyurtmalar"
        api={orderApi}
        queryKey={['orders']}
        columns={orderColumns}
        filterKeys={['status']}
        searchPlaceholder="Ism, telefon yoki manzil..."
        permissions={{ change: 'orders.change_order' }}
        formConfig={orderFormConfig}
        toUpdatePayload={(v) => v}
        filterBar={(state) => (
          <Select
            value={state.filters.status ?? ''}
            onChange={(e) => state.setFilter('status', e.target.value || null)}
            className="max-w-48"
          >
            {STATUS_FILTER.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
        )}
        rowActions={(item) => {
          const next = ORDER_STATUS[item.status]?.next
          const awaitingPayment =
            item.payment_status !== 'paid' && item.status !== 'cancelled'
          return (
            <>
              {next && (
                <Button
                  size="sm"
                  loading={pendingId === item.id}
                  onClick={() => setStatus(item, next.to)}
                >
                  {next.action}
                </Button>
              )}
              {awaitingPayment && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={pendingId === item.id}
                  onClick={() => resendInvoice(item)}
                >
                  💳 Hisobni qayta yuborish
                </Button>
              )}
              {(item.status === 'new' || item.status === 'confirmed') && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-900/30"
                  disabled={pendingId === item.id}
                  onClick={() => setCancelling(item)}
                >
                  Bekor
                </Button>
              )}
            </>
          )
        }}
      />
      <ConfirmDialog
        open={cancelling !== null}
        title={`Buyurtma #${cancelling?.id} ni bekor qilish`}
        message={
          cancelling?.payment_status === 'paid'
            ? `Diqqat: bu buyurtma to'langan (${cancelling.provider_charge_id || "to'lov ID yo'q"}). ` +
              "Bekor qilish pulni QAYTARMAYDI — mijozga pulni Click merchant kabinetidan " +
              'qo\'lda qaytarishingiz kerak. Davom etasizmi?'
            : "Mijozga xabar bermaydi. Buyurtma bekor qilingan deb belgilanadi."
        }
        danger
        confirmLabel="Ha, bekor qilish"
        pending={pendingId === cancelling?.id}
        onConfirm={async () => {
          if (cancelling) await setStatus(cancelling, 'cancelled')
          setCancelling(null)
        }}
        onCancel={() => setCancelling(null)}
      />
    </div>
  )
}
