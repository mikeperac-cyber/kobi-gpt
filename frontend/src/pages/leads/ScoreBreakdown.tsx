import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'

/** Score with a breakdown popover that opens on hover, focus or tap, and closes on Escape/blur. */
export default function ScoreBreakdown({ score, breakdown }: { score: number; breakdown?: Record<string, number> }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <span className="relative inline-block" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-expanded={open} aria-describedby={open ? id : undefined} aria-label={t('leads.scoreOf', { n: score })}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onClick={() => setOpen(true)} onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        className="min-h-11 min-w-11 px-2 font-semibold underline decoration-dotted underline-offset-4 focus-visible:outline-2 focus-visible:outline-navy">
        {score}
      </button>
      {open && (
        <div id={id} role="tooltip" className="absolute z-20 left-0 top-full w-56 bg-white border border-slate-300 rounded-md shadow-lg p-3 text-sm text-left font-normal">
          <p className="font-semibold mb-1">{t('leads.breakdown.title')}</p>
          <dl className="grid grid-cols-[1fr_auto] gap-x-3">
            {(['source', 'product_match', 'country', 'email'] as const).map((k) => (
              <div key={k} className="contents"><dt>{t(`leads.breakdown.${k}`)}</dt><dd className="font-semibold">{breakdown?.[k] ?? 0}</dd></div>
            ))}
          </dl>
          <p className="text-slate-600 mt-2">{t('leads.scoreEstimated')}</p>
        </div>
      )}
    </span>
  )
}
