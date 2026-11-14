export class ApiError extends Error {
  status: number
  code: string
  messageKey: string
  fields: string[]
  rows: { row: number }[]
  constructor(status: number, code: string, messageKey: string, fields: string[] = [], rows: { row: number }[] = []) {
    super(code)
    this.rows = rows
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
    let d: { code?: string; message_key?: string; fields?: string[]; rows?: { row: number }[] } = {}
    try {
      d = (await res.json()).detail ?? {}
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, d.code ?? 'unknown', d.message_key ?? 'errors.generic', d.fields, d.rows)
  }
  const text = await res.text() // 201/204 may have an empty body
  return (text ? JSON.parse(text) : undefined) as T
}
