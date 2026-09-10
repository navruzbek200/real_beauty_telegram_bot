import { Navigate, useLocation } from 'react-router-dom'

import { useLogin } from '@/features/auth-login'
import { Button, FieldError, Input, Label } from '@/shared/ui'
import { useSessionStore } from '@/entities/session'

export function LoginPage() {
  const user = useSessionStore((s) => s.user)
  const location = useLocation()
  const { form, onSubmit, isPending, error } = useLogin()

  if (user) {
    const from = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={from} replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h1 className="mb-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Real Beauty CRM
        </h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">Xodim sifatida kiring</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <Label htmlFor="username">Login</Label>
            <Input id="username" autoFocus {...form.register('username')} />
            <FieldError message={form.formState.errors.username?.message} />
          </div>
          <div>
            <Label htmlFor="password">Parol</Label>
            <Input id="password" type="password" {...form.register('password')} />
            <FieldError message={form.formState.errors.password?.message} />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? 'Kirilmoqda...' : 'Kirish'}
          </Button>
        </form>
      </div>
    </div>
  )
}
