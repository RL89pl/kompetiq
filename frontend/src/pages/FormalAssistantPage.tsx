import { useAssistantStatus } from '../api/hooks'
import { AssistantChat } from '../components/AssistantChat'
import { PageHeader } from '../components/ui'

const KINDS: Record<string, string> = { ACT: 'ustawa', REGULATION: 'rozporządzenia', GUIDE: 'poradniki KPRM', MODEL: 'model kompetencji', FAQ: 'pytania i odpowiedzi' }

export function FormalAssistantPage() {
  const s = useAssistantStatus()
  const k = s.data?.knowledge
  return (
    <div>
      <PageHeader title="Asystent formalny" lead="Rozmowa o procedurze pierwszej i okresowej oceny: terminy, kryteria, arkusze, obowiązki przełożonego. Każda odpowiedź wskazuje źródło." />
      {k && (
        <p className="mb-6 text-sm text-ink-soft">
          Baza wiedzy: {Object.entries(KINDS).map(([key, label]) => `${label} (${k[key] ?? 0})`).join(', ')}.
          {!k.ACT && ' Ustawa o służbie cywilnej nie została jeszcze dodana.'}
        </p>
      )}
      <AssistantChat mode="FORMAL" />
    </div>
  )
}
