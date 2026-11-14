import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import AgentSteps from '../../components/AgentSteps'
import Button from '../../components/ui/Button'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import { useJob } from '../../hooks/useJob'
import { useSpeech } from '../../hooks/useSpeech'

const KEYS = ['analysis', 'adaptation', 'content', 'theme']
const INCOTERMS = ['EXW', 'FCA', 'FOB', 'CIF', 'DAP']

export default function Intake({ onDone, onCancel }: { onDone(): void; onCancel?(): void }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [text, setText] = useState('')
  const [positioning, setPositioning] = useState<'b2b' | 'b2c'>('b2b')
  const [leadTime, setLeadTime] = useState('')
  const [samplePolicy, setSamplePolicy] = useState('')
  const [incoterms, setIncoterms] = useState<string[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const { job, done } = useJob(jobId)
  const speech = useSpeech(user?.ui_language === 'en' ? 'en-US' : 'tr-TR', (s) => setText((x) => (x ? `${x} ${s}` : s)))

  useEffect(() => { if (done && job?.status === 'done') onDone() }, [done, job, onDone])

  const submit = async () => {
    setBusy(true)
    setErr('')
    try {
      const r = await api<{ job_id: string }>('/api/storefronts/generate', {
        method: 'POST',
        json: { text, positioning, lead_time: leadTime || null, sample_policy: samplePolicy || null, incoterms },
      })
      setJobId(r.job_id)
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
      setBusy(false)
    }
  }

  if (jobId) {
    const failed = job?.status === 'error'
    const steps = job?.steps ?? KEYS.map((key) => ({ key, status: 'waiting' as const, elapsed_ms: null }))
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-2xl font-bold">{t('storefront.generating')}</h1>
        <p className="text-slate-600">{t('storefront.generatingHelp')}</p>
        <AgentSteps steps={steps} failed={failed} labels={(k) => t(`agent.steps.${k}.label`)} explain={(k) => t(`agent.steps.${k}.explain`)} />
        {failed && (
          <div className="rounded-md bg-slate-100 p-4 space-y-3" role="status">
            <p>{t('agent.failed')}</p>
            <Button onClick={() => { setJobId(null); setBusy(false) }}>{t('agent.retry')}</Button>
          </div>
        )}
      </div>
    )
  }

  return (
    <form className="max-w-2xl mx-auto space-y-5" onSubmit={(e) => { e.preventDefault(); void submit() }}>
      <h1 className="text-2xl font-bold">{t('storefront.intakeTitle')}</h1>
      <p className="text-slate-600">{t('storefront.intakeHelp')}</p>
      <Field label={t('storefront.textLabel')}>
        <Textarea rows={6} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} placeholder={t('storefront.textPlaceholder')} />
      </Field>
      {speech.supported && (
        <div className="flex items-center gap-3">
          <Button type="button" variant="secondary" onClick={speech.listening ? speech.stop : speech.start}>
            {speech.listening ? `■ ${t('storefront.micStop')}` : `🎤 ${t('storefront.mic')}`}
          </Button>
          {speech.listening && <span className="text-sm text-slate-600" role="status">{t('storefront.listening')} {speech.transcript}</span>}
        </div>
      )}
      <fieldset className="space-y-2">
        <legend className="text-sm font-semibold">{t('storefront.positioning')}</legend>
        {(['b2b', 'b2c'] as const).map((p) => (
          <label key={p} className="flex items-center gap-2 min-h-11">
            <input type="radio" name="positioning" checked={positioning === p} onChange={() => setPositioning(p)} />
            {t(`storefront.${p}`)}
          </label>
        ))}
      </fieldset>
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label={t('storefront.leadTime')}><Input value={leadTime} maxLength={200} onChange={(e) => setLeadTime(e.target.value)} placeholder={t('storefront.leadTimePh')} /></Field>
        <Field label={t('storefront.samplePolicy')}><Input value={samplePolicy} maxLength={300} onChange={(e) => setSamplePolicy(e.target.value)} placeholder={t('storefront.samplePolicyPh')} /></Field>
      </div>
      <fieldset>
        <legend className="text-sm font-semibold">{t('storefront.incoterms')}</legend>
        <div className="flex flex-wrap gap-x-4">
          {INCOTERMS.map((i) => (
            <label key={i} className="flex items-center gap-2 min-h-11">
              <input type="checkbox" checked={incoterms.includes(i)}
                onChange={(e) => setIncoterms(e.target.checked ? [...incoterms, i] : incoterms.filter((x) => x !== i))} />
              {i}
            </label>
          ))}
        </div>
      </fieldset>
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      <div className="flex gap-3">
        <Button type="submit" disabled={busy || !text.trim()}>{t('storefront.generate')}</Button>
        {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>{t('common.cancel')}</Button>}
      </div>
    </form>
  )
}
