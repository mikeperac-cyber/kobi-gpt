import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'

export default function ModuleCard({ title, badge, tone = 'neutral', to, cta }: {
  title: string; badge: ReactNode; tone?: 'neutral' | 'good'; to: string; cta: string
}) {
  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-semibold">{title}</h2>
      <Badge className={`self-start ${tone === 'good' ? '!bg-green-100 !text-green-900' : ''}`}>{badge}</Badge>
      <Link to={to} className="mt-auto min-h-11 px-4 rounded-md font-semibold inline-flex items-center justify-center bg-brand text-white hover:bg-red-800">{cta}</Link>
    </Card>
  )
}
