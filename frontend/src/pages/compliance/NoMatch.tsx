import { useTranslation } from 'react-i18next'
import Card from '../../components/ui/Card'

export default function NoMatch() {
  const { t } = useTranslation()
  return (
    <Card role="status" className="space-y-2">
      <h2 className="font-semibold text-lg">{t('compliance.noMatchTitle')}</h2>
      <p>{t('compliance.noMatchBody')}</p>
      <ul className="list-disc pl-5 space-y-1">
        <li>{t('compliance.contactTim')}</li>
        <li>{t('compliance.contactChamber')}</li>
        <li>{t('compliance.contactAttache')}</li>
      </ul>
    </Card>
  )
}
