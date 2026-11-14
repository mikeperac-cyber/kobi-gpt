// Full literal class names so Tailwind can see them.
export type Theme = {
  page: string; muted: string; hero: string; heroSub: string; btn: string; card: string; h: string
  section: string; chip: string; grid: string; photo: string
}

const base = 'rounded-md px-5 py-3 font-semibold min-h-11 '
export const THEMES: Record<string, Theme> = {
  industrial: {
    page: 'bg-slate-100 text-slate-900', muted: 'text-slate-600', hero: 'bg-[#12263F] text-white',
    heroSub: 'text-slate-300', btn: base + 'bg-sky-600 text-white hover:bg-sky-700',
    card: 'bg-white border border-slate-300 rounded-md', h: 'font-bold tracking-tight uppercase text-[#12263F]',
    section: 'border-t-4 border-slate-400', chip: 'bg-slate-200 text-slate-800',
    grid: 'sm:grid-cols-2', photo: 'aspect-[4/3]',
  },
  natural: {
    page: 'bg-[#FAF5EA] text-stone-900', muted: 'text-stone-600', hero: 'bg-[#2F5D3A] text-[#FAF5EA]',
    heroSub: 'text-[#DCE7D5]', btn: base + 'bg-[#FAF5EA] text-[#2F5D3A] hover:bg-white',
    card: 'bg-white/70 border border-[#E4D9BF] rounded-2xl', h: 'font-serif font-bold text-[#2F5D3A]',
    section: '', chip: 'bg-[#E8EFDD] text-[#2F5D3A]',
    grid: 'sm:grid-cols-2', photo: 'aspect-[4/3]',
  },
  textile: {
    page: 'bg-white text-neutral-900', muted: 'text-neutral-500', hero: 'bg-neutral-100 text-neutral-900',
    heroSub: 'text-neutral-600', btn: base + 'bg-neutral-900 text-white hover:bg-neutral-700',
    card: 'bg-white', h: 'font-light tracking-wide text-neutral-900',
    section: '', chip: 'bg-neutral-100 text-neutral-700',
    grid: 'sm:grid-cols-2 lg:grid-cols-3', photo: 'aspect-[3/4]',
  },
}
