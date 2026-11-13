import type { SelectHTMLAttributes } from 'react'

export default function Select({ className = '', ...p }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...p} className={`w-full min-h-11 px-3 rounded-md border border-slate-300 bg-white focus:outline-2 focus:outline-navy ${className}`} />
}
