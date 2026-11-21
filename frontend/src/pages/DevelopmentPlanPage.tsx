import { Link, useParams } from 'react-router-dom'
import { usePlanDetail } from '../api/hooks'
import { DevelopmentPlanEditor } from '../components/DevelopmentPlanEditor'
import { Download } from '../components/Download'
import { Badge, Loading, Notice } from '../components/ui'
import { fmtDate } from '../lib'

export function DevelopmentPlanPage() {
  const id = Number(useParams().id)
  const { data: p, isLoading, error } = usePlanDetail(id)
  if (isLoading) return <Loading />
  if (error || !p) return <Notice tone="bad" title="Nie można otworzyć planu.">Plan nie istnieje albo nie masz do niego dostępu.</Notice>
  return (
    <div className="space-y-8">
      <div>
        <Link to="/rozwoj" className="text-sm underline">Wszystkie plany rozwoju</Link>
        <h1 className="mt-2 text-[2rem]">{p.employee_name}</h1>
        <p className="text-ink-soft">{p.position}{p.org_unit && `, ${p.org_unit}`}. Oceniający: {p.evaluator_name}.</p>
        <p className="mt-2 flex flex-wrap items-center gap-3 text-[15px]">
          <span>Plan z oceny: <Link to={`/oceny/${p.assessment}`} className="font-bold underline">{p.assessment_label}</Link>{p.assessment_date && `, ${fmtDate(p.assessment_date)}`}</span>
          {p.assessment_result && <Badge tone={p.assessment_result === 'POSITIVE' ? 'ok' : 'bad'}>{p.assessment_result === 'POSITIVE' ? 'ocena pozytywna' : 'ocena negatywna'}</Badge>}
          <Download path={`/assessments/${p.assessment}/export/development-plan/`} label="Plan do druku" />
        </p>
      </div>
      {p.summary && (
        <section className="max-w-[75ch]">
          <h2 className="text-xl">Wnioski z oceny</h2>
          <p className="mt-1 whitespace-pre-line">{p.summary}</p>
        </section>
      )}
      <section>
        <h2 className="mb-3 text-xl">Działania rozwojowe</h2>
        {!p.can_edit && <p className="mb-2 text-sm text-ink-soft">Podgląd. Plan prowadzi oceniający: {p.evaluator_name}.</p>}
        <DevelopmentPlanEditor plan={p} editable={p.can_edit} />
      </section>
      {p.history.length > 0 && (
        <section>
          <h2 className="text-xl">Wcześniejsze plany</h2>
          <ul className="mt-2 divide-y divide-rule border-y border-rule">
            {p.history.map((h) => (
              <li key={h.id} className="flex flex-wrap justify-between gap-2 py-2">
                <Link to={`/rozwoj/${h.id}`} className="underline">{h.label}, {fmtDate(h.date)}</Link>
                <span className="text-sm text-ink-soft">{h.progress.done} z {h.progress.total} działań zrealizowanych</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
