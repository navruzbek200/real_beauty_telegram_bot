import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { Staff } from '@/entities/staff'

export const staffFormSchema = z.object({
  username: z.string().min(1, 'Login shart'),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  is_active: z.boolean(),
  role: z.enum(['admin', 'seller']),
  password: z.string().optional(),
  telegram_id: z.coerce.number().optional(),
  display_name: z.string().optional(),
})

export type StaffFormValues = z.infer<typeof staffFormSchema>

export const staffFormConfig: ResourceFormConfig<StaffFormValues> = {
  schema: staffFormSchema,
  fields: [
    { name: 'username', label: 'Login', type: 'text', help: 'Panelga kirish uchun. Masalan: dilnoza.' },
    { name: 'password', label: 'Parol', type: 'text', help: "Tahrirlashda bo'sh qoldirsangiz o'zgarmaydi." },
    { name: 'first_name', label: 'Ism', type: 'text' },
    { name: 'last_name', label: 'Familiya', type: 'text' },
    {
      name: 'role',
      label: 'Roli',
      type: 'select',
      options: [
        { value: 'seller', label: 'Sotuvchi' },
        { value: 'admin', label: 'Administrator' },
      ],
      help: 'Sotuvchi — mijoz va mahsulotlar bilan ishlaydi. Administrator — hamma narsani boshqaradi.',
    },
    { name: 'telegram_id', label: 'Telegram ID (sotuvchi)', type: 'number', help: 'Sotuvchining shaxsiy Telegram raqamli IDsi — referal havola va bildirishnomalar uchun. IDni @userinfobot orqali bilsa bo\'ladi.' },
    { name: 'display_name', label: "Ko'rinadigan ism", type: 'text', help: 'Mijozga botda ko\'rinadigan ism. Masalan: «Dilnoza opa».' },
    { name: 'is_active', label: 'Faol', type: 'checkbox', help: 'O\'chirsangiz panelga kira olmaydi.' },
  ],
  defaultValues: {
    username: '',
    first_name: '',
    last_name: '',
    is_active: true,
    role: 'seller',
    password: '',
    display_name: '',
  },
  toFormValues: (item) => ({
    username: (item.username as string) ?? '',
    first_name: (item.first_name as string) ?? '',
    last_name: (item.last_name as string) ?? '',
    is_active: Boolean(item.is_active),
    role: (item.role as 'admin' | 'seller') ?? 'seller',
    password: '',
    telegram_id: (item.seller_profile as { telegram_id?: number } | null)?.telegram_id,
    display_name: (item.seller_profile as { display_name?: string } | null)?.display_name ?? '',
  }),
}

export function toStaffPayload(values: StaffFormValues) {
  const { telegram_id, display_name, password, ...rest } = values
  return {
    ...rest,
    ...(password ? { password } : {}),
    ...(telegram_id
      ? { seller_profile: { telegram_id, display_name: display_name ?? '', is_active: true } }
      : {}),
  }
}

export const staffColumns: ResourceColumn<Staff>[] = [
  { key: 'username', header: 'Login', sortField: 'username', render: (s) => s.username },
  {
    key: 'name',
    header: 'Ism',
    render: (s) => [s.first_name, s.last_name].filter(Boolean).join(' ') || '—',
  },
  {
    key: 'role',
    header: 'Roli',
    render: (s) => (
      <Badge tone={s.role === 'admin' ? 'info' : 'neutral'}>
        {s.role === 'admin' ? 'Administrator' : 'Sotuvchi'}
      </Badge>
    ),
  },
  {
    key: 'is_active',
    header: 'Holat',
    render: (s) => <Badge tone={s.is_active ? 'success' : 'danger'}>{s.is_active ? 'Faol' : "Kira olmaydi"}</Badge>,
  },
]
