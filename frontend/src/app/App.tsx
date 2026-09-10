import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter } from 'react-router-dom'

import { AppRoutes } from './router/routes'
import { queryClient } from './providers/query-client'
import { SessionBootstrap } from './providers/session-bootstrap'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionBootstrap>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </SessionBootstrap>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
