import type { HTMLAttributes } from 'react'

export default function Badge({ className = '', ...p }: HTMLAttributes<HTMLSpanElement>) {
  return <span {...p} className={`inline-block rounded-full bg-slate-100 text-navy text-xs font-semibold px-2.5 py-1 ${className}`} />
}
