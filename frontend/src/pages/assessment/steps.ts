import type { Assessment } from '../../api/types'
import { criterionDone } from './context'

export interface StepDef {
  path: string
  title: string
  hint: string
  done: (a: Assessment) => boolean
}

const after = (a: Assessment, ...s: Assessment['status'][]) => s.includes(a.status)
const LATE = ['INTERVIEW_DONE', 'FINALIZED', 'APPROVED', 'ACKNOWLEDGED'] as const

export function stepsFor(a: Assessment): StepDef[] {
  const first = a.form_type === 'FIRST'
  const all: StepDef[] = [
    {
      path: 'stanowisko', title: first ? 'Opis stanowiska' : 'Analiza opisu stanowiska',
      hint: first ? 'Obowiązki i wskaźniki istotne na stanowisku' : 'Arkusz, kryteria dodatkowe, wskaźniki',
      done: (x) => x.status !== 'DRAFT',
    },
    {
      path: 'kryteria', title: first ? 'Rozmowa wstępna' : 'Ustalenie kryteriów',
      hint: first ? '§ 3 i § 4 rozporządzenia z 2015 r.' : '§ 5–7 rozporządzenia z 2016 r.',
      done: (x) => x.status !== 'DRAFT',
    },
    {
      path: 'zachowania', title: 'Ocena zachowań', hint: 'Wskaźniki, przykłady, sugerowany poziom',
      done: (x) => x.criteria.every(criterionDone),
    },
    {
      path: 'oceny', title: first ? 'Sprawozdanie i oceny cząstkowe' : 'Oceny cząstkowe',
      hint: 'Twoja decyzja, z uzasadnieniem', done: (x) => x.criteria.every((c) => c.score !== null),
    },
    {
      path: 'rozmowa', title: 'Rozmowa oceniająca', hint: 'Scenariusz i informacja zwrotna',
      done: (x) => after(x, ...LATE),
    },
    {
      path: 'rozwoj', title: first ? 'Wnioski rozwojowe' : 'Program rozwoju (IPRZ)', hint: 'Działania i mierniki',
      done: (x) => !!x.development_conclusions.trim(),
    },
    {
      path: 'sporzadzenie', title: first ? 'Dokonanie oceny' : 'Sporządzenie oceny', hint: 'Lista kontrolna, arkusz, podpisy',
      done: (x) => after(x, 'FINALIZED', 'APPROVED', 'ACKNOWLEDGED'),
    },
  ]
  return all
}
