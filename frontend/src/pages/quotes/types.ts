export interface EstLine { label_key: string; formula: string; value: number }
export interface Estimate { gross_kg: number; mode: string; trucks: number | null; freight_eur: number; lines: EstLine[]; estimated?: boolean }
export interface Quote {
  id: string; lead_id: string; product_id: string; quantity: number; unit: string; incoterm: string
  unit_price: number; currency: string; payment_terms: string; logistics_estimate: Estimate
  freight_included: boolean; total: number; valid_until: string; status: string; created_at: string
  lead?: { company_name?: string; email?: string; contact_name?: string; country?: string; is_demo?: boolean }
}
