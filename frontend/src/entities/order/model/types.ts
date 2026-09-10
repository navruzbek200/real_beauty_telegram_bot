export interface OrderItem {
  id: number
  product: number | null
  product_name: string
  price: number
  quantity: number
  subtotal: number
}

export type OrderStatus = 'new' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled'
export type OrderDelivery = 'yandex' | 'bts'
export type OrderPaymentMethod = 'cod' | 'online'
export type OrderPaymentStatus = 'unpaid' | 'pending' | 'paid'

export interface Order {
  id: number
  customer_name: string
  phone_number: string
  telegram_id: number
  delivery_method: OrderDelivery
  delivery_label: string
  address: string
  comment: string
  latitude: number | null
  longitude: number | null
  delivery_fee: number
  status: OrderStatus
  status_label: string
  payment_method: OrderPaymentMethod
  payment_label: string
  payment_status: OrderPaymentStatus
  payment_status_label: string
  paid_at: string | null
  provider_charge_id: string
  total: number
  items: OrderItem[]
  created_at: string
}
