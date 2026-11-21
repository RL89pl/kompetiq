import { useState, type ReactNode } from 'react'
import { reportOutcome } from '../api/hooks'
import { Button } from './ui'

/**
 * Wspólny wzorzec prezentacji treści AI: zawsze oznaczona, zawsze do decyzji przełożonego.
 * onAccept otrzymuje (ewentualnie zredagowany) tekst; brak onAccept = treść tylko informacyjna.
 */
export function AISuggestion({
  title, interactionId, children, editableText, onAccept, acceptLabel = 'Wstaw', onDismiss,
}: {
  title: string
  interactionId: number | null
  children?: ReactNode
  editableText?: string
  onAccept?: (text: string) => void
  acceptLabel?: string
  onDismiss?: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(editableText ?? '')
  const [done, setDone] = useState<null | 'accepted' | 'rejected'>(null)

  if (done === 'rejected') return null

  return (
    <aside className="rounded-md border border-dashed border-ai bg-ai-tint/60 p-4" aria-label={`Sugestia AI: ${title}`}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 font-bold text-ai">
          <svg viewBox="0 0 16 16" className="size-4" aria-hidden><path fill="currentColor" d="M8 0l1.8 6.2L16 8l-6.2 1.8L8 16l-1.8-6.2L0 8l6.2-1.8z" /></svg>
          Sugestia AI: {title}
        </p>
        <p className="text-[13px] text-ai">Do weryfikacji. Decyzję podejmujesz Ty.</p>
      </div>
      {children}
      {editableText !== undefined && (
        editing ? (
          <textarea className="mt-2 w-full rounded-md border border-ai/50 bg-white p-3 text-[15px] leading-relaxed" rows={6}
            value={text} onChange={(e) => setText(e.target.value)} aria-label="Edycja sugestii" />
        ) : (
          <p className="mt-2 whitespace-pre-line rounded-md bg-white p-3 text-[15px] leading-relaxed">{text}</p>
        )
      )}
      {done === 'accepted' ? (
        <p className="mt-3 text-sm font-bold text-ok" role="status">Wstawiono — możesz dalej edytować w formularzu.</p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {onAccept && (
            <Button variant="ai" onClick={() => {
              onAccept(text)
              reportOutcome(interactionId, text !== editableText ? 'EDITED' : 'ACCEPTED')
              setDone('accepted')
            }}>{acceptLabel}</Button>
          )}
          {editableText !== undefined && onAccept && (
            <Button variant="ghost" onClick={() => setEditing((v) => !v)}>{editing ? 'Podgląd' : 'Edytuj przed wstawieniem'}</Button>
          )}
          <Button variant="ghost" onClick={() => {
            reportOutcome(interactionId, 'REJECTED')
            setDone('rejected')
            onDismiss?.()
          }}>Odrzuć</Button>
        </div>
      )}
    </aside>
  )
}

export function AIList({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null
  return (
    <div className="mt-3">
      <p className="text-sm font-bold">{title}</p>
      <ul className="mt-1 list-disc space-y-1 pl-5 text-[15px]">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  )
}
