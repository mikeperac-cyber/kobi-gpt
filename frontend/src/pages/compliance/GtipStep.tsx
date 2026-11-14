import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import NoMatch from './NoMatch'
import type { Candidate } from './types'

export default function GtipStep({ candidates, busy, onConfirm, onBack }: {
  candidates: Candidate[]; busy: boolean; onConfirm(code: string): void; onBack(): void
}) {
  const { t } = useTranslation()
  const [code, setCode] = useState('')
  return (
    <form className="space-y-4 max-w-3xl" onSubmit={(e) => { e.preventDefault(); if (code) onConfirm(code) }}>
      <h2 className="text-xl font-bold">{t('compliance.gtipTitle')}</h2>
      <p className="text-slate-600">{t('compliance.gtipHelp')}</p>
      <p role="note" className="rounded-md bg-amber-50 border border-amber-200 p-3 font-semibold">{t('compliance.gtipWarning')}</p>
      <a href="https://ticaret.gov.tr" target="_blank" rel="noopener noreferrer" className="underline text-navy">{t('compliance.tariffLink')}</a>
      {candidates.length === 0 ? <NoMatch /> : (
        <fieldset className="space-y-3">
          <legend className="sr-only">{t('compliance.gtipTitle')}</legend>
          {candidates.map((c) => (
            <Card key={c.code} className={code === c.code ? 'border-navy border-2' : ''}>
              <label className="flex gap-3 cursor-pointer items-start">
                <input type="radio" name="gtip" className="mt-1 w-5 h-5" value={c.code} checked={code === c.code} onChange={() => setCode(c.code)} />
                <span className="space-y-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <b className="text-lg">{c.code}</b>
                    <Badge>{t('compliance.confidenceLabel')}: {t(`compliance.confidence.${c.confidence}`)}</Badge>
                    {c.in_kb && <Badge className="bg-green-100 text-green-900">{t('compliance.inKb')}</Badge>}
                  </span>
                  <span className="block">{c.description}</span>
                  <span className="block text-sm text-slate-600"><b>{t('compliance.reasoning')}: </b>{c.reasoning}</span>
                </span>
              </label>
            </Card>
          ))}
        </fieldset>
      )}
      {candidates.length > 0 && !code && <p className="text-sm text-slate-600">{t('compliance.pickOne')}</p>}
      <div className="flex gap-3">
        <Button type="button" variant="secondary" onClick={onBack}>{t('compliance.back')}</Button>
        {candidates.length > 0 && <Button type="submit" disabled={!code || busy}>{t('compliance.confirm')}</Button>}
      </div>
    </form>
  )
}
