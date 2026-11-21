import { Link } from 'react-router-dom'
import { useAssessments, useDeadlines, useMe } from '../api/hooks'
import { Badge, Loading } from '../components/ui'
import { daysLabel, fmtDate } from '../lib'

const PATHS = [
  {
    key: 'FIRST', title: 'Pierwsza ocena w służbie cywilnej', tone: 'first',
    steps: ['Rozmowa wstępna i termin sprawozdania', 'Przykłady zachowań w 5 elementach oceny',
      'Sprawozdanie, oceny cząstkowe i rozmowa', 'Potwierdzenie przez kierującego komórką'],
  },
  {
    key: 'PERIODIC', title: 'Ocena okresowa w służbie cywilnej', tone: 'periodic',
    steps: ['Analiza opisu stanowiska i wybór arkusza B lub C', 'Kryteria, oczekiwania i termin oceny',
      'Przykłady zachowań i oceny cząstkowe', 'Rozmowa oceniająca, IPRZ i sporządzenie oceny'],
  },
] as const

export function DashboardPage() {
  const { data: me } = useMe()
  const active = useAssessments('?status=DRAFT,CRITERIA_SET,INTERVIEW_DONE,FINALIZED,APPROVED')
  const deadlines = useDeadlines()
  const firstName = me?.full_name.split(' ')[0]

  return (
    <div className="space-y-12">
      <header>
        <p className="text-ink-soft">Dzień dobry{firstName ? `, ${firstName}` : ''}.</p>
        <h1 className="mt-1 text-[2.25rem]">Którą ocenę przygotowujesz?</h1>
        {(me?.active_membership?.role === 'HR' || me?.active_membership?.role === 'ADMIN') && (
          <p className="mt-2"><Link to="/panel-hr" className="font-bold underline">Przejdź do panelu HR</Link>: statusy ocen, terminy i przypomnienia.</p>
        )}
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        {PATHS.map((p) => (
          <Link key={p.key} to={`/pracownicy?rozpocznij=${p.key}`}
            className={`group relative block rounded-lg border-2 bg-white p-6 transition-colors ${p.tone === 'first' ? 'border-first/30 hover:border-first' : 'border-periodic/30 hover:border-periodic'}`}>
            <h2 className={`text-2xl ${p.tone === 'first' ? 'text-first' : 'text-periodic'}`}>{p.title}</h2>
            <ol className="mt-5 space-y-3">
              {p.steps.map((s, i) => (
                <li key={s} className="flex gap-3">
                  <span className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full text-[13px] font-bold text-white ${p.tone === 'first' ? 'bg-first' : 'bg-periodic'}`}>{i + 1}</span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
            <p className={`mt-6 font-bold underline-offset-4 group-hover:underline ${p.tone === 'first' ? 'text-first' : 'text-periodic'}`}>Wybierz pracownika</p>
          </Link>
        ))}
      </div>

      <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <section>
          <h2 className="text-xl">Oceny w toku</h2>
          {active.isLoading ? <Loading /> : active.data?.length ? (
            <ul className="mt-3 divide-y divide-rule border-y border-rule">
              {active.data.map((a) => (
                <li key={a.id}>
                  <Link to={`/oceny/${a.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-white">
                    <span>
                      <span className="font-bold">{a.employee_name}</span>
                      <span className="text-ink-soft"> — {a.employee_position}</span>
                    </span>
                    <span className="flex items-center gap-2">
                      <Badge tone={a.form_type === 'FIRST' ? 'first' : 'periodic'}>{a.form_type === 'FIRST' ? 'Pierwsza' : a.form_label.split('—')[1]?.trim().split(' (')[0]}</Badge>
                      <span className="text-sm text-ink-soft">{a.status_label}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : <p className="mt-3 text-ink-soft">Nie masz ocen w toku. Wybierz ścieżkę powyżej, aby rozpocząć.</p>}
        </section>
        <section>
          <h2 className="text-xl">Najbliższe terminy</h2>
          {deadlines.isLoading ? <Loading /> : deadlines.data?.length ? (
            <ul className="mt-3 space-y-3">
              {deadlines.data.slice(0, 6).map((d, i) => (
                <li key={i} className="flex gap-3">
                  <span className={`w-24 shrink-0 text-sm font-bold ${d.overdue ? 'text-bad' : d.days_left <= 14 ? 'text-warn' : 'text-ink-soft'}`}>{daysLabel(d.days_left)}</span>
                  <Link to={`/oceny/${d.assessment}`} className="hover:underline">
                    {d.label}: <span className="font-bold">{d.employee}</span>
                    <span className="block text-sm text-ink-soft">{fmtDate(d.date)}{d.basis && `, ${d.basis}`}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : <p className="mt-3 text-ink-soft">Brak terminów w najbliższych 90 dniach.</p>}
        </section>
      </div>
    </div>
  )
}
