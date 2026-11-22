import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { qk, useCreateAssessment, useEmployees, useMe } from '../api/hooks'
import type { Employee, FormType } from '../api/types'
import { Badge, Button, ErrorList, Loading, Notice, PageHeader } from '../components/ui'
import { fmtDate } from '../lib'
import { EmployeeDialog } from '../components/EmployeeDialog'

const FORM_NAMES: Record<FormType, string> = {
  FIRST: 'Pierwsza ocena', PERIODIC_A: 'Okresowa, arkusz A', PERIODIC_B: 'Okresowa, arkusz B', PERIODIC_C: 'Okresowa, arkusz C',
}

function StartButtons({ e, mode }: { e: Employee; mode: string | null }) {
  const create = useCreateAssessment()
  const nav = useNavigate()
  const role = useMe().data?.active_membership?.role
  if (e.active_assessment)
    return <Link to={`/oceny/${e.active_assessment.id}`} className="font-bold text-ink underline underline-offset-2">Otwórz ocenę w toku</Link>
  // ocenę rozpoczyna bezpośredni przełożony (lub administrator) — kadry tylko podglądają
  if (role === 'HR') return null
  const options: FormType[] = mode === 'FIRST' ? ['FIRST'] : mode === 'PERIODIC' ? [e.suggested_form] : ['FIRST', e.suggested_form]
  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap justify-end gap-2">
        {options.map((ft) => (
          <Button key={ft} variant={ft === 'FIRST' ? 'secondary' : 'primary'} busy={create.isPending && create.variables?.form_type === ft}
            disabled={ft === 'FIRST' && !!e.first_assessment_block} disabledReason={ft === 'FIRST' ? e.first_assessment_block : null}
            onClick={() => create.mutate({ employee: e.id, form_type: ft }, { onSuccess: (a) => nav(`/oceny/${a.id}`) })}>
            Rozpocznij: {FORM_NAMES[ft]}
          </Button>
        ))}
      </div>
      {create.error && <ErrorList error={create.error} />}
    </div>
  )
}

function Deactivate({ e }: { e: Employee }) {
  const qc = useQueryClient()
  const [ask, setAsk] = useState(false)
  const m = useMutation({ mutationFn: () => api(`/employees/${e.id}/`, { method: 'DELETE' }), onSuccess: () => qc.invalidateQueries({ queryKey: qk.employees }) })
  if (!ask) return <button className="text-ink-soft underline underline-offset-2" onClick={() => setAsk(true)}>Usuń z listy</button>
  return (
    <span className="flex items-center gap-2">
      <span className="text-ink-soft">Ukryć {e.full_name}? Oceny i dokumenty zostaną.</span>
      <button className="font-bold text-bad underline underline-offset-2" disabled={m.isPending} onClick={() => m.mutate()}>Tak, usuń</button>
      <button className="underline underline-offset-2" onClick={() => setAsk(false)}>Anuluj</button>
    </span>
  )
}

function AddressField({ e, canEdit }: { e: Employee; canEdit: boolean }) {
  const qc = useQueryClient()
  const m = useMutation({
    mutationFn: (v: string) => api(`/employees/${e.id}/`, { method: 'PATCH', body: { form_of_address: v } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.employees }),
  })
  if (!canEdit) return e.form_of_address ? <Badge>{e.form_of_address === 'PANI' ? 'Pani' : 'Pan'}</Badge> : null
  return (
    <label className="inline-flex items-center gap-1">
      <span>Forma:</span>
      <select value={e.form_of_address} disabled={m.isPending} onChange={(ev) => m.mutate(ev.target.value)}
        className="rounded border border-rule-strong bg-white px-1 py-0.5 text-sm" aria-label={`Forma zwracania się: ${e.full_name}`}>
        <option value="">nieokreślona</option><option value="PANI">Pani</option><option value="PAN">Pan</option>
      </select>
    </label>
  )
}

export function EmployeesPage() {
  const me = useMe()
  const isHR = ['HR', 'ADMIN'].includes(me.data?.active_membership?.role ?? '')
  const { data, isLoading } = useEmployees()
  const [params] = useSearchParams()
  const mode = params.get('rozpocznij')
  const [q, setQ] = useState('')
  const [dialog, setDialog] = useState<Employee | 'new' | null>(null)
  const [saved, setSaved] = useState('')
  const list = (data ?? []).filter((e) => `${e.full_name} ${e.position}`.toLowerCase().includes(q.toLowerCase()))

  return (
    <div>
      <PageHeader title="Pracownicy"
        lead={mode === 'FIRST' ? 'Wybierz osobę, której pierwszą ocenę przygotowujesz.'
          : mode === 'PERIODIC' ? 'Wybierz osobę do oceny okresowej. Arkusz podpowiadamy na podstawie danych o stanowisku (§ 3 rozporządzenia z 2016 r.).'
            : isHR ? 'Kartoteka pracowników urzędu: dane do arkuszy ocen, przełożeni i opisy stanowisk.'
              : 'Osoby, dla których jesteś bezpośrednim przełożonym lub kierujesz ich komórką.'}>
        {isHR && <Button onClick={() => setDialog('new')}>Dodaj pracownika</Button>}
      </PageHeader>
      {dialog && <EmployeeDialog employee={dialog === 'new' ? undefined : dialog} onClose={() => setDialog(null)}
        onSaved={(e) => setSaved(`${dialog === 'new' ? 'Dodano' : 'Zapisano'}: ${e.first_name} ${e.last_name}`)} />}
      {saved && <div className="mb-4"><Notice tone="ok" title={saved}>{isHR && 'Przełożony zobaczy tę osobę na swojej liście pracowników i rozpocznie ocenę.'}</Notice></div>}
      <label className="mb-4 block max-w-sm">
        <span className="sr-only">Szukaj pracownika</span>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Szukaj po nazwisku lub stanowisku"
          className="w-full rounded-md border border-rule-strong bg-white px-3 py-2" />
      </label>
      {isLoading ? <Loading /> : list.length === 0 ? (
        <Notice title="Brak pracowników">Dane pracowników wprowadza kadra (HR) lub administrator instytucji.</Notice>
      ) : (
        <ul className="divide-y divide-rule border-y border-rule">
          {list.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
              <div>
                <p className="font-bold">{e.full_name}</p>
                <p className="text-ink-soft">{e.position}{e.org_unit_name && `, ${e.org_unit_name}`}</p>
                <p className="mt-1 flex flex-wrap gap-2 text-sm text-ink-soft">
                  <span>Zatrudnienie: {fmtDate(e.employment_date)}</span>
                  <AddressField e={e} canEdit={isHR} />
                  {e.is_managerial && <Badge>kieruje pracownikami</Badge>}
                  {e.is_civil_servant && <Badge>urzędnik SC{e.service_grade && `, ${e.service_grade}`}</Badge>}
                  {!e.latest_job_description && <Badge tone="warn">brak opisu stanowiska</Badge>}
                </p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <StartButtons e={e} mode={mode} />
                {isHR && (
                  <div className="flex gap-3 text-sm">
                    <button className="underline underline-offset-2" onClick={() => setDialog(e)}>Edytuj dane</button>
                    <Deactivate e={e} />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
