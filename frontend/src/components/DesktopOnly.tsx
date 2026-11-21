import { useEffect, useState, type ReactNode } from 'react'
import { CompassMark } from './Layout'

/**
 * Wymaganie wyzwania: system nie jest dostępny na smartfonach.
 *
 * Decyduje rodzaj urządzenia, nie szerokość okna: blokujemy tylko ekran dotykowy (wskaźnik „coarse”),
 * którego KRÓTSZY bok fizycznego ekranu ma mniej niż 600 px CSS — to smartfon w każdej orientacji.
 * Tablety (np. iPad mini: 744 px) i zwężone okna przeglądarki na komputerze działają normalnie.
 */
const PHONE_MAX_SHORT_SIDE = 600

export function isSmartphone() {
  const coarse = window.matchMedia('(pointer: coarse)').matches
  const shortSide = Math.min(window.screen.width, window.screen.height)
  return coarse && shortSide < PHONE_MAX_SHORT_SIDE
}

export function DesktopOnly({ children }: { children: ReactNode }) {
  const [phone, setPhone] = useState(isSmartphone)
  useEffect(() => {
    const on = () => setPhone(isSmartphone())
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  if (!phone) return <>{children}</>
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <CompassMark className="size-12" />
      <h1 className="text-2xl">Otwórz KompetIQ na komputerze lub tablecie</h1>
      <p className="max-w-sm text-ink-soft">Ocena pracownika wymaga pracy z arkuszem i modelem kompetencji, dlatego aplikacja nie jest dostępna na smartfonach.</p>
    </main>
  )
}
