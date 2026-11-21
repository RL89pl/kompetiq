import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { qk, useNotifications } from '../api/hooks'
import { Badge, Button, Loading, PageHeader } from '../components/ui'
import { fmtDate } from '../lib'

const TONE = { REMINDER: 'warn', APPROVAL: 'first', STATUS: 'ok', MESSAGE: 'neutral' } as const

export function NotificationsPage() {
  const { data, isLoading } = useNotifications()
  const qc = useQueryClient()
  const refresh = () => qc.invalidateQueries({ queryKey: qk.notifications })
  const read = useMutation({ mutationFn: (id: number) => api(`/notifications/${id}/read/`, { method: 'POST' }), onSuccess: refresh })
  const readAll = useMutation({ mutationFn: () => api('/notifications/read-all/', { method: 'POST' }), onSuccess: refresh })
  return (
    <div>
      <PageHeader title="Powiadomienia" lead="Przypomnienia o terminach, prośby o potwierdzenie oceny i wiadomości w procesie.">
        {data?.some((n) => !n.read_at) && <Button variant="secondary" onClick={() => readAll.mutate()}>Oznacz wszystkie jako przeczytane</Button>}
      </PageHeader>
      {isLoading ? <Loading /> : !data?.length ? <p className="text-ink-soft">Brak powiadomień.</p> : (
        <ul className="divide-y divide-rule border-y border-rule">
          {data.map((n) => (
            <li key={n.id} className={`flex flex-wrap items-start justify-between gap-3 py-3 ${n.read_at ? 'opacity-70' : ''}`}>
              <div className="max-w-[70ch]">
                <p className="flex flex-wrap items-center gap-2"><Badge tone={TONE[n.kind]}>{n.kind_label}</Badge>
                  <span className={n.read_at ? '' : 'font-bold'}>{n.title}</span></p>
                {n.body && <p className="mt-1 whitespace-pre-line text-[15px]">{n.body}</p>}
                <p className="mt-1 text-sm text-ink-soft">{n.sender_name}, {fmtDate(n.created_at)}</p>
              </div>
              <div className="flex gap-2">
                {n.assessment && <Link className="font-bold underline" to={`/oceny/${n.assessment}`} onClick={() => !n.read_at && read.mutate(n.id)}>Otwórz ocenę</Link>}
                {!n.read_at && <button className="text-sm underline" onClick={() => read.mutate(n.id)}>Przeczytane</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
