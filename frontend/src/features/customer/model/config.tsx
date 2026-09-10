import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { Customer } from '@/entities/customer'

export const customerFormSchema = z.object({
  full_name: z.string().min(1, "Ism-familiya shart"),
  // The bot links a customer to their card by phone number, so it's the one
  // field that actually has to be right. The country is detected server-side
  // (UZ by default, +code for anyone abroad), so the form only checks it
  // looks phone-ish.
  phone_number: z
    .string()
    .min(1, "Telefon raqami shart")
    .regex(/^[+\d][\d\s()-]*$/, "Faqat raqam. UZ: 90 123 45 67 · boshqa: +7…"),
  birth_date: z.string().optional(),
  face_condition: z.enum(['', 'dry', 'oily', 'combined', 'normal', 'sensitive']).optional(),
  is_active: z.boolean(),
})

export type CustomerFormValues = z.infer<typeof customerFormSchema>

export const customerFormConfig: ResourceFormConfig<CustomerFormValues> = {
  schema: customerFormSchema,
  fields: [
    { name: 'full_name', label: 'Ism-familiya', type: 'text' },
    {
      name: 'phone_number',
      label: 'Telefon raqami',
      type: 'text',
      help: "O'zbekiston: 90 123 45 67 (o'zi +998 qo'yadi). Chet el: +7 916 …",
    },
    { name: 'birth_date', label: "Tug'ilgan sana", type: 'date', help: 'Ixtiyoriy.' },
    {
      name: 'face_condition',
      label: 'Teri turi',
      type: 'select',
      options: [
        { value: 'dry', label: 'Quruq' },
        { value: 'oily', label: "Yog'li" },
        { value: 'combined', label: 'Aralash' },
        { value: 'normal', label: 'Normal' },
        { value: 'sensitive', label: 'Sezgir' },
      ],
    },
    { name: 'is_active', label: 'Faol', type: 'checkbox' },
  ],
  defaultValues: {
    full_name: '',
    phone_number: '+998 ',
    birth_date: '',
    face_condition: '',
    is_active: true,
  },
  toFormValues: (item) => ({
    full_name: (item.full_name as string) ?? '',
    phone_number: (item.phone_number as string) || '+998 ',
    birth_date: (item.birth_date as string) ?? '',
    face_condition: (item.face_condition as CustomerFormValues['face_condition']) ?? '',
    is_active: Boolean(item.is_active),
  }),
}

export const customerColumns: ResourceColumn<Customer>[] = [
  { key: 'full_name', header: 'Ism-familiya', sortField: 'full_name', render: (c) => c.full_name || "Ismsiz" },
  { key: 'phone_number', header: 'Telefon', render: (c) => c.phone_number || '—' },
  {
    key: 'source',
    header: 'Manba',
    render: (c) => (
      <Badge tone={c.source === 'app' ? 'info' : c.source === 'admin' ? 'warning' : 'neutral'}>
        {c.source === 'app' ? 'Mobil ilova' : c.source === 'admin' ? 'Admin' : "O'zi"}
      </Badge>
    ),
  },
  {
    key: 'linked',
    header: 'Bot',
    render: (c) => (c.telegram_id ? <Badge tone="success">Ulangan</Badge> : <Badge>Ulanmagan</Badge>),
  },
  {
    key: 'created_at',
    header: "Qo'shilgan",
    sortField: 'created_at',
    render: (c) => new Date(c.created_at as string).toLocaleDateString('uz-UZ'),
  },
]
