import { useEffect, useState } from 'react'
import { onRateLimit, type RateLimitState } from '../api/client'

/** Komunikat w rogu ekranu, gdy dostawca modelu (np. darmowy plan Groq) zwrócił limit zapytań. */
export function RateLimitNotice() {
  const [s, setS] = useState<RateLimitState | null>(null)
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => onRateLimit(setS), [])
  useEffect(() => {
    if (!s) return
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [s])
  if (!s) return null
  const left = Math.max(0, Math.ceil((s.until - now) / 1000))
  return (
    <div role="status" aria-live="polite"
      className="fixed bottom-4 right-4 z-[60] w-[min(26rem,calc(100vw-2rem))] rounded-md border-l-4 border-warn bg-warn-tint px-4 py-3 shadow-lg">
      <p className="font-bold">{s.plan ? `Limit zapytań: ${s.plan}` : 'Limit zapytań dostawcy modelu AI'}</p>
      <p className="mt-1 text-[15px]">
        {s.plan.includes('Groq')
          ? 'Asystent działa na darmowym planie Groq, który ogranicza liczbę zapytań na minutę. '
          : 'Dostawca modelu chwilowo ogranicza liczbę zapytań. '}
        {left > 0 ? <>Ponowię zapytanie automatycznie za <b>{left} s</b>.</> : 'Ponawiam zapytanie…'}
        {s.attempt > 1 && <span className="text-ink-soft"> (próba {s.attempt} z {s.max})</span>}
      </p>
      <p className="mt-1 text-sm text-ink-soft">Nie musisz nic klikać — wynik pojawi się sam.</p>
    </div>
  )
}
