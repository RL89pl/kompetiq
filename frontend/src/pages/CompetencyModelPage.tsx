import { useState } from 'react'
import { useCompetencyModel } from '../api/hooks'
import { ErrorList, Loading, PageHeader } from '../components/ui'
import { LevelScale } from '../components/LevelScale'

export function CompetencyModelPage() {
  const { data, isLoading, error } = useCompetencyModel()
  const [sel, setSel] = useState<number | null>(null)
  if (error) return <ErrorList error={error} />
  if (isLoading || !data) return <Loading />
  const comp = data.competencies.find((c) => c.id === sel) ?? data.competencies[0]
  const nInd = data.competencies.reduce((n, c) => n + c.indicators.length, 0)
  return (
    <div>
      <PageHeader title="Model kompetencji" lead={`${data.competencies.length} kompetencji, ${nInd} wskaźników behawioralnych, 5 poziomów opisu. Poziom „na poziomie oczekiwań” opisuje standard wykonania.`} />
      <div className="mb-8 max-w-[75ch] space-y-2 text-[15px] text-ink-soft">{data.guidance.split('\n').map((g, i) => <p key={i}>{g}</p>)}</div>
      <div className="grid gap-8 md:grid-cols-[16rem_1fr]">
        <nav aria-label="Kompetencje">
          <ul className="space-y-0.5">
            {data.competencies.map((c) => (
              <li key={c.id}>
                <button onClick={() => setSel(c.id)} aria-current={comp.id === c.id}
                  className={`w-full rounded-md px-3 py-2 text-left text-[15px] ${comp.id === c.id ? 'bg-ink font-bold text-white' : 'hover:bg-white'}`}>
                  {c.name} <span className={comp.id === c.id ? 'text-white/70' : 'text-ink-soft'}>({c.indicators.length})</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <div className="space-y-8">
          <h2 className="text-2xl">{comp.name}</h2>
          {comp.indicators.map((ind) => (
            <article key={ind.id}>
              <h3 className="font-sans text-[17px] font-bold">{ind.text}</h3>
              <LevelScale indicator={ind} />
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
