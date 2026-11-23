import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '../../components/ui/Button'
import QrPresenter from '../../components/QrPresenter'

export default function PublishSuccess({ slug, onBack }: { slug: string; onBack(): void }) {
  const { t } = useTranslation()
  const h1 = useRef<HTMLHeadingElement>(null)
  useEffect(() => { h1.current?.focus() }, [])
  const [toast, setToast] = useState('')
  const [ts] = useState(() => Date.now())
  const url = `${window.location.origin}/s/${slug}`

  const share = async () => {
    try {
      if (navigator.share) { await navigator.share({ url, title: slug }); return }
      await navigator.clipboard.writeText(url)
      setToast(t('storefront.copied'))
    } catch (x) {
      if ((x as Error).name !== 'AbortError') setToast(url) // clipboard blocked: show the link to copy by hand
    }
  }

  return (
    <div className="max-w-md mx-auto text-center space-y-4">
      <h1 ref={h1} tabIndex={-1} className="text-2xl font-bold outline-none">{t('storefront.successTitle')}</h1>
      <p className="text-slate-600">{t('storefront.successHelp')}</p>
      <a href={url} target="_blank" rel="noreferrer" className="block font-semibold text-brand break-all underline">{url}</a>
      <img src={`/api/storefronts/mine/qr.png?ts=${ts}`} alt={t('storefront.qrAlt')} className="mx-auto w-56 h-56 border border-slate-200 rounded-md bg-white" />
      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={() => void share()}>{t('storefront.share')}</Button>
        <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center min-h-11 px-4 rounded-md font-semibold border border-slate-300 bg-white">{t('storefront.open')}</a>
        <QrPresenter />
        <Button variant="secondary" onClick={onBack}>{t('storefront.backToEditor')}</Button>
      </div>
      {toast && <p role="status" className="text-sm text-slate-700">{toast}</p>}
    </div>
  )
}
