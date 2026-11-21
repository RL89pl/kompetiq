import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useAssistant, useInvalidateAssessment } from '../../api/hooks'
import type { Criterion, Evidence, EvidenceAnalysis, GuidingQuestions, Indicator } from '../../api/types'
import { AIList, AISuggestion } from '../../components/AISuggestion'
import { LevelScale } from '../../components/LevelScale'
import { SuggestedLevel } from '../../components/SuggestedLevel'
import { Badge, Button, ErrorList, Field, Input, Section, Textarea } from '../../components/ui'
import { fmtDate, LEVEL_SHORT } from '../../lib'
import type { StepProps } from './context'

const COMPLETENESS: Record<string, string> = {
  complete: 'kompletny', missing_action: 'brak opisu działania', missing_result: 'brak rezultatu', too_general: 'zbyt ogólny',
}

function EvidenceForm({ crit, indicator, assessmentId, initial, onDone }: {
  crit: Criterion; indicator: number | null; assessmentId: number; initial?: Evidence; onDone: () => void
}) {
  const invalidate = useInvalidateAssessment(assessmentId)
  const [f, setF] = useState({
    situation: initial?.situation ?? '', action: initial?.action ?? '', result: initial?.result ?? '', occurred_on: initial?.occurred_on ?? '',
  })
  const save = useMutation({
    mutationFn: () => initial
      ? api(`/evidence/${initial.id}/`, { method: 'PATCH', body: { ...f, occurred_on: f.occurred_on || null } })
      : api('/evidence/', { method: 'POST', body: { ...f, occurred_on: f.occurred_on || null, criterion: crit.id, indicator } }),
    onSuccess: () => { invalidate(); onDone() },
  })
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value })
  return (
    <form className="mt-3 grid gap-3 rounded-md border border-rule bg-white p-4 md:grid-cols-3" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <Field label="Sytuacja" hint="Kiedy, gdzie, jakie zadanie?">{(id) => <Textarea id={id} rows={3} required value={f.situation} onChange={set('situation')} />}</Field>
      <Field label="Działanie" hint="Co konkretnie zrobił(a) oceniany?">{(id) => <Textarea id={id} rows={3} value={f.action} onChange={set('action')} />}</Field>
      <Field label="Rezultat" hint="Jaki był efekt dla zadania lub zespołu?">{(id) => <Textarea id={id} rows={3} value={f.result} onChange={set('result')} />}</Field>
      <Field label="Data zdarzenia">{(id) => <Input id={id} type="date" value={f.occurred_on ?? ''} onChange={set('occurred_on')} />}</Field>
      <div className="flex items-end gap-2 md:col-span-2">
        <Button type="submit" busy={save.isPending}>{initial ? 'Zapisz zmiany' : 'Dodaj przykład'}</Button>
        <Button type="button" variant="ghost" onClick={onDone}>Anuluj</Button>
      </div>
      <div className="md:col-span-3"><ErrorList error={save.error} /></div>
    </form>
  )
}

function EvidenceItem({ e, crit, assessmentId, editable, mapping }: {
  e: Evidence; crit: Criterion; assessmentId: number; editable: boolean; mapping?: EvidenceAnalysis['mappings'][number]
}) {
  const [edit, setEdit] = useState(false)
  const invalidate = useInvalidateAssessment(assessmentId)
  const del = useMutation({ mutationFn: () => api(`/evidence/${e.id}/`, { method: 'DELETE' }), onSuccess: invalidate })
  if (edit) return <EvidenceForm crit={crit} indicator={e.indicator} assessmentId={assessmentId} initial={e} onDone={() => setEdit(false)} />
  return (
    <li className="rounded-md border border-rule bg-white p-3">
      <p className="text-sm text-ink-soft">{fmtDate(e.occurred_on)}</p>
      <dl className="mt-1 grid gap-x-4 gap-y-1 text-[15px] md:grid-cols-[6rem_1fr]">
        <dt className="font-bold">Sytuacja</dt><dd>{e.situation}</dd>
        <dt className="font-bold">Działanie</dt><dd>{e.action || <span className="text-warn">nie opisano</span>}</dd>
        <dt className="font-bold">Rezultat</dt><dd>{e.result || <span className="text-warn">nie opisano</span>}</dd>
      </dl>
      {mapping && (
        <p className="mt-2 border-l-2 border-ai pl-3 text-[14px] text-ai">
          AI: {mapping.observed_behaviour}
          {mapping.closest_anchor_level && <> Najbliższy opis: <b>{LEVEL_SHORT[mapping.closest_anchor_level].toLowerCase()} oczekiwań</b>. {mapping.anchor_rationale}</>}
          {mapping.completeness !== 'complete' && <> Przykład: {COMPLETENESS[mapping.completeness]}.</>}
        </p>
      )}
      {editable && (
        <div className="mt-2 flex gap-2">
          <Button variant="ghost" className="!px-2 !py-1 text-sm" onClick={() => setEdit(true)}>Edytuj</Button>
          <Button variant="ghost" className="!px-2 !py-1 text-sm" busy={del.isPending} onClick={() => del.mutate()}>Usuń</Button>
        </div>
      )}
    </li>
  )
}

function IndicatorBlock({ ind, crit, assessmentId, editable, questions, analysis }: {
  ind: Indicator; crit: Criterion; assessmentId: number; editable: boolean; questions?: string[]; analysis?: EvidenceAnalysis
}) {
  const [adding, setAdding] = useState(false)
  const invalidate = useInvalidateAssessment(assessmentId)
  const rating = crit.ratings.find((r) => r.indicator === ind.id)
  const rate = useMutation({
    mutationFn: (b: { level: number | null; no_basis?: boolean }) => api(`/criteria/${crit.id}/rating/`, { method: 'PUT', body: { indicator: ind.id, ...b } }),
    onSuccess: invalidate,
  })
  const items = crit.evidence.filter((e) => e.indicator === ind.id)
  const maps = analysis?.mappings.filter((m) => m.indicator_id === ind.id && m.closest_anchor_level) ?? []
  const highlight = maps.length === 1 ? maps[0].closest_anchor_level : null
  const noEvidence = analysis?.indicators_without_evidence.includes(ind.id)
  return (
    <article className="border-t border-rule pt-5">
      <h3 className="font-sans text-[17px] font-bold">{ind.text} {noEvidence && <Badge tone="warn">brak przykładów</Badge>}</h3>
      {questions && questions.length > 0 && (
        <ul className="mt-2 space-y-1 border-l-2 border-dashed border-ai pl-3 text-[15px] text-ai" aria-label="Pytania pomocnicze AI">
          {questions.map((q) => <li key={q}>{q}</li>)}
        </ul>
      )}
      <ul className="mt-3 space-y-2">
        {items.map((e) => <EvidenceItem key={e.id} e={e} crit={crit} assessmentId={assessmentId} editable={editable} mapping={analysis?.mappings.find((m) => m.evidence_id === e.id)} />)}
      </ul>
      {editable && (adding
        ? <EvidenceForm crit={crit} indicator={ind.id} assessmentId={assessmentId} onDone={() => setAdding(false)} />
        : <Button variant="secondary" className="mt-3" onClick={() => setAdding(true)}>Dodaj przykład zachowania</Button>)}
      <details className="mt-4" open>
        <summary className="cursor-pointer text-[15px] font-bold">Które zachowanie najlepiej opisuje to, co obserwowałeś? {rating?.level ? `(${LEVEL_SHORT[rating.level].toLowerCase()})` : rating?.no_basis ? '(brak podstaw)' : ''}</summary>
        <LevelScale indicator={ind} value={rating?.no_basis ? null : rating?.level ?? null} disabled={!editable || rate.isPending}
          onChange={(level) => rate.mutate({ level })} highlight={highlight} />
        <label className="mt-2 flex items-center gap-2 text-[15px]">
          <input type="checkbox" disabled={!editable} checked={!!rating?.no_basis} onChange={(e) => rate.mutate({ level: null, no_basis: e.target.checked })} />
          Brak okazji do zaobserwowania zachowania (brak podstaw do oceny wskaźnika)
        </label>
      </details>
    </article>
  )
}

export function EvidenceStep({ a, form, model, editable }: StepProps) {
  const [sel, setSel] = useState(a.criteria[0]?.id)
  const crit = a.criteria.find((c) => c.id === sel) ?? a.criteria[0]
  const comp = model.competencies.find((c) => c.id === crit.competency)!
  const inds = comp.indicators.filter((i) => crit.selected_indicators.includes(i.id))
  const qs = useAssistant<GuidingQuestions>(a.id, 'guiding-questions')
  const an = useAssistant<EvidenceAnalysis>(a.id, 'analyze-evidence')
  const questions = qs.data && qs.variables?.criterion === crit.id ? qs.data.result : undefined
  const analysis = an.data && an.variables?.criterion === crit.id ? an.data.result : undefined
  const loose = crit.evidence.filter((e) => !e.indicator)

  return (
    <div className="space-y-8">
      <Section title="Ocena zachowań" description="Oprzyj ocenę na konkretnych przykładach z ocenianego okresu. Uwzględnij powtarzalność zachowania, złożoność sytuacji i uprawnienia ocenianego. Zapisuj na bieżąco, nie tylko przed oceną.">
        <div role="tablist" aria-label="Kryteria" className="flex flex-wrap gap-1">
          {a.criteria.map((c) => (
            <button key={c.id} role="tab" aria-selected={c.id === crit.id} onClick={() => setSel(c.id)}
              className={`rounded-md px-3 py-1.5 text-[15px] ${c.id === crit.id ? 'bg-ink font-bold text-white' : 'bg-white hover:bg-rule/50'}`}>
              {c.competency_name} <span className={c.id === crit.id ? 'text-white/70' : 'text-ink-soft'}>({c.evidence.length})</span>
            </button>
          ))}
        </div>
      </Section>

      <div role="tabpanel" className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl">{crit.competency_name}</h2>
          {editable && (
            <div className="flex flex-wrap gap-2">
              <Button variant="ai" busy={qs.isPending} onClick={() => qs.mutate({ criterion: crit.id })}>Pytania pomocnicze</Button>
              <Button variant="ai" busy={an.isPending} disabled={!crit.evidence.length}
                disabledReason="Dodaj co najmniej jeden przykład zachowania dla tego kryterium." onClick={() => an.mutate({ criterion: crit.id })}>Przeanalizuj przykłady</Button>
            </div>
          )}
        </div>
        <ErrorList error={qs.error || an.error} />
        {analysis && (
          <AISuggestion title={`Analiza przykładów: ${crit.competency_name}`} interactionId={an.data!.interaction_id}>
            <p className="text-[15px]">{analysis.overview}</p>
            <AIList title="Czego brakuje w materiale" items={analysis.missing_evidence_prompts} />
            {analysis.neutrality_issues.length > 0 && (
              <div className="mt-3">
                <p className="text-sm font-bold">Sformułowania do zmiany</p>
                <ul className="mt-1 space-y-2 text-[15px]">
                  {analysis.neutrality_issues.map((n, i) => (
                    <li key={i}><q className="italic">{n.fragment}</q>: {n.issue} <span className="block">Propozycja: {n.suggestion}</span></li>
                  ))}
                </ul>
              </div>
            )}
            <AIList title="Ryzyko błędów oceniania" items={analysis.bias_warnings} />
            <AIList title="Mocne strony widoczne w przykładach" items={analysis.strengths} />
            <AIList title="Obszary do rozwoju" items={analysis.development_areas} />
            <AIList title="Do poruszenia na rozmowie" items={analysis.interview_topics} />
          </AISuggestion>
        )}
        {inds.map((ind) => (
          <IndicatorBlock key={ind.id} ind={ind} crit={crit} assessmentId={a.id} editable={editable} analysis={analysis}
            questions={questions?.items.find((x) => x.indicator_id === ind.id)?.questions} />
        ))}
        <SuggestedLevel crit={crit} form={form} assessmentId={a.id} editable={editable && a.status !== 'DRAFT'} />
        {loose.length > 0 && (
          <div className="border-t border-rule pt-5">
            <h3 className="font-sans font-bold">Przykłady bez przypisanego wskaźnika</h3>
            <ul className="mt-2 space-y-2">{loose.map((e) => <EvidenceItem key={e.id} e={e} crit={crit} assessmentId={a.id} editable={editable} mapping={analysis?.mappings.find((m) => m.evidence_id === e.id)} />)}</ul>
          </div>
        )}
      </div>
    </div>
  )
}
