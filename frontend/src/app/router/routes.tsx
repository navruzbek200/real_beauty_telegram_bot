import { Route, Routes } from 'react-router-dom'

import { AutoMessagesPage } from '@/pages/auto-messages'
import { BroadcastsPage } from '@/pages/broadcasts'
import { CustomersPage } from '@/pages/customers'
import { DashboardPage } from '@/pages/dashboard'
import { LoginPage } from '@/pages/login'
import { MessageTemplatesPage } from '@/pages/message-templates'
import { OrdersPage } from '@/pages/orders'
import { ProductsPage } from '@/pages/products'
import { SettingsPage } from '@/pages/settings'
import { SkinQuizResultsPage } from '@/pages/skin-quiz-results'
import { SupportThreadsPage } from '@/pages/support-threads'
import { TopProductsPage } from '@/pages/top-products'
import { TutorialStepsPage } from '@/pages/tutorial-steps'
import { ProtectedRoute } from './protected-route'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />

      <Route
        path="/customers"
        element={<ProtectedRoute permission="users.view_telegramuser"><CustomersPage /></ProtectedRoute>}
      />
      <Route
        path="/orders"
        element={<ProtectedRoute permission="orders.view_order"><OrdersPage /></ProtectedRoute>}
      />
      <Route
        path="/support-threads"
        element={<ProtectedRoute permission="support.view_supportthread"><SupportThreadsPage /></ProtectedRoute>}
      />

      <Route
        path="/products"
        element={<ProtectedRoute permission="products.view_product"><ProductsPage /></ProtectedRoute>}
      />
      <Route
        path="/top-products"
        element={<ProtectedRoute permission="products.view_product"><TopProductsPage /></ProtectedRoute>}
      />
      <Route
        path="/tutorial-steps"
        element={
          <ProtectedRoute permission="products.view_producttutorialstep">
            <TutorialStepsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/auto-messages"
        element={<ProtectedRoute permission="campaigns.view_automessage"><AutoMessagesPage /></ProtectedRoute>}
      />
      <Route
        path="/broadcasts"
        element={<ProtectedRoute permission="campaigns.view_broadcast"><BroadcastsPage /></ProtectedRoute>}
      />
      <Route
        path="/message-templates"
        element={<ProtectedRoute permission="campaigns.view_messagetemplate"><MessageTemplatesPage /></ProtectedRoute>}
      />

      <Route
        path="/skin-quiz-results"
        element={<ProtectedRoute permission="analytics.view_skinquizresult"><SkinQuizResultsPage /></ProtectedRoute>}
      />

      <Route path="/settings" element={<ProtectedRoute superuserOnly><SettingsPage /></ProtectedRoute>} />
    </Routes>
  )
}
