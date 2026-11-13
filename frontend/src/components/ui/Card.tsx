import type { HTMLAttributes } from 'react'

export default function Card({ className = '', ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div {...p} className={`bg-white rounded-lg border border-slate-200 shadow-sm p-5 ${className}`} />
}
