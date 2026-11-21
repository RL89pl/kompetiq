import { Download } from '../../components/Download'
import { reportOutcome, useAssistant, usePatchAssessment, useTransition } from '../../api/hooks'
import type { FeedbackItem, InterviewScript } from '../../api/types'
import { AISuggestion } from '../../components/AISuggestion'
import { AssistantChat } from '../../components/AssistantChat'
import { Badge, Button, ErrorList, Field, Input, Notice, Section, Textarea } from '../../components/ui'
import { useDraft, type StepProps } from './context'

function Feedback({ items }: { items: FeedbackItem[] }) {
  return (
    <ul className="space-y-3">
      {items.map((f, i) => (
        <li key={i} className="rounded-md border border-rule bg-white p-3 text-[15px]">
          <p className="font-bold">{f.competency}</p>
          <p><span className="text-ink-soft">Sytuacja: </span>{f.situation}</p>
          <p><span className="text-ink-soft">Zachowanie: </span>{f.behaviour}</p>
          <p><span className="text-ink-soft">Wpływ: </span>{f.impact}</p>
        </li>
      ))}
    </ul>
  )
}

function Script({ s }: { s: InterviewScript }) {
  return (
    <div className="space-y-6">
      <div><h3 className="text-lg">Cel rozmowy</h3><p className="mt-1 max-w-[75ch]">{s.goal}</p></div>
      <div>
        <h3 className="text-lg">Przygotowanie</h3>
        <ul className="mt-1 space-y-1">{s.preparation_checklist.map((x) => <li key={x} className="flex gap-2"><input type="checkbox" className="mt-1.5" aria-label={x} /> <span>{x}</span></li>)}</ul>
      </div>
      <div><h3 className="text-lg">Otwarcie</h3><p className="mt-1 max-w-[75ch]">{s.opening}</p></div>
      <ol className="space-y-5">
        {s.sections.map((sec, i) => (
          <li key={i}>
            <h3 className="text-lg">{i + 1}. {sec.title}</h3>
            <ul className="mt-1 list-disc space-y-1 pl-5">{sec.talking_points.map((x) => <li key={x}>{x}</li>)}</ul>
            {sec.questions_to_employee.length > 0 && (
              <ul className="mt-2 space-y-1 border-l-2 border-rule-strong pl-3 italic">{sec.questions_to_employee.map((x) => <li key={x}>{x}</li>)}</ul>
            )}
          </li>
        ))}
      </ol>
      {s.strengths_feedback.length > 0 && <div><h3 className="mb-2 text-lg">Informacja zwrotna: mocne strony</h3><Feedback items={s.strengths_feedback} /></div>}
      {s.development_feedback.length > 0 && <div><h3 className="mb-2 text-lg">Informacja zwrotna: obszary do rozwoju</h3><Feedback items={s.development_feedback} /></div>}
      <div><h3 className="text-lg">Rozmowa o rozwoju</h3><ul className="mt-1 space-y-1 italic">{s.development_dialogue_questions.map((x) => <li key={x}>{x}</li>)}</ul></div>
      <div><h3 className="text-lg">Zamknięcie</h3><p className="mt-1 max-w-[75ch]">{s.closing}</p></div>
      <div><h3 className="text-lg">Elementy formalne</h3><ul className="mt-1 list-disc pl-5">{s.formal_reminders.map((x) => <li key={x}>{x}</li>)}</ul></div>
      <div><h3 className="text-lg">Trudne momenty</h3><ul className="mt-1 list-disc pl-5">{s.difficult_moments_tips.map((x) => <li key={x}>{x}</li>)}</ul></div>
    </div>
  )
}

export function InterviewStep({ a, form, editable }: StepProps) {
  const ai = useAssistant<InterviewScript>(a.id, 'interview-script')
  const patch = usePatchAssessment(a.id)
  const tr = useTransition(a.id)
  const keys = form.is_first ? (['evaluation_interview_date', 'interview_notes'] as const)
    : (['evaluation_interview_date', 'period_from', 'period_to', 'interview_notes'] as const)
  const d = useDraft(a, [...keys])
  const canComplete = a.available_actions.includes('complete_interview')

  return (
    <div className="space-y-10">
      <Section title="Scenariusz rozmowy oceniającej"
        description={form.is_first ? 'Rozmowę przeprowadzasz niezwłocznie po złożeniu sprawozdania. Może w niej uczestniczyć kierujący komórką (§ 8). Możesz omówić kierunki rozwoju i potrzeby ocenianego.'
          : 'Rozmowę przeprowadzasz przed sporządzeniem oceny na piśmie (§ 10 rozporządzenia z 2016 r.).'}
        actions={editable && <Button variant="ai" busy={ai.isPending} onClick={() => ai.mutate({})}>{a.interview_plan ? 'Przygotuj nowy scenariusz' : 'Przygotuj scenariusz z asystentem'}</Button>}>
        <ErrorList error={ai.error} />
        {ai.data && (
          <AISuggestion title="Scenariusz rozmowy" interactionId={ai.data.interaction_id}
            onAccept={() => patch.mutate({ interview_plan: ai.data!.result })} acceptLabel="Zapisz jako mój scenariusz">
            <div className="mt-2 max-h-[32rem] overflow-y-auto rounded-md bg-white p-4"><Script s={ai.data.result} /></div>
          </AISuggestion>
        )}
        {a.interview_plan && !ai.data && (
          <div>
            <p className="mb-4 flex flex-wrap items-center gap-3"><Badge tone="ai">przygotowany z asystentem, zatwierdzony przez Ciebie</Badge>
              <Download path={`/assessments/${a.id}/export/interview/`} label="Scenariusz do druku" />
              {editable && <button className="text-sm underline" onClick={() => { patch.mutate({ interview_plan: null }); reportOutcome(null, 'REJECTED') }}>Usuń scenariusz</button>}</p>
            <Script s={a.interview_plan} />
          </div>
        )}
        {!a.interview_plan && !ai.data && <p className="text-ink-soft">Asystent przygotuje scenariusz na podstawie Twoich przykładów i ocen. Bez nich będzie ogólny.</p>}
      </Section>

      {editable && (
        <Section title="Porozmawiaj z asystentem o tej rozmowie"
          description="Zapytaj o pytania do pracownika, kwestie do omówienia, uporządkowanie argumentów lub reakcję na trudne momenty. Asystent korzysta z materiału z tej oceny.">
          <AssistantChat mode="INTERVIEW" assessmentId={a.id} />
        </Section>
      )}

      <Section title="Po rozmowie">
        <fieldset disabled={!editable} className="grid max-w-3xl gap-5 md:grid-cols-3">
          <Field label="Data rozmowy oceniającej">{(id) => <Input id={id} type="date" {...d.bind('evaluation_interview_date')} />}</Field>
          {!form.is_first && <>
            <Field label="Okres podlegania ocenie: od">{(id) => <Input id={id} type="date" {...d.bind('period_from' as never)} />}</Field>
            <Field label="Okres podlegania ocenie: do">{(id) => <Input id={id} type="date" {...d.bind('period_to' as never)} />}</Field>
          </>}
          <div className="md:col-span-3">
            <Field label="Notatki i wnioski z rozmowy" hint="Wnioski z rozmowy uwzględniasz przy przyznawaniu ocen cząstkowych.">{(id) => <Textarea id={id} rows={5} {...d.bind('interview_notes')} />}</Field>
          </div>
        </fieldset>
        <div className="mt-4 space-y-3">
          <ErrorList error={d.patch.error || tr.error} />
          {editable && (
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" disabled={!d.dirty} disabledReason="Brak zmian do zapisania." busy={d.patch.isPending} onClick={() => d.save()}>Zapisz</Button>
              {canComplete && <Button busy={tr.isPending} onClick={async () => { if (d.dirty) await d.save(); tr.mutate({ action: 'complete_interview' }) }}>Potwierdź przeprowadzenie rozmowy</Button>}
            </div>
          )}
          {a.status === 'DRAFT' && <Notice tone="warn">Najpierw potwierdź ustalenie kryteriów.</Notice>}
        </div>
      </Section>
    </div>
  )
}
