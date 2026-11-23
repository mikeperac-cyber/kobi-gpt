import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type RfqAlert = { id: string; company: string; leadId: string | null }
type Since = { now: string; items: { id: string; type: string; params: { company?: string }; lead_id: string | null }[] }

const POLL_MS = 5000
const SHOW_MS = 10000

/** Polls the server for new quote requests; raises toasts and a `kobi:rfq` window event for pages to reload. */
export function useRfqAlerts(enabled: boolean) {
  const [alerts, setAlerts] = useState<RfqAlert[]>([])
  const dismiss = useCallback((id: string) => setAlerts((a) => a.filter((x) => x.id !== id)), [])

  useEffect(() => {
    if (!enabled) return
    let after: string | null = null // always the server's own `now`: the laptop clock never matters
    const seen = new Set<string>() // the server window overlaps on purpose; show each notification once
    let timer = 0
    let stopped = false
    const poll = async () => {
      window.clearTimeout(timer)
      if (stopped) return
      if (!document.hidden) {
        try {
          const r = await api<Since>(`/api/notifications/since${after ? `?after=${encodeURIComponent(after)}` : ''}`)
          if (stopped) return
          after = r.now
          const fresh = r.items.filter((i) => i.type === 'rfq' && !seen.has(i.id))
          fresh.forEach((i) => seen.add(i.id))
          if (fresh.length) {
            setAlerts((a) => [...a, ...fresh.map((i) => ({ id: i.id, company: i.params.company ?? '', leadId: i.lead_id }))])
            fresh.forEach((i) => window.setTimeout(() => dismiss(i.id), SHOW_MS))
            window.dispatchEvent(new Event('kobi:rfq'))
          }
        } catch { /* offline or logged out: keep the last `now` and try again */ }
      }
      timer = window.setTimeout(poll, POLL_MS)
    }
    const onVisible = () => { if (!document.hidden) void poll() }
    document.addEventListener('visibilitychange', onVisible)
    void poll()
    return () => { stopped = true; window.clearTimeout(timer); document.removeEventListener('visibilitychange', onVisible) }
  }, [enabled, dismiss])

  return { alerts, dismiss }
}

/** Reload a page's data whenever a new quote request arrives. */
export function useOnRfq(reload: () => void) {
  useEffect(() => {
    window.addEventListener('kobi:rfq', reload)
    return () => window.removeEventListener('kobi:rfq', reload)
  }, [reload])
}
