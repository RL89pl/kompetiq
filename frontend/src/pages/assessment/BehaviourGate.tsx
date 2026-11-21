import { useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useInvalidateAssessment } from '../../api/hooks'
import type { Assessment, CompetencyModel } from '../../api/types'
import { Button, ErrorList, Notice } from '../../components/ui'
import { plural } from '../../lib'
import { unratedIndicators } from './context'

export const NO_BASIS_LABEL = 'Brak okazji do zaobserwowania zachowania (brak podstaw do oceny wskaźnika)'

export interface Filled { criterion: string; indicator: string }

/** Kryteria z nieocenionymi wskaźnikami (nazwa kryterium + treść wskaźników). */
export function pendingRatings(a: Assessment, model: CompetencyModel) {
  const texts = new Map(model.competencies.flatMap((c) => c.indicators.map((i) => [i.id, i.text] as const)))
  return a.criteria
    .map((c) => ({ criterion: c.competency_name, indicators: unratedIndicators(c).map((id) => texts.get(id) ?? `#${id}`) }))
    .filter((x) => x.indicators.length > 0)
}

/** Okno przy próbie wyjścia z „Oceny zachowań” bez oceny wszystkich wskaźników. */
export function BehaviourGate({ a, model, onBack, onSkipped }: {
  a: Assessment; model: CompetencyModel; onBack: () => void; onSkipped: (filled: Filled[]) => void
}) {
  const pending = pendingRatings(a, model)
  const count = pending.reduce((n, p) => n + p.indicators.length, 0)
  const qc = useQueryClient()
  const invalidate = useInvalidateAssessment(a.id)
  const fill = useMutation({
    mutationFn: () => api<{ filled: Filled[]; assessment: Assessment }>(`/assessments/${a.id}/fill-no-basis/`, { method: 'POST' }),
    onSuccess: (r) => {
      qc.setQueryData(['assessment', a.id], r.assessment)
      invalidate()
      onSkipped(r.filled)
    },
  })
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onBack()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onBack])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" onClick={onBack}>
      <div role="dialog" aria-modal="true" aria-labelledby="gate-title" onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl">
        <div className="px-6 pt-6">
        <h2 id="gate-title" className="text-2xl">Nie wszystkie wskaźniki zostały ocenione</h2>
        <p className="mt-2 text-[15px]">
          W {pending.length === 1 ? 'jednym kryterium' : `${pending.length} kryteriach`} {plural(count, 'pozostał', 'pozostały', 'pozostało')} {count} {plural(count, 'wskaźnik', 'wskaźniki', 'wskaźników')} bez
          wybranego poziomu zachowania. Możesz wrócić i je uzupełnić albo przejść dalej.
        </p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6">
        <ul className="mt-4 space-y-3">
          {pending.map((p) => (
            <li key={p.criterion} className="rounded-md border border-rule p-3">
              <p className="font-bold">{p.criterion} <span className="font-normal text-ink-soft">({p.indicators.length} {plural(p.indicators.length, 'nieoceniony', 'nieocenione', 'nieocenionych')})</span></p>
              <ul className="mt-1 list-disc pl-5 text-[15px] text-ink-soft">{p.indicators.map((t) => <li key={t}>{t}</li>)}</ul>
            </li>
          ))}
        </ul>
        </div>
        <div className="border-t border-rule px-6 pb-6">
        <div className="mt-4">
          <Notice tone="warn" title="Co się stanie po wybraniu „Pomiń i przejdź dalej”">
            Wszystkie wymienione wskaźniki zostaną oznaczone jako <q>{NO_BASIS_LABEL}</q>. Nie wpływają one na sugerowany poziom
            kryterium. Oznaczenie możesz w każdej chwili zmienić, wracając do etapu „Ocena zachowań”.
          </Notice>
        </div>
        <ErrorList error={fill.error} />
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <Button autoFocus variant="primary" onClick={onBack}>Wróć i uzupełnij</Button>
          <Button variant="secondary" busy={fill.isPending} onClick={() => fill.mutate()}>Pomiń i przejdź dalej</Button>
        </div>
        </div>
      </div>
    </div>
  )
}

export function SkippedNotice({ filled, onClose }: { filled: Filled[]; onClose: () => void }) {
  if (!filled.length) return null
  const by = new Map<string, number>()
  filled.forEach((f) => by.set(f.criterion, (by.get(f.criterion) ?? 0) + 1))
  return (
    <div className="mb-6">
      <Notice tone="warn" title={`Oznaczono ${filled.length} ${plural(filled.length, 'wskaźnik', 'wskaźniki', 'wskaźników')} jako „brak okazji do zaobserwowania zachowania”`}>
        <p>{[...by].map(([c, n]) => `${c} (${n})`).join(', ')}.</p>
        <p className="mt-1">Zmienisz to w etapie „Ocena zachowań”.{' '}
          <button className="font-bold underline underline-offset-4" onClick={onClose}>Zamknij</button>
        </p>
      </Notice>
    </div>
  )
}
