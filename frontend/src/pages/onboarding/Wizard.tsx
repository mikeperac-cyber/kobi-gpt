import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { companyPayload, emptyCompany, serverErrs, type CompanyDraft } from '../../components/CompanyFields'
import { emptyProduct, productPayload, type ProductDraft } from '../../components/ProductForm'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import StepCompany from './StepCompany'
import StepMarket from './StepMarket'
import StepProduct from './StepProduct'

export default function Wizard() {
  const { t } = useTranslation()
  const { user, refresh } = useAuth()
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [company, setCompany] = useState<CompanyDraft>(emptyCompany)
  const [product, setProduct] = useState<ProductDraft>(emptyProduct)
  const [cErrs, setCErrs] = useState<Record<string, string>>({})
  const [pErrs, setPErrs] = useState<Record<string, string>>({})
  const [top, setTop] = useState('')
  const [busy, setBusy] = useState(false)
  if (user?.has_company && !busy) return <Navigate to="/" replace />

  const go = (n: number) => { setStep(n); setTop(''); window.scrollTo(0, 0) }
  const next = () => {
    if (step === 0) {
      const { errs } = companyPayload(company)
      setCErrs(errs)
      if (!Object.keys(errs).length) go(1)
    } else {
      const { errs } = productPayload(product, 'onboarding')
      setPErrs(errs)
      if (!Object.keys(errs).length) go(2)
    }
  }
  const submit = async () => {
    const c = companyPayload(company)
    const p = productPayload(product, 'onboarding')
    if (Object.keys(c.errs).length) { setCErrs(c.errs); return go(0) }
    if (Object.keys(p.errs).length) { setPErrs(p.errs); return go(1) }
    setBusy(true)
    setTop('')
    try {
      await api('/api/onboarding', { method: 'POST', json: { company: c.payload, product: p.payload, market: { country_code: 'DE' } } })
      await refresh()
      nav('/', { replace: true })
    } catch (x) {
      setBusy(false)
      if (x instanceof ApiError && x.code === 'company_exists') { await refresh(); return nav('/', { replace: true }) }
      const ce = serverErrs(x, 'company.'), pe = serverErrs(x, 'product.')
      setCErrs(ce.fields)
      setPErrs(pe.fields)
      if (Object.keys(ce.fields).length) return go(0)
      if (Object.keys(pe.fields).length) return go(1)
      setTop(ce.top || pe.top || 'errors.generic')
    }
  }

  return (
    <Card className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold">{t('onboarding.title')}</h1>
      <p className="text-sm font-semibold mt-2" aria-live="polite">{t('onboarding.stepOf', { n: step + 1, total: 3 })}</p>
      <div className="h-2 bg-slate-200 rounded-full mt-1 mb-5" role="progressbar" aria-valuemin={1} aria-valuemax={3} aria-valuenow={step + 1}>
        <div className="h-2 bg-brand rounded-full transition-all" style={{ width: `${((step + 1) / 3) * 100}%` }} />
      </div>
      {step === 0 && <StepCompany value={company} onChange={(v) => { setCompany(v); setCErrs({}) }} errs={cErrs} />}
      {step === 1 && <StepProduct value={product} onChange={(v) => { setProduct(v); setPErrs({}) }} errs={pErrs} />}
      {step === 2 && <StepMarket />}
      {top && <p role="alert" className="text-brand font-semibold mt-4">{t(top)}</p>}
      <div className="flex gap-3 mt-6">
        {step > 0 && <Button type="button" variant="secondary" disabled={busy} onClick={() => go(step - 1)}>{t('onboarding.back')}</Button>}
        {step < 2
          ? <Button type="button" className="flex-1" onClick={next}>{t('onboarding.next')}</Button>
          : <Button type="button" className="flex-1" disabled={busy} onClick={() => void submit()}>{busy ? t('onboarding.creating') : t('onboarding.finish')}</Button>}
      </div>
    </Card>
  )
}
