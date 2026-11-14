import { useTranslation } from 'react-i18next'
import { formatDate } from '../i18n/format'

export default function VerifiedBadge({ verified, lastVerified }: { verified: boolean; lastVerified?: string | null }) {
  const { t } = useTranslation()
  const ok = verified && !!lastVerified
  return (
    <span className={`inline-block rounded-full text-xs font-semibold px-2.5 py-1 ${ok ? 'bg-green-100 text-green-900' : 'bg-slate-200 text-slate-800'}`}>
      {ok ? t('adminKb.verified', { date: formatDate(lastVerified!) }) : t('adminKb.notVerified')}
    </span>
  )
}
