import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { Order, OrderStatus } from '@/entities/order'

export const ORDER_STATUS: Record<
  OrderStatus,
  { tone: 'neutral' | 'info' | 'warning' | 'success' | 'danger'; label: string; next?: { to: OrderStatus; action: string } }
> = {
  new: { tone: 'info', label: '🆕 Yangi', next: { to: 'confirmed', action: '☎️ Tasdiqlash' } },
  confirmed: { tone: 'warning', label: '☎️ Tasdiqlangan', next: { to: 'shipped', action: "🚚 Yo'lga chiqdi" } },
  shipped: { tone: 'warning', label: "🚚 Yo'lda", next: { to: 'delivered', action: '✅ Yetkazildi' } },
  delivered: { tone: 'success', label: '✅ Yetkazildi' },
  cancelled: { tone: 'danger', label: '❌ Bekor qilingan' },
}

export function formatSom(value: number): string {
  return `${value.toLocaleString('uz-UZ').replaceAll(',', ' ')} so'm`
}

export const orderColumns: ResourceColumn<Order>[] = [
  { key: 'id', header: '№', render: (o) => <span className="font-medium">#{o.id}</span> },
  {
    key: 'customer',
    header: 'Mijoz',
    render: (o) => (
      <div>
        <p className="font-medium">{o.customer_name}</p>
        <p className="text-xs text-slate-400">{o.phone_number}</p>
      </div>
    ),
  },
  {
    key: 'items',
    header: 'Mahsulotlar',
    render: (o) => (
      <div className="max-w-56">
        {o.items.slice(0, 3).map((item) => (
          <p key={item.id} className="truncate text-xs text-slate-500 dark:text-slate-400">
            {item.product_name} × {item.quantity}
          </p>
        ))}
        {o.items.length > 3 && (
          <p className="text-xs text-slate-400">… yana {o.items.length - 3} ta</p>
        )}
      </div>
    ),
  },
  {
    key: 'total',
    header: 'Jami',
    sortField: 'total',
    render: (o) => (
      <div>
        <p className="font-medium">{formatSom(o.total)}</p>
        {o.delivery_fee > 0 && (
          <p className="text-xs text-slate-400">
            shundan yetkazish {formatSom(o.delivery_fee)}
          </p>
        )}
        <p
          className={`mt-0.5 text-xs font-medium ${
            o.payment_status === 'paid'
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-amber-600 dark:text-amber-400'
          }`}
        >
          {o.payment_status === 'paid'
            ? "💳 To'langan"
            : o.payment_method === 'online'
              ? "💳 To'lov kutilmoqda"
              : "⚠️ To'lov kelishilmagan"}
        </p>
        {o.provider_charge_id && (
          <p
            className="truncate text-[11px] text-slate-400"
            title={`Click to'lov ID: ${o.provider_charge_id} — pulni qaytarish yoki solishtirish uchun`}
          >
            ID: {o.provider_charge_id}
          </p>
        )}
      </div>
    ),
  },
  {
    key: 'delivery',
    header: 'Yetkazish',
    render: (o) => (
      <div className="max-w-56">
        <Badge tone={o.delivery_method === 'yandex' ? 'warning' : 'info'}>
          {o.delivery_method === 'yandex' ? '🚕 Yandeks' : '📦 BTS'}
        </Badge>
        <p className="mt-1 truncate text-xs text-slate-400" title={o.address}>{o.address}</p>
        {o.latitude != null ? (
          <a
            href={`https://yandex.uz/maps/?pt=${o.longitude},${o.latitude}&z=17&l=map`}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
          >
            📍 Xaritada ochish
          </a>
        ) : o.delivery_method === 'yandex' ? (
          <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
            📍 Lokatsiya kutilmoqda
          </p>
        ) : null}
      </div>
    ),
  },
  {
    key: 'status',
    header: 'Holat',
    render: (o) => {
      const s = ORDER_STATUS[o.status] ?? { tone: 'neutral' as const, label: o.status }
      return <Badge tone={s.tone}>{s.label}</Badge>
    },
  },
  {
    key: 'created_at',
    header: 'Vaqt',
    sortField: 'created_at',
    render: (o) => new Date(o.created_at).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' }),
  },
]

export const orderFormSchema = z.object({
  status: z.enum(['new', 'confirmed', 'shipped', 'delivered', 'cancelled']),
  address: z.string().min(1, 'Manzil shart'),
  comment: z.string().optional(),
  delivery_method: z.enum(['yandex', 'bts']),
})
export type OrderFormValues = z.infer<typeof orderFormSchema>

export const orderFormConfig: ResourceFormConfig<OrderFormValues> = {
  schema: orderFormSchema,
  fields: [
    {
      name: 'status',
      label: 'Holat',
      type: 'select',
      options: [
        { value: 'new', label: '🆕 Yangi' },
        { value: 'confirmed', label: '☎️ Tasdiqlangan' },
        { value: 'shipped', label: "🚚 Yo'lda" },
        { value: 'delivered', label: '✅ Yetkazildi' },
        { value: 'cancelled', label: '❌ Bekor qilingan' },
      ],
      help: 'Odatda ro\'yxatdagi bitta tugma bilan keyingi bosqichga o\'tkaziladi — bu yerdan istalgan holatga to\'g\'rilash mumkin.',
    },
    {
      name: 'delivery_method',
      label: 'Yetkazish',
      type: 'select',
      options: [
        { value: 'yandex', label: '🚕 Yandeks (Toshkent bo\'ylab)' },
        { value: 'bts', label: '📦 BTS (viloyatlarga)' },
      ],
      help: 'Mijoz bilan kelishilgan bo\'lsa o\'zgartiring.',
    },
    { name: 'address', label: 'Manzil', type: 'textarea', help: 'Yandeks: ko\'cha va uy. BTS: viloyat, shahar, filial.' },
    { name: 'comment', label: 'Izoh', type: 'textarea', help: 'Operator belgilari — mijozga ko\'rinmaydi.' },
  ],
  defaultValues: { status: 'new', address: '', comment: '', delivery_method: 'yandex' },
  toFormValues: (item) => ({
    status: (item.status as OrderFormValues['status']) ?? 'new',
    address: (item.address as string) ?? '',
    comment: (item.comment as string) ?? '',
    delivery_method: (item.delivery_method as OrderFormValues['delivery_method']) ?? 'yandex',
  }),
}
