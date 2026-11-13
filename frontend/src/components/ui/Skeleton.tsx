export default function Skeleton({ className = 'h-6 w-full' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded bg-slate-200 ${className}`} />
}
