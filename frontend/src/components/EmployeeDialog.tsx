import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError, upload } from '../api/client'
import { qk } from '../api/hooks'
import type { Employee, InstitutionUser, OrgUnit } from '../api/types'
import { fmtDate } from '../lib'
import { Button, ErrorList } from './ui'

type Form = {
  first_name: string; last_name: string; form_of_address: '' | 'PANI' | 'PAN'; position: string
  org_unit: string; supervisor: string; employment_date: string; contract_end_date: string
  is_civil_servant: boolean; service_grade: string; appointment_year: string; service_grade_date: string
  is_managerial: boolean; is_office_head: boolean
}

const EMPTY: Form = {
  first_name: '', last_name: '', form_of_address: '', position: '', org_unit: '', supervisor: '', employment_date: '',
  contract_end_date: '', is_civil_servant: false, service_grade: '', appointment_year: '', service_grade_date: '',
  is_managerial: false, is_office_head: false,
}
const GRADES = ['radca', 'starszy radca', 'radca ministra', 'radca generalny', 'radca generalny Prezesa Rady Ministrów']

function fromEmployee(e: Employee): Form {
  return {
    first_name: e.first_name, last_name: e.last_name, form_of_address: e.form_of_address, position: e.position,
    org_unit: e.org_unit ? String(e.org_unit) : '', supervisor: e.supervisor ? String(e.supervisor) : '',
    employment_date: e.employment_date ?? '', contract_end_date: e.contract_end_date ?? '', is_civil_servant: e.is_civil_servant,
    service_grade: e.service_grade, appointment_year: e.appointment_year ? String(e.appointment_year) : '',
    service_grade_date: e.service_grade_date ?? '', is_managerial: e.is_managerial, is_office_head: e.is_office_head,
  }
}

/** Ostatni dzień na pierwszą ocenę: miesiąc przed końcem pierwszej umowy (domyślnie 12 miesięcy), art. 38 ust. 1. */
function firstAssessmentDeadline(start: string, end: string): Date | null {
  if (!start) return null
  const d = end ? new Date(end) : (() => { const x = new Date(start); x.setFullYear(x.getFullYear() + 1); x.setDate(x.getDate() - 1); return x })()
  d.setMonth(d.getMonth() - 1)
  return d
}

const inputCls = 'w-full rounded-md border border-rule-strong bg-white px-3 py-2 text-[15px] focus:border-ink disabled:bg-paper'

function F({ label, error, hint, children, wide }: { label: string; error?: string; hint?: React.ReactNode; children: React.ReactNode; wide?: boolean }) {
  return (
    <label className={`flex flex-col gap-1 ${wide ? 'md:col-span-2' : ''}`}>
      <span className="text-[15px] font-bold">{label}</span>
      {children}
      {hint && <span className="text-[13px] text-ink-soft">{hint}</span>}
      {error && <span className="text-sm text-bad">{error}</span>}
    </label>
  )
}

function Check({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint: string }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-md border border-rule px-3 py-2.5 hover:border-rule-strong">
      <input type="checkbox" className="mt-1 size-4" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span><span className="block font-bold leading-tight">{label}</span><span className="text-[13px] text-ink-soft">{hint}</span></span>
    </label>
  )
}

/** Dodawanie i edycja pracownika przez kadry (HR) lub administratora — wszystkie dane potrzebne do ocen. */
export function EmployeeDialog({ employee, onClose, onSaved }: { employee?: Employee; onClose: () => void; onSaved?: (e: Employee) => void }) {
  const qc = useQueryClient()
  const units = useQuery({ queryKey: ['org-units'], queryFn: () => api<OrgUnit[]>('/org-units/') })
  const users = useQuery({ queryKey: ['institution-users'], queryFn: () => api<InstitutionUser[]>('/users/') })
  const [f, setF] = useState<Form>(employee ? fromEmployee(employee) : EMPTY)
  const [jdMode, setJdMode] = useState<'none' | 'text' | 'file'>(employee ? 'none' : 'text')
  const [duties, setDuties] = useState('')
  const [purpose, setPurpose] = useState('')
  const [file, setFile] = useState<File | null>(null)
  // utworzony już pracownik — ponowienie po błędzie opisu stanowiska nie tworzy duplikatu
  const [created, setCreated] = useState<Employee | null>(null)
  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF((x) => ({ ...x, [k]: v }))

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        ...f, org_unit: f.org_unit ? Number(f.org_unit) : null, supervisor: f.supervisor ? Number(f.supervisor) : null,
        employment_date: f.employment_date || null, contract_end_date: f.contract_end_date || null,
        appointment_year: f.appointment_year ? Number(f.appointment_year) : null, service_grade_date: f.service_grade_date || null,
        ...(f.is_civil_servant ? {} : { service_grade: '', appointment_year: null, service_grade_date: null }),
      }
      const existing = employee ?? created
      const emp = existing
        ? await api<Employee>(`/employees/${existing.id}/`, { method: 'PATCH', body })
        : await api<Employee>('/employees/', { method: 'POST', body })
      if (!existing) setCreated(emp)
      if (jdMode === 'text' && duties.trim())
        await api('/job-descriptions/', { method: 'POST', body: { employee: emp.id, main_duties: duties.trim(), purpose: purpose.trim() } })
      if (jdMode === 'file' && file) {
        const fd = new FormData(); fd.append('employee', String(emp.id)); fd.append('file', file)
        await upload('/job-descriptions/import-osp/', fd)
      }
      return emp
    },
    onSuccess: (emp) => { qc.invalidateQueries({ queryKey: qk.employees }); onSaved?.(emp); onClose() },
  })
  const fieldErr = (k: string) => {
    const d = save.error instanceof ApiError ? (save.error.data as Record<string, unknown> | null) : null
    const v = d?.[k]
    return v ? (Array.isArray(v) ? v.join(' ') : String(v)) : undefined
  }

  const sheet = f.is_office_head ? 'A (kierownik urzędu)' : f.is_managerial ? 'B (kieruje pracownikami)' : 'C (pozostałe stanowiska)'
  const deadline = firstAssessmentDeadline(f.employment_date, f.contract_end_date)
  const firstOk = deadline && deadline >= new Date(new Date().toDateString())
  const supervisors = (users.data ?? []).filter((u) => u.role !== 'HR')
  const unit = units.data?.find((u) => String(u.id) === f.org_unit)
  const missing = !f.first_name.trim() || !f.last_name.trim() || !f.position.trim()
  const jdMissing = jdMode === 'file' && !file

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="emp-title" onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-white shadow-xl">
        <header className="flex items-start justify-between gap-4 border-b border-rule px-6 py-4">
          <div>
            <h2 id="emp-title" className="text-xl">{employee ? `Edycja: ${employee.full_name}` : 'Nowy pracownik'}</h2>
            <p className="text-sm text-ink-soft">Dane potrzebne do arkuszy ocen. Pola z gwiazdką są wymagane.</p>
          </div>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-sm text-ink-soft hover:bg-paper">Zamknij</button>
        </header>

        <form className="flex min-h-0 flex-1 flex-col" onSubmit={(e) => { e.preventDefault(); if (!missing && !jdMissing) save.mutate() }}>
          <div className="min-h-0 flex-1 space-y-7 overflow-y-auto px-6 py-5">
            <section>
              <h3 className="mb-3 font-sans text-sm font-bold uppercase tracking-wide text-ink-soft">Dane osobowe</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <F label="Imię *" error={fieldErr('first_name')}><input className={inputCls} autoFocus value={f.first_name} onChange={(e) => set('first_name', e.target.value)} /></F>
                <F label="Nazwisko *" error={fieldErr('last_name')}><input className={inputCls} value={f.last_name} onChange={(e) => set('last_name', e.target.value)} /></F>
                <F label="Forma zwracania się" hint="Asystent AI użyje jej w pytaniach i scenariuszu rozmowy. Nie zgadujemy jej z imienia." wide>
                  <div className="flex gap-2">
                    {([['PANI', 'Pani'], ['PAN', 'Pan'], ['', 'nie wskazano']] as const).map(([v, l]) => (
                      <button key={v} type="button" onClick={() => set('form_of_address', v)} aria-pressed={f.form_of_address === v}
                        className={`rounded-md border-2 px-4 py-1.5 text-[15px] ${f.form_of_address === v ? 'border-ink bg-ink font-bold text-white' : 'border-rule-strong bg-white hover:border-ink'}`}>{l}</button>
                    ))}
                  </div>
                </F>
              </div>
            </section>

            <section>
              <h3 className="mb-3 font-sans text-sm font-bold uppercase tracking-wide text-ink-soft">Zatrudnienie</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <F label="Stanowisko *" error={fieldErr('position')} hint="Pełna nazwa, jak w opisie stanowiska." wide>
                  <input className={inputCls} value={f.position} onChange={(e) => set('position', e.target.value)} placeholder="np. Starszy specjalista ds. zezwoleń" />
                </F>
                <F label="Komórka organizacyjna" error={fieldErr('org_unit')}
                  hint={unit ? (unit.head_name ? `Kierujący komórką: ${unit.head_name} — potwierdza pierwszą ocenę.` : 'Komórka nie ma przypisanego kierującego.') : undefined}>
                  <select className={inputCls} value={f.org_unit} onChange={(e) => set('org_unit', e.target.value)}>
                    <option value="">— wybierz —</option>
                    {units.data?.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                  </select>
                </F>
                <F label="Bezpośredni przełożony (oceniający)" error={fieldErr('supervisor')} hint="Ta osoba zobaczy pracownika i rozpocznie jego ocenę.">
                  <select className={inputCls} value={f.supervisor} onChange={(e) => set('supervisor', e.target.value)}>
                    <option value="">— wybierz —</option>
                    {supervisors.map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.role_display})</option>)}
                  </select>
                </F>
                <F label="Data nawiązania stosunku pracy" error={fieldErr('employment_date')}>
                  <input type="date" className={inputCls} value={f.employment_date} onChange={(e) => set('employment_date', e.target.value)} />
                </F>
                <F label="Koniec umowy na czas określony" error={fieldErr('contract_end_date')} hint="Puste: przyjmujemy 12 miesięcy pierwszej umowy.">
                  <input type="date" className={inputCls} value={f.contract_end_date} onChange={(e) => set('contract_end_date', e.target.value)} />
                </F>
              </div>
            </section>

            <section>
              <h3 className="mb-3 font-sans text-sm font-bold uppercase tracking-wide text-ink-soft">Stanowisko i służba cywilna</h3>
              <div className="grid gap-3 md:grid-cols-2">
                <Check checked={f.is_managerial} onChange={(v) => set('is_managerial', v)} label="Kieruje pracownikami" hint="Stanowisko kierownicze — arkusz B (§ 3 rozp. z 2016 r.)." />
                <Check checked={f.is_office_head} onChange={(v) => setF((x) => ({ ...x, is_office_head: v, is_managerial: v || x.is_managerial }))} label="Kierownik urzędu" hint="Arkusz A." />
                <Check checked={f.is_civil_servant} onChange={(v) => set('is_civil_servant', v)} label="Urzędnik służby cywilnej (mianowany)" hint="Część III arkusza: wniosek o kolejny stopień." />
              </div>
              {fieldErr('is_civil_servant') && <p className="mt-2 text-sm text-bad">{fieldErr('is_civil_servant')}</p>}
              {f.is_civil_servant && (
                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <F label="Stopień służbowy" error={fieldErr('service_grade')}>
                    <input className={inputCls} list="grades" value={f.service_grade} onChange={(e) => set('service_grade', e.target.value)} />
                    <datalist id="grades">{GRADES.map((g) => <option key={g} value={g} />)}</datalist>
                  </F>
                  <F label="Rok mianowania" error={fieldErr('appointment_year')}>
                    <input type="number" min={1996} max={new Date().getFullYear()} className={inputCls} value={f.appointment_year} onChange={(e) => set('appointment_year', e.target.value)} />
                  </F>
                  <F label="Data przyznania stopnia" error={fieldErr('service_grade_date')}>
                    <input type="date" className={inputCls} value={f.service_grade_date} onChange={(e) => set('service_grade_date', e.target.value)} />
                  </F>
                </div>
              )}
            </section>

            <section>
              <h3 className="mb-3 font-sans text-sm font-bold uppercase tracking-wide text-ink-soft">Opis stanowiska pracy</h3>
              {employee?.latest_job_description && (
                <p className="mb-2 text-sm text-ink-soft">Obecny opis: {employee.latest_job_description.source_name || 'wpisany ręcznie'}, {fmtDate(employee.latest_job_description.created_at)}. Nowy opis zastąpi go w kolejnych ocenach.</p>
              )}
              <div className="mb-3 flex flex-wrap gap-2">
                {([['text', 'Wpiszę zadania'], ['file', 'Wczytam plik OSP (.docx)'], ['none', employee ? 'Bez zmian' : 'Później']] as const).map(([v, l]) => (
                  <button key={v} type="button" onClick={() => setJdMode(v)} aria-pressed={jdMode === v}
                    className={`rounded-md border-2 px-3 py-1.5 text-[15px] ${jdMode === v ? 'border-ink bg-paper font-bold' : 'border-rule-strong bg-white hover:border-ink'}`}>{l}</button>
                ))}
              </div>
              {jdMode === 'text' && (
                <div className="grid gap-4">
                  <F label="Główne zadania na stanowisku" hint="Jedno zadanie w wierszu. Na ich podstawie asystent podpowie wskaźniki i kryteria.">
                    <textarea rows={4} className={inputCls} value={duties} onChange={(e) => setDuties(e.target.value)} placeholder={'Rozpatrywanie wniosków o zezwolenia zgodnie z KPA\nPrzygotowywanie projektów decyzji'} />
                  </F>
                  <F label="Cel stanowiska (opcjonalnie)">
                    <input className={inputCls} value={purpose} onChange={(e) => setPurpose(e.target.value)} />
                  </F>
                </div>
              )}
              {jdMode === 'file' && (
                <F label="Plik opisu stanowiska (OSP, .docx, do 5 MB)" hint="Odczytamy zadania, uprawnienia, liczbę podległych i kompetencje z OSP.">
                  <input type="file" accept=".docx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-[15px]" />
                </F>
              )}
            </section>

            <section className="rounded-md bg-paper px-4 py-3 text-[15px]">
              <p><b>Arkusz oceny okresowej:</b> {sheet}</p>
              <p className="mt-1"><b>Pierwsza ocena:</b>{' '}
                {!deadline ? 'podaj datę zatrudnienia, aby wyliczyć termin.'
                  : firstOk ? `można ją rozpocząć — dokonuje się jej najpóźniej do ${deadline.toLocaleDateString('pl-PL')}.`
                    : `termin minął ${deadline.toLocaleDateString('pl-PL')} — dla tej osoby rozpoczniesz ocenę okresową.`}
              </p>
            </section>
            {save.error && (Object.keys(EMPTY).some((k) => fieldErr(k))
              ? <p className="text-sm text-bad" role="alert">Popraw zaznaczone pola.</p>
              : <ErrorList error={save.error} />)}
            {created && save.error && <p className="text-sm text-ink-soft">Pracownik został zapisany — popraw opis stanowiska albo wybierz „Później”.</p>}
          </div>
          <footer className="flex justify-end gap-2 border-t border-rule px-6 py-4">
            <Button type="button" variant="ghost" onClick={onClose}>Anuluj</Button>
            <Button type="submit" busy={save.isPending} disabled={missing || jdMissing}
              disabledReason={missing ? 'Uzupełnij imię, nazwisko i stanowisko.' : 'Wybierz plik OSP albo inną opcję opisu stanowiska.'}>
              {employee ? 'Zapisz zmiany' : 'Dodaj pracownika'}
            </Button>
          </footer>
        </form>
      </div>
    </div>
  )
}
