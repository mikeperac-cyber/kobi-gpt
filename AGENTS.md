You are the lead engineer building **KOBİ-GPT & Otonom İhracat Ajanı** — a web app that helps small Turkish manufacturers (KOBİ / SMEs) start exporting. I will give you the build in phases (Prompt 01, 02, ...). Read this whole context first.
## 1. The product in one paragraph

A small producer (e.g. a pistachio processor in Gaziantep, a towel workshop in Denizli, a fastener maker in Bursa) signs up, describes their product in Turkish and uploads photos. The app then: **(A)** generates and publishes a multilingual export storefront tailored to a target market (Germany first), **(B)** suggests the product's GTİP/HS code, produces a compliance checklist for the target market and matches Turkish state export incentives, and **(C)** helps find and contact buyers: it drafts outreach emails and quotes in the buyer's language, but **the producer approves every message before it goes out**.

## 2. Who uses it

- **Primary user:** owner of a 5–50 person manufacturing business in Anatolia. Not technical. Speaks Turkish only. Uses a phone as much as a laptop. Has never exported, or exports only via middlemen.
- **Secondary user (viewer):** foreign buyer (German importer) who visits the generated storefront and sends a quote request.
- **Audience for the MVP:** a jury (government / TÜBİTAK / competition judges). The app must survive a **live 3-minute demo**.

## 3. Non-negotiable product principles

1. **Human-in-the-loop for anything external.** The AI never sends an email, commits to a price, or signs anything by itself. It drafts; the producer clicks "Onayla ve Gönder" (Approve & Send). No exceptions.
2. **No invented regulations.** Compliance and incentive information may ONLY come from the curated knowledge base in the database (seeded in Prompt 03). The LLM may explain, summarize and personalize those records, but must never make up a rule, a tariff rate or a support amount. If the knowledge base has nothing for a product/country, say so plainly and recommend an expert (e.g. the İhracatçı Birliği / chamber of commerce).
3. **Every regulatory statement shows its source** (a link to the official page) and a "son doğrulama tarihi" (last verified date).
4. **GTİP codes are suggestions, never facts.** Always show the top candidates, the reasoning and a confidence label, and require the user to confirm. Show a warning that the final classification must be checked with a customs broker (gümrük müşaviri).
5. **Bilingual UI, Turkish first.** All producer-facing UI text exists in Turkish and English, with Turkish as the default. Plain language, no jargon without explanation (e.g. "GTİP (ürününüzün gümrük kodu)" / "HS code (your product's customs code)"). Storefronts are in the target market's language(s) + English.
6. **Honest numbers.** Never show fabricated metrics. Estimates (logistics cost, readiness score) are labelled "tahmini" (estimated) and explain how they were computed.
7. **Demo-proof.** Every AI step shows a visible progress state and has a graceful fallback if the LLM call fails or is slow (details in Prompt 05).

## 4. Out of scope for the MVP (do NOT build)

- Payments / checkout (iyzico, Stripe) — storefronts collect quote requests (RFQ) only.
- E-Devlet login, MERSİS, or any real government system integration.
- Real integration with Kolay İhracat Platformu (it has no public API). We use our own curated seed data.
- Automatic web scraping of importer databases or LinkedIn.
- Fully autonomous emailing or negotiation.
- Fine-tuning models. Use a general LLM with structured prompts + our knowledge base.
- Native mobile apps (responsive web is enough).

## 5. Tech stack

- **Frontend:** React (Vite or CRA, your choice) + Tailwind CSS + shadcn/ui-style components. React Router. i18n via `react-i18next` (Turkish default; English available).
- **Backend:** Python FastAPI. Pydantic models. Async.
- **Database:** MongoDB (Motor async driver).
- **LLM:** a single `llm_service` module in the backend that wraps the provider (use an OpenAI, Gemini or Anthropic API key from `.env`). Every LLM call goes through it. It must support: plain text, **JSON output validated against a Pydantic schema** (retry up to 2 times on invalid JSON), image input (product photos), and a timeout.
- **File storage:** local `/uploads` folder served statically for the MVP (abstract it behind a `storage_service` so it can be swapped for S3 later).
- **PDF generation:** server-side (WeasyPrint or ReportLab) for reports and quotes.
- **Auth:** email + password, JWT, bcrypt. Single role "producer" plus an "admin" flag.
- Secrets only in `.env`. Never hard-code keys.

## 6. Core data model (MongoDB collections — extend as needed)

- `users` — email, password_hash, name, is_admin, created_at, kvkk_consent_at
- `companies` — owner_id, name, city, sector (tekstil | gida | otomotiv_yan_sanayi | diger), description_tr, founded_year, employee_count, certifications[], contact {phone, email, website}, logo_url, min_order_note
- `products` — company_id, name_tr, description_tr, photos[], material/ingredients, unit, moq, price_floor (private, never shown to buyers or the LLM output for buyers), hs_code_confirmed, created_at
- `markets` — company_id, country_code (DE first), languages[], status
- `storefronts` — company_id, market country, slug, template, site_config (JSON: sections, texts per language, theme), status (draft | published), published_at
- `classifications` — product_id, candidates[{code, description, confidence, reasoning}], confirmed_code, confirmed_at
- `kb_rules` — curated compliance rules (Prompt 03)
- `kb_incentives` — curated incentive records (Prompt 03)
- `readiness_reports` — product_id, country, checklist[], incentives[], score, pdf_url, created_at
- `leads` — company_id, source (rfq | csv_import | manual | demo), company_name, country, contact_name, email, website, notes, score, status, created_at, source_note (where the contact came from — required)
- `messages` — lead_id, direction (outbound | inbound), language, subject, body, body_tr (Turkish translation), status (draft | approved | sent | rejected), approved_by, approved_at
- `quotes` — lead_id, product_id, quantity, incoterm, unit_price, logistics_estimate, currency, valid_until, pdf_url
- `agent_runs` — type, input, output, status, duration_ms, error (for showing the agent's steps in the UI and debugging)

## 7. Engineering rules

- Keep the code modular: `backend/app/routers/*`, `backend/app/services/*` (llm_service, storefront_service, regai_service, outreach_service, logistics_service, pdf_service), `backend/app/prompts/*` (LLM prompt templates as separate files, not inline strings), `backend/app/seed/*`.
- All LLM prompt templates live in files and include: role, task, the exact JSON schema expected, and the rule "do not invent facts that are not in the provided context".
- Log every AI call into `agent_runs`.
- Write at least basic backend tests (pytest) for each service's non-LLM logic (scoring, logistics math, slug generation, schema validation). Mock the LLM in tests.
- After finishing each phase: run the app, verify the acceptance criteria I give you, and report back with (1) what you built, (2) what you could not do and why, (3) how I can test it in the UI, step by step.
- If something in my instructions is ambiguous or seems wrong, ask before building it.
