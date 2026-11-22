import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { MessageRecipient } from '../api/types'
import { Button, ErrorList, Loading } from './ui'

const MAX = 1000
const ICON: Record<MessageRecipient['key'], string> = { evaluator: 'OC', unit_head: 'KK', hr: 'HR' }

/** Komunikacja w procesie oceny (oceniający ↔ kierujący komórką ↔ kadry) — okno nad stroną. */
export function MessageDialog({ assessmentId, employeeName, onClose }: { assessmentId: number; employeeName: string; onClose: () => void }) {
  const rec = useQuery({ queryKey: ['message-recipients', assessmentId], queryFn: () => api<MessageRecipient[]>(`/assessments/${assessmentId}/message/`) })
  const [to, setTo] = useState<MessageRecipient['key'] | null>(null)
  const [text, setText] = useState('')
  const [sentTo, setSentTo] = useState<MessageRecipient | null>(null)
  const chosen = rec.data?.find((r) => r.key === to) ?? rec.data?.[0]
  const m = useMutation({
    mutationFn: () => api(`/assessments/${assessmentId}/message/`, { method: 'POST', body: { to: chosen!.key, message: text } }),
    onSuccess: () => { setSentTo(chosen!); setText('') },
  })
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="msg-title" onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-lg bg-white shadow-xl">
        <header className="flex items-start justify-between gap-4 border-b border-rule px-6 py-4">
          <div>
            <h2 id="msg-title" className="text-xl">Wiadomość w sprawie oceny</h2>
            <p className="text-sm text-ink-soft">{employeeName}</p>
          </div>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-sm text-ink-soft hover:bg-paper" aria-label="Zamknij okno">Zamknij</button>
        </header>

        {sentTo ? (
          <div className="space-y-4 px-6 py-6">
            <div className="flex items-start gap-3 rounded-md bg-ok-tint px-4 py-3">
              <span aria-hidden className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-ok text-sm font-bold text-white">✓</span>
              <div>
                <p className="font-bold">Wiadomość wysłana: {sentTo.label}</p>
                <p className="text-[15px]">{sentTo.names.join(', ')} {sentTo.names.length > 1 ? 'zobaczą' : 'zobaczy'} ją w powiadomieniach i {sentTo.names.length > 1 ? 'dostaną' : 'dostanie'} e-mail z informacją o nowej wiadomości.</p>
              </div>
            </div>
            <p className="text-[15px]">E-mail, który poszedł do adresata, znajdziesz w <Link to="/skrzynka-testowa" onClick={onClose} className="font-bold underline underline-offset-4">skrzynce testowej</Link>.</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setSentTo(null)}>Napisz kolejną</Button>
              <Button autoFocus onClick={onClose}>Gotowe</Button>
            </div>
          </div>
        ) : (
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={(e) => { e.preventDefault(); if (chosen && text.trim()) m.mutate() }}>
            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-6 py-5">
              <fieldset>
                <legend className="text-[15px] font-bold">Do kogo</legend>
                {rec.isLoading ? <Loading /> : !rec.data?.length ? (
                  <p className="mt-2 text-[15px] text-ink-soft">Brak adresatów — komórka nie ma przypisanego kierującego, a w urzędzie nie ma konta kadr.</p>
                ) : (
                  <div className="mt-2 grid gap-2 sm:grid-cols-2" role="radiogroup">
                    {rec.data.map((r) => {
                      const active = chosen?.key === r.key
                      return (
                        <label key={r.key} className={`flex cursor-pointer items-start gap-3 rounded-md border-2 px-3 py-2.5 ${active ? 'border-ink bg-paper' : 'border-rule hover:border-rule-strong'}`}>
                          <input type="radio" name="msg-to" className="sr-only" checked={active} onChange={() => setTo(r.key)} />
                          <span aria-hidden className={`flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-bold ${active ? 'bg-ink text-white' : 'bg-rule text-ink-soft'}`}>{ICON[r.key]}</span>
                          <span className="min-w-0">
                            <span className="block font-bold leading-tight">{r.label}</span>
                            <span className="block truncate text-sm">{r.names.join(', ')}</span>
                            <span className="block text-[13px] text-ink-soft">{r.hint}</span>
                          </span>
                        </label>
                      )
                    })}
                  </div>
                )}
              </fieldset>
              <div>
                <div className="flex items-baseline justify-between">
                  <label htmlFor="msg-text" className="text-[15px] font-bold">Treść</label>
                  <span className={`text-[13px] ${text.length > MAX * 0.9 ? 'text-warn' : 'text-ink-soft'}`}>{text.length} / {MAX}</span>
                </div>
                <textarea id="msg-text" rows={6} maxLength={MAX} value={text} autoFocus onChange={(e) => setText(e.target.value)}
                  placeholder="Np. prośba o konsultację oceny, pytanie o termin albo informacja o nieobecności ocenianego."
                  onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && chosen && text.trim()) m.mutate() }}
                  className="mt-1 w-full rounded-md border border-rule-strong bg-white px-3 py-2 text-[15px] leading-relaxed placeholder:text-ink-soft/70 focus:border-ink" />
              </div>
              <p className="rounded-md bg-paper px-3 py-2 text-[13px] text-ink-soft">
                Adresat zobaczy treść w powiadomieniach po zalogowaniu. E-mail zawiera tylko informację o nowej wiadomości — bez treści i danych oceny.
              </p>
              <ErrorList error={m.error} />
            </div>
            <footer className="flex items-center justify-between gap-3 border-t border-rule px-6 py-4">
              <span className="hidden text-[13px] text-ink-soft sm:inline">⌘/Ctrl + Enter — wyślij</span>
              <div className="flex gap-2">
                <Button type="button" variant="ghost" onClick={onClose}>Anuluj</Button>
                <Button type="submit" busy={m.isPending} disabled={!chosen || !text.trim()}
                  disabledReason={!chosen ? 'Brak dostępnego adresata.' : 'Wpisz treść wiadomości.'}>Wyślij wiadomość</Button>
              </div>
            </footer>
          </form>
        )}
      </div>
    </div>
  )
}
