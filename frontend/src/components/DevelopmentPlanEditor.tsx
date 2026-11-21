import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { qk, useCompetencyModel } from '../api/hooks'
import type { DevAction, DevPlan } from '../api/types'
import { fmtDate } from '../lib'
import { Badge, Button, ErrorList, Field, Input, Select, Textarea } from './ui'

export const ACTION_TYPES: Record<string, string> = {
  ON_THE_JOB: 'Zadanie rozwojowe w pracy', MENTORING: 'Mentoring', COACHING: 'Coaching', TRAINING: 'Szkolenie',
  SELF_STUDY: 'Samokształcenie', FEEDBACK: 'Regularna informacja zwrotna',
}
const STATUSES: Record<string, string> = { PLANNED: 'Zaplanowane', IN_PROGRESS: 'W realizacji', DONE: 'Zrealizowane', CANCELLED: 'Anulowane' }

export function useActionMutations(plan: DevPlan) {
  const qc = useQueryClient()
  const refresh = () => {
    qc.invalidateQueries({ queryKey: qk.plan(plan.assessment) })
    qc.invalidateQueries({ queryKey: qk.plans })
    qc.invalidateQueries({ queryKey: ['plan-detail', plan.id] })
    qc.invalidateQueries({ queryKey: qk.deadlines })
  }
  return {
    create: useMutation({ mutationFn: (b: Partial<DevAction>) => api('/development-actions/', { method: 'POST', body: { plan: plan.id, ...b } }), onSuccess: refresh }),
    update: useMutation({ mutationFn: ({ id, ...b }: Partial<DevAction> & { id: number }) => api(`/development-actions/${id}/`, { method: 'PATCH', body: b }), onSuccess: refresh }),
    remove: useMutation({ mutationFn: (id: number) => api(`/development-actions/${id}/`, { method: 'DELETE' }), onSuccess: refresh }),
    note: useMutation({ mutationFn: ({ id, text }: { id: number; text: string }) => api(`/development-actions/${id}/notes/`, { method: 'POST', body: { text } }), onSuccess: refresh }),
  }
}

function ActionRow({ a, plan, editable }: { a: DevAction; plan: DevPlan; editable: boolean }) {
  const m = useActionMutations(plan)
  const [note, setNote] = useState('')
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-[65ch]">
          <p className="font-bold">{a.title} {a.from_ai_suggestion && <Badge tone="ai">z sugestii AI</Badge>}</p>
          <p className="text-sm text-ink-soft">{a.type_label}{a.competency_name && `, ${a.competency_name}`}, termin {fmtDate(a.due_date)}</p>
          {a.description && <p className="mt-1 text-[15px]">{a.description}</p>}
          {a.success_measure && <p className="mt-1 text-[15px]"><span className="font-bold">Miernik: </span>{a.success_measure}</p>}
        </div>
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor={`st-${a.id}`}>Status działania</label>
          <Select id={`st-${a.id}`} className="w-auto" value={a.status} disabled={!editable}
            onChange={(e) => m.update.mutate({ id: a.id, status: e.target.value })}>
            {Object.entries(STATUSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          {editable && <Button variant="ghost" onClick={() => m.remove.mutate(a.id)} aria-label={`Usuń działanie ${a.title}`}>Usuń</Button>}
        </div>
      </div>
      {(a.notes.length > 0 || editable) && (
        <div className="mt-3 border-l-2 border-rule pl-4">
          {a.notes.map((n) => <p key={n.id} className="text-sm"><span className="text-ink-soft">{fmtDate(n.created_at)}:</span> {n.text}</p>)}
          {editable && (
            <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (note.trim()) m.note.mutate({ id: a.id, text: note }, { onSuccess: () => setNote('') }) }}>
              <label className="sr-only" htmlFor={`n-${a.id}`}>Notatka o postępie</label>
              <Input id={`n-${a.id}`} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Dodaj notatkę o postępie" />
              <Button variant="secondary" type="submit" busy={m.note.isPending}>Dodaj</Button>
            </form>
          )}
        </div>
      )}
    </li>
  )
}

export function NewActionForm({ plan, onDone }: { plan: DevPlan; onDone?: () => void }) {
  const model = useCompetencyModel()
  const m = useActionMutations(plan)
  const [f, setF] = useState({ title: '', description: '', type: 'ON_THE_JOB', competency: '', success_measure: '', due_date: '', owner: '' })
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value })
  return (
    <form className="grid gap-4 rounded-md border border-rule bg-white p-4 md:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault()
        m.create.mutate({ ...f, competency: f.competency ? Number(f.competency) : null, due_date: f.due_date || null },
          { onSuccess: () => { setF({ ...f, title: '', description: '', success_measure: '' }); onDone?.() } })
      }}>
      <Field label="Działanie">{(id) => <Input id={id} required value={f.title} onChange={set('title')} />}</Field>
      <Field label="Forma">{(id) => <Select id={id} value={f.type} onChange={set('type')}>{Object.entries(ACTION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>}</Field>
      <Field label="Kompetencja">{(id) => (
        <Select id={id} value={f.competency} onChange={set('competency')}>
          <option value="">(bez przypisania)</option>
          {model.data?.competencies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>)}</Field>
      <Field label="Termin">{(id) => <Input id={id} type="date" value={f.due_date} onChange={set('due_date')} />}</Field>
      <div className="md:col-span-2"><Field label="Opis">{(id) => <Textarea id={id} rows={2} value={f.description} onChange={set('description')} />}</Field></div>
      <Field label="Miernik sukcesu">{(id) => <Input id={id} value={f.success_measure} onChange={set('success_measure')} />}</Field>
      <Field label="Odpowiedzialny">{(id) => <Input id={id} value={f.owner} onChange={set('owner')} />}</Field>
      <div className="md:col-span-2"><ErrorList error={m.create.error} /><Button type="submit" busy={m.create.isPending}>Dodaj działanie</Button></div>
    </form>
  )
}

export function DevelopmentPlanEditor({ plan, editable }: { plan: DevPlan; editable: boolean }) {
  const [adding, setAdding] = useState(false)
  return (
    <div>
      <div className="flex items-center gap-4">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-rule" role="progressbar" aria-valuenow={plan.progress.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Postęp realizacji planu">
          <div className="h-full bg-ok" style={{ width: `${plan.progress.percent}%` }} />
        </div>
        <span className="text-sm text-ink-soft">{plan.progress.done} z {plan.progress.total} zrealizowanych</span>
      </div>
      {plan.actions.length ? (
        <ul className="mt-2 divide-y divide-rule">{plan.actions.map((a) => <ActionRow key={a.id} a={a} plan={plan} editable={editable} />)}</ul>
      ) : <p className="mt-3 text-ink-soft">Plan nie zawiera jeszcze działań.</p>}
      {editable && (adding ? <div className="mt-4"><NewActionForm plan={plan} onDone={() => setAdding(false)} /></div>
        : <Button variant="secondary" className="mt-4" onClick={() => setAdding(true)}>Dodaj działanie ręcznie</Button>)}
    </div>
  )
}
