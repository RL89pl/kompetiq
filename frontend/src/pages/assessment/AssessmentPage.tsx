import { useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useAssessment, useCompetencyModel, useForms, useMe } from '../../api/hooks'
import { AssistantDrawer } from '../../components/AssistantDrawer'
import { MessageBox } from '../../components/MessageBox'
import { Badge, Button, Loading, Notice } from '../../components/ui'
import { fmtDate } from '../../lib'
import { stepsFor } from './steps'
import { JobStep } from './JobStep'
import { CriteriaStep } from './CriteriaStep'
import { EvidenceStep } from './EvidenceStep'
import { ScoresStep } from './ScoresStep'
import { InterviewStep } from './InterviewStep'
import { DevelopmentStep } from './DevelopmentStep'
import { FinalizeStep } from './FinalizeStep'
import type { StepProps } from './context'
import { BehaviourGate, pendingRatings, SkippedNotice, type Filled } from './BehaviourGate'

const COMPONENTS: Record<string, (p: StepProps) => React.ReactNode> = {
  stanowisko: JobStep, kryteria: CriteriaStep, zachowania: EvidenceStep, oceny: ScoresStep,
  rozmowa: InterviewStep, rozwoj: DevelopmentStep, sporzadzenie: FinalizeStep,
}

export function AssessmentPage() {
  const id = Number(useParams().id)
  const a = useAssessment(id)
  const forms = useForms()
  const model = useCompetencyModel()
  const me = useMe()
  const [drawer, setDrawer] = useState(false)
  const [msg, setMsg] = useState(false)
  const [gateTo, setGateTo] = useState<string | null>(null)
  const [skipped, setSkipped] = useState<Filled[]>([])
  const location = useLocation()
  const navigate = useNavigate()
  if (a.isLoading || forms.isLoading || model.isLoading) return <Loading />
  if (a.error || !a.data) return <Notice tone="bad" title="Nie można otworzyć oceny.">Ocena nie istnieje albo nie masz do niej dostępu.</Notice>
  const as = a.data
  const form = forms.data!.find((f) => f.form_type === as.form_type)!
  const steps = stepsFor(as)
  const first = as.form_type === 'FIRST'
  const accent = first ? 'first' : 'periodic'
  const props: StepProps = { a: as, form, model: model.data!, editable: as.can_edit }
  // Wyjście z „Oceny zachowań” do dalszych etapów przy nieocenionych wskaźnikach wymaga świadomej decyzji.
  const current = location.pathname.split('/').filter(Boolean)[2]
  const gateIdx = steps.findIndex((s) => s.path === 'zachowania')
  const guard = (target: string) => (e: React.MouseEvent) => {
    const ti = steps.findIndex((s) => s.path === target)
    if (as.can_edit && current === 'zachowania' && ti > gateIdx && pendingRatings(as, model.data!).length) {
      e.preventDefault()
      setGateTo(target)
    }
  }

  return (
    <div>
      <AssistantDrawer assessmentId={as.id} canUseInterview={as.can_edit || me.data?.id === as.evaluator} open={drawer} onClose={() => setDrawer(false)} />
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
        <p className="flex flex-wrap items-center gap-2">
          <Badge tone={accent}>{first ? 'Pierwsza ocena' : `Ocena okresowa, arkusz ${form.form_type.slice(-1)}`}</Badge>
          <span className="text-sm text-ink-soft">{as.status_label}</span>
          {as.result && <Badge tone={as.result === 'POSITIVE' ? 'ok' : 'bad'}>{as.result === 'POSITIVE' ? 'Ocena pozytywna' : 'Ocena negatywna'}</Badge>}
        </p>
        <h1 className="mt-2 text-[2rem]">{as.employee_detail.full_name}</h1>
        <p className="text-ink-soft">
          {as.employee_detail.position}{as.employee_detail.org_unit && `, ${as.employee_detail.org_unit}`}.
          {' '}{first ? `Okres na dokonanie oceny: ${fmtDate(as.window_from)} – ${fmtDate(as.window_to)}` : `Termin sporządzenia oceny: ${fmtDate(as.due_date)}`}
        </p>
        {!as.can_edit && (me.data?.id === as.evaluator
          ? <p className="mt-2 text-sm text-ink-soft">{as.status === 'ACKNOWLEDGED' ? 'Ocena zakończona: oceniany zapoznał się z oceną, dalsza edycja nie jest możliwa.' : 'Ocena jest tylko do odczytu na tym etapie.'}</p>
          : <p className="mt-2 text-sm text-ink-soft">Tryb podglądu. Ocenę edytuje oceniający: {as.evaluator_name}.</p>)}
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setMsg((v) => !v)} aria-expanded={msg}>Wiadomość</Button>
            <Button variant="ai" onClick={() => setDrawer(true)}>Zapytaj asystenta</Button>
          </div>
          {msg && me.data?.active_membership && (
            <div className="w-80 rounded-md border border-rule-strong bg-white p-4">
              <MessageBox assessmentId={as.id} role={me.data.active_membership.role} isEvaluator={me.data.id === as.evaluator} />
            </div>
          )}
        </div>
      </header>

      <div className="grid gap-10 lg:grid-cols-[15rem_1fr]">
        <nav aria-label="Etapy oceny" className="lg:sticky lg:top-6 lg:self-start">
          <ol className="relative">
            {steps.map((s, i) => {
              const done = s.done(as)
              return (
                <li key={s.path} className="relative pb-1 pl-9">
                  {i < steps.length - 1 && (
                    <span aria-hidden className={`absolute left-[11px] top-7 h-[calc(100%-1rem)] w-0.5 ${done ? (first ? 'bg-first' : 'bg-periodic') : 'bg-rule-strong'}`} />
                  )}
                  <NavLink to={`/oceny/${as.id}/${s.path}`} onClick={guard(s.path)} className={({ isActive }) => `group block rounded-md py-1.5 pr-2 ${isActive ? 'font-bold' : ''}`}>
                    {({ isActive }) => (
                      <>
                        <span aria-hidden className={`absolute left-0 top-2 flex size-6 items-center justify-center rounded-full border-2 text-[12px] font-bold ${done ? (first ? 'border-first bg-first text-white' : 'border-periodic bg-periodic text-white') : isActive ? 'border-ink bg-white text-ink' : 'border-rule-strong bg-paper text-ink-soft'}`}>
                          {done ? '✓' : i + 1}
                        </span>
                        <span className={`block leading-tight ${isActive ? 'text-ink' : 'text-ink group-hover:underline'}`}>{s.title}</span>
                        <span className="block text-[13px] font-normal text-ink-soft">{s.hint}</span>
                        <span className="sr-only">{done ? '(zakończony)' : ''}</span>
                      </>
                    )}
                  </NavLink>
                </li>
              )
            })}
          </ol>
        </nav>
        <div className="min-w-0">
          {gateTo && (
            <BehaviourGate a={as} model={model.data!} onBack={() => setGateTo(null)}
              onSkipped={(f) => { setSkipped(f); navigate(`/oceny/${as.id}/${gateTo}`); setGateTo(null) }} />
          )}
          {current !== 'zachowania' && <SkippedNotice filled={skipped} onClose={() => setSkipped([])} />}
          <Routes>
            <Route index element={<Navigate to={(steps.find((s) => !s.done(as)) ?? steps[steps.length - 1]).path} replace />} />
            {steps.map((s, i) => {
              const C = COMPONENTS[s.path]
              const next = steps[i + 1]
              return (
                <Route key={s.path} path={s.path} element={
                  <div>
                    <C {...props} />
                    {next && <div className="mt-10 border-t border-rule pt-4 text-right"><NavLink to={`/oceny/${as.id}/${next.path}`} onClick={guard(next.path)} className="font-bold underline underline-offset-4">Dalej: {next.title}</NavLink></div>}
                  </div>
                } />
              )
            })}
          </Routes>
        </div>
      </div>
    </div>
  )
}
