import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { LoyaltySettings, Reward } from '@/entities/loyalty'

const points = z.coerce.number().int().min(0).max(65535)
const percent = z.coerce.number().int().min(0).max(100)
const threshold = z.coerce.number().int().min(1)

export const loyaltySettingsFormSchema = z
  .object({
    is_enabled: z.boolean(),
    points_registration: points,
    points_referral: points,
    points_purchase: points,
    points_quiz: points,
    points_feedback: points,
    points_progress: points,
    points_birthday: points,
    bronze_cashback: percent,
    silver_from: threshold,
    silver_cashback: percent,
    gold_from: threshold,
    gold_cashback: percent,
    platinum_from: threshold,
    platinum_cashback: percent,
  })
  .refine((v) => v.silver_from < v.gold_from && v.gold_from < v.platinum_from, {
    message: 'Chegaralar ortib borishi kerak: Kumush < Oltin < Platina',
    path: ['gold_from'],
  })
export type LoyaltySettingsFormValues = z.infer<typeof loyaltySettingsFormSchema>

export const loyaltySettingsFormConfig: ResourceFormConfig<LoyaltySettingsFormValues> = {
  schema: loyaltySettingsFormSchema,
  fields: [
    { name: 'is_enabled', label: 'Bonus dasturi yoqilgan', type: 'checkbox', help: 'O\'chirsangiz botdagi «💎 Bonuslarim» bo\'limi vaqtincha yopiladi.' },
    { name: 'points_registration', label: "Ro'yxatdan o'tgani uchun (ball)", type: 'number', help: 'Yangi mijoz botda ro\'yxatdan o\'tganda bir marta beriladi.' },
    { name: 'points_referral', label: "Do'st taklif qilgani uchun (ball)", type: 'number', help: 'Do\'sti havola orqali ro\'yxatdan o\'tsa, taklif qilganga beriladi.' },
    { name: 'points_purchase', label: 'Har bir xarid uchun (ball)', type: 'number' },
    { name: 'points_quiz', label: 'Teri testi uchun (ball)', type: 'number' },
    { name: 'points_feedback', label: 'Baho bergani uchun (ball)', type: 'number' },
    { name: 'points_progress', label: 'Natija rasmi uchun (ball)', type: 'number' },
    { name: 'points_birthday', label: "Tug'ilgan kun sovg'asi (ball)", type: 'number' },
    { name: 'bronze_cashback', label: 'Bronza keshbek (%)', type: 'number', help: 'Boshlang\'ich daraja — hamma shu yerdan boshlaydi.' },
    { name: 'silver_from', label: 'Kumush darajasi (balldan)', type: 'number', help: 'Shu ballga yetganda mijoz Kumushga o\'tadi. Masalan: 1000.' },
    { name: 'silver_cashback', label: 'Kumush keshbek (%)', type: 'number' },
    { name: 'gold_from', label: 'Oltin darajasi (balldan)', type: 'number', help: 'Kumushdan katta bo\'lishi shart. Masalan: 3000.' },
    { name: 'gold_cashback', label: 'Oltin keshbek (%)', type: 'number' },
    { name: 'platinum_from', label: 'Platina darajasi (balldan)', type: 'number', help: 'Oltindan katta bo\'lishi shart. Masalan: 7000.' },
    { name: 'platinum_cashback', label: 'Platina keshbek (%)', type: 'number' },
  ],
  defaultValues: {
    is_enabled: true,
    points_registration: 50,
    points_referral: 150,
    points_purchase: 100,
    points_quiz: 20,
    points_feedback: 30,
    points_progress: 50,
    points_birthday: 200,
    bronze_cashback: 3,
    silver_from: 1000,
    silver_cashback: 5,
    gold_from: 3000,
    gold_cashback: 7,
    platinum_from: 7000,
    platinum_cashback: 10,
  },
  toFormValues: (item) => ({
    is_enabled: Boolean(item.is_enabled),
    points_registration: (item.points_registration as number) ?? 50,
    points_referral: (item.points_referral as number) ?? 150,
    points_purchase: (item.points_purchase as number) ?? 100,
    points_quiz: (item.points_quiz as number) ?? 20,
    points_feedback: (item.points_feedback as number) ?? 30,
    points_progress: (item.points_progress as number) ?? 50,
    points_birthday: (item.points_birthday as number) ?? 200,
    bronze_cashback: (item.bronze_cashback as number) ?? 3,
    silver_from: (item.silver_from as number) ?? 1000,
    silver_cashback: (item.silver_cashback as number) ?? 5,
    gold_from: (item.gold_from as number) ?? 3000,
    gold_cashback: (item.gold_cashback as number) ?? 7,
    platinum_from: (item.platinum_from as number) ?? 7000,
    platinum_cashback: (item.platinum_cashback as number) ?? 10,
  }),
}

export const rewardFormSchema = z.object({
  title: z.string().min(1),
  title_ru: z.string().optional(),
  title_en: z.string().optional(),
  description: z.string().optional(),
  cost_points: z.coerce.number().int().min(1),
  code_prefix: z.string().min(1).max(12),
  stock: z.string().optional(),
  is_active: z.boolean(),
})
export type RewardFormValues = z.infer<typeof rewardFormSchema>

export const rewardFormConfig: ResourceFormConfig<RewardFormValues> = {
  schema: rewardFormSchema,
  fields: [
    { name: 'title', label: 'Nomi', type: 'text', help: 'Masalan: «10% chegirma kuponi» yoki «Mini serum sovg\'a».' },
    { name: 'title_ru', label: 'Nomi (ruscha)', type: 'text', help: 'Bo\'sh qoldirsangiz o\'zbekchasi ko\'rinadi.' },
    { name: 'title_en', label: 'Nomi (inglizcha)', type: 'text', help: 'Bo\'sh qoldirsangiz o\'zbekchasi ko\'rinadi.' },
    { name: 'description', label: 'Tavsif', type: 'textarea' },
    { name: 'cost_points', label: 'Narxi (ball)', type: 'number', help: 'Mijoz shuncha ball to\'lab oladi. Masalan: 500.' },
    { name: 'code_prefix', label: 'Promokod boshlanishi', type: 'text', help: 'Masalan: RB — mijozga «RB-XXXX» ko\'rinishida kod beriladi, do\'konda shu kodni ko\'rsatadi.' },
    { name: 'stock', label: 'Nechta qoldi', type: 'text', help: 'Bo\'sh — cheklanmagan. Raqam yozsangiz, tugagach sovg\'a botdan yashiriladi.' },
    { name: 'is_active', label: 'Faol', type: 'checkbox' },
  ],
  defaultValues: {
    title: '',
    title_ru: '',
    title_en: '',
    description: '',
    cost_points: 500,
    code_prefix: 'RB',
    stock: '',
    is_active: true,
  },
  toFormValues: (item) => ({
    title: (item.title as string) ?? '',
    title_ru: (item.title_ru as string) ?? '',
    title_en: (item.title_en as string) ?? '',
    description: (item.description as string) ?? '',
    cost_points: (item.cost_points as number) ?? 500,
    code_prefix: (item.code_prefix as string) ?? 'RB',
    stock: item.stock == null ? '' : String(item.stock),
    is_active: Boolean(item.is_active),
  }),
}

export const rewardColumns: ResourceColumn<Reward>[] = [
  { key: 'title', header: 'Nomi', render: (r) => r.title },
  { key: 'cost_points', header: 'Narxi', render: (r) => `${r.cost_points} ball` },
  { key: 'stock', header: 'Qoldiq', render: (r) => (r.stock == null ? '∞' : String(r.stock)) },
  {
    key: 'is_active',
    header: 'Holat',
    render: (r) => (
      <Badge tone={r.is_available ? 'success' : 'neutral'}>
        {r.is_available ? 'Faol' : "Yashirin"}
      </Badge>
    ),
  },
]

export type { LoyaltySettings }
