import { useEffect, useState } from 'react'
import { api } from '../api/client'

export type JobStep = { key: string; status: 'waiting' | 'running' | 'done' | 'fallback'; source?: string | null; elapsed_ms: number | null }
export type Job = { _id: string; status: 'running' | 'done' | 'error'; steps: JobStep[]; result?: Record<string, string> | null }

/** Polls GET /api/jobs/{id} every 700 ms until the job is no longer running; stops on unmount. */
export function useJob(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null)
  useEffect(() => {
    setJob(null)
    if (!jobId) return
    let stop = false
    let timer: number
    const tick = async () => {
      let next: Job | null = null
      try { next = await api<Job>(`/api/jobs/${jobId}`) } catch { /* transient: keep polling */ }
      if (stop) return
      if (next) setJob(next)
      if (!next || next.status === 'running') timer = window.setTimeout(tick, 700)
    }
    void tick()
    return () => { stop = true; window.clearTimeout(timer) }
  }, [jobId])
  return { job, done: !!job && job.status !== 'running' }
}
