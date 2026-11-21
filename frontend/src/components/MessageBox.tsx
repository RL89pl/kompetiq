import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Role } from '../api/types'
import { Button, ErrorList, Select, Textarea } from './ui'

/** Komunikacja w procesie oceny: oceniający ↔ kierujący komórką ↔ kadry. */
export function MessageBox({ assessmentId, role, isEvaluator }: { assessmentId: number; role: Role; isEvaluator: boolean }) {
  const options = [
    ...(!isEvaluator ? [['evaluator', 'Oceniający (bezpośredni przełożony)']] : []),
    ['unit_head', 'Kierujący komórką organizacyjną'],
    ...(role !== 'HR' ? [['hr', 'Kadry (HR)']] : []),
  ].filter(([k]) => !(k === 'evaluator' && role === 'SUPERVISOR'))
  const [to, setTo] = useState(options[0]?.[0] ?? 'hr')
  const [text, setText] = useState('')
  const [sent, setSent] = useState(false)
  const m = useMutation({
    mutationFn: () => api(`/assessments/${assessmentId}/message/`, { method: 'POST', body: { to, message: text } }),
    onSuccess: () => { setSent(true); setText('') },
  })
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate() }}>
      <div>
        <label htmlFor="msg-to" className="text-[15px] font-bold">Do</label>
        <Select id="msg-to" value={to} onChange={(e) => { setTo(e.target.value); setSent(false) }}>
          {options.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </Select>
      </div>
      <div>
        <label htmlFor="msg-text" className="text-[15px] font-bold">Wiadomość</label>
        <Textarea id="msg-text" rows={3} maxLength={1000} value={text} onChange={(e) => { setText(e.target.value); setSent(false) }}
          placeholder="Np. prośba o konsultację oceny lub informacja o zmianie terminu" />
        <p className="mt-1 text-[13px] text-ink-soft">Adresat zobaczy wiadomość w powiadomieniach; e-mail zawiera tylko informację o nowej wiadomości.</p>
      </div>
      <ErrorList error={m.error} />
      {sent ? <p className="font-bold text-ok" role="status">Wiadomość wysłana.</p> : <Button type="submit" variant="secondary" busy={m.isPending} disabled={!text.trim()} disabledReason="Wpisz treść wiadomości.">Wyślij</Button>}
    </form>
  )
}
