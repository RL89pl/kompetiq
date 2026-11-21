import { Link } from 'react-router-dom'
import { useDeadlines } from '../api/hooks'
import { Loading, PageHeader } from '../components/ui'
import { daysLabel, fmtDate } from '../lib'

export function DeadlinesPage() {
  const { data, isLoading } = useDeadlines()
  return (
    <div>
      <PageHeader title="Terminy" lead="Terminy wyliczone z ustawy o służbie cywilnej i rozporządzeń na najbliższe 90 dni oraz terminy przekroczone. Przy nieobecnościach dłuższych niż miesiąc termin oceny okresowej się wydłuża (art. 81 ust. 7 ustawy)." />
      {isLoading ? <Loading /> : !data?.length ? <p className="text-ink-soft">Brak terminów.</p> : (
        <ol className="relative ml-3 border-l-2 border-rule">
          {data.map((d, i) => (
            <li key={i} className="relative pb-6 pl-6">
              <span className={`absolute -left-[9px] top-1.5 size-4 rounded-full border-2 border-white ${d.overdue ? 'bg-bad' : d.days_left <= 14 ? 'bg-warn' : 'bg-ink-soft'}`} aria-hidden />
              <p className={`text-sm font-bold ${d.overdue ? 'text-bad' : 'text-ink-soft'}`}>{fmtDate(d.date)}, {daysLabel(d.days_left)}</p>
              <Link to={`/oceny/${d.assessment}`} className="hover:underline"><span className="font-bold">{d.label}</span>: {d.employee}</Link>
              {d.basis && <p className="text-sm text-ink-soft">{d.basis}</p>}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
