import { useEffect, useState } from 'react'
import { usePatchAssessment } from '../../api/hooks'
import type { Assessment, CompetencyModel, FormConfig } from '../../api/types'

export interface StepProps {
  a: Assessment
  form: FormConfig
  model: CompetencyModel
  editable: boolean
}

type Fields = Partial<Assessment>

/** Lokalna kopia wybranych pól oceny z jawnym zapisem. */
export function useDraft<K extends keyof Assessment>(a: Assessment, keys: K[]) {
  const pick = () => Object.fromEntries(keys.map((k) => [k, a[k] ?? ''])) as Pick<Assessment, K>
  const [draft, setDraft] = useState(pick)
  const patch = usePatchAssessment(a.id)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setDraft(pick()), [a.updated_at])
  const dirty = keys.some((k) => (draft[k] ?? '') !== (a[k] ?? ''))
  const set = <T extends K>(k: T, v: Assessment[T]) => setDraft((d) => ({ ...d, [k]: v }))
  const bind = (k: K) => ({
    value: (draft[k] ?? '') as string,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => set(k, e.target.value as Assessment[K]),
  })
  const save = (extra: Fields = {}) => {
    const body: Fields = {}
    for (const k of keys) {
      const v = draft[k] as unknown
      ;(body as Record<string, unknown>)[k as string] = v === '' && (k as string).match(/date|_from|_to|_on|^promotion_request$|report_on_time/) ? null : v
    }
    return patch.mutateAsync({ ...body, ...extra })
  }
  return { draft, set, bind, save, dirty, patch }
}

type Crit = Assessment['criteria'][number]

/** Wybrane wskaźniki kryterium bez oceny poziomu i bez „brak podstaw”. */
export function unratedIndicators(c: Crit) {
  const rated = new Set(c.ratings.filter((r) => r.level !== null || r.no_basis).map((r) => r.indicator))
  return c.selected_indicators.filter((id) => !rated.has(id))
}

export function criterionDone(c: Crit) {
  return unratedIndicators(c).length === 0
}
