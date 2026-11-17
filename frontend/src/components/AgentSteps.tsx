import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDemoGuide } from './DemoGuide'

export type StepView = { key: string; status: 'waiting' | 'running' | 'done' | 'fallback'; elapsed_ms: number | null; source?: string | null }

/** Live agent progress. `failed` stops running spinners (job errored): calm grey, never red. */
export default function AgentSteps({ steps, labels, explain, failed = false }: {
  steps: StepView[]
  labels(key: string): string
  explain(key: string): string
  failed?: boolean
}) {
  const { t } = useTranslation()
  const guide = useDemoGuide()
  const { report } = guide
  useEffect(() => report(steps), [steps, report])
  const [now, setNow] = useState(() => Date.now())
  const began = useRef<Record<string, number>>({})
  const running = steps.some((s) => s.status === 'running') && !failed
  useEffect(() => {
    if (!running) return
    const id = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(id)
  }, [running])
  steps.forEach((s) => { if (s.status === 'running') began.current[s.key] ??= Date.now() })

  return (
    <ol className="space-y-3" aria-live="polite">
      {steps.map((s) => {
        const live = s.status === 'running' && !failed
        const state = s.status === 'running' && !live ? 'waiting' : s.status
        const secs = live ? (now - (began.current[s.key] ?? now)) / 1000 : (s.elapsed_ms ?? 0) / 1000
        return (
          <li key={s.key} className="flex gap-3 items-start" data-state={state}>
            <span className="mt-1 w-5 h-5 shrink-0 flex items-center justify-center" aria-hidden>
              {live ? <span className="w-4 h-4 rounded-full border-2 border-navy border-t-transparent animate-spin" />
                : state === 'done' ? <span className="text-green-700 font-bold">✓</span>
                : state === 'fallback' ? <span className="text-slate-500">↺</span>
                : <span className="w-3 h-3 rounded-full border-2 border-slate-300" />}
            </span>
            <div className="min-w-0">
              <p className={`font-semibold ${state === 'waiting' ? 'text-slate-500' : ''}`}>{labels(s.key)}</p>
              <p className="text-sm text-slate-600">{explain(s.key)}</p>
              <p className="text-xs text-slate-500">
                {t(`agent.state.${live ? 'running' : state}`)}
                {(live || state === 'done' || state === 'fallback') && ` · ${secs.toFixed(1)} s`}
                {guide.open && state === 'fallback' && s.source !== 'llm' && (
                  <span role="img" aria-label={t(`demo.guide.source.${s.source ?? 'template'}`)} className={`ml-2 inline-block w-2 h-2 rounded-full ${s.source === 'cache' ? 'bg-amber-500' : 'bg-slate-400'}`} />
                )}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
