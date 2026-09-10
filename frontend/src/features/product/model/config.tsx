import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { Product, TopProduct } from '@/entities/product'

export const productFormSchema = z.object({
  name: z.string().min(1, "Nomi shart"),
  description: z.string().optional(),
  is_active: z.boolean(),
  current_price: z.coerce.number().int().min(0),
  old_price: z.coerce.number().int().min(0).optional(),
  is_top: z.boolean(),
  top_order: z.coerce.number().int().min(1),
  top_note: z.string().optional(),
  photo: z.instanceof(File).optional(),
})

export type ProductFormValues = z.infer<typeof productFormSchema>

export const productFormConfig: ResourceFormConfig<ProductFormValues> = {
  schema: productFormSchema,
  fields: [
    { name: 'name', label: 'Nomi', type: 'text', help: 'Masalan: «Vitamin C serum 30ml». Botda va Mini Appda shu nom chiqadi.' },
    { name: 'description', label: 'Tavsif', type: 'textarea', help: 'Tarkibi, foydasi, qanday ishlatiladi — mijoz «Batafsil»da o\'qiydi.' },
    { name: 'photo', label: 'Rasm', type: 'file', help: 'Kvadrat (1:1) rasm eng chiroyli ko\'rinadi. Yangi rasm eskisini almashtiradi.' },
    { name: 'is_active', label: 'Faol', type: 'checkbox', help: 'O\'chirsangiz mahsulot botdan va Mini Appdan yashiriladi (o\'chirilmaydi).' },
    { name: 'current_price', label: "Hozirgi narxi (so'm)", type: 'number', help: 'Masalan: 250000.' },
    {
      name: 'old_price',
      label: "Eski narxi (so'm)",
      type: 'number',
      help: 'Chegirma ko\'rsatish uchun: eski narxni yozing, foiz avtomatik chiqadi. Chegirma bo\'lmasa bo\'sh qoldiring.',
    },
    { name: 'is_top', label: "Bu oyning top mahsuloti", type: 'checkbox', help: 'Belgilansa «🔥 TOP» bo\'limida va TOP belgisi bilan chiqadi.' },
    { name: 'top_order', label: 'Top ro\'yxatdagi o\'rni', type: 'number', help: '1 — birinchi, 2 — ikkinchi… Faqat TOP belgilanganda ishlaydi.' },
    { name: 'top_note', label: 'Top izohi', type: 'text', help: 'Masalan: «Eng ko\'p sotilgan» yoki «Yangi kelgan».' },
  ],
  defaultValues: {
    name: '',
    description: '',
    is_active: true,
    current_price: 0,
    old_price: undefined,
    is_top: false,
    top_order: 1,
    top_note: '',
  },
  toFormValues: (item) => ({
    name: (item.name as string) ?? '',
    description: (item.description as string) ?? '',
    is_active: Boolean(item.is_active),
    current_price: (item.current_price as number) ?? 0,
    old_price: (item.old_price as number | null) ?? undefined,
    is_top: Boolean(item.is_top),
    top_order: (item.top_order as number) ?? 1,
    top_note: (item.top_note as string) ?? '',
  }),
}

export function toProductFormData(values: ProductFormValues): FormData {
  const formData = new FormData()
  formData.set('name', values.name)
  formData.set('description', values.description ?? '')
  formData.set('is_active', String(values.is_active))
  formData.set('current_price', String(values.current_price))
  formData.set('old_price', values.old_price != null ? String(values.old_price) : '')
  formData.set('is_top', String(values.is_top))
  formData.set('top_order', String(values.top_order))
  formData.set('top_note', values.top_note ?? '')
  if (values.photo) formData.set('photo', values.photo)
  return formData
}

export function formatSom(value: number | null | undefined): string {
  return `${(value ?? 0).toLocaleString('uz-UZ').replaceAll(',', ' ')} so'm`
}

function PriceCell({ item }: { item: Product | TopProduct }) {
  const hasDiscount = Boolean(item.old_price && item.old_price > item.current_price)
  if (!hasDiscount) return <span>{formatSom(item.current_price)}</span>
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-400 line-through">{formatSom(item.old_price)}</span>
      <span className="font-medium text-rose-600 dark:text-rose-400">
        {formatSom(item.current_price)}
        {item.discount_percent != null && ` (-${item.discount_percent}%)`}
      </span>
    </div>
  )
}

export const productColumns: ResourceColumn<Product>[] = [
  {
    key: 'photo',
    header: '',
    render: (p) =>
      p.photo ? (
        <img src={p.photo} alt="" className="h-12 w-12 rounded-lg border border-slate-100 object-cover dark:border-slate-800" />
      ) : (
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100 text-slate-300 dark:bg-slate-800">—</div>
      ),
  },
  { key: 'name', header: 'Nomi', sortField: 'name', render: (p) => p.name },
  { key: 'price', header: 'Narxi', render: (p) => <PriceCell item={p} /> },
  {
    key: 'status',
    header: 'Holat',
    render: (p) => (
      <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Faol' : "O'chirilgan"}</Badge>
    ),
  },
  {
    key: 'top',
    header: 'Top',
    render: (p) => (p.is_top ? <Badge tone="warning">#{p.top_order}</Badge> : '—'),
  },
  {
    key: 'buyers',
    header: 'Xaridorlar',
    render: (p) => `${p.buyers_count ?? 0} ta`,
  },
  {
    key: 'created_at',
    header: "Qo'shilgan",
    sortField: 'created_at',
    render: (p) => new Date(p.created_at as string).toLocaleDateString('uz-UZ'),
  },
]

export const topProductFormSchema = z.object({
  name: z.string().min(1, "Nomi shart"),
  current_price: z.coerce.number().int().min(0),
  old_price: z.coerce.number().int().min(0).optional(),
  top_order: z.coerce.number().int().min(1),
  top_note: z.string().optional(),
  photo: z.instanceof(File).optional(),
})
export type TopProductFormValues = z.infer<typeof topProductFormSchema>
export const topProductFormConfig: ResourceFormConfig<TopProductFormValues> = {
  schema: topProductFormSchema,
  fields: [
    { name: 'name', label: 'Nomi', type: 'text' },
    { name: 'photo', label: 'Rasm', type: 'file', help: 'Ixtiyoriy — mavjud rasmni almashtiradi.' },
    { name: 'current_price', label: "Hozirgi narxi (so'm)", type: 'number' },
    {
      name: 'old_price',
      label: "Eski narxi (so'm)",
      type: 'number',
      help: "Ixtiyoriy — chegirmani ko'rsatish uchun. Chegirma bo'lmasa bo'sh qoldiring.",
    },
    {
      name: 'top_order',
      label: "Ro'yxatdagi o'rni",
      type: 'number',
      help: '1 — birinchi bo\'lib chiqadi. Raqamni o\'zgartirib tartibni almashtiring.',
    },
    { name: 'top_note', label: 'Izoh (masalan: «Eng ko\'p sotilgan»)', type: 'text' },
  ],
  defaultValues: {
    name: '',
    current_price: 0,
    old_price: undefined,
    top_order: 1,
    top_note: '',
  },
  toFormValues: (item) => ({
    name: (item.name as string) ?? '',
    current_price: (item.current_price as number) ?? 0,
    old_price: (item.old_price as number | null) ?? undefined,
    top_order: (item.top_order as number) ?? 1,
    top_note: (item.top_note as string) ?? '',
  }),
}

export function toTopProductFormData(values: TopProductFormValues): FormData {
  const formData = new FormData()
  formData.set('name', values.name)
  formData.set('current_price', String(values.current_price))
  formData.set('old_price', values.old_price != null ? String(values.old_price) : '')
  formData.set('top_order', String(values.top_order))
  formData.set('top_note', values.top_note ?? '')
  if (values.photo) formData.set('photo', values.photo)
  return formData
}

export const topProductColumns: ResourceColumn<TopProduct>[] = [
  {
    key: 'photo',
    header: '',
    render: (p) =>
      p.photo ? (
        <img src={p.photo} alt="" className="h-10 w-10 rounded-lg object-cover" />
      ) : (
        <span className="text-slate-300">—</span>
      ),
  },
  { key: 'top_order', header: "O'rni", sortField: 'top_order', render: (p) => `#${p.top_order}` },
  { key: 'name', header: 'Nomi', render: (p) => p.name },
  { key: 'price', header: 'Narxi', render: (p) => <PriceCell item={p} /> },
  { key: 'top_note', header: 'Izoh', render: (p) => p.top_note || '—' },
  { key: 'buyers', header: 'Xaridorlar', render: (p) => `${p.buyers_count ?? 0} ta` },
]
