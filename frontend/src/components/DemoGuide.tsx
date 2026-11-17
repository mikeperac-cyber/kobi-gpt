import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { SCRIPT, fmt } from '../demo/script'
import type { StepView } from './AgentSteps'

type Watch = { acc: number; start: number | null }
type Ctx = { open: boolean; steps: StepView[]; report(s: StepView[]): void; watch: Watch; setWatch(w: Watch): void }
const DemoGuideContext = createContext<Ctx>({ open: false, steps: [], report: () => {}, watch: { acc: 0, start: null }, setWatch: () => {} })
export const useDemoGuide = () => useContext(DemoGuideContext)

const WKEY = 'demoGuideWatch'
const readWatch = (): Watch => { try { const w = JSON.parse(sessionStorage.getItem(WKEY) ?? ''); return { acc: Number(w.acc) || 0, start: w.start ? Number(w.start) : null } } catch { return { acc: 0, start: null } } }
const KEY = 'demoGuideStep'
const readStep = () => { try { return Math.min(Math.max(Number(sessionStorage.getItem(KEY)) || 0, 0), SCRIPT.length - 1) } catch { return 0 } }

export function DemoGuideProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [steps, setSteps] = useState<StepView[]>([])
  const [watch, setWatchState] = useState(readWatch)
  const setWatch = useCallback((w: Watch) => {
    setWatchState(w)
    try { sessionStorage.setItem(WKEY, JSON.stringify(w)) } catch { /* private mode */ }
  }, [])
  const last = useRef('')
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') { e.preventDefault(); setOpen((o) => !o) }
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
    <DemoGuideContext.Provider value={{ open, steps, report, watch, setWatch }}>
      {children}
      {open && <Panel onClose={() => setOpen(false)} />}
    </DemoGuideContext.Provider>
  )
}

function Panel({ onClose }: { onClose(): void }) {
  const { t } = useTranslation()
  const { steps, watch, setWatch } = useDemoGuide()
  const [idx, setIdx] = useState(readStep)
  const [min, setMin] = useState(false)
  const [, tick] = useState(0)
  const run = watch.start !== null
  useEffect(() => {
    if (!run) return
    const id = window.setInterval(() => tick((n) => n + 1), 1000)
    return () => window.clearInterval(id)
  }, [run])
  const secs = Math.floor((watch.acc + (watch.start !== null ? Date.now() - watch.start : 0)) / 1000)
  const go = (n: number) => {
    setIdx(n)
    try { sessionStorage.setItem(KEY, String(n)) } catch { /* private mode */ }
  }
  const color = secs > 210 ? 'text-red-700' : secs > 180 ? 'text-amber-600' : 'text-navy'
  const fb = steps.filter((s) => s.status === 'fallback')
  const btn = 'min-h-11 min-w-11 px-3 rounded-md border border-slate-300 bg-white font-semibold text-navy disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-navy'
  const cur = SCRIPT[idx]
  return (
    <aside onKeyDown={(e) => { if (e.key === 'Escape') onClose() }} aria-label={t('demo.guide.title')} className="fixed bottom-2 right-2 z-50 w-[min(20rem,calc(100vw-1rem))] bg-white border border-slate-300 rounded-lg shadow-lg p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">{t('demo.guide.title')}</h2>
        <div className="flex gap-1">
          <button className={btn} aria-expanded={!min} onClick={() => setMin(!min)}>{min ? t('demo.guide.expand') : t('demo.guide.collapse')}</button>
          <button className={btn} onClick={onClose} aria-label={t('demo.guide.close')}>×</button>
        </div>
      </div>
      <p role="timer" className={`mt-2 text-2xl font-mono font-bold ${color}`} aria-label={t('demo.guide.stopwatch')}>{fmt(secs)}</p>
      {!min && (
        <>
          <div className="flex gap-1 mt-1">
            <button className={btn} onClick={() => setWatch(run ? { acc: watch.acc + Date.now() - (watch.start ?? 0), start: null } : { acc: watch.acc, start: Date.now() })}>{run ? t('demo.guide.pause') : t('demo.guide.start')}</button>
            <button className={btn} onClick={() => setWatch({ acc: 0, start: null })}>{t('demo.guide.reset')}</button>
          </div>
          <div className="mt-3 border-t border-slate-200 pt-2">
            <p className="text-xs text-slate-600">{t('demo.guide.stepOf', { n: idx + 1, total: SCRIPT.length })} · {fmt(cur.at)}</p>
            <p className="font-semibold">{t(`demo.guide.steps.${cur.key}`)}</p>
            <div className="flex gap-1 mt-2">
              <button className={btn} disabled={idx === 0} onClick={() => go(idx - 1)}>{t('demo.guide.prev')}</button>
              <button className={btn} disabled={idx === SCRIPT.length - 1} onClick={() => go(idx + 1)}>{t('demo.guide.next')}</button>
            </div>
          </div>
          {fb.length > 0 && (
            <div className="mt-3 border-t border-slate-200 pt-2">
              <p className="text-xs text-slate-600">{t('demo.guide.fallbacks')}</p>
              <ul>{fb.map((s) => <li key={s.key}>{t(`agent.steps.${s.key}.label`, { defaultValue: s.key })}: {t(`demo.guide.source.${s.source ?? 'template'}`)}</li>)}</ul>
            </div>
          )}
        </>
      )}
    </aside>
  )
}
