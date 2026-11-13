export class ApiError extends Error {
  status: number
  code: string
  messageKey: string
  fields: string[]
  constructor(status: number, code: string, messageKey: string, fields: string[] = []) {
    super(code)
    this.status = status
    this.code = code
    this.messageKey = messageKey
    this.fields = fields
  }
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init
  const res = await fetch(path, {
    credentials: 'include',
    ...rest,
    headers: { ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}), ...headers },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  if (!res.ok) {
    let d: { code?: string; message_key?: string; fields?: string[] } = {}
    try {
      d = (await res.json()).detail ?? {}
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, d.code ?? 'unknown', d.message_key ?? 'errors.generic', d.fields)
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}
