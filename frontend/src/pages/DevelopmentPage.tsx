import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { usePlans } from '../api/hooks'
import type { PlanListItem } from '../api/types'
import { Loading, Notice, PageHeader } from '../components/ui'
import { daysLabel, fmtDate } from '../lib'

type Filter = 'all' | 'overdue' | 'active' | 'done' | 'empty'
type Sort = 'name' | 'next' | 'progress'

const FILTERS: [Filter, string][] = [['all', 'Wszystkie'], ['overdue', 'Z działaniami po terminie'], ['active', 'W realizacji'], ['done', 'Zrealizowane'], ['empty', 'Bez działań']]

function matches(p: PlanListItem, f: Filter) {
  const s = p.stats
  if (f === 'overdue') return s.overdue > 0
  if (f === 'active') return s.total > 0 && s.done < s.total
  if (f === 'done') return s.total > 0 && s.done === s.total
  if (f === 'empty') return s.total === 0
  return true
}

function Progress({ s }: { s: PlanListItem['stats'] }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-28 overflow-hidden rounded-full bg-rule" role="progressbar" aria-valuenow={s.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Postęp planu">
        <div className="h-full bg-ok" style={{ width: `${s.percent}%` }} />
      </div>
      <span className="text-sm tabular-nums">{s.done}/{s.total}</span>
    </div>
  )
}

export function DevelopmentPage() {
  const { data, isLoading } = usePlans()
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [sort, setSort] = useState<Sort>('next')

  const counts = useMemo(() => Object.fromEntries(FILTERS.map(([k]) => [k, (data ?? []).filter((p) => matches(p, k)).length])), [data])
  const rows = useMemo(() => {
    const needle = q.toLowerCase()
    const list = (data ?? []).filter((p) => matches(p, filter) && `${p.employee_name} ${p.position} ${p.org_unit} ${p.evaluator_name}`.toLowerCase().includes(needle))
    const nextKey = (p: PlanListItem) => p.stats.next_action?.due_date ?? '9999'
    return [...list].sort((a, b) =>
      sort === 'name' ? a.employee_name.localeCompare(b.employee_name, 'pl')
        : sort === 'progress' ? a.stats.percent - b.stats.percent
          : (b.stats.overdue - a.stats.overdue) || nextKey(a).localeCompare(nextKey(b)))
  }, [data, q, filter, sort])

  const today = new Date().toISOString().slice(0, 10)
  return (
    <div>
      <PageHeader title="Plany rozwoju" lead="Aktualny plan rozwoju każdego pracownika, z najnowszej oceny. Otwórz plan, aby zaktualizować działania i zapisać postęp; wcześniejsze plany są w jego historii." />
      {isLoading ? <Loading /> : !data?.length ? (
        <Notice title="Brak planów rozwoju">Plany powstają w kroku „Program rozwoju” (ocena okresowa) albo „Wnioski rozwojowe” (pierwsza ocena).</Notice>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <label className="w-full max-w-xs">
              <span className="sr-only">Szukaj</span>
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Szukaj: pracownik, stanowisko, komórka"
                className="w-full rounded-md border border-rule-strong bg-white px-3 py-2" />
            </label>
            <div role="tablist" aria-label="Filtr planów" className="flex flex-wrap gap-1">
              {FILTERS.map(([k, l]) => (
                <button key={k} role="tab" aria-selected={filter === k} onClick={() => setFilter(k)}
                  className={`rounded-md px-3 py-1.5 text-[15px] ${filter === k ? 'bg-ink font-bold text-white' : 'hover:bg-rule/60'}`}>
                  {l} <span className={filter === k ? 'text-white/70' : 'text-ink-soft'}>({counts[k]})</span>
                </button>
              ))}
            </div>
            <label className="ml-auto flex items-center gap-2 text-[15px]">
              Sortuj
              <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} className="rounded-md border border-rule-strong bg-white px-2 py-1.5">
                <option value="next">wg pilności (po terminie, najbliższe)</option>
                <option value="name">wg nazwiska</option>
                <option value="progress">wg postępu (najmniejszy)</option>
              </select>
            </label>
          </div>
          {rows.length === 0 ? <p className="text-ink-soft">Brak planów w tym widoku.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[15px]">
                <thead className="border-b border-rule-strong text-sm text-ink-soft">
                  <tr>
                    <th className="py-2 pr-4">Pracownik</th>
                    <th className="pr-4">Postęp</th>
                    <th className="pr-4">W realizacji</th>
                    <th className="pr-4">Najbliższe działanie</th>
                    <th className="pr-4">Ostatnia aktualizacja</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule">
                  {rows.map((p) => {
                    const n = p.stats.next_action
                    const days = n ? Math.round((new Date(n.due_date).getTime() - new Date(today).getTime()) / 86400000) : 0
                    return (
                      <tr key={p.id} className="hover:bg-white">
                        <td className="py-3 pr-4">
                          <Link to={`/rozwoj/${p.id}`} className="font-bold hover:underline">{p.employee_name}</Link>
                          <span className="block text-sm text-ink-soft">{p.position}{p.org_unit && `, ${p.org_unit}`}</span>
                        </td>
                        <td className="pr-4"><Progress s={p.stats} /></td>
                        <td className="pr-4">
                          {p.stats.in_progress + p.stats.planned}
                          {p.stats.overdue > 0 && <span className="ml-2 rounded bg-bad-tint px-2 py-0.5 text-[13px] font-bold text-bad">{p.stats.overdue} po terminie</span>}
                        </td>
                        <td className="max-w-[22rem] pr-4">
                          {n ? <><span className="block truncate" title={n.title}>{n.title}</span>
                            <span className={`text-sm ${n.overdue ? 'font-bold text-bad' : days <= 14 ? 'text-warn' : 'text-ink-soft'}`}>{fmtDate(n.due_date)}, {daysLabel(days)}</span></>
                            : <span className="text-ink-soft">{p.stats.total ? 'wszystko zrealizowane' : 'brak działań'}</span>}
                        </td>
                        <td className="pr-4 text-sm text-ink-soft">{fmtDate(p.stats.last_activity)}</td>
                        <td><Link to={`/rozwoj/${p.id}`} className="text-sm font-bold underline">Otwórz plan</Link></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
