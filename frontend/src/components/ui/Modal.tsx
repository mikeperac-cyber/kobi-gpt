import { useEffect, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import Button from './Button'

export default function Modal({ title, onClose, children }: { title: string; onClose(): void; children: ReactNode }) {
  const { t } = useTranslation()
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 bg-navy/60 flex items-end sm:items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}
        className="bg-white w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto rounded-t-lg sm:rounded-lg p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 className="text-lg font-semibold">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label={t('common.close')}>✕</Button>
        </div>
        {children}
      </div>
    </div>
  )
}
