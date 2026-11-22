export class ApiError extends Error {
  status: number
  errors: string[]
  data: unknown
  constructor(status: number, message: string, errors: string[] = [], data: unknown = null) {
    super(message)
    this.status = status
    this.errors = errors
    this.data = data
  }
}

function csrfToken(): string {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

function flattenErrors(data: unknown): string[] {
  if (!data || typeof data !== 'object') return []
  const d = data as Record<string, unknown>
  if (Array.isArray(d.errors)) return d.errors as string[]
  if (Array.isArray(data)) return (data as unknown[]).map(String)
  const out: string[] = []
  for (const [k, v] of Object.entries(d)) {
    if (k === 'detail') continue
    out.push(...(Array.isArray(v) ? v.map((x) => String(x)) : [String(v)]))
  }
  return out
}

/** Limit zapytań dostawcy modelu (np. darmowy plan Groq): stan dla komunikatu z odliczaniem w interfejsie. */
export interface RateLimitState { plan: string; until: number; attempt: number; max: number }
type Listener = (s: RateLimitState | null) => void
const rateListeners = new Set<Listener>()
export function onRateLimit(fn: Listener) { rateListeners.add(fn); return () => { rateListeners.delete(fn) } }
const emitRate = (s: RateLimitState | null) => rateListeners.forEach((f) => f(s))
const MAX_RATE_RETRIES = 3

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  for (let attempt = 1; ; attempt++) {
    try {
      const out = await request<T>(path, opts)
      if (attempt > 1) emitRate(null)
      return out
    } catch (e) {
      const d = e instanceof ApiError ? (e.data as { code?: string; retry_after?: number; plan?: string } | null) : null
      if (!(e instanceof ApiError) || e.status !== 429 || d?.code !== 'llm_rate_limit') {
        if (attempt > 1) emitRate(null)
        throw e
      }
      if (attempt > MAX_RATE_RETRIES) {
        emitRate(null)
        throw new ApiError(429, `Limit zapytań${d.plan ? ` (${d.plan})` : ''} nadal obowiązuje mimo ${MAX_RATE_RETRIES} ponowień. `
          + 'Odczekaj około minuty i spróbuj ponownie.', [], e.data)
      }
      // Serwer nie czeka po cichu: zwraca czas oczekiwania, a przeglądarka informuje użytkownika i sama ponawia.
      const wait = Math.min(120, Math.max(1, d.retry_after ?? 20)) * 1000
      emitRate({ plan: d.plan ?? '', until: Date.now() + wait, attempt, max: MAX_RATE_RETRIES })
      await new Promise((r) => setTimeout(r, wait))
    }
  }
}

async function request<T>(path: string, opts: { method?: string; body?: unknown }): Promise<T> {
  const method = opts.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json'
    headers['X-CSRFToken'] = csrfToken()
  }
  const res = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  })
  if (res.status === 204) return undefined as T
  const isJson = res.headers.get('content-type')?.includes('json')
  const data = isJson ? await res.json() : null
  if (!res.ok) {
    const d = (data ?? {}) as { detail?: string }
    const errors = flattenErrors(data)
    throw new ApiError(res.status, d.detail ?? errors[0] ?? `Błąd ${res.status}`, errors, data)
  }
  return data as T
}

export const ensureCsrf = () => api('/auth/csrf/')

/** Wysyłka pliku (multipart) z tokenem CSRF. */
export async function upload<T = unknown>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    method: 'POST', body: form, credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken() },
  })
  const data = res.headers.get('content-type')?.includes('json') ? await res.json() : null
  if (!res.ok) {
    const d = (data ?? {}) as { detail?: string }
    const errors = flattenErrors(data)
    throw new ApiError(res.status, d.detail ?? errors[0] ?? `Błąd ${res.status}`, errors, data)
  }
  return data as T
}

export function downloadUrl(path: string) {
  return `/api/v1${path}`
}
