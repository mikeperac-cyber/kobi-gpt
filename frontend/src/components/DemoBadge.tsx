import { useTranslation } from 'react-i18next'
import Badge from './ui/Badge'

export default function DemoBadge() {
  const { t } = useTranslation()
  return <Badge className="bg-amber-100! text-amber-900! border border-amber-300">{t('demo.badge')}</Badge>
}
