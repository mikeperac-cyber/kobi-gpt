import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { RfqAlert } from '../hooks/useRfqAlerts'

export default function RfqToast({ alerts, onClose }: { alerts: RfqAlert[]; onClose(id: string): void }) {
  const { t } = useTranslation()
  return (
    <div role="status" aria-live="polite" className="fixed bottom-4 right-4 left-4 sm:left-auto z-40 flex flex-col gap-2 sm:w-96">
      {alerts.map((a) => (
        <div key={a.id} className="bg-white border-l-4 border-brand shadow-lg rounded-md p-4 flex items-start gap-3">
          <span aria-hidden className="text-xl">📩</span>
          <div className="flex-1 min-w-0">
            <p className="font-semibold">{t('alerts.newRfq', { company: a.company })}</p>
            <Link to={a.leadId ? `/leads/${a.leadId}` : '/leads'} onClick={() => onClose(a.id)}
              className="inline-flex min-h-11 items-center text-brand font-semibold underline">{t('alerts.open')}</Link>
          </div>
          <button type="button" onClick={() => onClose(a.id)} aria-label={t('alerts.close')}
            className="min-h-11 min-w-11 text-slate-500 hover:text-slate-900">×</button>
        </div>
      ))}
    </div>
  )
}
