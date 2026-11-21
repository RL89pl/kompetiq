import { useTransition } from '../../api/hooks'
import { Download } from '../../components/Download'
import { Button, ErrorList, Field, Input, Notice, Section, Select, Textarea } from '../../components/ui'
import { fmtDate } from '../../lib'
import { useDraft, type StepProps } from './context'

function addMonths(iso: string, n: number) {
  const d = new Date(iso + 'T12:00:00')
  d.setMonth(d.getMonth() + n)
  return d.toISOString().slice(0, 10)
}

export function CriteriaStep({ a, form, editable }: StepProps) {
  const first = form.is_first
  const keys = first
    ? (['criteria_interview_date', 'report_deadline_from', 'report_deadline_to', 'window_from', 'window_to', 'expectations'] as const)
    : (['criteria_interview_date', 'due_date', 'expectations', 'goals', 'previous_result', 'previous_level', 'previous_date'] as const)
  const d = useDraft(a, [...keys])
  const tr = useTransition(a.id)
  const draft = a.status === 'DRAFT'
  const can = editable && draft

  const agenda = first
    ? ['Zapoznaj ocenianego ze sposobem dokonywania pierwszej oceny.',
       'Omów główne obowiązki z opisu stanowiska i oczekiwania co do sposobu ich wykonywania.',
       'Omów oczekiwania co do postawy, zaangażowania i postępów w pracy, relacji ze współpracownikami i terminowości (5 elementów oceny).',
       'Wyznacz termin na złożenie sprawozdania (po upływie 8 miesięcy od zatrudnienia).']
    : ['Omów główne obowiązki wynikające z opisu stanowiska.',
       'Przedstaw kryteria obowiązkowe i wybrane kryteria dodatkowe.',
       'Przedstaw swoje oczekiwania co do sposobu spełniania kryteriów.',
       'Ustal cele na okres oceny, jeżeli uzasadnia to charakter obowiązków, i sposób ich realizacji.']

  async function confirm() {
    if (d.dirty) await d.save()
    tr.mutate({ action: 'set_criteria' })
  }

  return (
    <div className="space-y-10">
      <Section title={first ? 'Rozmowa wstępna' : 'Rozmowa o kryteriach i oczekiwaniach'}
        description={first ? 'Przeprowadź ją w terminie 21 dni od dnia nawiązania stosunku pracy (§ 3 rozporządzenia z 2015 r.).'
          : 'Przeprowadź ją w terminie 30 dni od poprzedniej oceny lub zatrudnienia na czas nieokreślony, a po ocenie negatywnej w 7 dni (§ 7 rozporządzenia z 2016 r.).'}>
        <ol className="mb-6 max-w-[75ch] list-decimal space-y-1.5 pl-5">{agenda.map((x) => <li key={x}>{x}</li>)}</ol>
        <fieldset disabled={!can} className="grid max-w-3xl gap-5 md:grid-cols-2">
          <Field label={first ? 'Data rozmowy wstępnej' : 'Data rozmowy'}>{(id) => <Input id={id} type="date" {...d.bind('criteria_interview_date')} />}</Field>
          {first ? (
            <>
              <div className="hidden md:block" />
              <Field label="Termin sprawozdania: od">{(id) => <Input id={id} type="date" {...d.bind('report_deadline_from')} />}</Field>
              <Field label="Termin sprawozdania: do">{(id) => <Input id={id} type="date" {...d.bind('report_deadline_to')} />}</Field>
              <Field label="Okres na pierwszą ocenę: od">{(id) => <Input id={id} type="date" {...d.bind('window_from')} />}</Field>
              <Field label="Okres na pierwszą ocenę: do" hint="Nie później niż miesiąc przed zakończeniem umowy (art. 38 ust. 1 ustawy).">{(id) => <Input id={id} type="date" {...d.bind('window_to')} />}</Field>
            </>
          ) : (
            <Field label="Termin sporządzenia oceny na piśmie"
              hint={d.draft.previous_date ? <>24 miesiące od poprzedniej oceny: <button type="button" className="underline" onClick={() => d.set('due_date', addMonths(d.draft.previous_date as string, 24))}>{fmtDate(addMonths(d.draft.previous_date as string, 24))}</button></> : 'Co 24 miesiące od poprzedniej oceny (art. 81 ust. 4 ustawy).'}>
              {(id) => <Input id={id} type="date" {...d.bind('due_date')} />}
            </Field>
          )}
          <div className="md:col-span-2">
            <Field label="Oczekiwania przełożonego" hint="Zapisz je językiem zachowań, odnosząc się do wskaźników.">{(id) => <Textarea id={id} rows={5} {...d.bind('expectations')} />}</Field>
          </div>
          {!first && (
            <div className="md:col-span-2">
              <Field label="Cele na okres oceny (opcjonalnie)">{(id) => <Textarea id={id} rows={4} {...d.bind('goals')} />}</Field>
            </div>
          )}
        </fieldset>
      </Section>

      {!first && (
        <Section title="Poprzednia ocena okresowa" description="Dane do części II arkusza (dotyczy urzędników służby cywilnej).">
          <fieldset disabled={!editable} className="grid max-w-3xl gap-5 md:grid-cols-3">
            <Field label="Ocena">{(id) => <Select id={id} {...d.bind('previous_result')}><option value="">brak</option><option value="POSITIVE">pozytywna</option><option value="NEGATIVE">negatywna</option></Select>}</Field>
            <Field label="Poziom">{(id) => <Input id={id} {...d.bind('previous_level')} />}</Field>
            <Field label="Data sporządzenia">{(id) => <Input id={id} type="date" {...d.bind('previous_date')} />}</Field>
          </fieldset>
        </Section>
      )}

      <div className="space-y-3">
        <ErrorList error={d.patch.error} />
        <ErrorList error={tr.error} />
        {editable && (
          <div className="flex flex-wrap gap-2">
            {(can || !first) && <Button variant="secondary" onClick={() => d.save()} busy={d.patch.isPending} disabled={!d.dirty}>Zapisz</Button>}
            {can && <Button onClick={confirm} busy={tr.isPending}>Potwierdź: kryteria ustalone, rozmowa przeprowadzona</Button>}
            {a.available_actions.includes('reopen_criteria') && <Button variant="ghost" onClick={() => tr.mutate({ action: 'reopen_criteria' })}>Wróć do edycji kryteriów</Button>}
          </div>
        )}
        {!draft && (
          <Notice tone="ok" title="Kryteria ustalone">
            Wydrukuj część I arkusza, aby oceniany potwierdził podpisem rozmowę i zapoznanie się z kryteriami i terminem.
            Oryginał trafia do akt osobowych, kopia do ocenianego (§ 6 rozporządzenia z 2016 r.; § 4 rozporządzenia z 2015 r.).{' '}
            <Download path={`/assessments/${a.id}/export/sheet/`} label="Pobierz arkusz" />
          </Notice>
        )}
      </div>
    </div>
  )
}
