import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Card from '../../components/ui/Card'
import { formatDate } from '../../i18n/format'

export type Notif = { id: string; type: string; message_key: string; params: Record<string, string>; read: boolean; created_at: string | null }

export default function Notifications({ items, onRead }: { items: Notif[]; onRead: (id: string) => void }) {
  const { t, i18n } = useTranslation()
  return (
    <Card>
      <h2 className="font-semibold mb-2">{t('dashboard.notif.title')}</h2>
      {items.length === 0 ? <div className="space-y-2"><p className="text-sm text-slate-600">{t('dashboard.notif.empty')}</p><Link to="/leads" className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold bg-brand text-white">{t('dashboard.leads.find')}</Link></div> : (
        <ul className="divide-y divide-slate-100">
          {items.map((n) => (
            <li key={n.id}>
              <button type="button" onClick={() => !n.read && onRead(n.id)} className="w-full min-h-11 py-2 text-left flex items-start gap-2">
                <span aria-hidden className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? 'bg-transparent' : 'bg-brand'}`} />
                <span className={`flex-1 text-sm ${n.read ? 'text-slate-600' : 'font-semibold'}`}>
                  {i18n.exists(n.message_key) ? t(n.message_key, n.params) : t('dashboard.notif.unknown')}
                </span>
                {n.created_at && <span className="text-xs text-slate-600">{formatDate(n.created_at)}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
