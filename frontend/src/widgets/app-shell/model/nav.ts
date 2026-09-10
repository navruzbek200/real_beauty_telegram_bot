export interface NavItem {
  to: string
  label: string
  permission?: string
  superuserOnly?: boolean
}

export interface NavSection {
  title: string
  items: NavItem[]
}

// One short, task-shaped sidebar: the sections a shop actually opens the CRM
// to do, nothing that writes to a retired system. Settings that used to be
// four separate pages now live behind one "Sozlamalar" entry with tabs.
export const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Asosiy',
    items: [
      { to: '/', label: 'Boshqaruv paneli' },
      { to: '/orders', label: 'Buyurtmalar', permission: 'orders.view_order' },
      { to: '/customers', label: 'Xaridorlar', permission: 'users.view_telegramuser' },
      { to: '/support-threads', label: 'Murojaatlar', permission: 'support.view_supportthread' },
    ],
  },
  {
    title: 'Mahsulotlar',
    items: [
      { to: '/products', label: 'Mahsulotlar', permission: 'products.view_product' },
      { to: '/top-products', label: 'Bu oydagi top', permission: 'products.view_product' },
      {
        to: '/tutorial-steps',
        label: 'Video darsliklar',
        permission: 'products.view_producttutorialstep',
      },
    ],
  },
  {
    title: 'Marketing',
    items: [
      { to: '/auto-messages', label: 'Avtomatik xabarlar', permission: 'campaigns.view_automessage' },
      { to: '/broadcasts', label: "E'lonlar", permission: 'campaigns.view_broadcast' },
      { to: '/message-templates', label: 'Xabar shablonlari', permission: 'campaigns.view_messagetemplate' },
    ],
  },
  {
    title: 'Analitika',
    items: [
      {
        to: '/skin-quiz-results',
        label: 'Teri testi natijalari',
        permission: 'analytics.view_skinquizresult',
      },
    ],
  },
  {
    title: 'Sozlamalar',
    items: [{ to: '/settings', label: 'Sozlamalar', superuserOnly: true }],
  },
]
