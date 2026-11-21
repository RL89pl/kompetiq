import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, upload } from '../../api/client'
import { qk, reportOutcome, useAssistant, useInvalidateAssessment, usePatchAssessment } from '../../api/hooks'
import type { Assessment, JobAnalysis, JobDescription } from '../../api/types'
import { AIList, AISuggestion } from '../../components/AISuggestion'
import { Badge, Button, ErrorList, Field, Notice, Section, Textarea } from '../../components/ui'
import type { StepProps } from './context'

export function useJobDescription(employee: number) {
  return useQuery({ queryKey: ['jd', employee], queryFn: () => api<JobDescription[]>(`/job-descriptions/?employee=${employee}`) })
}

function OspImport({ a, onDone }: { a: Assessment; onDone: () => void }) {
  const qc = useQueryClient()
  const imp = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('employee', String(a.employee))
      fd.append('file', file)
      return upload('/job-descriptions/import-osp/', fd)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jd', a.employee] })
      qc.invalidateQueries({ queryKey: qk.employees })
      qc.invalidateQueries({ queryKey: qk.assessment(a.id) })
      onDone()
    },
  })
  return (
    <div className="space-y-2">
      <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-rule-strong bg-white px-3.5 py-2 text-[15px] font-bold hover:border-ink">
        {imp.isPending ? 'Wczytywanie…' : 'Wczytaj opis stanowiska z pliku (.docx)'}
        <input type="file" accept=".docx" className="sr-only" disabled={imp.isPending}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) imp.mutate(f); e.target.value = '' }} />
      </label>
      <p className="text-[13px] text-ink-soft">Standardowy opis stanowiska pracy (OSP) w służbie cywilnej. Plik jest analizowany na serwerze, bez udziału AI.</p>
      <ErrorList error={imp.error} />
    </div>
  )
}

function JobDescriptionBox({ a, editable, model }: { a: Assessment; editable: boolean; model: StepProps['model'] }) {
  const qc = useQueryClient()
  const jd = useJobDescription(a.employee)
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState('')
  const save = useMutation({
    mutationFn: (main_duties: string) => api('/job-descriptions/', { method: 'POST', body: { employee: a.employee, main_duties } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['jd', a.employee] }); qc.invalidateQueries({ queryKey: qk.employees }); setEditing(false) },
  })
  const current = jd.data?.[0]
  if (editing || (!current && editable && !jd.isLoading)) {
    return (
      <div className="space-y-4">
        {!current && <Notice tone="warn" title="Brak opisu stanowiska">Wczytaj opis stanowiska pracy z pliku albo wklej główne zadania. To podstawa doboru arkusza, kryteriów i wskaźników.</Notice>}
        {editable && <OspImport a={a} onDone={() => setEditing(false)} />}
        <Field label="…albo wpisz główne zadania na stanowisku">{(id) => <Textarea id={id} rows={6} value={text} onChange={(e) => setText(e.target.value)} />}</Field>
        <ErrorList error={save.error} />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => save.mutate(text)} busy={save.isPending} disabled={!text.trim()} disabledReason="Wpisz lub wczytaj z pliku opis stanowiska.">Zapisz opis</Button>
          {current && <Button variant="ghost" onClick={() => setEditing(false)}>Anuluj</Button>}
        </div>
      </div>
    )
  }
  if (!current) return <p className="text-ink-soft">Brak opisu stanowiska.</p>
  const soft = current.soft_competencies.map((c) => model.competencies.find((m) => m.code === c)?.name).filter(Boolean)
  return (
    <div className="space-y-3">
      <dl className="grid max-w-[75ch] gap-x-4 gap-y-1 text-[15px] md:grid-cols-[12rem_1fr]">
        {current.symbol && <><dt className="text-ink-soft">Symbol stanowiska</dt><dd>{current.symbol}{current.source_name && <span className="text-ink-soft"> (z pliku {current.source_name})</span>}</dd></>}
        {current.subordinates && <><dt className="text-ink-soft">Podlegli pracownicy</dt><dd>{current.subordinates}</dd></>}
        {current.purpose && <><dt className="text-ink-soft">Cel stanowiska</dt><dd>{current.purpose}</dd></>}
        {soft.length > 0 && <><dt className="text-ink-soft">Kompetencje w OSP</dt><dd>{soft.join(', ')}</dd></>}
      </dl>
      <details>
        <summary className="cursor-pointer font-bold">Główne zadania</summary>
        <div className="mt-2 max-w-[75ch] whitespace-pre-line rounded-md border border-rule bg-white p-4 leading-relaxed">{current.main_duties}</div>
      </details>
      {editable && <Button variant="ghost" onClick={() => { setText(current.main_duties); setEditing(true) }}>Zmień opis stanowiska</Button>}
    </div>
  )
}

export function JobStep({ a, form, model, editable }: StepProps) {
  const ai = useAssistant<JobAnalysis>(a.id, 'analyze-job-description')
  const invalidate = useInvalidateAssessment(a.id)
  const patch = usePatchAssessment(a.id)
  const draft = a.status === 'DRAFT' && editable
  const mandatory = new Set(form.mandatory)
  const additional = a.criteria.filter((c) => !c.is_mandatory).map((c) => c.competency_code)
  const setAdditional = useMutation({
    mutationFn: (codes: string[]) => api(`/assessments/${a.id}/additional-criteria/`, {
      method: 'PUT', body: { competency_ids: model.competencies.filter((c) => codes.includes(c.code)).map((c) => c.id) },
    }),
    onSuccess: invalidate,
  })
  const setIndicators = useMutation({
    mutationFn: ({ crit, ids }: { crit: number; ids: number[] }) => api(`/criteria/${crit}/`, { method: 'PATCH', body: { selected_indicators: ids } }),
    onSuccess: invalidate,
  })
  const jd = useJobDescription(a.employee).data?.[0]
  const ospCodes = (jd?.soft_competencies ?? []).filter((c) => !mandatory.has(c)).slice(0, form.max_additional)
  const ospSuggestsB = !form.is_first && jd?.manages_people && a.form_type === 'PERIODIC_C'
  const ospSuggestsC = !form.is_first && jd?.manages_people === false && a.form_type === 'PERIODIC_B'
  const priority = new Map((ai.data?.result.priority_indicators ?? []).map((p) => [p.indicator_id, p.rationale]))
  const res = ai.data?.result

  function toggleAdditional(code: string) {
    const next = additional.includes(code) ? additional.filter((c) => c !== code) : [...additional, code]
    if (next.length <= form.max_additional) setAdditional.mutate(next)
  }

  return (
    <div className="space-y-10">
      <Section title="Opis stanowiska pracy"
        description={form.is_first
          ? 'Na rozmowie wstępnej omawiasz główne obowiązki i oczekiwania co do sposobu ich wykonywania (§ 3 rozporządzenia z 2015 r.).'
          : 'Kryteria dodatkowe wybierasz, jeżeli uzasadnia to charakter obowiązków z opisu stanowiska (§ 2 ust. 2 i § 5 ust. 2 rozporządzenia z 2016 r.).'}
        actions={editable && <Button variant="ai" busy={ai.isPending} onClick={() => ai.mutate({})}>Przeanalizuj opis z asystentem</Button>}>
        <JobDescriptionBox a={a} editable={editable} model={model} />
        <div className="mt-4"><ErrorList error={ai.error} /></div>
        {res && (
          <div className="mt-4 space-y-4">
            <AISuggestion title="Analiza opisu stanowiska" interactionId={ai.data!.interaction_id}>
              {!form.is_first && res.suggested_form !== a.form_type && (
                <Notice tone="warn" title={`Asystent wskazuje arkusz ${res.suggested_form.slice(-1)}`}>{res.form_rationale} Arkusza nie można zmienić w trakcie. Jeśli to trafna uwaga, anuluj tę ocenę i rozpocznij nową.</Notice>
              )}
              {!form.is_first && res.suggested_form === a.form_type && <p className="text-[15px]"><span className="font-bold">Arkusz: </span>{res.form_rationale}</p>}
              <AIList title="Kluczowe obowiązki" items={res.key_duties} />
              {res.additional_criteria.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-bold">Proponowane kryteria dodatkowe</p>
                  <ul className="mt-1 space-y-1 text-[15px]">
                    {res.additional_criteria.map((c) => (
                      <li key={c.competency_code}><span className="font-bold">{model.competencies.find((m) => m.code === c.competency_code)?.name}:</span> {c.rationale}</li>
                    ))}
                  </ul>
                  {draft && <Button variant="ai" className="mt-2" busy={setAdditional.isPending} onClick={() => { setAdditional.mutate(res.additional_criteria.map((c) => c.competency_code)); reportOutcome(ai.data!.interaction_id, 'ACCEPTED') }}>Ustaw te kryteria dodatkowe</Button>}
                </div>
              )}
              <AIList title="Czego nie da się ustalić z opisu" items={res.caveats} />
            </AISuggestion>
            {editable && res.expectations_draft && (
              <AISuggestion title="Projekt oczekiwań do omówienia" interactionId={ai.data!.interaction_id} editableText={res.expectations_draft}
                onAccept={(t) => patch.mutate({ expectations: t })} acceptLabel="Wstaw do oczekiwań" />
            )}
            {editable && res.goals_suggestions.length > 0 && (
              <AISuggestion title="Propozycje celów" interactionId={ai.data!.interaction_id} editableText={res.goals_suggestions.map((g) => `• ${g}`).join('\n')}
                onAccept={(t) => patch.mutate({ goals: t })} acceptLabel="Wstaw do celów" />
            )}
          </div>
        )}
      </Section>

      {!form.is_first && (
        <Section title="Kryteria oceny" description={`Obowiązkowe dla arkusza ${form.short_name.slice(-1)} oraz do ${form.max_additional} dodatkowych, najistotniejszych dla stanowiska.`}>
          {(ospSuggestsB || ospSuggestsC) && (
            <div className="mb-4"><Notice tone="warn" title={`Opis stanowiska wskazuje arkusz ${ospSuggestsB ? 'B' : 'C'}`}>
              {jd?.subordinates}. Arkusz B dotyczy stanowisk polegających na bezpośrednim kierowaniu pracownikami (§ 3 rozporządzenia z 2016 r.). Jeśli opis jest aktualny, anuluj tę ocenę i rozpocznij ją na właściwym arkuszu.
            </Notice></div>
          )}
          {ospCodes.length > 0 && draft && ospCodes.some((c) => !additional.includes(c)) && (
            <div className="mb-4 rounded-md border border-rule-strong bg-white p-4">
              <p className="font-bold">Opis stanowiska wskazuje kompetencje spoza obowiązkowych</p>
              <p className="mt-1 text-[15px]">{ospCodes.map((c) => model.competencies.find((m) => m.code === c)?.name).join(', ')}</p>
              <Button variant="secondary" className="mt-2" busy={setAdditional.isPending} onClick={() => setAdditional.mutate(ospCodes)}>Ustaw jako kryteria dodatkowe</Button>
            </div>
          )}
          <ErrorList error={setAdditional.error} />
          <fieldset disabled={!draft || setAdditional.isPending}>
            <legend className="sr-only">Kryteria dodatkowe</legend>
            <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
              {model.competencies.map((c) => {
                const isMand = mandatory.has(c.code)
                const checked = isMand || additional.includes(c.code)
                const suggested = res?.additional_criteria.some((s) => s.competency_code === c.code)
                return (
                  <li key={c.id}>
                    <label className={`flex items-center gap-3 rounded-md px-2 py-1.5 ${isMand ? '' : 'hover:bg-white'}`}
                      title={isMand ? 'Kryterium obowiązkowe dla tego arkusza — nie można go odznaczyć.' : !checked && additional.length >= form.max_additional ? `Wybrano już maksymalną liczbę kryteriów dodatkowych (${form.max_additional}). Odznacz inne, aby wybrać to.` : undefined}>
                      <input type="checkbox" className="size-4 accent-[var(--color-periodic)]" checked={checked} disabled={isMand || (!checked && additional.length >= form.max_additional)}
                        onChange={() => toggleAdditional(c.code)} />
                      <span>{c.name}</span>
                      {isMand && <Badge>obowiązkowe</Badge>}
                      {suggested && !isMand && <Badge tone="ai">sugestia AI</Badge>}
                      {!isMand && jd?.soft_competencies.includes(c.code) && <Badge>w opisie stanowiska</Badge>}
                    </label>
                  </li>
                )
              })}
            </ul>
          </fieldset>
          {!draft && <p className="mt-2 text-sm text-ink-soft">Kryteria zostały ustalone i potwierdzone na rozmowie.</p>}
        </Section>
      )}

      <Section title="Wskaźniki behawioralne" description="Dobierz wskaźniki do zadań i zakresu odpowiedzialności na stanowisku. Na nich oprzesz przykłady zachowań.">
        <ErrorList error={setIndicators.error} />
        <div className="space-y-6">
          {a.criteria.map((crit) => {
            const comp = model.competencies.find((c) => c.id === crit.competency)!
            return (
              <fieldset key={crit.id} disabled={!draft || setIndicators.isPending}>
                <legend className="font-serif text-lg font-semibold">{crit.competency_name}</legend>
                <ul className="mt-2 space-y-1.5">
                  {comp.indicators.map((ind) => {
                    const on = crit.selected_indicators.includes(ind.id)
                    return (
                      <li key={ind.id}>
                        <label className="flex gap-3">
                          <input type="checkbox" className="mt-1 size-4 shrink-0" checked={on}
                            onChange={() => setIndicators.mutate({ crit: crit.id, ids: on ? crit.selected_indicators.filter((x) => x !== ind.id) : [...crit.selected_indicators, ind.id] })} />
                          <span className="text-[15px]">
                            {ind.text}
                            {priority.has(ind.id) && <span className="mt-0.5 block text-[14px] text-ai">AI: {priority.get(ind.id)}</span>}
                          </span>
                        </label>
                      </li>
                    )
                  })}
                </ul>
              </fieldset>
            )
          })}
        </div>
      </Section>
    </div>
  )
}
