import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { fetchMe, login, useSessionStore } from '@/entities/session'

const loginSchema = z.object({
  username: z.string().min(1, 'Loginni kiriting'),
  password: z.string().min(1, "Parolni kiriting"),
})

type LoginValues = z.infer<typeof loginSchema>

export function useLogin() {
  const setTokens = useSessionStore((s) => s.setTokens)
  const setUser = useSessionStore((s) => s.setUser)

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  const mutation = useMutation({
    mutationFn: async (values: LoginValues) => {
      const tokens = await login(values.username, values.password)
      setTokens({ access: tokens.access, refresh: tokens.refresh })
      const me = await fetchMe(tokens.access)
      setUser(me)
    },
  })

  return {
    form,
    onSubmit: form.handleSubmit((values) => mutation.mutateAsync(values)),
    isPending: mutation.isPending,
    error: mutation.isError ? "Login yoki parol noto'g'ri." : undefined,
  }
}
