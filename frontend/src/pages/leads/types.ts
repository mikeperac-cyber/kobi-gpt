export interface Lead {
  id: string
  company_name: string
  country: string
  contact_name?: string
  email?: string
  website?: string | null
  notes?: string
  source: 'rfq' | 'csv_import' | 'manual' | 'demo'
  source_note: string
  status: string
  score: number
  score_breakdown?: Record<string, number>
  is_hot: boolean
  is_demo: boolean
  products_of_interest?: string[]
  quantity?: string | number | null
  created_at: string
  deal_value?: number | null // self-reported when the lead was marked won
  deal_currency?: 'EUR' | 'USD' | 'TRY' | null
  won_at?: string | null
}

export interface Analysis {
  translation: string | null
  summary: string[]
  intent: string
  terms: { quantity: string | null; incoterm: string | null; delivery_date: string | null; certifications: string[] }
  red_flags: string[]
  opt_out: boolean
  opt_out_source?: string
}

export interface Message {
  id: string
  lead_id: string
  direction: 'inbound' | 'outbound'
  kind: string
  language: string
  subject: string | null
  body: string
  body_tr: string | null
  translation_language?: string
  translation_fallback?: boolean
  fallback?: boolean
  status: string
  created_at: string
  analysis?: Analysis
}

export const STATUSES = ['new', 'draft_ready', 'sent', 'replied', 'quoted', 'won', 'lost', 'do_not_contact'] as const
