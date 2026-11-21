import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import { useInvalidateAssessment } from '../api/hooks'
import type { Criterion, FormConfig } from '../api/types'
import { LEVEL_SHORT } from '../lib'
import { ErrorList } from './ui'

/**
 * Sugerowany poziom spełniania kompetencji wyliczany z ocen wskaźników (mediana wybranych poziomów,
 * przeliczona na skalę arkusza). Rekomendacja pomocnicza — ocenę cząstkową wybiera przełożony.
 */
export function SuggestedLevel({ crit, form, assessmentId, editable }: { crit: Criterion; form: FormConfig; assessmentId: number; editable: boolean }) {
  const invalidate = useInvalidateAssessment(assessmentId)
  const patch = useMutation({
    mutationFn: (score: number) => api(`/criteria/${crit.id}/`, { method: 'PATCH', body: { score } }),
    onSuccess: invalidate,
  })
  const rated = crit.ratings.filter((r) => r.level)
  const noBasis = crit.ratings.filter((r) => r.no_basis).length
  const pending = crit.selected_indicators.length - rated.length - noBasis
  const sug = form.scale.find((p) => p.points === crit.suggested_points)
  const counts = [1, 2, 3, 4, 5].map((l) => rated.filter((r) => r.level === l).length)

  return (
    <section aria-label={`Poziom kompetencji: ${crit.competency_name}`} className="rounded-md border-2 border-ink bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg">Sugerowany poziom kompetencji</h3>
          {sug ? (
            <p className="mt-1"><span className="font-serif text-2xl">{sug.points} pkt</span> <span className="font-bold">{sug.label.toLowerCase()}</span></p>
          ) : <p className="mt-1 text-ink-soft">Oceń co najmniej jeden wskaźnik, wybierając zachowanie najlepiej odpowiadające temu, co obserwowałeś.</p>}
          <p className="mt-1 text-sm text-ink-soft">
            Na podstawie {rated.length} z {crit.selected_indicators.length} wskaźników (mediana wybranych poziomów)
            {noBasis > 0 && `, ${noBasis} bez podstaw do oceny`}{pending > 0 && `, ${pending} jeszcze nieocenionych`}.
          </p>
        </div>
        {rated.length > 0 && (
          <ul className="flex gap-1 text-center text-[12px]" aria-label="Rozkład ocen wskaźników">
            {counts.map((n, i) => (
              <li key={i} className="w-16">
                <span className="mx-auto flex h-10 w-8 items-end rounded bg-rule"><span className="block w-8 rounded bg-periodic" style={{ height: `${(n / Math.max(...counts)) * 100}%` }} /></span>
                <span className="mt-1 block leading-tight">{LEVEL_SHORT[i + 1]} ({n})</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <fieldset className="mt-4" disabled={!editable || patch.isPending}>
        <legend className="text-[15px] font-bold">Twoja decyzja: ocena cząstkowa</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {form.scale.map((p) => (
            <label key={p.points} className={`cursor-pointer rounded-md border-2 px-3 py-2 text-[15px] ${crit.score === p.points ? 'border-ink bg-ink text-white' : p.points === crit.suggested_points ? 'border-dashed border-periodic bg-periodic-tint' : 'border-rule-strong bg-white hover:border-ink'}`}>
              <input type="radio" className="sr-only" name={`ev-score-${crit.id}`} checked={crit.score === p.points} onChange={() => patch.mutate(p.points)} />
              <span className="font-bold">{p.points} pkt</span> {p.label.toLowerCase()}
              {p.points === crit.suggested_points && crit.score !== p.points && <span className="sr-only"> (sugerowany)</span>}
            </label>
          ))}
        </div>
        <p className="mt-2 text-sm text-ink-soft">
          {crit.score === null ? 'Ostateczny poziom wybierasz Ty. Możesz wybrać inny niż sugerowany, jeśli przemawiają za tym powtarzalność zachowań, złożoność sytuacji lub zakres uprawnień.'
            : crit.score === crit.suggested_points ? 'Wybrana ocena jest zgodna z sugestią.'
              : 'Wybrałeś ocenę inną niż sugerowana. Uzasadnij ją w kroku „Oceny cząstkowe”.'}
        </p>
      </fieldset>
      <ErrorList error={patch.error} />
    </section>
  )
}
