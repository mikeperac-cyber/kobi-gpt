import type { TextareaHTMLAttributes } from 'react'

export default function Textarea({ className = '', ...p }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={4} {...p} className={`w-full px-3 py-2 rounded-md border border-slate-300 bg-white focus:outline-2 focus:outline-navy ${className}`} />
}
