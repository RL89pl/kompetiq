import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { api, ensureCsrf } from '../api/client'
import { qk } from '../api/hooks'
import type { Me } from '../api/types'
import { CompassMark } from '../components/Layout'
import { Button, ErrorList, Field, Input } from '../components/ui'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  const loc = useLocation()
  const qc = useQueryClient()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await ensureCsrf()
      const me = await api<Me>('/auth/login/', { method: 'POST', body: { username, password } })
      qc.setQueryData(qk.me, me)
      nav((loc.state as { from?: string })?.from ?? '/', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen md:grid-cols-[1.1fr_1fr]">
      <div className="hidden flex-col justify-between bg-ink p-12 text-white md:flex">
        <CompassMark className="size-12 text-white" />
        <div className="max-w-md">
          <p className="font-serif text-4xl leading-tight">Ocena oparta na tym, co pracownik rzeczywiście zrobił.</p>
          <p className="mt-4 text-white/75">
            Pierwsza ocena i ocena okresowa w służbie cywilnej: od opisu stanowiska, przez przykłady zachowań,
            po rozmowę oceniającą i plan rozwoju.
          </p>
        </div>
        <p className="text-sm text-white/60">Asystent AI porządkuje i podpowiada. Ocenę wystawia przełożony.</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5" aria-labelledby="login-title">
          <div className="flex items-center gap-3 md:hidden"><CompassMark /><span className="font-serif text-xl">Kompas Kompetencji</span></div>
          <h1 id="login-title" className="text-3xl">Zaloguj się</h1>
          <Field label="Login">{(id) => <Input id={id} autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />}</Field>
          <Field label="Hasło">{(id) => <Input id={id} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />}</Field>
          <ErrorList error={error} />
          <Button type="submit" busy={busy} className="w-full justify-center py-2.5">Zaloguj się</Button>
        </form>
      </div>
    </div>
  )
}
