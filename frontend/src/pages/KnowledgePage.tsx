import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, upload } from '../api/client'
import { qk, useMe } from '../api/hooks'
import type { KnowledgeDocument, SourceKind } from '../api/types'
import { Badge, Button, ErrorList, Field, Input, Loading, Notice, PageHeader, Section, Select } from '../components/ui'
import { fmtDate } from '../lib'

const KINDS: [SourceKind, string][] = [
  ['ACT', 'Ustawa'], ['REGULATION', 'Rozporządzenie'], ['GUIDE', 'Poradnik'], ['FAQ', 'Pytania i odpowiedzi'], ['OTHER', 'Inne'],
]
const KEY = ['knowledge-documents']

export function KnowledgePage() {
  const { data: me } = useMe()
  const isAdmin = me?.active_membership?.role === 'ADMIN'
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: KEY, queryFn: () => api<KnowledgeDocument[]>('/knowledge-documents/') })
  const refresh = () => {
    qc.invalidateQueries({ queryKey: KEY })
    qc.invalidateQueries({ queryKey: qk.assistantStatus })
  }
  const toggle = useMutation({
    mutationFn: (d: KnowledgeDocument) => {
      const on = d.shared ? d.disabled_here : !d.is_active
      return api(`/knowledge-documents/${d.id}/${on ? 'enable' : 'disable'}/`, { method: 'POST' })
    },
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api(`/knowledge-documents/${id}/`, { method: 'DELETE' }),
    onSuccess: refresh,
  })

  if (isLoading || !data) return <Loading />
  const shared = data.filter((d) => d.shared)
  const own = data.filter((d) => !d.shared)
  const active = (d: KnowledgeDocument) => (d.shared ? !d.disabled_here : d.is_active)

  const table = (rows: KnowledgeDocument[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[15px]">
        <thead className="border-b border-rule-strong text-sm text-ink-soft">
          <tr><th className="py-2 pr-3">Źródło</th><th className="pr-3">Rodzaj</th><th className="pr-3">Obowiązuje od</th>
            <th className="pr-3">Fragmenty</th><th className="pr-3">Status</th>{isAdmin && <th />}</tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {rows.map((d) => (
            <tr key={d.id} className={active(d) ? '' : 'text-ink-soft'}>
              <td className="py-2 pr-3">
                <p className="font-bold">{d.title}</p>
                <p className="text-sm text-ink-soft">{d.source}{d.uploaded_by_name && `, dodał(a) ${d.uploaded_by_name} ${fmtDate(d.created_at)}`}</p>
                {d.replaces_title && <p className="text-sm">Zastępuje: {d.replaces_title}</p>}
                {d.note && <p className="text-sm">{d.note}</p>}
              </td>
              <td className="pr-3">{d.kind_label}</td>
              <td className="pr-3">{fmtDate(d.valid_from)}</td>
              <td className="pr-3">{d.chunk_count}</td>
              <td className="pr-3">{active(d) ? <Badge tone="ok">Używane</Badge> : <Badge tone="warn">Wyłączone</Badge>}</td>
              {isAdmin && (
                <td className="whitespace-nowrap text-right">
                  <button className="text-sm underline" disabled={toggle.isPending} onClick={() => toggle.mutate(d)}>
                    {active(d) ? 'Wyłącz' : 'Włącz'}
                  </button>
                  {!d.shared && (
                    <button className="ml-3 text-sm text-bad underline" disabled={remove.isPending}
                      onClick={() => window.confirm(`Usunąć źródło „${d.title}” z bazy wiedzy?`) && remove.mutate(d.id)}>Usuń</button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="space-y-10">
      <PageHeader title="Baza wiedzy asystenta"
        lead="Źródła, na podstawie których asystent formalny odpowiada i które cytuje. Po zmianie przepisów dodaj nowy akt i wskaż, który zastępuje: asystent od razu przestanie korzystać ze starego." />
      <ErrorList error={toggle.error ?? remove.error} />
      {isAdmin ? <UploadForm candidates={shared.concat(own).filter(active)} onDone={refresh} />
        : <Notice title="Podgląd">Źródłami zarządza administrator instytucji.</Notice>}
      <Section title="Źródła urzędu" description="Dodane w tym urzędzie: zarządzenia, regulaminy, wewnętrzne wytyczne, nowe wersje przepisów.">
        {own.length ? table(own) : <p className="text-ink-soft">Urząd nie dodał jeszcze własnych źródeł.</p>}
      </Section>
      <Section title="Źródła wspólne" description="Ustawa, rozporządzenia, poradniki KPRM, model kompetencji i zestaw pytań i odpowiedzi — wspólne dla wszystkich urzędów. Urząd może wyłączyć źródło u siebie, ale nie może go usunąć.">
        {table(shared)}
      </Section>
    </div>
  )
}

function UploadForm({ candidates, onDone }: { candidates: KnowledgeDocument[]; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [kind, setKind] = useState<SourceKind>('REGULATION')
  const [validFrom, setValidFrom] = useState('')
  const [replaces, setReplaces] = useState('')
  const [note, setNote] = useState('')
  const send = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('file', file as File)
      fd.append('title', title)
      fd.append('kind', kind)
      if (validFrom) fd.append('valid_from', validFrom)
      if (replaces) fd.append('replaces', replaces)
      if (note) fd.append('note', note)
      return upload<KnowledgeDocument>('/knowledge-documents/', fd)
    },
    onSuccess: () => {
      setFile(null); setTitle(''); setValidFrom(''); setReplaces(''); setNote('')
      onDone()
    },
  })
  return (
    <Section title="Dodaj źródło" description="PDF z warstwą tekstową, DOCX, TXT lub MD, do 20 MB. Tekst jest dzielony na fragmenty i od razu trafia do wyszukiwania asystenta.">
      <form className="grid gap-4 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); send.mutate() }}>
        <Field label="Plik">{(id) => <Input id={id} type="file" accept=".pdf,.docx,.txt,.md" required
          onChange={(e) => { const f = e.target.files?.[0] ?? null; setFile(f); if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, '')) }} />}</Field>
        <Field label="Tytuł źródła" hint="Tak asystent poda źródło w odpowiedzi.">{(id) => <Input id={id} value={title} required maxLength={255} onChange={(e) => setTitle(e.target.value)} />}</Field>
        <Field label="Rodzaj">{(id) => (
          <Select id={id} value={kind} onChange={(e) => setKind(e.target.value as SourceKind)}>
            {KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </Select>)}</Field>
        <Field label="Obowiązuje od" hint="Opcjonalnie.">{(id) => <Input id={id} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />}</Field>
        <Field label="Zastępuje źródło" hint="Wskazane źródło zostanie wyłączone w urzędzie.">{(id) => (
          <Select id={id} value={replaces} onChange={(e) => setReplaces(e.target.value)}>
            <option value="">— nie zastępuje —</option>
            {candidates.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
          </Select>)}</Field>
        <Field label="Uwagi" hint="Np. sygnatura, Dz.U.">{(id) => <Input id={id} value={note} maxLength={255} onChange={(e) => setNote(e.target.value)} />}</Field>
        <div className="md:col-span-2">
          <Button type="submit" busy={send.isPending} disabled={!file} disabledReason="Najpierw wybierz plik.">Dodaj do bazy wiedzy</Button>
          {send.isSuccess && <p className="mt-2 text-sm text-ok" role="status">Dodano: {send.data.title} ({send.data.chunk_count} fragm.)</p>}
          <ErrorList error={send.error} />
        </div>
      </form>
    </Section>
  )
}
