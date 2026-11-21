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

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
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
