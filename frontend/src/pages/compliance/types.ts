export type Candidate = { code: string; description: string; confidence: 'yüksek' | 'orta' | 'düşük'; reasoning: string; in_kb: boolean }
export type Classification = { candidates: Candidate[]; processing: string | null; confirmed_code: string | null }
export type Level = 'zorunlu' | 'koşullu' | 'önerilen'
export type Item = {
  rule_id: string; title_tr: string; title_en?: string; side: 'TR' | 'DEST'; level: Level
  source_url?: string; last_verified?: string | null; verified?: boolean; applies?: boolean
  reason?: string; next_step?: string; summary?: string; what_to_do?: string; done?: boolean
}
export type Incentive = { incentive_id: string; name_tr: string; name_en?: string; provider?: string; source_url?: string; why?: string; summary?: string }
export type Report = {
  id: string; checklist: Item[]; incentives: Incentive[]; next_steps?: { rule_id: string; text: string }[]
  score: number; no_match?: boolean; ui_language?: string
}
export type Params = { channel: 'b2b' | 'b2c'; structural: boolean; processing: 'roasted' | 'raw' | 'na' | null }
