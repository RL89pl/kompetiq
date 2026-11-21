import { useId, type ButtonHTMLAttributes, type ReactNode, type InputHTMLAttributes, type TextareaHTMLAttributes, type SelectHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'ai'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-ink text-white hover:bg-[#25365a] disabled:bg-ink-soft',
  secondary: 'bg-white text-ink border border-rule-strong hover:border-ink',
  ghost: 'text-ink hover:bg-rule/60',
  danger: 'bg-white text-bad border border-bad/40 hover:bg-bad-tint',
  ai: 'bg-ai-tint text-ai border border-dashed border-ai hover:bg-[#d5ece8]',
}

export function Button({ variant = 'primary', busy, children, className = '', ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex items-center gap-2 rounded-md px-3.5 py-2 text-[15px] font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
    >
      {busy && <Spinner />}
      {children}
    </button>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span role={label ? 'status' : undefined} className="inline-flex items-center gap-2">
      <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
      {label && <span>{label}</span>}
    </span>
  )
}

export function Field({ label, hint, error, children, id }: { label: string; hint?: ReactNode; error?: string; children: (id: string) => ReactNode; id?: string }) {
  const auto = useId()
  const fid = id ?? auto
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={fid} className="text-[15px] font-bold">{label}</label>
      {children(fid)}
      {hint && <p className="text-sm text-ink-soft">{hint}</p>}
      {error && <p className="text-sm text-bad">{error}</p>}
    </div>
  )
}

const inputCls = 'w-full rounded-md border border-rule-strong bg-white px-3 py-2 text-[15px] placeholder:text-ink-soft/70 focus:border-ink'

export const Input = (p: InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={`${inputCls} ${p.className ?? ''}`} />
export const Textarea = (p: TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea rows={4} {...p} className={`${inputCls} leading-relaxed ${p.className ?? ''}`} />
export const Select = (p: SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} className={`${inputCls} ${p.className ?? ''}`} />

export function Notice({ tone = 'info', title, children }: { tone?: 'info' | 'ok' | 'warn' | 'bad'; title?: string; children?: ReactNode }) {
  const map = {
    info: 'border-rule-strong bg-white',
    ok: 'border-ok/40 bg-ok-tint',
    warn: 'border-warn/40 bg-warn-tint',
    bad: 'border-bad/40 bg-bad-tint',
  }
  return (
    <div role={tone === 'bad' ? 'alert' : undefined} className={`rounded-md border-l-4 px-4 py-3 ${map[tone]}`}>
      {title && <p className="font-bold">{title}</p>}
      {children && <div className="text-[15px]">{children}</div>}
    </div>
  )
}

export function ErrorList({ error }: { error: unknown }) {
  if (!error) return null
  const e = error as { message?: string; errors?: string[] }
  return (
    <Notice tone="bad" title={e.message ?? 'Wystąpił błąd.'}>
      {e.errors && e.errors.length > 0 && (
        <ul className="mt-1 list-disc pl-5">{e.errors.map((x, i) => <li key={i}>{x}</li>)}</ul>
      )}
    </Notice>
  )
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'first' | 'periodic' | 'ok' | 'warn' | 'bad' | 'ai' }) {
  const map = {
    neutral: 'bg-rule/70 text-ink',
    first: 'bg-first-tint text-first',
    periodic: 'bg-periodic-tint text-periodic',
    ok: 'bg-ok-tint text-ok',
    warn: 'bg-warn-tint text-warn',
    bad: 'bg-bad-tint text-bad',
    ai: 'bg-ai-tint text-ai',
  }
  return <span className={`inline-flex items-center rounded px-2 py-0.5 text-[13px] font-bold ${map[tone]}`}>{children}</span>
}

export function Section({ title, description, actions, children }: { title: string; description?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-t border-rule pt-6 first:border-t-0 first:pt-0">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-[68ch]">
          <h2 className="text-xl">{title}</h2>
          {description && <div className="mt-1 text-[15px] text-ink-soft">{description}</div>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  )
}

export function PageHeader({ title, lead, children }: { title: string; lead?: ReactNode; children?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-[70ch]">
        <h1 className="text-[2rem]">{title}</h1>
        {lead && <p className="mt-2 text-ink-soft">{lead}</p>}
      </div>
      {children}
    </header>
  )
}

export function Loading() {
  return <div className="py-16 text-center text-ink-soft"><Spinner label="Wczytywanie…" /></div>
}
