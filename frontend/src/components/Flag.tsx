import { useTranslation } from 'react-i18next'

const BANDS: Record<string, string[]> = { DE: ['#000000', '#DD0000', '#FFCE00'] }

export default function Flag({ country }: { country: string }) {
  const { t } = useTranslation()
  const label = t(`dashboard.market.${country}`, { defaultValue: country })
  const bands = BANDS[country]
  if (!bands) return <span>{country}</span>
  return (
    <svg role="img" aria-label={label} viewBox="0 0 5 3" width="20" height="12" className="inline-block align-middle rounded-sm border border-slate-300">
      {bands.map((c, i) => <rect key={c} y={i} width="5" height="1" fill={c} />)}
    </svg>
  )
}
