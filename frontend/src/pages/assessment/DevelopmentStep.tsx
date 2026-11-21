import { useState } from 'react'
import { reportOutcome, useAssistant, useMe, usePlan } from '../../api/hooks'
import type { DevelopmentSuggestions } from '../../api/types'
import { AISuggestion } from '../../components/AISuggestion'
import { ACTION_TYPES, DevelopmentPlanEditor, useActionMutations } from '../../components/DevelopmentPlanEditor'
import { Button, ErrorList, Field, Loading, Section, Textarea } from '../../components/ui'
import { useDraft, type StepProps } from './context'

function addMonths(n: number) {
  const d = new Date()
  d.setMonth(d.getMonth() + n)
  return d.toISOString().slice(0, 10)
}

export function DevelopmentStep({ a, form, model, editable }: StepProps) {
  const plan = usePlan(a.id)
  const me = useMe()
  const owner = me.data?.id === a.evaluator || me.data?.active_membership?.role === 'ADMIN'
  const ai = useAssistant<DevelopmentSuggestions>(a.id, 'development-suggestions')
  const d = useDraft(a, ['development_conclusions'])
  const [added, setAdded] = useState<Set<number>>(new Set())
  const muts = useActionMutations(plan.data ?? ({ id: 0, assessment: a.id } as never))
  if (plan.isLoading || !plan.data) return <Loading />

  return (
    <div className="space-y-10">
      <Section title={form.is_first ? 'Wnioski dotyczące rozwoju zawodowego' : 'Wnioski do indywidualnego programu rozwoju zawodowego'}
        description={form.is_first ? 'Przy ocenie pozytywnej możesz, w porozumieniu z kierującym komórką, sporządzić wnioski dotyczące rozwoju (§ 10 ust. 6).'
          : 'Wnioski wpisujesz do arkusza; IPRZ ustala się na ich podstawie (art. 81 ust. 5 ustawy).'}
        actions={editable && <Button variant="ai" busy={ai.isPending} onClick={() => ai.mutate({})}>Zaproponuj działania rozwojowe</Button>}>
        <ErrorList error={ai.error} />
        {ai.data && (
          <div className="mb-6 space-y-4">
            <AISuggestion title="Wnioski do arkusza" interactionId={ai.data.interaction_id} editableText={ai.data.result.conclusions_draft}
              onAccept={(t) => d.patch.mutate({ development_conclusions: t })} acceptLabel="Wstaw do wniosków" />
            <AISuggestion title="Proponowane działania (70-20-10)" interactionId={ai.data.interaction_id}>
              <ul className="divide-y divide-ai/20">
                {ai.data.result.actions.map((x, i) => {
                  const comp = model.competencies.find((c) => c.code === x.competency_code)
                  return (
                    <li key={i} className="flex flex-wrap items-start justify-between gap-3 py-3">
                      <div className="max-w-[62ch] text-[15px]">
                        <p className="font-bold">{x.title}</p>
                        <p className="text-ink-soft">{ACTION_TYPES[x.type]}{comp && `, ${comp.name}`}, około {x.timeframe_months} mies.</p>
                        <p className="mt-1">{x.description}</p>
                        <p className="mt-1"><span className="font-bold">Miernik: </span>{x.success_measure}</p>
                      </div>
                      {editable && (added.has(i) ? <span className="text-sm font-bold text-ok">Dodano do planu</span> : (
                        <Button variant="ai" busy={muts.create.isPending && muts.create.variables?.title === x.title}
                          onClick={() => muts.create.mutate({
                            title: x.title, description: x.description, type: x.type, success_measure: x.success_measure,
                            competency: comp?.id ?? null, due_date: addMonths(x.timeframe_months), from_ai_suggestion: true,
                          }, { onSuccess: () => { setAdded(new Set(added).add(i)); reportOutcome(ai.data!.interaction_id, 'ACCEPTED') } })}>Dodaj do planu</Button>
                      ))}
                    </li>
                  )
                })}
              </ul>
            </AISuggestion>
          </div>
        )}
        <fieldset disabled={!editable || a.status === 'FINALIZED' || a.status === 'ACKNOWLEDGED' || a.status === 'APPROVED'}>
          <Field label="Wnioski (pole arkusza)">{(id) => <Textarea id={id} rows={5} {...d.bind('development_conclusions')} />}</Field>
          <ErrorList error={d.patch.error} />
          {editable && <Button className="mt-3" variant="secondary" disabled={!d.dirty} busy={d.patch.isPending} onClick={() => d.save()}>Zapisz wnioski</Button>}
        </fieldset>
      </Section>
      <Section title="Plan działań rozwojowych" description="Plan żyje po ocenie: aktualizuj statusy i notuj postępy. Widać go też w zakładce Plany rozwoju.">
        <DevelopmentPlanEditor plan={plan.data} editable={owner} />
      </Section>
    </div>
  )
}
