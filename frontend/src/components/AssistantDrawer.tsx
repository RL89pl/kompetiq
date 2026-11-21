import { useEffect, useState } from 'react'
import { AssistantChat } from './AssistantChat'

export function AssistantDrawer({ assessmentId, canUseInterview, open, onClose }: {
  assessmentId: number; canUseInterview: boolean; open: boolean; onClose: () => void
}) {
  const [mode, setMode] = useState<'FORMAL' | 'INTERVIEW'>('FORMAL')
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div role="dialog" aria-modal="false" aria-label="Asystent AI"
      className="fixed inset-y-0 right-0 z-30 flex w-full max-w-[34rem] flex-col border-l border-rule-strong bg-paper shadow-[-8px_0_24px_rgba(23,35,59,0.12)]">
      <div className="flex items-center justify-between border-b border-rule bg-white px-5 py-3">
        <p className="font-serif text-lg font-semibold">Asystent AI</p>
        <button onClick={onClose} className="rounded-md px-2 py-1 hover:bg-rule/60" aria-label="Zamknij asystenta">Zamknij</button>
      </div>
      <div role="tablist" className="flex gap-1 border-b border-rule bg-white px-4 py-2">
        <button role="tab" aria-selected={mode === 'FORMAL'} onClick={() => setMode('FORMAL')}
          className={`rounded-md px-3 py-1.5 text-[15px] ${mode === 'FORMAL' ? 'bg-ink font-bold text-white' : 'hover:bg-rule/60'}`}>Zasady i wymagania</button>
        {canUseInterview && (
          <button role="tab" aria-selected={mode === 'INTERVIEW'} onClick={() => setMode('INTERVIEW')}
            className={`rounded-md px-3 py-1.5 text-[15px] ${mode === 'INTERVIEW' ? 'bg-ink font-bold text-white' : 'hover:bg-rule/60'}`}>Przygotowanie do rozmowy</button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-5">
        {mode === 'FORMAL'
          ? <AssistantChat key="f" mode="FORMAL" assessmentId={canUseInterview ? assessmentId : undefined} compact />
          : <AssistantChat key="i" mode="INTERVIEW" assessmentId={assessmentId} compact />}
      </div>
    </div>
  )
}
