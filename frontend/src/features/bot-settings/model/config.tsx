import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { Discount, GlobalSettings } from '@/entities/bot-settings'

export const discountFormSchema = z.object({
  title: z.string().min(1),
  percent: z.coerce.number().int().min(0).max(100),
  description: z.string().optional(),
  promo_code: z.string().optional(),
  valid_until: z.string().optional(),
  is_active: z.boolean(),
})
export type DiscountFormValues = z.infer<typeof discountFormSchema>
export const discountFormConfig: ResourceFormConfig<DiscountFormValues> = {
  schema: discountFormSchema,
  fields: [
    { name: 'title', label: 'Sarlavha', type: 'text', help: 'Masalan: «Bahoriy aksiya». Botdagi «💣 Qaynoq chegirmalar»da ko\'rinadi.' },
    { name: 'percent', label: 'Chegirma foizi (%)', type: 'number', help: 'Masalan: 20.' },
    { name: 'description', label: 'Tavsif', type: 'textarea', help: 'Ixtiyoriy qo\'shimcha izoh — qaysi mahsulotlarga, qanday shart bilan.' },
    { name: 'promo_code', label: 'Promokod', type: 'text', help: 'Ixtiyoriy. Masalan: BAHOR20 — mijoz do\'konda aytadi.' },
    { name: 'valid_until', label: 'Amal qilish muddati', type: 'date', help: 'Ixtiyoriy — bo\'sh qoldirsangiz muddatsiz. Muddati o\'tgach botda ko\'rinmaydi.' },
    { name: 'is_active', label: 'Faol', type: 'checkbox' },
  ],
  defaultValues: {
    title: '',
    percent: 0,
    description: '',
    promo_code: '',
    valid_until: '',
    is_active: true,
  },
  toFormValues: (item) => ({
    title: (item.title as string) ?? '',
    percent: (item.percent as number) ?? 0,
    description: (item.description as string) ?? '',
    promo_code: (item.promo_code as string) ?? '',
    valid_until: (item.valid_until as string) ?? '',
    is_active: Boolean(item.is_active),
  }),
}
export const discountColumns: ResourceColumn<Discount>[] = [
  { key: 'title', header: 'Sarlavha', render: (d) => d.title },
  { key: 'percent', header: 'Foiz', render: (d) => `${d.percent}%` },
  { key: 'promo_code', header: 'Promokod', render: (d) => d.promo_code || '—' },
  {
    key: 'is_active',
    header: 'Holat',
    render: (d) => <Badge tone={d.is_active ? 'success' : 'neutral'}>{d.is_active ? 'Faol' : "O'chirilgan"}</Badge>,
  },
]

export const deliveryFeeFormSchema = z.object({
  delivery_fee_yandex: z.coerce.number().int().min(0),
  delivery_fee_bts: z.coerce.number().int().min(0),
})
export type DeliveryFeeFormValues = z.infer<typeof deliveryFeeFormSchema>
export const deliveryFeeFormConfig: ResourceFormConfig<DeliveryFeeFormValues> = {
  schema: deliveryFeeFormSchema,
  fields: [
    {
      name: 'delivery_fee_yandex',
      label: '🚕 Yandeks yetkazish haqi (so\'m)',
      type: 'number',
      help: 'Toshkent bo\'ylab. Mijoz savatchasiga alohida qator bo\'lib qo\'shiladi. Masalan: 25000.',
    },
    {
      name: 'delivery_fee_bts',
      label: '📦 BTS yetkazish haqi (so\'m)',
      type: 'number',
      help: 'Viloyatlarga pochta. Masalan: 35000.',
    },
  ],
  defaultValues: { delivery_fee_yandex: 25000, delivery_fee_bts: 35000 },
  toFormValues: (item) => ({
    delivery_fee_yandex: (item.delivery_fee_yandex as number) ?? 25000,
    delivery_fee_bts: (item.delivery_fee_bts as number) ?? 35000,
  }),
}

export const globalSettingsFormSchema = z.object({
  birthday_discount_percent: z.coerce.number().int().min(0).max(100),
})
export type GlobalSettingsFormValues = z.infer<typeof globalSettingsFormSchema>
export const globalSettingsFormConfig: ResourceFormConfig<GlobalSettingsFormValues> = {
  schema: globalSettingsFormSchema,
  fields: [
    { name: 'birthday_discount_percent', label: "Tug'ilgan kun chegirmasi (%)", type: 'number', help: 'Bot mijozga tug\'ilgan kunida shu foizni tabrik xabari bilan yuboradi.' },
  ],
  defaultValues: { birthday_discount_percent: 30 },
  toFormValues: (item) => ({
    birthday_discount_percent: (item.birthday_discount_percent as number) ?? 30,
  }),
}

const url = z.string().url('To\'g\'ri havola kiriting').or(z.literal('')).optional()
export const shopSettingsFormSchema = z.object({
  shop_name: z.string().min(1, 'Nomi shart'),
  shop_tagline: z.string().optional(),
  shop_tagline_ru: z.string().optional(),
  shop_tagline_en: z.string().optional(),
  instagram_url: url,
  youtube_url: url,
  telegram_url: url,
})
export type ShopSettingsFormValues = z.infer<typeof shopSettingsFormSchema>
export const shopSettingsFormConfig: ResourceFormConfig<ShopSettingsFormValues> = {
  schema: shopSettingsFormSchema,
  fields: [
    { name: 'shop_name', label: "Do'kon nomi", type: 'text', help: 'Mini App bosh sahifasida katta harflar bilan chiqadi.' },
    { name: 'shop_tagline', label: 'Shior', type: 'text', help: 'Nom ostidagi qisqa matn. Masalan: «Teringizga professional g\'amxo\'rlik».' },
    { name: 'shop_tagline_ru', label: 'Shior (ruscha)', type: 'text', help: 'Bo\'sh qoldirsangiz o\'zbekchasi ko\'rsatiladi.' },
    { name: 'shop_tagline_en', label: 'Shior (inglizcha)', type: 'text', help: 'Bo\'sh qoldirsangiz o\'zbekchasi ko\'rsatiladi.' },
    { name: 'instagram_url', label: 'Instagram havolasi', type: 'text', help: 'Masalan: https://instagram.com/realbeauty — Mini App «Aloqa» bo\'limida chiqadi.' },
    { name: 'youtube_url', label: 'YouTube havolasi', type: 'text', help: 'Bo\'sh qoldirsangiz bu tugma ko\'rinmaydi.' },
    { name: 'telegram_url', label: 'Telegram kanal havolasi', type: 'text', help: 'Masalan: https://t.me/realbeauty_uz. Bo\'sh — ko\'rinmaydi.' },
  ],
  defaultValues: {
    shop_name: 'Real Beauty',
    shop_tagline: '',
    shop_tagline_ru: '',
    shop_tagline_en: '',
    instagram_url: '',
    youtube_url: '',
    telegram_url: '',
  },
  toFormValues: (item) => ({
    shop_name: (item.shop_name as string) ?? 'Real Beauty',
    shop_tagline: (item.shop_tagline as string) ?? '',
    shop_tagline_ru: (item.shop_tagline_ru as string) ?? '',
    shop_tagline_en: (item.shop_tagline_en as string) ?? '',
    instagram_url: (item.instagram_url as string) ?? '',
    youtube_url: (item.youtube_url as string) ?? '',
    telegram_url: (item.telegram_url as string) ?? '',
  }),
}
export type { GlobalSettings }
