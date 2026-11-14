import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import AgentSteps from '../../components/AgentSteps'
import Button from '../../components/ui/Button'
import Field from '../../components/ui/Field'
import Select from '../../components/ui/Select'
import { useJob } from '../../hooks/useJob'
import ComplianceStart, { type ProductOpt } from './ComplianceStart'
import GtipStep from './GtipStep'
import ReportPage from './ReportPage'
import type { Classification, Params, Report } from './types'

type Stage =
  | { k: 'loading' }
  | { k: 'start' }
  | { k: 'job'; kind: 'gtip' | 'check'; id: string }
  | { k: 'gtip'; c: Classification }
  | { k: 'report'; r: Report }

export default function CompliancePage() {
  const { t } = useTranslation()
  const [products, setProducts] = useState<ProductOpt[]>([])
  const [sector, setSector] = useState('')
  const [productId, setProductId] = useState('')
  const [params, setParams] = useState<Params>({ channel: 'b2b', structural: false, processing: null })
  const [stage, setStage] = useState<Stage>({ k: 'loading' })
  const [hasReport, setHasReport] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const isFood = sector === 'gida'
  const fail = (x: unknown) => setErr(x instanceof ApiError ? x.messageKey : 'errors.network')

  // show the latest report for the product instead of forcing a re-run
  const select = useCallback(async (id: string) => {
    setProductId(id)
    setErr('')
    if (!id) return setStage({ k: 'start' })
    try {
      const r = await api<Report>(`/api/compliance/reports/latest?product_id=${id}`)
      setHasReport(true)
      setStage({ k: 'report', r })
    } catch {
      setHasReport(false)
      setStage({ k: 'start' })
    }
  }, [])

  useEffect(() => {
    Promise.all([api<ProductOpt[]>('/api/products'), api<{ sector: string }>('/api/company')])
      .then(([p, c]) => { setProducts(p); setSector(c.sector); void select(p[0]?.id ?? '') })
      .catch((x) => { fail(x); setStage({ k: 'start' }) })
  }, [select])

  const post = async (kind: 'gtip' | 'check', json: unknown) => {
    setBusy(true)
    setErr('')
    try {
      const r = await api<{ job_id: string }>(`/api/compliance/${kind}`, { method: 'POST', json })
      setStage({ k: 'job', kind, id: r.job_id })
    } catch (x) { fail(x) }
    setBusy(false)
  }
  const startGtip = () => post('gtip', { product_id: productId, processing: isFood ? params.processing : 'na' })
  const confirm = async (code: string) => {
    setBusy(true)
    setErr('')
    try {
      await api('/api/compliance/gtip/confirm', { method: 'POST', json: { product_id: productId, code } })
    } catch (x) { fail(x); setBusy(false); return }
    await post('check', { product_id: productId, channel: params.channel, structural_use: params.structural })
  }

  const { job, done } = useJob(stage.k === 'job' ? stage.id : null)
  useEffect(() => {
    if (stage.k !== 'job' || !done || job?.status !== 'done') return
    const next = stage.kind === 'gtip'
      ? api<Classification>(`/api/compliance/gtip?product_id=${productId}`).then((c): Stage => ({ k: 'gtip', c }))
      : api<Report>(`/api/compliance/reports/latest?product_id=${productId}`).then((r): Stage => { setHasReport(true); return { k: 'report', r } })
    next.then(setStage).catch((x) => { fail(x); setStage({ k: 'start' }) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, job?.status])

  let body
  if (stage.k === 'loading') body = <p>{t('common.loading')}</p>
  else if (stage.k === 'job') {
    const keys = stage.kind === 'gtip' ? ['gtip'] : ['rules', 'incentives', 'next_steps']
    const failed = job?.status === 'error'
    body = (
      <div className="max-w-xl space-y-4">
        <AgentSteps steps={job?.steps ?? keys.map((key) => ({ key, status: 'waiting' as const, elapsed_ms: null }))} failed={failed}
          labels={(k) => t(`agent.steps.${k}.label`)} explain={(k) => t(`agent.steps.${k}.explain`)} />
        {failed && (
          <div className="rounded-md bg-slate-100 p-4 space-y-3" role="status">
            <p>{t('agent.failed')}</p>
            <Button onClick={() => setStage({ k: 'start' })}>{t('agent.retry')}</Button>
          </div>
        )}
      </div>
    )
  } else if (stage.k === 'gtip') {
    body = <GtipStep candidates={stage.c.candidates} busy={busy} onConfirm={(c) => void confirm(c)} onBack={() => setStage({ k: 'start' })} />
  } else if (stage.k === 'report') {
    body = (
      <>
        {products.length > 1 && (
          <div className="max-w-sm mb-4">
            <Field label={t('compliance.product')}>
              <Select value={productId} onChange={(e) => void select(e.target.value)}>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name_tr}</option>)}
              </Select>
            </Field>
          </div>
        )}
        <ReportPage key={stage.r.id} initial={stage.r} onRerun={() => setStage({ k: 'start' })} />
      </>
    )
  } else {
    body = (
      <ComplianceStart products={products} productId={productId} onProduct={(id) => void select(id)} params={params} onParams={setParams}
        isFood={isFood} hasReport={hasReport} busy={busy} onStart={() => void startGtip()} />
    )
  }
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">{t('compliance.title')}</h1>
      {stage.k === 'start' && <p className="text-slate-600 max-w-xl">{t('compliance.intro')}</p>}
      {err && <p role="alert" className="text-brand font-semibold">{t(err)}</p>}
      {body}
    </div>
  )
}
