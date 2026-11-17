import { useTranslation } from 'react-i18next'
export default function Skeleton({ className = 'h-6 w-full' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded bg-slate-200 ${className}`} />
}

export function PageSkeleton({ error }: { error?: string }) {
  const { t } = useTranslation()
  if (error) return <p role="alert" className="text-brand font-semibold">{error}</p>
  return (
    <div role="status" aria-label={t('common.loading')} className="space-y-3">
      <Skeleton className="h-8 w-64" /><Skeleton className="h-24" /><Skeleton className="h-24" />
    </div>
  )
}
