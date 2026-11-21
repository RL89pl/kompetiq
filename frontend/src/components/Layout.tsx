import { useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useMe, useNotifications } from '../api/hooks'

const NAV: { to: string; label: string; end?: boolean; roles?: string[] }[] = [
  { to: '/', label: 'Pulpit', end: true },
  { to: '/panel-hr', label: 'Panel HR', roles: ['HR', 'ADMIN'] },
  { to: '/pracownicy', label: 'Pracownicy' },
  { to: '/oceny', label: 'Oceny' },
  { to: '/rozwoj', label: 'Plany rozwoju' },
  { to: '/terminy', label: 'Terminy' },
  { to: '/model', label: 'Model kompetencji' },
  { to: '/asystent-formalny', label: 'Asystent formalny' },
  { to: '/przejrzystosc-ai', label: 'Przejrzystość AI' },
  { to: '/baza-wiedzy', label: 'Baza wiedzy', roles: ['HR', 'ADMIN'] },
]

export function CompassMark({ className = 'size-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <circle cx="16" cy="16" r="14.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M16 4.5l3.6 11.5L16 27.5 12.4 16z" fill="currentColor" />
      <path d="M16 4.5l3.6 11.5h-7.2z" fill="var(--color-first)" />
    </svg>
  )
}

export function Layout() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const nav = useNavigate()
  const m = me?.active_membership
  const notes = useNotifications()
  const unread = notes.data?.filter((n) => !n.read_at).length ?? 0

  async function logout() {
    await api('/auth/logout/', { method: 'POST' })
    qc.clear()
    nav('/logowanie')
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[15rem_1fr]">
      <a href="#tresc" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:bg-white focus:p-2">Przejdź do treści</a>
      <aside className="border-b border-rule bg-white md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r">
        <Link to="/" className="flex items-center gap-3 px-5 py-5" aria-label="KompetIQ — strona główna">
          <CompassMark />
          <div>
            <p className="font-serif text-lg font-semibold leading-tight">KompetIQ</p>
            <p className="text-[13px] text-ink-soft">{m?.institution_name}</p>
          </div>
        </Link>
        <nav aria-label="Główna nawigacja" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible">
          {NAV.filter((n) => !n.roles || (m && n.roles.includes(m.role))).map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => `whitespace-nowrap rounded-md px-3 py-2 text-[15px] ${isActive ? 'bg-ink text-white font-bold' : 'hover:bg-paper'}`}>
              {n.label}
            </NavLink>
          ))}
          <NavLink to="/powiadomienia"
            className={({ isActive }) => `flex items-center justify-between whitespace-nowrap rounded-md px-3 py-2 text-[15px] ${isActive ? 'bg-ink text-white font-bold' : 'hover:bg-paper'}`}>
            Powiadomienia
            {unread > 0 && <span className="ml-2 rounded-full bg-bad px-2 text-[12px] font-bold text-white" aria-label={`${unread} nieprzeczytanych`}>{unread}</span>}
          </NavLink>
          <NavLink to="/skrzynka-testowa"
            className={({ isActive }) => `whitespace-nowrap rounded-md px-3 py-2 text-[15px] ${isActive ? 'bg-ink text-white font-bold' : 'hover:bg-paper'}`}>
            Skrzynka testowa
          </NavLink>
        </nav>
        <div className="hidden border-t border-rule px-5 py-4 text-sm md:absolute md:bottom-0 md:block md:w-full">
          <p className="font-bold">{me?.full_name}</p>
          <p className="text-ink-soft">{m?.role_display}</p>
          <button onClick={logout} className="mt-2 text-ink underline underline-offset-2 hover:text-first">Wyloguj</button>
        </div>
      </aside>
      <main id="tresc" className="mx-auto w-full max-w-6xl px-4 py-8 md:px-10">
        <Outlet />
        <button onClick={logout} className="mt-10 text-sm underline md:hidden">Wyloguj ({me?.full_name})</button>
      </main>
    </div>
  )
}
