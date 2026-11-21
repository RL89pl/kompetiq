import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Download } from '../../components/Download'
import { useAssistant, useChecklist, useTransition } from '../../api/hooks'
import type { JustificationDraft } from '../../api/types'
import { AIList, AISuggestion } from '../../components/AISuggestion'
import { Badge, Button, ErrorList, Field, Input, Notice, Section, Select, Textarea } from '../../components/ui'
import { fmtDate } from '../../lib'
import { useDraft, type StepProps } from './context'

const SEVERITY = { ok: 'text-ok', warning: 'text-warn', error: 'text-bad', info: 'text-ink-soft' }
const MARK = { ok: '✓', warning: '!', error: '✕', info: 'i' }

export function FinalizeStep({ a, form, editable }: StepProps) {
  const checklist = useChecklist(a.id)
  const tr = useTransition(a.id)
  const ai = useAssistant<JustificationDraft>(a.id, 'draft-justification')
  const d = useDraft(a, ['justification', 'promotion_request', 'promotion_grade', 'promotion_motivation', 'unit_head'])
  const [ackDate, setAckDate] = useState(new Date().toISOString().slice(0, 10))
  const s = a.summary
  const negative = s.complete && s.result === 'NEGATIVE'
  const locked = ['FINALIZED', 'APPROVED', 'ACKNOWLEDGED'].includes(a.status)
  const acts = a.available_actions
  const errors = checklist.data?.filter((i) => i.severity === 'error').length ?? 0

  return (
    <div className="space-y-10">
      <Section title="Lista kontrolna" description="Wymogi formalne sprawdzane automatycznie na podstawie przepisów i danych w ocenie.">
        <ul className="space-y-2">
          {checklist.data?.map((i) => (
            <li key={i.key} className="flex gap-3">
              <span aria-hidden className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border-2 text-[12px] font-bold ${SEVERITY[i.severity]} border-current`}>{MARK[i.severity]}</span>
              <span>
                <span className={i.severity === 'error' ? 'font-bold' : ''}>{i.label}</span>
                <span className="sr-only"> ({i.severity === 'ok' ? 'spełnione' : i.severity === 'error' ? 'do uzupełnienia' : 'uwaga'})</span>
                {i.hint && <span className="text-ink-soft">: {i.hint}</span>}
                <span className="block text-sm text-ink-soft">{i.basis}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[15px]">Wątpliwość proceduralna? <Link to="/asystent-formalny" className="font-bold underline">Zapytaj asystenta formalnego</Link>.</p>
      </Section>

      <Section title={form.is_first ? 'Pierwsza ocena' : 'Ocena okresowa'}>
        <div className="flex flex-wrap items-end gap-x-10 gap-y-3">
          <p><span className="text-sm text-ink-soft">{form.is_first ? 'Ocena łączna' : 'Średnia arytmetyczna'}</span><br /><span className="font-serif text-3xl">{s.average ?? '—'}</span></p>
          {!form.is_first && <p><span className="text-sm text-ink-soft">Ogólny poziom spełnienia kryteriów</span><br /><span className="font-bold">{s.level_label || '—'}</span></p>}
          <p><span className="text-sm text-ink-soft">Wynik</span><br />{s.complete ? <Badge tone={s.result === 'POSITIVE' ? 'ok' : 'bad'}>{s.result === 'POSITIVE' ? 'POZYTYWNA' : 'NEGATYWNA'}</Badge> : '—'}</p>
        </div>
        {s.reasons.length > 0 && <ul className="mt-3 list-disc pl-5 text-[15px]">{s.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
        <p className="mt-3 max-w-[75ch] text-sm text-ink-soft">Wynik wynika wprost z przepisów i przyznanych przez Ciebie ocen cząstkowych. Asystent AI nie uczestniczy w jego wyliczeniu.</p>
      </Section>

      <Section title="Uzasadnienie przyznanej oceny" description={negative ? 'Przy ocenie negatywnej uzasadnienie jest obowiązkowe.' : 'Przy ocenie pozytywnej uzasadnienie jest opcjonalne.'}
        actions={editable && !locked && <Button variant="ai" busy={ai.isPending} disabled={!s.complete} onClick={() => ai.mutate({})}
          disabledReason={`Projekt uzasadnienia będzie dostępny po uzupełnieniu oceny. ${s.reasons.join(' ') || 'Przyznaj oceny cząstkowe za wszystkie kryteria.'}`}>Projekt uzasadnienia</Button>}>
        <ErrorList error={ai.error} />
        {ai.data && (
          <div className="mb-4">
            <AISuggestion title="Uzasadnienie oceny" interactionId={ai.data.interaction_id} editableText={ai.data.result.draft}
              onAccept={(t) => d.patch.mutate({ justification: t })} acceptLabel="Wstaw do uzasadnienia">
              <AIList title="Spójność" items={ai.data.result.consistency_warnings} />
              <AIList title="Czego brakuje" items={ai.data.result.missing_points} />
            </AISuggestion>
          </div>
        )}
        <fieldset disabled={!editable || locked} className="space-y-5">
          <Field label="Uzasadnienie">{(id) => <Textarea id={id} rows={6} {...d.bind('justification')} />}</Field>
          {!form.is_first && a.employee_detail.is_civil_servant && (
            <div className="grid max-w-3xl gap-5 md:grid-cols-2">
              <Field label="Wniosek o przyznanie kolejnego stopnia służbowego (art. 89 ust. 1)">{(id) => (
                <Select id={id} value={d.draft.promotion_request === null || d.draft.promotion_request === ('' as unknown) ? '' : String(d.draft.promotion_request)}
                  onChange={(e) => d.set('promotion_request', e.target.value === '' ? null : e.target.value === 'true')}>
                  <option value="">nie ustalono</option><option value="false">nie</option><option value="true" disabled={s.result !== 'POSITIVE'}>tak</option>
                </Select>)}</Field>
              {d.draft.promotion_request === true && <>
                <Field label="Wnioskowany stopień">{(id) => <Input id={id} {...d.bind('promotion_grade')} />}</Field>
                <div className="md:col-span-2"><Field label="Umotywowanie wniosku">{(id) => <Textarea id={id} rows={3} {...d.bind('promotion_motivation')} />}</Field></div>
              </>}
            </div>
          )}
          {editable && !locked && <Button variant="secondary" disabled={!d.dirty} disabledReason="Brak zmian do zapisania." busy={d.patch.isPending} onClick={() => d.save()}>Zapisz</Button>}
        </fieldset>
        <ErrorList error={d.patch.error} />
      </Section>

      <Section title="Sporządzenie i potwierdzenia">
        <div className="space-y-4">
          <ErrorList error={tr.error} />
          {acts.includes('finalize') && (
            <div>
              <Button busy={tr.isPending} onClick={async () => { if (d.dirty) await d.save(); tr.mutate({ action: 'finalize' }) }}>
                {form.is_first ? 'Dokonaj pierwszej oceny' : 'Sporządź ocenę na piśmie'}
              </Button>
              {errors > 0 && <p className="mt-2 text-sm text-warn">Lista kontrolna zawiera {errors} pozycje do uzupełnienia.</p>}
            </div>
          )}
          {a.status === 'FINALIZED' && form.is_first && (
            <Notice tone="info" title="Oczekuje na potwierdzenie kierującego komórką organizacyjną">
              Pierwszą ocenę potwierdzają podpisem bezpośredni przełożony i kierujący komórką.
              {acts.includes('approve') && <div className="mt-2"><Button busy={tr.isPending} onClick={() => tr.mutate({ action: 'approve' })}>Potwierdzam dokonanie pierwszej oceny</Button></div>}
            </Notice>
          )}
          {acts.includes('reopen') && <Button variant="ghost" onClick={() => tr.mutate({ action: 'reopen' })}>Otwórz ponownie do edycji</Button>}
          {acts.includes('acknowledge') && (
            <div className="flex flex-wrap items-end gap-3 rounded-md border border-rule bg-white p-4">
              <Field label="Data zapoznania się ocenianego z oceną">{(id) => <Input id={id} type="date" value={ackDate} onChange={(e) => setAckDate(e.target.value)} />}</Field>
              <Button busy={tr.isPending} onClick={() => tr.mutate({ action: 'acknowledge', acknowledged_on: ackDate })}>Potwierdź zapoznanie się z oceną</Button>
            </div>
          )}
          {a.status === 'ACKNOWLEDGED' && (
            <Notice tone="ok" title={`Oceniany zapoznał się z oceną ${fmtDate(a.acknowledged_on)}`}>
              Oryginał arkusza włącz do akt osobowych, kopię przekaż ocenianemu.
              {!form.is_first && ' Od oceny okresowej przysługuje sprzeciw do dyrektora generalnego urzędu w terminie 7 dni (art. 83 ust. 1 ustawy).'}
            </Notice>
          )}
          <p className="flex flex-wrap gap-4">
            <Download path={`/assessments/${a.id}/export/sheet/`} label={`Pobierz ${form.is_first ? 'arkusz pierwszej oceny' : `arkusz ${form.form_type.slice(-1)}`}`} />
            <Download path={`/assessments/${a.id}/export/development-plan/`} label="Plan rozwoju" />
          </p>
        </div>
      </Section>
    </div>
  )
}
