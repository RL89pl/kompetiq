import type { Indicator } from '../api/types'
import { LEVEL_SHORT } from '../lib'

/** Pięć opisów poziomu jako skala; opcjonalnie wybór poziomu (ocena pomocnicza wskaźnika). */
export function LevelScale({ indicator, value, onChange, disabled, highlight }: {
  indicator: Indicator
  value?: number | null
  onChange?: (level: number | null) => void
  disabled?: boolean
  highlight?: number | null
}) {
  const interactive = !!onChange
  return (
    <div role={interactive ? 'radiogroup' : undefined} aria-label={interactive ? `Poziom: ${indicator.text}` : undefined}
      className="mt-2 grid gap-px overflow-hidden rounded-md border border-rule bg-rule md:grid-cols-5">
      {indicator.levels.map((lv) => {
        const selected = value === lv.level
        const base = lv.level === 3 ? 'bg-[#fbfcfe]' : 'bg-white'
        const content = (
          <>
            <span className={`block text-[13px] font-bold ${selected ? 'text-white' : lv.level === 3 ? 'text-ink' : 'text-ink-soft'}`}>
              {LEVEL_SHORT[lv.level]}{lv.level === 3 && ' (standard)'}
            </span>
            <span className={`mt-1 block text-[14px] leading-snug ${selected ? 'text-white' : ''}`}>{lv.text}</span>
            {highlight === lv.level && !selected && <span className="mt-1 block text-[12px] font-bold text-ai">najbliższy wg AI</span>}
          </>
        )
        return interactive ? (
          <button key={lv.level} type="button" role="radio" aria-checked={selected} disabled={disabled}
            onClick={() => onChange!(selected ? null : lv.level)}
            className={`flex flex-col justify-start p-3 text-left transition-colors ${selected ? 'bg-ink' : `${base} hover:bg-first-tint`} ${highlight === lv.level && !selected ? 'outline-2 -outline-offset-2 outline-dashed outline-ai' : ''} disabled:cursor-not-allowed`}>
            {content}
          </button>
        ) : <div key={lv.level} className={`p-3 ${base}`}>{content}</div>
      })}
    </div>
  )
}
