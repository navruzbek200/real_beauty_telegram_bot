import { useQueryClient } from '@tanstack/react-query'

import { ResourcePage } from '@/widgets/resource-crud'
import { Button, Select } from '@/shared/ui'
import { hasPermission, useSessionStore } from '@/entities/session'
import { productApi, type Product } from '@/entities/product'
import {
  productColumns,
  productFormConfig,
  toProductFormData,
  type ProductFormValues,
} from '@/features/product'

export function ProductsPage() {
  const user = useSessionStore((s) => s.user)
  const queryClient = useQueryClient()
  const canChange = hasPermission(user, 'products.change_product')

  async function toggleTop(product: Product) {
    if (product.is_top) await productApi.removeFromTop([product.id])
    else await productApi.addToTop([product.id])
    queryClient.invalidateQueries({ queryKey: ['products'] })
  }

  // Taking something off sale is not the same as hiding it: the product keeps
  // its place in the catalogue and the bot says it is coming back.
  async function toggleStock(product: Product) {
    if (product.in_stock === false) await productApi.markInStock([product.id])
    else await productApi.markOutOfStock([product.id])
    queryClient.invalidateQueries({ queryKey: ['products'] })
  }

  return (
    <ResourcePage<Product, ProductFormValues, FormData, FormData>
      title="Mahsulotlar"
      api={productApi}
      queryKey={['products']}
      columns={productColumns}
      filterKeys={['is_active', 'is_top', 'in_stock']}
      searchPlaceholder="Nomi yoki tavsif bo'yicha qidirish..."
      permissions={{
        add: 'products.add_product',
        change: 'products.change_product',
        delete: 'products.delete_product',
      }}
      formConfig={productFormConfig}
      toCreatePayload={toProductFormData}
      toUpdatePayload={toProductFormData}
      filterBar={(state) => (
        <>
          <Select
            value={state.filters.is_active ?? ''}
            onChange={(e) => state.setFilter('is_active', e.target.value || null)}
            className="max-w-40"
          >
            <option value="">Barcha holatlar</option>
            <option value="true">Faol</option>
            <option value="false">O'chirilgan</option>
          </Select>
          <Select
            value={state.filters.in_stock ?? ''}
            onChange={(e) => state.setFilter('in_stock', e.target.value || null)}
            className="max-w-40"
          >
            <option value="">Sotuvda: barchasi</option>
            <option value="true">Sotuvda bor</option>
            <option value="false">Tugagan</option>
          </Select>
          <Select
            value={state.filters.is_top ?? ''}
            onChange={(e) => state.setFilter('is_top', e.target.value || null)}
            className="max-w-40"
          >
            <option value="">Barchasi</option>
            <option value="true">Topda</option>
            <option value="false">Topda emas</option>
          </Select>
        </>
      )}
      rowActions={
        canChange
          ? (product) => (
              <>
                <Button variant="ghost" onClick={() => toggleStock(product)}>
                  {product.in_stock === false ? '🟢 Sotuvda bor' : '🔴 Tugadi'}
                </Button>
                <Button variant="ghost" onClick={() => toggleTop(product)}>
                  {product.is_top ? 'Topdan olish' : "Topga qo'shish"}
                </Button>
              </>
            )
          : undefined
      }
    />
  )
}
