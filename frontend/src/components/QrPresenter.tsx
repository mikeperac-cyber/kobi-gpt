import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import Button from './ui/Button'
import Modal from './ui/Modal'

/** Big storefront QR for a room: judges scan it from their seats. Warns when the encoded URL is local-only. */
export default function QrPresenter() {
  const { t } = useTranslation()
  const [open, setOpen] = useState<{ url: string | null; ts: number } | null>(null)
  const show = async () => {
    const ts = Date.now()
    setOpen({ url: null, ts })
    try { setOpen({ url: (await api<{ url: string }>('/api/storefronts/mine/qr-url')).url, ts }) } catch { /* QR image still shows */ }
  }
  const local = open?.url ? ['localhost', '127.0.0.1'].includes(new URL(open.url).hostname) : false
  return (
    <>
      <Button variant="secondary" onClick={() => void show()}>{t('qr.show')}</Button>
      {open && (
        <Modal title={t('qr.show')} onClose={() => setOpen(null)}>
          <div className="text-center space-y-3">
            {local && <p role="alert" className="text-brand font-semibold">{t('qr.localWarning')}</p>}
            <img src={`/api/storefronts/mine/qr.png?ts=${open.ts}`} alt={t('storefront.qrAlt')}
              className="mx-auto w-[min(60vh,80vw)] max-w-full aspect-square bg-white" />
            {open.url && <p className="text-xl sm:text-2xl font-bold break-all">{open.url}</p>}
          </div>
        </Modal>
      )}
    </>
  )
}
