import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import ChecklistItem from './ChecklistItem'
import NoMatch from './NoMatch'
import ScoreBadge from './ScoreBadge'
import type { Incentive, Report } from './types'

export default function ReportPage({ initial, onRerun }: { initial: Report; onRerun(): void }) {
  const { t, i18n } = useTranslation()
  const [rep, setRep] = useState(initial)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const tick = async (ruleId: string, done: boolean) => {
    setMsg('')
    const mark = (v: boolean) => setRep((r) => ({ ...r, checklist: r.checklist.map((i) => (i.rule_id === ruleId ? { ...i, done: v } : i)) }))
    mark(done) // optimistic
    try {
      const r = await api<{ score: number }>(`/api/compliance/reports/${rep.id}/items/${ruleId}`, { method: 'PATCH', json: { done } })
      setRep((x) => ({ ...x, score: r.score }))
    } catch {
      mark(!done)
      setMsg(t('compliance.tickFailed'))
    }
  }
  const refresh = async () => {
    setBusy(true)
    try {
      const r = await api<{ next_steps: Report['next_steps'] }>(`/api/compliance/reports/${rep.id}/next-steps`, { method: 'POST' })
      setRep((x) => ({ ...x, next_steps: r.next_steps }))
    } catch { setMsg(t('errors.generic')) }
    setBusy(false)
  }
  const en = i18n.language === 'en'
  const applicable = rep.checklist.filter((i) => i.applies !== false)
  const na = rep.checklist.filter((i) => i.applies === false)
  const inc = (i: Incentive) => (
    <Card key={i.incentive_id} className="space-y-2">
      <h3 className="font-semibold">{en ? i.name_en || i.name_tr : i.name_tr}</h3>
      {i.provider && <p className="text-sm text-slate-600">{i.provider}</p>}
      {i.summary && <p><span className="text-xs font-semibold text-slate-600 block">{t('compliance.officialText')}</span>{i.summary}</p>}
      {i.why && i.why !== i.summary && (
        <p className="rounded-md bg-slate-50 border border-slate-200 p-2 text-sm">
          <span className="text-xs font-semibold text-slate-600 block">{t('compliance.whyEligible')} · {t('compliance.aiExplanation')}</span>{i.why}
        </p>
      )}
      {i.source_url && <a href={i.source_url} target="_blank" rel="noopener noreferrer" className="text-sm underline text-navy break-all">{t('compliance.source')}: {i.source_url}</a>}
    </Card>
  )

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex flex-wrap gap-3 items-center">
        <Button variant="secondary" onClick={onRerun}>{t('compliance.rerun')}</Button>
        <a href={`/api/compliance/reports/${rep.id}/pdf`} className="inline-flex items-center min-h-11 px-4 rounded-md font-semibold bg-brand text-white hover:bg-red-800">{t('compliance.pdf')}</a>
      </div>
      {rep.ui_language && rep.ui_language !== (en ? 'en' : 'tr') && <p className="text-sm text-slate-600" role="note">{t('compliance.langNote')}</p>}
      {rep.no_match ? <NoMatch /> : (
        <>
          <ScoreBadge score={rep.score} />
          {msg && <p role="status" className="rounded-md bg-slate-100 p-3">{msg}</p>}
          {(['TR', 'DEST'] as const).map((side) => {
            const items = applicable.filter((i) => i.side === side)
            return items.length > 0 && (
              <section key={side} className="space-y-3">
                <h2 className="text-xl font-bold">{t(`compliance.side${side}`)}</h2>
                {items.map((i) => <ChecklistItem key={i.rule_id} item={i} onTick={(d) => void tick(i.rule_id, d)} />)}
              </section>
            )
          })}
          {na.length > 0 && (
            <details>
              <summary className="cursor-pointer font-semibold min-h-11">{t('compliance.notApplicable')} ({na.length})</summary>
              <div className="space-y-3 mt-3">{na.map((i) => <ChecklistItem key={i.rule_id} item={i} />)}</div>
            </details>
          )}
          {rep.incentives.length > 0 && (
            <section className="space-y-3"><h2 className="text-xl font-bold">{t('compliance.incentives')}</h2>{rep.incentives.map(inc)}</section>
          )}
          {!!rep.next_steps?.length && (
            <section className="space-y-3">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold">{t('compliance.nextSteps')}</h2>
                <Button variant="secondary" disabled={busy} onClick={() => void refresh()}>{t('compliance.refresh')}</Button>
              </div>
              <ol className="list-decimal pl-5 space-y-1">{rep.next_steps.map((s) => <li key={s.rule_id}>{s.text}</li>)}</ol>
            </section>
          )}
        </>
      )}
    </div>
  )
}
