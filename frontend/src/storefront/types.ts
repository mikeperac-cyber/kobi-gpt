export type Lang = 'de' | 'en'
export type Template = 'industrial' | 'natural' | 'textile'
type S = string | null

export type ProductBlock = {
  product_id: string; name: S; short: S; long: S
  specs: { label: string; value: string }[]
  moq: S; packaging: S; photos: string[]
}
export type LocalizedContent = {
  hero: { headline: S; subheadline: S; cta: S }
  about: { story: S; city: S; founded_year: number | null; team_size: number | null; certifications: string[] }
  products: ProductBlock[]
  why_us: string[]
  export_info: { incoterms: string[]; lead_time: S; sample_policy: S }
  rfq: { title: S; intro: S }
  footer: { note: S }
  seo: { title: S; description: S }
}
export type SiteConfig = {
  de: LocalizedContent; en: LocalizedContent; review: LocalizedContent
  review_language: 'tr' | 'en'
  slug_suggestion: string
  template: Template
  missing: string[]
  positioning: 'b2b' | 'b2c'
}
export type Storefront = {
  _id?: string; slug: string; template: Template; status: 'draft' | 'published'
  site_config: SiteConfig
}
