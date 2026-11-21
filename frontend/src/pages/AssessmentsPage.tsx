import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAssessments } from '../api/hooks'
import { Badge, Loading, PageHeader } from '../components/ui'
import { fmtDate } from '../lib'

const FILTERS = [
  { key: '?status=DRAFT,CRITERIA_SET,INTERVIEW_DONE,FINALIZED,APPROVED', label: 'W toku' },
  { key: '?status=ACKNOWLEDGED', label: 'Zakończone' },
  { key: '', label: 'Wszystkie' },
]

export function AssessmentsPage() {
  const [f, setF] = useState(FILTERS[0].key)
  const { data, isLoading } = useAssessments(f)
  return (
    <div>
      <PageHeader title="Oceny" />
      <div role="tablist" className="mb-4 flex gap-1">
        {FILTERS.map((x) => (
          <button key={x.label} role="tab" aria-selected={f === x.key} onClick={() => setF(x.key)}
            className={`rounded-md px-3 py-1.5 text-[15px] ${f === x.key ? 'bg-ink font-bold text-white' : 'hover:bg-rule/60'}`}>{x.label}</button>
        ))}
      </div>
      {isLoading ? <Loading /> : !data?.length ? <p className="text-ink-soft">Brak ocen w tym widoku.</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[15px]">
            <thead className="border-b border-rule-strong text-sm text-ink-soft">
              <tr><th className="py-2 pr-4">Oceniany</th><th className="pr-4">Rodzaj</th><th className="pr-4">Status</th><th className="pr-4">Termin</th><th className="pr-4">Wynik</th><th>Oceniający</th></tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {data.map((a) => (
                <tr key={a.id} className="hover:bg-white">
                  <td className="py-3 pr-4"><Link to={`/oceny/${a.id}`} className="font-bold hover:underline">{a.employee_name}</Link><br /><span className="text-sm text-ink-soft">{a.employee_position}</span></td>
                  <td className="pr-4"><Badge tone={a.form_type === 'FIRST' ? 'first' : 'periodic'}>{a.form_type === 'FIRST' ? 'Pierwsza' : `Okresowa ${a.form_type.slice(-1)}`}</Badge></td>
                  <td className="pr-4">{a.status_label}</td>
                  <td className="pr-4">{fmtDate(a.due_date ?? a.window_to)}</td>
                  <td className="pr-4">{a.result ? <Badge tone={a.result === 'POSITIVE' ? 'ok' : 'bad'}>{a.result === 'POSITIVE' ? 'pozytywna' : 'negatywna'}</Badge> : '—'}</td>
                  <td>{a.evaluator_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
