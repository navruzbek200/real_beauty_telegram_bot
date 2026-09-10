import { useEffect, useState, type ReactNode } from 'react'

import { restoreSession } from '@/entities/session'
import { Spinner } from '@/shared/ui'

/** Turns a persisted refresh token back into a live session before the app
 * renders any protected route, so a reload doesn't flash the login screen. */
export function SessionBootstrap({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    restoreSession().finally(() => setReady(true))
  }, [])

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return <>{children}</>
}
