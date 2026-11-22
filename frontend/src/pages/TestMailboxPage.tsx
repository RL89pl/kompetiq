import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useMe } from '../api/hooks'
import type { OutgoingEmail } from '../api/types'
import { Badge, Button, Loading, Notice, PageHeader } from '../components/ui'

const TONE = { CAPTURED: 'ai', SENT: 'ok', REDIRECTED: 'warn', FAILED: 'bad' } as const

function when(iso: string) {
  return new Date(iso).toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/** Skrzynka testowa: podgląd e-maili wysłanych przez system (poczta kont demo nie wychodzi poza aplikację). */
export function TestMailboxPage() {
  const me = useMe()
  const isAdmin = me.data?.active_membership?.role === 'ADMIN'
  const q = useQuery({ queryKey: ['test-mailbox'], queryFn: () => api<OutgoingEmail[]>('/test-mailbox/'), refetchInterval: 10000 })
  const [sel, setSel] = useState<number | null>(null)
  const current = q.data?.find((m) => m.id === sel) ?? q.data?.[0]

  return (
    <div>
      <PageHeader title="Skrzynka testowa"
        lead={isAdmin
          ? 'E-maile wysłane przez system do użytkowników urzędu. Wiadomości do kont demonstracyjnych (adresy w domenie .test) nie wychodzą poza aplikację — trafiają tylko tutaj.'
          : 'E-maile wysłane przez system na Twój adres oraz e-maile, które Twoje działania wysłały innym (np. Twoja wiadomość do kadr). Wiadomości do kont demonstracyjnych (adresy w domenie .test) nie wychodzą poza aplikację — trafiają tylko tutaj.'}>
        <Button variant="secondary" busy={q.isFetching} onClick={() => q.refetch()}>Odśwież</Button>
      </PageHeader>
      {q.isLoading ? <Loading /> : !q.data?.length ? (
        <Notice title="Skrzynka jest pusta">E-mail powstaje razem z powiadomieniem: np. po dokonaniu pierwszej oceny (prośba do kierującego o potwierdzenie), po wysłaniu przypomnienia lub wiadomości w sprawie oceny.</Notice>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
          <ul className="divide-y divide-rule overflow-hidden rounded-lg border border-rule bg-white" aria-label="Wiadomości">
            {q.data.map((m) => (
              <li key={m.id}>
                <button onClick={() => setSel(m.id)} aria-current={current?.id === m.id}
                  className={`block w-full px-4 py-3 text-left ${current?.id === m.id ? 'bg-first-tint' : 'hover:bg-paper'}`}>
                  <span className="flex items-center justify-between gap-2 text-xs text-ink-soft"><span className="truncate">{m.to}</span><span className="shrink-0">{when(m.created_at)}</span></span>
                  <span className="mt-1 block font-bold leading-snug">{m.subject.replace(/^KompetIQ: /, '')}</span>
                  <span className="mt-1 flex flex-wrap gap-1"><Badge tone={TONE[m.status]}>{m.status_label}</Badge>{m.sent_by_me && <Badge tone="periodic">wysłane przez Ciebie</Badge>}</span>
                </button>
              </li>
            ))}
          </ul>
          {current && (
            <article className="min-w-0 rounded-lg border border-rule bg-white">
              <header className="border-b border-rule px-5 py-4 text-[15px]">
                <h2 className="font-sans text-lg font-bold">{current.subject}</h2>
                <p className="mt-1 text-ink-soft">Do: {current.to} · {when(current.created_at)}</p>
                {current.sent_by_me && <p className="mt-1 text-sm text-ink-soft">Tak ten e-mail zobaczył adresat — wysłany w wyniku Twojej wiadomości lub przypomnienia.</p>}
                {current.status === 'REDIRECTED' && <p className="mt-1 font-bold text-warn">Tryb testowy: wysłano na {current.delivered_to}</p>}
                {current.status === 'FAILED' && (
                  <p className="mt-2 rounded-md bg-bad-tint px-3 py-2 text-sm text-bad">
                    <b>Nie wysłano{current.delivered_to ? ` na ${current.delivered_to}` : ''}.</b> {current.error || 'Dostawca poczty zwrócił błąd.'}
                    {' '}Sprawdź konfigurację poczty w panelu Django: Ustawienia systemu → „Wyślij e-mail testowy”.
                  </p>
                )}
              </header>
              {current.body_html
                ? <iframe title={`Treść: ${current.subject}`} sandbox="" srcDoc={current.body_html} className="h-[640px] w-full" />
                : <pre className="whitespace-pre-wrap p-5 font-sans text-[15px]">{current.body_text}</pre>}
            </article>
          )}
        </div>
      )}
    </div>
  )
}
