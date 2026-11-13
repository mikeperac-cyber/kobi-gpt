# PROMPT 02 — Module 1: Anında Dijital Vitrin (Instant Export Storefront)

---

Build Phase 2: the producer's product info becomes a published, multilingual export storefront for the target market (Germany). 

**Key design decision:** do NOT generate raw HTML/React code per user. Instead the AI generates a structured `site_config` JSON, and our own templates render it. This is reliable, safe, editable and fast enough for a live demo.

## Build

### 1. Intake ("Vitrinimi oluştur")
- Pre-fill from the company + products already saved.
- Let the producer add more context in their own words in Turkish: a large text box **plus a microphone button** that uses the browser Web Speech API (`tr-TR`) to dictate. If the browser does not support it, hide the button.
- Choose a positioning: **B2B Toptan** (wholesale catalogue, default) or **B2C Perakende** (retail-style showcase). Both end in a quote request; no checkout.

### 2. AI generation (`storefront_service`)
Run as a visible multi-step agent with progress shown in the UI (each step logged to `agent_runs`):
1. **Ürün analizi** — send photos + Turkish text to the LLM (vision). Extract: product attributes, key selling points, quality signals, suitable buyer types.
2. **Pazar uyarlaması** — adapt the message to German B2B buyer expectations: precise specs, certifications, MOQ, lead time, packaging, Incoterms offered, reliability over hype. Avoid superlatives that German consumer law could treat as misleading ("best in the world").
3. **İçerik üretimi** — produce `site_config` JSON with texts in **German (de)** and **English (en)**, and a Turkish copy (tr) only for the producer to review what was written. Sections:
   - hero (headline, sub-headline, call-to-action "Angebot anfordern")
   - about the company (story, city, year, team size, certifications as badges)
   - product cards (name, short + long description, specs table, MOQ, packaging, photos)
   - why us (3–4 points, factual)
   - export info (Incoterms offered, lead time, sample policy) — only use what the producer gave; mark missing fields so the producer can fill them in, do not invent them
   - RFQ form
   - footer + legal pages
   - SEO: page title, meta description, slug suggestion
4. **Tema seçimi** — pick one of 3 templates based on sector, which the user can change: `industrial` (Bursa, metal/automotive: dark navy, technical), `natural` (food: warm, cream/green), `textile` (soft, light, product-photo-heavy).

The JSON must be validated against a Pydantic schema. If the LLM fails, retry; if it still fails, fall back to a deterministic template filled with the raw product data (so the demo never shows a blank page).

### 3. Editor
- Split view: left = section list with editable fields (tabs DE / EN / TR-preview), right = live preview (desktop / mobile toggle).
- "Bu bölümü yeniden yaz" (regenerate this section) with an optional instruction box ("daha kısa", "daha teknik").
- Photo reorder / remove.
- Highlight fields the AI marked as missing in yellow: "Bu bilgiyi siz girmelisiniz".

### 4. Publish
- "Yayınla" publishes to a public route `/s/{slug}` (no login). Unpublish is possible.
- Public storefront: language switcher (DE / EN), fully responsive, fast, proper `<html lang>`, OpenGraph tags, favicon from the logo.
- **Germany-specific legal pages:** an **Impressum** page (mandatory for German commercial websites; fill it from company data and show the producer a checklist of required fields) and a **Datenschutzerklärung** (privacy notice) template covering the RFQ form. Show the producer a note in Turkish: "Bu metinler şablondur; yayın öncesi bir hukukçuya kontrol ettiriniz."
- **RFQ form** on the storefront: company name, contact name, email, country, product(s) of interest, quantity, message, GDPR consent checkbox. Submissions create a `lead` (source = `rfq`) and a notification on the producer's dashboard. Add basic spam protection (honeypot field + rate limit).
- After publishing, show a success screen with the URL, a QR code (for business cards / trade fairs) and a "Paylaş" (share) button.

## Acceptance criteria
- [ ] For the seeded Gaziantep company, generating a storefront takes under ~60 seconds and shows each agent step live.
- [ ] Generated German text uses only facts from the input; fields not provided appear as "missing" in the editor rather than invented.
- [ ] I can edit text, regenerate one section, switch template and publish.
- [ ] `/s/{slug}` works logged out, on mobile and desktop, in DE and EN.
- [ ] Impressum and privacy pages exist and are linked in the footer.
- [ ] Submitting the RFQ form creates a lead visible on the producer's dashboard.
- [ ] If I disable the LLM key, generation falls back to the deterministic template instead of crashing.
