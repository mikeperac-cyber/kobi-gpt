import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import type { Storefront } from '../../storefront/types'
import Editor from './Editor'
import Intake, { type IntakeValues } from './Intake'
import PublishSuccess from './PublishSuccess'

type View = { kind: 'loading' } | { kind: 'error'; key: string } | { kind: 'intake' } | { kind: 'edit'; sf: Storefront } | { kind: 'done'; slug: string; sf: Storefront }

export default function StorefrontPage() {
  const { t } = useTranslation()
  const [view, setView] = useState<View>({ kind: 'loading' })
  const [lastIntake, setLastIntake] = useState<IntakeValues>()

  const load = useCallback(async () => {
    try {
      setView({ kind: 'edit', sf: await api<Storefront>('/api/storefronts/mine') })
    } catch (x) {
      if (x instanceof ApiError && x.status === 404) setView({ kind: 'intake' })
      else setView({ kind: 'error', key: x instanceof ApiError ? x.messageKey : 'errors.network' })
    }
  }, [])
  useEffect(() => { void load() }, [load])

  switch (view.kind) {
    case 'loading': return <p>{t('common.loading')}</p>
    case 'error': return (
      <div className="space-y-3"><p>{t(view.key)}</p><Button onClick={() => { setView({ kind: 'loading' }); void load() }}>{t('common.retry')}</Button></div>
    )
    case 'intake': return <Intake initial={lastIntake} onSubmitted={setLastIntake} onDone={() => void load()} onCancel={undefined} />
    case 'edit': return <Editor key={view.sf._id} initial={view.sf} onPublished={(slug) => setView({ kind: 'done', slug, sf: view.sf })} onRestart={() => setView({ kind: 'intake' })} />
    case 'done': return <PublishSuccess slug={view.slug} onBack={() => void load()} />
  }
}
