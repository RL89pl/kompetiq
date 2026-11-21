export function fmtDate(d: string | null | undefined) {
  if (!d) return '—'
  const [y, m, day] = d.slice(0, 10).split('-')
  return `${day}.${m}.${y}`
}

export function daysLabel(n: number) {
  if (n < 0) return `${-n} dni po terminie`
  if (n === 0) return 'dziś'
  if (n === 1) return 'jutro'
  return `za ${n} dni`
}

export const isFirst = (ft: string) => ft === 'FIRST'

export const LEVEL_SHORT: Record<number, string> = {
  1: 'Znacznie poniżej',
  2: 'Poniżej',
  3: 'Na poziomie',
  4: 'Powyżej',
  5: 'Znacznie powyżej',
}
