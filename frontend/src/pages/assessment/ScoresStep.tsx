import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useAssistant, useInvalidateAssessment } from '../../api/hooks'
import type { Criterion, JustificationDraft } from '../../api/types'
import { AIList, AISuggestion } from '../../components/AISuggestion'
import { Badge, Button, ErrorList, Field, Notice, Section, Select, Textarea } from '../../components/ui'
import { Link } from 'react-router-dom'
import { unratedIndicators, useDraft, type StepProps } from './context'

function CriterionScore({ crit, props }: { crit: Criterion; props: StepProps }) {
  const { a, form, editable } = props
  const invalidate = useInvalidateAssessment(a.id)
  const [just, setJust] = useState(crit.justification)
  useEffect(() => setJust(crit.justification), [crit.justification])
  const patch = useMutation({
    mutationFn: (b: Partial<Criterion>) => api(`/criteria/${crit.id}/`, { method: 'PATCH', body: b }),
    onSuccess: invalidate,
  })
  const ai = useAssistant<JustificationDraft>(a.id, 'draft-justification')
  const suggestedLabel = crit.suggested_points ? form.scale.find((s) => s.points === crit.suggested_points)?.label : null
  return (
    <article className="border-t border-rule pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xl">{crit.competency_name}</h3>
        <span className="text-sm text-ink-soft">{crit.evidence.length} przykładów, {crit.selected_indicators.length - unratedIndicators(crit).length}/{crit.selected_indicators.length} ocenionych wskaźników</span>
      </div>
      <fieldset className="mt-3" disabled={!editable || patch.isPending}>
        <legend className="sr-only">Ocena cząstkowa: {crit.competency_name}</legend>
        <div className="flex flex-wrap gap-2">
          {form.scale.map((s) => (
            <label key={s.points} className={`cursor-pointer rounded-md border-2 px-3 py-2 text-[15px] ${crit.score === s.points ? 'border-ink bg-ink text-white' : 'border-rule-strong bg-white hover:border-ink'}`}>
              <input type="radio" className="sr-only" name={`score-${crit.id}`} checked={crit.score === s.points} onChange={() => patch.mutate({ score: s.points })} />
              <span className="font-bold">{s.points} pkt</span> <span>{s.label.toLowerCase()}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {suggestedLabel && crit.score !== crit.suggested_points && (
        <p className="mt-2 text-sm text-ink-soft">Twoje oceny pomocnicze wskaźników odpowiadają poziomowi: <b>{suggestedLabel.toLowerCase()}</b> ({crit.suggested_points} pkt). To tylko odniesienie, decyzja należy do Ciebie.</p>
      )}
      {crit.evidence.length === 0 && <p className="mt-2 text-sm text-warn">Brak przykładów zachowań dla tego kryterium.</p>}
      <div className="mt-4">
        <Field label="Uzasadnienie oceny cząstkowej (do Twojej dokumentacji i rozmowy)">
          {(id) => <Textarea id={id} rows={3} value={just} disabled={!editable} onChange={(e) => setJust(e.target.value)}
            onBlur={() => just !== crit.justification && patch.mutate({ justification: just })} />}
        </Field>
        {editable && (
          <Button variant="ai" className="mt-2" disabled={crit.score === null} busy={ai.isPending} onClick={() => ai.mutate({ criterion: crit.id })}
            disabledReason="Najpierw wybierz ocenę cząstkową dla tego kryterium (przyciski z punktami powyżej).">Projekt uzasadnienia</Button>
        )}
        <div className="mt-2"><ErrorList error={ai.error || patch.error} /></div>
        {ai.data && (
          <div className="mt-3">
            <AISuggestion title={`Uzasadnienie: ${crit.competency_name}`} interactionId={ai.data.interaction_id} editableText={ai.data.result.draft}
              onAccept={(t) => { setJust(t); patch.mutate({ justification: t }) }} acceptLabel="Wstaw do uzasadnienia">
              <AIList title="Spójność oceny z materiałem" items={ai.data.result.consistency_warnings} />
              <AIList title="Czego brakuje" items={ai.data.result.missing_points} />
            </AISuggestion>
          </div>
        )}
      </div>
    </article>
  )
}

export function ScoresStep(props: StepProps) {
  const { a, form, editable } = props
  const s = a.summary
  const d = useDraft(a, ['report_text', 'report_on_time', 'prep_exam'])
  return (
    <div className="space-y-8">
      <Section title="Oceny cząstkowe"
        description={form.is_first ? 'Skala: 3 pkt poniżej oczekiwań, 5 pkt na poziomie oczekiwań, 7 pkt powyżej oczekiwań (§ 9 rozporządzenia z 2015 r.).'
          : 'Skala: 1, 3, 5, 7 lub 9 punktów. Oceny ustalasz po rozmowie oceniającej, uwzględniając jej wnioski.'}>
        <span />
      </Section>
      {editable && (() => {
        const n = a.criteria.reduce((k, c) => k + unratedIndicators(c).length, 0)
        return n > 0 && (
          <Notice tone="warn" title={`W ocenie zachowań nie oceniono ${n} ${n === 1 ? 'wskaźnika' : 'wskaźników'}`}>
            Sugerowany poziom kryterium powstaje tylko z ocenionych wskaźników.{' '}
            <Link to={`/oceny/${a.id}/zachowania`} className="font-bold underline underline-offset-4">Wróć do oceny zachowań</Link>
          </Notice>
        )
      })()}
      <div className="sticky top-2 z-10 rounded-md border border-rule-strong bg-white/95 p-4 backdrop-blur">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-2">
            <p><span className="text-sm text-ink-soft">{form.is_first ? 'Ocena łączna' : 'Średnia'}</span><br /><span className="font-serif text-2xl">{s.average ?? '—'}</span></p>
            {!form.is_first && <p><span className="text-sm text-ink-soft">Ogólny poziom</span><br /><span className="font-bold">{s.level_label || '—'}</span></p>}
            <p><span className="text-sm text-ink-soft">Wynik wg przepisów</span><br />
              {s.complete ? <Badge tone={s.result === 'POSITIVE' ? 'ok' : 'bad'}>{s.result === 'POSITIVE' ? 'pozytywna' : 'negatywna'}</Badge> : <span className="text-ink-soft">uzupełnij dane</span>}</p>
          </div>
          {s.reasons.length > 0 && <ul className="mt-2 list-disc pl-5 text-sm text-ink-soft">{s.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
        </div>


      {form.is_first && (
        <Section title="Sprawozdanie i egzamin" description="Warunki pozytywnej pierwszej oceny: zaliczony egzamin ze służby przygotowawczej (jeśli dotyczy), sprawozdanie w terminie, najwyżej jedna ocena 3 pkt i ocena łączna co najmniej 5 pkt (§ 10).">
          <fieldset disabled={!editable} className="grid max-w-3xl gap-5 md:grid-cols-2">
            <Field label="Sprawozdanie złożone w wyznaczonym terminie">{(id) => (
              <Select id={id} value={d.draft.report_on_time === null || d.draft.report_on_time === ('' as unknown) ? '' : String(d.draft.report_on_time)}
                onChange={(e) => d.set('report_on_time', e.target.value === '' ? null : e.target.value === 'true')}>
                <option value="">nie ustalono</option><option value="true">tak</option><option value="false">nie</option>
              </Select>)}</Field>
            <Field label="Egzamin ze służby przygotowawczej">{(id) => (
              <Select id={id} {...d.bind('prep_exam')}><option value="">nie ustalono</option><option value="PASSED">zaliczony</option><option value="FAILED">niezaliczony</option><option value="NA">nie dotyczy</option></Select>)}</Field>
            <div className="md:col-span-2"><Field label="Sprawozdanie ocenianego (treść lub najważniejsze punkty)" hint="Zadania, problemy i sposób ich rozwiązania, nowa wiedza i umiejętności, wnioski (§ 6).">{(id) => <Textarea id={id} rows={6} {...d.bind('report_text')} />}</Field></div>
          </fieldset>
          <ErrorList error={d.patch.error} />
          {editable && <Button className="mt-3" variant="secondary" disabled={!d.dirty} disabledReason="Brak zmian do zapisania." busy={d.patch.isPending} onClick={() => d.save()}>Zapisz</Button>}
        </Section>
      )}

      {a.status === 'DRAFT' && <Notice tone="warn" title="Kryteria nie są jeszcze ustalone">Oceny cząstkowe przyznajesz po okresie oceny. Najpierw potwierdź ustalenie kryteriów.</Notice>}
      {a.criteria.map((c) => <CriterionScore key={c.id} crit={c} props={props} />)}
    </div>
  )
}
