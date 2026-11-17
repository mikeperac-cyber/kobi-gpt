/** Presenter script (spec Phase 5): start time in seconds + i18n key under demo.guide.steps. */
export const SCRIPT = [
  { at: 0, key: 'dashboard' },
  { at: 15, key: 'storefront' },
  { at: 75, key: 'compliance' },
  { at: 135, key: 'rfq' },
  { at: 180, key: 'finish' },
] as const

export const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
