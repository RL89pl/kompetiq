import { useMutation, useQuery } from '@tanstack/react-query'
import { Fragment, useState } from 'react'
import { api } from '../api/client'
import { qk, useAssessments, useMe } from '../api/hooks'
import type { Assessment } from '../api/types'
import { Badge, Button, ErrorList, Field, Notice, PageHeader, Section, Select, Textarea } from '../components/ui'

type Feature =
  | 'analyze-job-description' | 'guiding-questions' | 'analyze-evidence' | 'draft-justification'
  | 'interview-script' | 'development-suggestions' | 'chat-formal' | 'chat-interview'

const FEATURES: { value: Feature; label: string; criterion?: 'required' | 'optional'; chat?: boolean; noAssessment?: boolean }[] = [
  { value: 'chat-formal', label: 'Rozmowa: zasady i wymagania formalne', chat: true, noAssessment: true },
  { value: 'chat-interview', label: 'Rozmowa: przygotowanie do rozmowy z pracownikiem', chat: true },
  { value: 'interview-script', label: 'Scenariusz rozmowy oceniającej' },
  { value: 'analyze-job-description', label: 'Analiza opisu stanowiska' },
  { value: 'analyze-evidence', label: 'Analiza przykładów zachowań', criterion: 'required' },
  { value: 'draft-justification', label: 'Projekt uzasadnienia', criterion: 'optional' },
  { value: 'guiding-questions', label: 'Pytania pomocnicze do wskaźników', criterion: 'required' },
  { value: 'development-suggestions', label: 'Propozycje działań rozwojowych' },
]

interface Call {
  method: 'structured' | 'answer_with_citations'
  system: string[]
  prompt: string
  documents: { title: string; text: string }[]
  history: { role: string; content: string }[]
  response_schema: Record<string, unknown> | null
}
interface Preview {
  feature_label: string
  would_call_model: boolean
  reason: string
  destination: { provider: string; model: string; host: string; enabled: boolean }
  calls: Call[]
  characters: number
  checks: { label: string; ok: boolean; detail: string }[]
  sent: string[]
  not_sent: string[]
}

/** Nazwy pól schematu odpowiedzi (z zagnieżdżeniami) — pokazują, że model nie zwraca ocen. */
function schemaFields(schema: Record<string, unknown> | null): string[] {
  if (!schema) return []
  const out = new Set<string>()
  const walk = (node: unknown) => {
    if (!node || typeof node !== 'object') return
    const n = node as Record<string, unknown>
    if (n.properties && typeof n.properties === 'object') Object.keys(n.properties).forEach((k) => out.add(k))
    Object.values(n).forEach(walk)
  }
  walk(schema)
  return [...out]
}

/** Podświetla słowa wstawione przez pseudonimizację. */
function Highlighted({ text }: { text: string }) {
  const parts = text.split(/\b(Oceniany|Oceniana)\b/)
  return <>{parts.map((p, i) => (i % 2 ? <mark key={i} className="rounded bg-ai/20 px-0.5 font-bold">{p}</mark> : <Fragment key={i}>{p}</Fragment>))}</>
}

const pre = 'mt-2 max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-md border border-rule bg-white p-3 font-mono text-[13px] leading-relaxed'

export function AITransparencyPage() {
  const { data: me } = useMe()
  const { data: list } = useAssessments()
  const [feature, setFeature] = useState<Feature>('chat-formal')
  const [assessmentId, setAssessmentId] = useState<number>(0)
  const [criterion, setCriterion] = useState('')
  const [question, setQuestion] = useState('Jaki jest termin na sprzeciw od oceny okresowej?')
  const f = FEATURES.find((x) => x.value === feature)!
  const { data: assessment } = useQuery({
    queryKey: qk.assessment(assessmentId), enabled: assessmentId > 0,
    queryFn: () => api<Assessment>(`/assessments/${assessmentId}/`),
  })
  const isAdmin = me?.active_membership?.role === 'ADMIN'
  const mine = (list ?? []).filter((a) => isAdmin || a.evaluator === me?.id)

  const run = useMutation({
    mutationFn: () => api<Preview>('/assistant/preview/', {
      method: 'POST',
      body: {
        feature,
        ...(assessmentId ? { assessment: assessmentId } : {}),
        ...(criterion ? { criterion: Number(criterion) } : {}),
        ...(f.chat ? { question } : {}),
      },
    }),
  })
  const d = run.data

  return (
    <div className="space-y-10">
      <PageHeader title="Przejrzystość AI"
        lead="Zobacz dokładnie, co asystent wysłałby do modelu językowego dla wybranej oceny: instrukcje, treść zapytania i źródła. Podgląd nie wywołuje modelu i niczego nie zapisuje." />

      <Section title="Wybierz funkcję asystenta">
        <form className="grid gap-4 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); run.mutate() }}>
          <Field label="Funkcja">{(id) => (
            <Select id={id} value={feature} onChange={(e) => { setFeature(e.target.value as Feature); setCriterion(''); run.reset() }}>
              {FEATURES.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
            </Select>)}</Field>
          <Field label="Ocena" hint={f.noAssessment ? 'Opcjonalnie: kontekst etapu i terminów oceny.' : 'Oceny, w których jesteś oceniającym.'}>{(id) => (
            <Select id={id} value={assessmentId} required={!f.noAssessment}
              onChange={(e) => { setAssessmentId(Number(e.target.value)); setCriterion(''); run.reset() }}>
              <option value={0}>{f.noAssessment ? '— bez oceny —' : '— wybierz ocenę —'}</option>
              {mine.map((a) => <option key={a.id} value={a.id}>{a.employee_name}: {a.form_label}</option>)}
            </Select>)}</Field>
          {f.criterion && (
            <Field label="Kryterium" hint={f.criterion === 'optional' ? 'Opcjonalnie: uzasadnienie jednego kryterium.' : undefined}>{(id) => (
              <Select id={id} value={criterion} required={f.criterion === 'required'} onChange={(e) => setCriterion(e.target.value)}>
                <option value="">{f.criterion === 'optional' ? '— całość oceny —' : '— wybierz kryterium —'}</option>
                {assessment?.criteria.map((c) => <option key={c.id} value={c.id}>{c.competency_name}</option>)}
              </Select>)}</Field>
          )}
          {f.chat && (
            <div className="md:col-span-2">
              <Field label="Pytanie do asystenta">{(id) => <Textarea id={id} rows={2} value={question} required maxLength={2000} onChange={(e) => setQuestion(e.target.value)} />}</Field>
            </div>
          )}
          <div className="md:col-span-2">
            <Button type="submit" busy={run.isPending}>Pokaż, co zostałoby wysłane</Button>
            <ErrorList error={run.error} />
          </div>
        </form>
      </Section>

      {d && (
        <>
          <Section title="Wynik kontroli">
            {!d.would_call_model ? (
              <Notice tone="ok" title="Model nie zostałby wywołany">{d.reason}</Notice>
            ) : (
              <div className="space-y-6">
                <p className="text-[15px]">
                  Adresat: {d.destination.enabled
                    ? <><b>{d.destination.host}</b>, model <b>{d.destination.model}</b></>
                    : <b>dostawca AI nie jest skonfigurowany — w tej instalacji nic nie zostałoby wysłane</b>}.
                  {' '}Rozmiar wysyłki: {d.characters.toLocaleString('pl-PL')} znaków.
                </p>
                <ul className="space-y-2">
                  {d.checks.map((c) => (
                    <li key={c.label} className="flex gap-3">
                      <span aria-hidden className={`font-bold ${c.ok ? 'text-ok' : 'text-bad'}`}>{c.ok ? '✓' : '✗'}</span>
                      <div><p className="font-bold">{c.label}</p><p className="text-sm text-ink-soft">{c.detail}</p></div>
                    </li>
                  ))}
                </ul>
                {d.checks.some((c) => !c.ok) && (
                  <Notice tone="warn" title="Znaleziono dane, które nie powinny trafić do modelu">
                    Najczęściej to nazwisko innej osoby wpisane w przykładzie zachowania. Pseudonimizacja obejmuje dane ocenianego;
                    w opisach używaj ról (np. „koleżanka z zespołu”) zamiast nazwisk.
                  </Notice>
                )}
                <div className="grid gap-6 md:grid-cols-2">
                  <div><h3 className="font-bold">Wysyłane</h3>
                    <ul className="mt-1 list-disc pl-5 text-[15px]">{d.sent.map((s) => <li key={s}>{s}</li>)}</ul></div>
                  <div><h3 className="font-bold">Nigdy nie jest wysyłane</h3>
                    <ul className="mt-1 list-disc pl-5 text-[15px]">{d.not_sent.map((s) => <li key={s}>{s}</li>)}</ul></div>
                </div>
              </div>
            )}
          </Section>

          {d.calls.map((c, i) => (
            <Section key={i} title={`Zapytanie do modelu: ${d.feature_label}`}
              description={c.method === 'structured' ? 'Odpowiedź ustrukturyzowana, walidowana schematem.' : 'Odpowiedź na podstawie dokumentów, z cytowaniem źródeł.'}>
              <div className="space-y-6">
                <div>
                  <h3 className="font-bold">Treść zapytania <Badge tone="ai">słowa wstawione przez pseudonimizację są podświetlone</Badge></h3>
                  <pre className={pre}><Highlighted text={c.prompt} /></pre>
                </div>
                {c.documents.length > 0 && (
                  <div>
                    <h3 className="font-bold">Źródła przekazane modelowi ({c.documents.length})</h3>
                    {c.documents.map((doc, j) => (
                      <details key={j} className="mt-2"><summary className="cursor-pointer">{doc.title}</summary>
                        <pre className={pre}><Highlighted text={doc.text} /></pre></details>
                    ))}
                  </div>
                )}
                {c.history.length > 0 && (
                  <details><summary className="cursor-pointer font-bold">Historia rozmowy ({c.history.length})</summary>
                    <pre className={pre}>{c.history.map((h) => `${h.role}: ${h.content}`).join('\n\n')}</pre></details>
                )}
                <details><summary className="cursor-pointer font-bold">Instrukcje systemowe ({c.system.length})</summary>
                  {c.system.map((s, j) => <pre key={j} className={pre}>{s}</pre>)}</details>
                {c.response_schema && (
                  <div>
                    <h3 className="font-bold">Pola, które model może zwrócić</h3>
                    <p className="mt-1 text-[15px]">{schemaFields(c.response_schema).join(', ')}</p>
                    <p className="mt-1 text-sm text-ink-soft">Schemat nie zawiera pól z oceną punktową, poziomem kompetencji ani wynikiem oceny — te ustala przełożony.</p>
                  </div>
                )}
              </div>
            </Section>
          ))}
        </>
      )}
    </div>
  )
}
