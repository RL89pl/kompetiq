import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { qk, useHROverview } from '../api/hooks'
import { Badge, Button, ErrorList, Loading, Notice, PageHeader } from '../components/ui'
import { daysLabel, fmtDate } from '../lib'

function Remind({ id }: { id: number }) {
  const [done, setDone] = useState(false)
  const m = useMutation({
    mutationFn: () => api(`/assessments/${id}/message/`, { method: 'POST', body: { to: 'evaluator', reminder: true, message: 'Proszę o kontynuację procesu oceny zgodnie z terminami.' } }),
    onSuccess: () => setDone(true),
  })
  if (done) return <span className="text-sm font-bold text-ok">Wysłano</span>
  return <Button variant="ghost" className="!px-2 !py-1 text-sm" busy={m.isPending} onClick={() => m.mutate()}>Przypomnij</Button>
}

export function HRPage() {
  const { data, isLoading, error } = useHROverview()
  const qc = useQueryClient()
  const send = useMutation({
    mutationFn: () => api<{ sent: number }>('/hr/send-reminders/', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.hr }),
  })
  const [filter, setFilter] = useState<'all' | 'overdue' | 'open'>('all')
  if (error) return <ErrorList error={error} />
  if (isLoading || !data) return <Loading />
  const max = Math.max(1, ...data.by_status.map((s) => s.count))
  const rows = data.assessments.filter((r) => filter === 'all' || (filter === 'overdue' ? r.next_deadline?.overdue : !['FINALIZED', 'APPROVED', 'ACKNOWLEDGED'].includes(r.status)))

  return (
    <div className="space-y-10">
      <PageHeader title="Panel HR" lead="Monitorowanie ocen w instytucji: statusy procesów, terminy i przypomnienia dla oceniających.">
        <div className="text-right">
          <Button busy={send.isPending} onClick={() => send.mutate()}>Wyślij przypomnienia o terminach</Button>
          {send.data && <p className="mt-1 text-sm text-ok" role="status">Wysłano: {send.data.sent} (bez powtórzeń wcześniejszych przypomnień)</p>}
          <ErrorList error={send.error} />
        </div>
      </PageHeader>

      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-rule bg-rule md:grid-cols-5">
        {[['Wszystkie oceny', data.totals.all, ''], ['W toku', data.totals.in_progress, ''], ['Sporządzone', data.totals.done, ''],
          ['Po terminie', data.totals.overdue, data.totals.overdue ? 'text-bad' : ''], ['Negatywne', data.totals.negative, '']].map(([l, v, cls]) => (
          <div key={l as string} className="bg-white p-4"><dt className="text-sm text-ink-soft">{l}</dt><dd className={`font-serif text-3xl ${cls}`}>{v}</dd></div>
        ))}
      </dl>

      <div className="grid gap-10 lg:grid-cols-2">
        <section>
          <h2 className="text-xl">Etapy procesu</h2>
          <ul className="mt-3 space-y-2">
            {data.by_status.map((s) => (
              <li key={s.status} className="grid grid-cols-[13rem_1fr_2rem] items-center gap-3 text-[15px]">
                <span>{s.label}</span>
                <span className="h-3 rounded bg-rule"><span className="block h-3 rounded bg-periodic" style={{ width: `${(s.count / max) * 100}%` }} /></span>
                <span className="text-right font-bold">{s.count}</span>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h2 className="text-xl">Komórki organizacyjne</h2>
          <table className="mt-3 w-full text-left text-[15px]">
            <thead className="border-b border-rule-strong text-sm text-ink-soft"><tr><th className="py-1">Komórka</th><th>W toku</th><th>Sporządzone</th><th>Po terminie</th></tr></thead>
            <tbody className="divide-y divide-rule">
              {data.units.map((u) => <tr key={u.unit}><td className="py-2">{u.unit}</td><td>{u.in_progress}</td><td>{u.done}</td><td className={u.overdue ? 'font-bold text-bad' : ''}>{u.overdue}</td></tr>)}
            </tbody>
          </table>
        </section>
      </div>

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl">Oceny i najbliższe terminy</h2>
          <div role="tablist" className="flex gap-1">
            {([['all', 'Wszystkie'], ['open', 'W toku'], ['overdue', 'Po terminie']] as const).map(([k, l]) => (
              <button key={k} role="tab" aria-selected={filter === k} onClick={() => setFilter(k)}
                className={`rounded-md px-3 py-1.5 text-[15px] ${filter === k ? 'bg-ink font-bold text-white' : 'hover:bg-rule/60'}`}>{l}</button>
            ))}
          </div>
        </div>
        {rows.length === 0 ? <Notice title="Brak ocen w tym widoku" /> : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-[15px]">
              <thead className="border-b border-rule-strong text-sm text-ink-soft">
                <tr><th className="py-2 pr-3">Oceniany</th><th className="pr-3">Rodzaj</th><th className="pr-3">Etap</th><th className="pr-3">Oceniający</th><th className="pr-3">Najbliższy termin</th><th /></tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="py-2 pr-3"><Link to={`/oceny/${r.id}`} className="font-bold hover:underline">{r.employee}</Link><br /><span className="text-sm text-ink-soft">{r.position}, {r.unit}</span></td>
                    <td className="pr-3"><Badge tone={r.form_type === 'FIRST' ? 'first' : 'periodic'}>{r.form_type === 'FIRST' ? 'Pierwsza' : `Okresowa ${r.form_type.slice(-1)}`}</Badge></td>
                    <td className="pr-3">{r.status_label}{r.result && <> <Badge tone={r.result === 'POSITIVE' ? 'ok' : 'bad'}>{r.result === 'POSITIVE' ? 'pozytywna' : 'negatywna'}</Badge></>}</td>
                    <td className="pr-3">{r.evaluator}</td>
                    <td className="pr-3">{r.next_deadline ? <><span className={r.next_deadline.overdue ? 'font-bold text-bad' : r.next_deadline.days_left <= 14 ? 'text-warn' : ''}>{r.next_deadline.label}</span><br /><span className="text-sm text-ink-soft">{fmtDate(r.next_deadline.date)}, {daysLabel(r.next_deadline.days_left)}</span></> : '—'}</td>
                    <td>{['ACKNOWLEDGED', 'CANCELLED'].includes(r.status) ? null : <Remind id={r.id} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
