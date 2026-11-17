import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { SCRIPT, fmt } from '../demo/script'
import type { StepView } from './AgentSteps'

type Ctx = { open: boolean; steps: StepView[]; report(s: StepView[]): void }
const DemoGuideContext = createContext<Ctx>({ open: false, steps: [], report: () => {} })
export const useDemoGuide = () => useContext(DemoGuideContext)

const KEY = 'demoGuideStep'
const readStep = () => { try { return Math.min(Math.max(Number(sessionStorage.getItem(KEY)) || 0, 0), SCRIPT.length - 1) } catch { return 0 } }

export function DemoGuideProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [steps, setSteps] = useState<StepView[]>([])
  const last = useRef('')
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') { e.preventDefault(); setOpen((o) => !o) }
      else if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])
  const report = useCallback((s: StepView[]) => {
    const sig = JSON.stringify(s.map((x) => [x.key, x.status, x.source]))
    if (sig === last.current || s.every((x) => x.status === 'waiting')) return
    last.current = sig
    setSteps(s)
  }, [])
  return (
    <DemoGuideContext.Provider value={{ open, steps, report }}>
      {children}
      {open && <Panel onClose={() => setOpen(false)} />}
    </DemoGuideContext.Provider>
  )
}

function Panel({ onClose }: { onClose(): void }) {
  const { t } = useTranslation()
  const { steps } = useDemoGuide()
  const [idx, setIdx] = useState(readStep)
  const [min, setMin] = useState(false)
  const [secs, setSecs] = useState(0)
  const [run, setRun] = useState(false)
  useEffect(() => {
    if (!run) return
    const id = window.setInterval(() => setSecs((s) => s + 1), 1000)
    return () => window.clearInterval(id)
  }, [run])
  const go = (n: number) => {
    setIdx(n)
    try { sessionStorage.setItem(KEY, String(n)) } catch { /* private mode */ }
  }
  const color = secs > 210 ? 'text-red-700' : secs > 180 ? 'text-amber-600' : 'text-navy'
  const fb = steps.filter((s) => s.status === 'fallback')
  const btn = 'min-h-11 min-w-11 px-3 rounded-md border border-slate-300 bg-white font-semibold text-navy disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-navy'
  const cur = SCRIPT[idx]
  return (
    <aside role="complementary" aria-label={t('demo.guide.title')} className="fixed bottom-2 right-2 z-50 w-[min(20rem,calc(100vw-1rem))] bg-white border border-slate-300 rounded-lg shadow-lg p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">{t('demo.guide.title')}</h2>
        <div className="flex gap-1">
          <button className={btn} aria-expanded={!min} onClick={() => setMin(!min)}>{min ? t('demo.guide.expand') : t('demo.guide.collapse')}</button>
          <button className={btn} onClick={onClose} aria-label={t('demo.guide.close')}>×</button>
        </div>
      </div>
      <p className={`mt-2 text-2xl font-mono font-bold ${color}`} aria-label={t('demo.guide.stopwatch')}>{fmt(secs)}</p>
      {!min && (
        <>
          <div className="flex gap-1 mt-1">
            <button className={btn} onClick={() => setRun(!run)}>{run ? t('demo.guide.pause') : t('demo.guide.start')}</button>
            <button className={btn} onClick={() => { setRun(false); setSecs(0) }}>{t('demo.guide.reset')}</button>
          </div>
          <div className="mt-3 border-t border-slate-200 pt-2">
            <p className="text-xs text-slate-500">{t('demo.guide.stepOf', { n: idx + 1, total: SCRIPT.length })} · {fmt(cur.at)}</p>
            <p className="font-semibold">{t(`demo.guide.steps.${cur.key}`)}</p>
            <div className="flex gap-1 mt-2">
              <button className={btn} disabled={idx === 0} onClick={() => go(idx - 1)}>{t('demo.guide.prev')}</button>
              <button className={btn} disabled={idx === SCRIPT.length - 1} onClick={() => go(idx + 1)}>{t('demo.guide.next')}</button>
            </div>
          </div>
          {fb.length > 0 && (
            <div className="mt-3 border-t border-slate-200 pt-2">
              <p className="text-xs text-slate-500">{t('demo.guide.fallbacks')}</p>
              <ul>{fb.map((s) => <li key={s.key}>{s.key}: {t(`demo.guide.source.${s.source ?? 'template'}`)}</li>)}</ul>
            </div>
          )}
        </>
      )}
    </aside>
  )
}
