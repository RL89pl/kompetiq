import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAssistantStatus } from '../api/hooks'
import type { ChatMessage, Conversation } from '../api/types'
import { Button, ErrorList, Notice, Spinner } from './ui'

const EXAMPLES: Record<Conversation['mode'], string[]> = {
  FORMAL: [
    'Ile kryteriów dodatkowych mogę wybrać i kiedy?',
    'Co zrobić, gdy pracownik był nieobecny ponad miesiąc w okresie oceny?',
    'Kiedy przyznaje się negatywną pierwszą ocenę?',
    'W jakim terminie przysługuje sprzeciw od oceny okresowej?',
  ],
  INTERVIEW: [
    'Jakie pytania zadać na otwarcie rozmowy?',
    'Pomóż mi uporządkować argumenty do oceny współpracy.',
    'Jak przekazać informację o obszarach do rozwoju, żeby nie zniechęcić?',
    'Jakie kwestie muszę omówić na rozmowie zgodnie z przepisami?',
  ],
}

function Bubble({ m }: { m: ChatMessage }) {
  if (m.role === 'user') return <p className="ml-auto max-w-[85%] whitespace-pre-line rounded-md bg-ink px-4 py-2 text-white">{m.content}</p>
  return (
    <div className={`rounded-md border border-dashed bg-white p-4 ${m.grounded ? 'border-ai' : 'border-warn'}`}>
      <p className={`mb-2 text-[13px] font-bold ${m.grounded ? 'text-ai' : 'text-warn'}`}>
        {m.grounded ? 'Odpowiedź AI na podstawie źródeł. Sprawdź je przed użyciem.' : 'Brak podstaw w bazie wiedzy'}
      </p>
      <div className="whitespace-pre-line leading-relaxed">{m.content.replace(/\*\*(.+?)\*\*/g, '$1')}</div>
      {m.citations.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer font-bold">Źródła odpowiedzi ({m.citations.length})</summary>
          <ul className="mt-2 space-y-2">
            {m.citations.map((c, j) => (
              <li key={j} className="border-l-2 border-ai pl-3">
                <span className="font-bold">{c.document_index !== null && /\[\d+\]/.test(m.content) ? `[${c.document_index + 1}] ` : ''}{c.document_title}</span>
                {c.cited_text && <><br /><q className="text-ink-soft">{c.cited_text}</q></>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

export function AssistantChat({ mode, assessmentId, compact }: { mode: Conversation['mode']; assessmentId?: number; compact?: boolean }) {
  const qc = useQueryClient()
  const status = useAssistantStatus()
  const listKey = ['conversations', mode, assessmentId ?? null]
  const convs = useQuery({
    queryKey: listKey,
    queryFn: () => api<Conversation[]>(`/assistant/conversations/?mode=${mode}${assessmentId ? `&assessment=${assessmentId}` : '&general=1'}`),
  })
  const [convId, setConvId] = useState<number | null>(null)
  const current = convs.data?.find((c) => c.id === convId) ?? (convId === null ? convs.data?.[0] : undefined)
  const [pending, setPending] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const end = useRef<HTMLDivElement>(null)

  const send = useMutation({
    mutationFn: async (content: string) => {
      let id = current?.id
      if (!id) {
        const c = await api<Conversation>('/assistant/conversations/', { method: 'POST', body: { mode, assessment: assessmentId ?? null } })
        id = c.id
        setConvId(c.id)
      }
      return api<ChatMessage>(`/assistant/conversations/${id}/messages/`, { method: 'POST', body: { content } })
    },
    onMutate: (content) => { setPending(content); setQ('') },
    onSettled: () => { setPending(null); qc.invalidateQueries({ queryKey: listKey }) },
  })
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }) }, [current?.messages.length, pending])

  const messages = current?.messages ?? []
  return (
    <div className={compact ? 'space-y-4' : 'max-w-3xl space-y-6'}>
      {status.data && !status.data.enabled && (
        <Notice tone="warn" title="Asystent AI nie jest skonfigurowany">Administrator musi wskazać dostawcę modelu w konfiguracji serwera.</Notice>
      )}
      {(convs.data?.length ?? 0) > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label htmlFor={`conv-${mode}`} className="text-ink-soft">Rozmowa:</label>
          <select id={`conv-${mode}`} className="max-w-xs rounded-md border border-rule-strong bg-white px-2 py-1"
            value={current?.id ?? ''} onChange={(e) => setConvId(Number(e.target.value))}>
            {convs.data!.map((c) => <option key={c.id} value={c.id}>{c.title || 'Nowa rozmowa'}</option>)}
          </select>
          <button className="underline" onClick={() => setConvId(-1)}>Nowa rozmowa</button>
        </div>
      )}
      <div className={`space-y-4 ${compact ? 'max-h-[55vh] overflow-y-auto pr-1' : ''}`} aria-live="polite">
        {messages.map((m) => <Bubble key={m.id} m={m} />)}
        {pending && <><p className="ml-auto max-w-[85%] rounded-md bg-ink px-4 py-2 text-white">{pending}</p><Spinner label="Asystent szuka w źródłach…" /></>}
        <div ref={end} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) send.mutate(q.trim()) }} className="space-y-3">
        <label htmlFor={`chat-${mode}`} className="font-bold">{mode === 'FORMAL' ? 'Zapytaj o zasady i wymagania formalne' : 'Przygotuj się do rozmowy z pracownikiem'}</label>
        <textarea id={`chat-${mode}`} rows={3} value={q} maxLength={2000} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && q.trim()) send.mutate(q.trim()) }}
          className="w-full rounded-md border border-rule-strong bg-white px-3 py-2 text-[15px]" />
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {EXAMPLES[mode].map((x) => <button key={x} type="button" onClick={() => setQ(x)} className="rounded-md border border-rule-strong bg-white px-3 py-1 text-sm hover:border-ink">{x}</button>)}
          </div>
        )}
        <ErrorList error={send.error} />
        <Button type="submit" variant="ai" busy={send.isPending} disabled={!q.trim()}>Wyślij</Button>
        <p className="text-[13px] text-ink-soft">
          {mode === 'FORMAL' ? 'Asystent odpowiada na podstawie ustawy, rozporządzeń, poradników KPRM, modelu kompetencji i zestawu pytań i odpowiedzi. Gdy źródła nie wystarczają, mówi o tym wprost.'
            : 'Asystent korzysta z Twoich przykładów i ocen w tej ocenie (dane ocenianego są pseudonimizowane). Nie zmienia ocen.'}
        </p>
      </form>
    </div>
  )
}
