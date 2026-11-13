# KOBİ-GPT & Otonom İhracat Ajanı — Full Build Prompt

> Hand everything below the line to an AI coding agent that works in the project folder. It is the complete spec for the whole MVP. Where it differs from the phase files in this folder, this prompt wins.

---

You are building **KOBİ-GPT & Otonom İhracat Ajanı**, a web app that helps small Turkish manufacturers (KOBİ) start exporting, starting with Germany. Build the whole MVP in this session, end to end. Do not wait for approval between phases. Build, test, verify, then move on.

## 0. How to work

1. **Check the environment first:** Python 3.11+, Node.js LTS, and a reachable MongoDB (local or Atlas). Set up what you can and say what is missing.
2. **Build in the order of section 6 (Phases 1–5).** After each phase, run the pytest suite and the app, check that phase's acceptance criteria, and record PASS or FAIL with evidence (test name, endpoint response, or the UI steps you ran) in `docs/ACCEPTANCE.md`. Do not mark anything PASS unless you actually ran it.
3. **Ambiguity:** choose the simplest option that meets the spec, record it in `docs/DECISIONS.md`, and keep going. Ask only when you are blocked by something you cannot work around.
4. **No API key?** The app must still run. Every AI step falls back to deterministic output (section 4.6).
5. **Do not touch** the root `README.md` (it is the build-kit guide), `prompts/`, or `AGENTS.md`. Write run instructions to `docs/RUNNING.md`.
6. **Languages:** code, comments and docs in English. The producer UI is bilingual, Turkish (default) and English, with every visible string in both (section 4.1). Storefront content is in German and English.
7. **Final message:** (a) what you built, (b) what you did not build or could not verify, and why, (c) the Windows PowerShell commands to run the app and the tests, (d) a step-by-step UI test script, (e) the decisions list from `docs/DECISIONS.md`.

**Decisions already made (do not re-open):**
- The producer UI is bilingual: Turkish by default, with English as a full alternative. The producer switches language in the header, and the choice is saved on the account (`users.ui_language`). The buyer-facing storefront is German and English.
- In mailto mode, "Onayla ve Gönder" does not send anything. It records the approval and marks the message `sent` with `delivery_channel: mailto`. The UI calls this "Mail uygulamasına aktarıldı" / "Handed to your mail app", not "Gönderildi" / "Sent".
- Quote builder needs `unit_weight_kg` on the product. It is optional at onboarding and asked for when missing.
- The demo storefront slug for Bozkurt is `bozkurt-pistazien`.
- Admins manage the knowledge base and see platform counts. They never read another company's products, leads or floor prices.

## 1. The product

A small producer (for example a pistachio processor in Gaziantep, a towel workshop in Denizli, or a fastener maker in Bursa) signs up, describes the product in Turkish, and uploads photos. The app then does three things:

- **A. Dijital Vitrin:** generates and publishes a multilingual export storefront for Germany (German and English), with a quote-request form.
- **B. Mevzuat Bekçisi:** suggests the GTİP/HS code, builds a compliance checklist for the target market with a source on every item, matches Turkish export incentives, and produces an İhracat Hazırlık Raporu (PDF).
- **C. Alıcı Ajanı:** manages leads and drafts outreach emails and quotes in the buyer's language. **The producer approves every message and every quote before anything leaves the system.**

**Users:** the producer owns a 5–50 person factory in Anatolia. They speak Turkish, use a phone as much as a laptop, and have never exported or export only through middlemen. A secondary user is a German buyer who views the storefront and sends a quote request. The MVP is shown to a jury in a live 3-minute demo, so it must work the first time. The English UI must be as complete as the Turkish one, for English-speaking users and the jury.

## 2. Non-negotiable principles

1. **Human approval for anything external.** The AI never sends an email, commits to a price or signs anything. The producer clicks "Onayla ve Gönder".
2. **No invented regulations.** Compliance and incentive content comes only from the knowledge base (section 5.2). The LLM may explain, summarize and personalize those records. It must never create a rule, tariff rate, deadline or support amount. If the knowledge base has nothing for a product or country, say so and recommend an expert (İhracatçı Birliği, chamber of commerce, customs broker).
3. **Every regulatory statement shows its source** (official link) and its "son doğrulama tarihi".
4. **GTİP codes are suggestions.** Show the candidates, the reasoning and a confidence label. The user must confirm one. Always show: "Kesin GTİP (12 hane) için gümrük müşavirinize danışın."
5. **Bilingual UI, Turkish first.** Every producer-facing string exists in Turkish and English, and Turkish is the default. Use plain language and explain jargon in both languages (for example "GTİP (ürününüzün gümrük kodu)" / "HS code (your product's customs code)").
6. **Honest numbers.** Never show fabricated metrics. Estimates are labelled "tahmini" and show how they were computed.
7. **Demo-proof.** Every AI step shows progress and has a graceful fallback when the LLM fails or is slow.
8. **Secrecy of the floor price.** `price_floor` never appears in any API response except to its owner, in any LLM prompt, in any generated text, or in any PDF.

## 3. Out of scope (do not build)

- Payments or checkout (iyzico, Stripe). Storefronts collect quote requests only.
- E-Devlet login, MERSİS, or any government system integration.
- Integration with Kolay İhracat Platformu (no public API). It appears only as a link.
- Scraping importer databases or LinkedIn.
- Autonomous emailing or negotiation.
- Fine-tuning models.
- Native mobile apps. Responsive web only.

## 4. Stack and engineering rules

### 4.1 Stack

- **Frontend:** React + Vite + TypeScript, Tailwind CSS, shadcn/ui-style components, React Router, react-i18next. Two producer UI languages: Turkish (`tr`, default) and English (`en`). No hard-coded UI strings. A test fails if a key exists in one language and not the other. Format dates and numbers with the active locale (tr-TR, en-GB).
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, async, Motor (MongoDB), PyJWT, bcrypt.
- **Database:** MongoDB.
- **PDF:** ReportLab. Do not use WeasyPrint (hard to install on Windows). Bundle a TTF font with full Turkish and German glyphs in the repo (for example Noto Sans, OFL licence). Do not rely on system fonts.
- **Images:** Pillow for validation, resizing and WebP compression.
- **QR codes:** the `qrcode` package.
- **Storage:** `storage_service` writes to a local `uploads/` folder served statically. Put it behind an interface so S3 can replace it later.
- **Auth:** email and password, bcrypt hashes, JWT in an httpOnly SameSite=Lax cookie. Roles: producer, plus an `is_admin` flag set by the seed script or env (no UI to grant it).

### 4.2 Layout

```
backend/app/main.py
backend/app/core/          config, security, db
backend/app/routers/       one file per area
backend/app/services/      llm_service, storage_service, storefront_service,
                           regai_service, outreach_service, logistics_service,
                           pdf_service, demo_service, scoring
backend/app/prompts/       LLM prompt templates as files
backend/app/seed/          seed script and seed data
backend/app/models/        Pydantic models
backend/tests/
frontend/src/pages/ components/ i18n/ (tr.json, en.json) api/
uploads/   docs/   .env.example
```

### 4.3 Configuration

Everything comes from `.env`. Commit `.env.example`, never `.env`.

`MONGO_URI`, `MONGO_DB`, `JWT_SECRET`, `LLM_PROVIDER` (openai | gemini | anthropic), `LLM_MODEL`, the matching key (`OPENAI_API_KEY`, `GEMINI_API_KEY` or `ANTHROPIC_API_KEY`), `LLM_TIMEOUT_SECONDS` (default 45), `DEMO_LLM_TIMEOUT_SECONDS` (default 25), `FRONTEND_ORIGIN`, `EMAIL_PROVIDER` (empty = off), `SEED_PASSWORD` (password for seeded demo logins).

### 4.4 Engineering rules

- Every LLM prompt template is a file in `backend/app/prompts/`. Each template has: role, task, the exact JSON schema, and the rule "do not invent facts that are not in the provided context". Never put `price_floor` in a prompt.
- Every LLM call goes through `llm_service`. Every call is logged to `agent_runs` (type, input summary, output, status, duration_ms, error).
- Structured AI output (storefront, classifications, checklist decisions) is validated against Pydantic schemas.
- Every prompt that writes text the producer reads takes a `ui_language` parameter (tr | en). The AI writes its reasons, summaries, next steps and translations in that language, and cache keys include it. Never auto-translate the producer's own input in place.
- Tests mock the LLM. The test suite must pass with no network and no API keys.

### 4.5 `llm_service`

- `generate_text()`, `generate_json(schema)`, image input for product photos.
- `generate_json` validates the output and retries up to 2 times on invalid JSON.
- Timeout: 45 s by default, 25 s in demo mode.
- With no key, or after a failed call, raise a typed error. Each caller then uses its fallback.
- `/api/health` reports the provider name and whether a key is set. It never returns key values.

### 4.6 Fallback rule

Each AI step has a deterministic fallback:

| AI step | Fallback |
|---|---|
| Storefront generation | Template filled with the raw company and product data. Missing fields stay marked as missing. |
| GTİP suggestion | Candidates from `kb_hs_codes` filtered by sector. The user answers a processing question ("kavrulmuş mu, çiğ mi?"). |
| Rule and incentive matching | The deterministic filter result, with each rule's own `summary_tr` as the reason. |
| Next steps | The top three unticked items by weight. |
| Outreach and reply drafts | A plain template in the buyer's language, with the producer's facts filled in. |

When a fallback runs, show a small indicator to the presenter only. Never show a scary error.

## 5. Data

### 5.1 Collections

- `users`: email, password_hash, name, is_admin, ui_language (tr | en, default tr), created_at, kvkk_consent_at
- `companies`: owner_id, name, city, sector (tekstil | gida | otomotiv_yan_sanayi | diger), description_tr, founded_year, employee_count, certifications[], contact {phone, email, website}, logo_url, min_order_note
- `products`: company_id, name_tr, description_tr, photos[], material_or_ingredients, unit (kg | adet | metre | koli), unit_weight_kg, moq, price_floor (private), hs_code_confirmed, created_at
- `markets`: company_id, country_code (DE first), languages[], status
- `storefronts`: company_id, country, slug, template (industrial | natural | textile), site_config (JSON), status (draft | published), published_at, unpublished_at
- `classifications`: product_id, candidates[{code, description, confidence, reasoning}], confirmed_code, confirmed_at
- `kb_hs_codes`, `kb_rules`, `kb_incentives`: section 5.2
- `readiness_reports`: product_id, country, channel, structural_use, checklist[], incentives[], score, pdf_url, created_at
- `leads`: company_id, source (rfq | csv_import | manual | demo), company_name, country, contact_name, email, website, notes, score, status, is_demo, source_note (required for csv_import and manual), created_at
- `messages`: lead_id, direction (outbound | inbound), language, subject, body, body_tr, status (draft | approved | sent | rejected), approved_by, approved_at, delivery_channel (mailto | clipboard | email_provider), reject_reason
- `quotes`: lead_id, product_id, quantity, incoterm, unit_price, currency, payment_terms, logistics_estimate, valid_until, status (draft | approved | sent), pdf_url, approved_by, approved_at
- `tasks`: company_id, type (numune_gonderimi), checklist, courier_estimate, created_at
- `logistics_rates`: admin-editable rows (phase 4)
- `notifications`: company_id, type, message_tr, read, created_at
- `demo_cache`: company_id, step, output, created_at
- `agent_runs`: type, company_id, input_summary, output, status, duration_ms, error, created_at

### 5.2 Knowledge base seed data

Insert exactly these records. Do not add rules of your own.

Every record starts with `verified: false` and `last_verified: null`. Write the Turkish fields (`description_tr`, `summary_tr`, `what_to_do_tr`, `documents`) yourself, in short plain Turkish, staying strictly within what the title and source imply. Write the matching English fields (`*_en`) as faithful translations of the Turkish text. The Turkish titles in the tables below are the authoritative wording. Do not state amounts, rates, deadlines or eligibility thresholds that are not in the title.

Record ids (`R1`…`R15`, `I1`…`I9`, and the HS6 code) are stable `id` strings. Mongo's `_id` is internal and is never used for matching.

**kb_hs_codes** (HS6 level; the national 12-digit GTİP must be checked in the Türk Gümrük Tarife Cetveli)

| hs6 | description_en | note | sector |
|---|---|---|---|
| 0802.51 | Pistachios, fresh or dried, in shell | raw or dried, not roasted | gida |
| 0802.52 | Pistachios, fresh or dried, shelled | raw or dried, not roasted | gida |
| 2008.19 | Nuts (incl. mixtures), otherwise prepared or preserved, e.g. roasted | roasted and salted pistachios usually fall here | gida |
| 6302.60 | Toilet and kitchen linen, of terry towelling, of cotton | towels | tekstil |
| 6207.91 | Men's bathrobes, dressing gowns etc., of cotton | | tekstil |
| 6208.91 | Women's and girls' bathrobes, dressing gowns etc., of cotton | | tekstil |
| 7318.15 | Other screws and bolts, of iron or steel | | otomotiv_yan_sanayi |
| 7318.16 | Nuts, of iron or steel | | otomotiv_yan_sanayi |

Write `description_tr` for each code in plain Turkish. The English descriptions above become `description_en`.

**kb_rules** (country DE unless stated). Side: TR = Turkish-side requirement, DEST = destination market. Each title is given in Turkish; write the English version as `title_en`.

| id | title_tr | applies to | side | level | source_url |
|---|---|---|---|---|---|
| R1 | İhracatçı Birliği üyeliği | all | TR | zorunlu | https://tim.org.tr |
| R2 | AB–Türkiye Gümrük Birliği: sanayi ürünlerinde A.TR dolaşım belgesi | sectors: tekstil, otomotiv_yan_sanayi | TR | zorunlu | https://trade.ec.europa.eu/access-to-markets/en/home |
| R3 | Tarım ürünleri Gümrük Birliği kapsamı dışında: gümrük vergisi ve menşe belgesi (EUR.1) TARIC'ten kontrol edilmeli | hs 0802, 2008 | DEST | zorunlu | https://ec.europa.eu/taxation_customs/dds2/taric/ |
| R4 | Tekstil lif etiketlemesi – Yönetmelik (AB) 1007/2011 (Almanya için Almanca etiket) | hs 6302, 6207, 6208 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg/2011/1007/oj |
| R5 | REACH Ek XVII – tekstilde yasaklı azo boyalar | hs 6302, 6207, 6208 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg/2006/1907/oj |
| R6 | OEKO-TEX Standard 100 (alıcılar sıkça ister) | hs 6302, 6207, 6208 | DEST | önerilen | https://www.oeko-tex.com |
| R7 | Aflatoksin azami limitleri – Yönetmelik (AB) 2023/915 | hs 0802, 2008 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg/2023/915/oj |
| R8 | Türkiye menşeli fıstıkta artırılmış resmi kontrol / özel şartlar – Uygulama Yönetmeliği (AB) 2019/1793 (resmi sertifika + analiz raporu; güncel kontrol sıklığını kontrol edin) | hs 0802, 2008 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg_impl/2019/1793/oj |
| R9 | Gıda etiketleme – Yönetmelik (AB) 1169/2011 (perakende ambalajda Almanca etiket, alerjen vurgusu) | hs 0802, 2008; channel b2c | DEST | koşullu | https://eur-lex.europa.eu/eli/reg/2011/1169/oj |
| R10 | Almanya Ambalaj Kanunu (VerpackG) – LUCID kaydı (ürünü Almanya'da piyasaya ilk süren taraf için) | all; channel b2c | DEST | koşullu | https://lucid.verpackungsregister.org |
| R11 | AB Genel Ürün Güvenliği Yönetmeliği (GPSR) 2023/988 – tüketiciye satışta AB'de sorumlu ekonomik operatör | sectors: tekstil, diger; channel b2c | DEST | koşullu | https://eur-lex.europa.eu/eli/reg/2023/988/oj |
| R12 | Sınırda Karbon Düzenleme Mekanizması (SKDM / CBAM) – Yönetmelik (AB) 2023/956: AB'li ithalatçı gömülü emisyon verisi isteyecek (2026'dan itibaren kesin dönem; ithalatçı bazında yıllık eşik var – güncelini kontrol edin) | hs 7318 | DEST | zorunlu | https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en |
| R13 | Araç Ömrünü Tamamlamış Araçlar Direktifi 2000/53/AT – otomotiv müşterileri altı değerlikli krom (Cr VI) içermeyen kaplama ister | hs 7318; sector otomotiv_yan_sanayi | DEST | koşullu | https://eur-lex.europa.eu/eli/dir/2000/53/oj |
| R14 | IMDS malzeme verisi girişi (otomotiv OEM tedarik zincirlerinde yaygın talep) | sector otomotiv_yan_sanayi | DEST | önerilen | https://www.mdsystem.com |
| R15 | Yapısal (inşaat) kullanım için cıvata setlerinde CE işareti – Yapı Malzemeleri Yönetmeliği | hs 7318; only when `structural_use` is true | DEST | koşullu | https://single-market-economy.ec.europa.eu/sectors/construction/construction-products-regulation-cpr_en |

**Level labels:** zorunlu = Mandatory, koşullu = Conditional, önerilen = Recommended. Store the Turkish values as given and translate them in the UI. Confidence labels: yüksek = High, orta = Medium, düşük = Low.

**Rule matching:** a rule matches when every constraint it has is satisfied. A missing constraint matches everything. Constraints are country, HS prefix, sector, channel and `structural_use`. An HS prefix matches the start of the confirmed HS6 code, so `0802` matches `0802.51`. A rule with no channel applies to both B2B and B2C.

**kb_incentives** (amounts intentionally omitted). Stages: ilk_ihracat | sertifika | fuar | e_ihracat | finansman. An empty sector list means all sectors.

| id | name_tr | provider | stages | sectors | source_url |
|---|---|---|---|---|---|
| I1 | Pazara Giriş Belgeleri Desteği (sertifika, test, analiz giderleri) | Ticaret Bakanlığı | sertifika | all | https://ticaret.gov.tr/destekler |
| I2 | E-İhracat Destekleri (e-ticaret pazar yeri üyeliği, dijital pazarlama) | Ticaret Bakanlığı | e_ihracat | all | https://ticaret.gov.tr/destekler |
| I3 | Yurt Dışı Fuar Katılım Desteği | Ticaret Bakanlığı | fuar | all | https://ticaret.gov.tr/destekler |
| I4 | Pazar Araştırması ve Pazara Giriş Desteği | Ticaret Bakanlığı | ilk_ihracat | all | https://ticaret.gov.tr/destekler |
| I5 | Tasarım Desteği | Ticaret Bakanlığı | ilk_ihracat | tekstil | https://ticaret.gov.tr/destekler |
| I6 | KOSGEB KOBİ destek programları (uluslararasılaşma) | KOSGEB | ilk_ihracat | all | https://www.kosgeb.gov.tr |
| I7 | Sevk Öncesi İhracat Kredisi | Türk Eximbank | finansman | all | https://www.eximbank.gov.tr |
| I8 | İhracat Kredi Sigortası (alıcının ödememe riskine karşı) | Türk Eximbank | finansman, ilk_ihracat | all | https://www.eximbank.gov.tr |
| I9 | Kolay İhracat Platformu – ücretsiz pazar raporu ve potansiyel alıcı listeleri (e-Devlet ile giriş) | Ticaret Bakanlığı | ilk_ihracat | all | https://www.kolayihracat.gov.tr |

Provider values: Ticaret Bakanlığı | KOSGEB | Türk Eximbank | TİM. Write `name_en` and the English summary for each incentive.

### 5.3 Admin knowledge base

Admin-only pages: list, add, edit, mark verified (records `verified_by` and `last_verified`), CSV import and export. Unverified records show a grey badge "Demo verisi – doğrulanmadı" / "Demo data – not verified". Verified records show "Doğrulandı · {tarih}" / "Verified · {date}".

## 6. Phases

Build all five, in order. Each phase lists what to build and its acceptance criteria.

### Phase 1 — Foundation

**Auth**
- Register (name, email, password of at least 8 characters, KVKK consent checkbox required, with the privacy notice ("Aydınlatma Metni") in a modal, in both languages), login, logout, protected routes.

**Onboarding wizard (3 steps, mobile-first, both languages)**
1. **Firma bilgileri:** company name; city (dropdown of the 81 provinces); sector (Tekstil / Gıda / Otomotiv Yan Sanayi / Diğer); employee count; founding year; certifications, multi-select (ISO 9001, ISO 22000, BRC, IFS, OEKO-TEX, Helal, Organik, CE, Diğer); phone; email; website (optional); logo upload (optional).
2. **İlk ürününüz:** product name; description ("Ürününüzü bir müşteriye anlatır gibi yazın"); material or ingredients; unit (kg / adet / metre / koli); minimum order quantity; unit weight in kg (optional); **gizli taban fiyat** with the tooltip "Bu fiyat alıcılara asla gösterilmez; ajan bunun altına teklif vermez."; 1–6 photos with previews.
3. **Hedef pazar:** Almanya (DE) is selectable. Hollanda, Fransa, ABD, BAE and Irak appear as "Yakında" / "Coming soon" and are disabled.

Save to `companies`, `products` and `markets`. A "Firmam" page edits the company. A "Ürünlerim" page adds and edits products.

**Dashboard ("İhracat Panosu")**
- Header with the company name and the target-market flag.
- Three cards, each with a status badge and a primary button:
  - **Dijital Vitrin:** "Vitrinimi oluştur" or "Vitrini görüntüle" (status: Taslak / Yayında)
  - **Mevzuat Bekçisi:** "Uygunluk kontrolü yap" (status: Yapılmadı / Hazırlık skoru %X)
  - **Alıcı Ajanı:** "Alıcı bul" (status: N lead, M onay bekleyen mesaj)
- Roadmap strip: Profil → Vitrin → Mevzuat → İlk teklif. Each step turns green when done.
- A notifications area (new RFQs).
- Placeholder pages for the three modules, filled in by later phases.

**Backend plumbing**
- `llm_service` as in section 4.5.
- `storage_service`: accept only jpg, png and webp, checked by file signature, not extension. Maximum 8 MB. Resize images wider or taller than 1600 px.
- `GET /api/health`: app status, LLM provider name and whether a key is set.
- Admin-only test endpoint that calls `generate_json` on a small schema and returns the validated result.
- Seed script (`python -m app.seed`), safe to run twice. It creates one admin user and three demo producers with products, and no storefronts yet:
  - **Gaziantep, "Bozkurt Antep Fıstığı" (gıda):** kabuklu kavrulmuş Antep fıstığı and iç fıstık, 1 kg and 10 kg packs, ISO 22000 and Helal certified.
  - **Denizli, "Pamukkale Havlu Atölyesi" (tekstil):** %100 pamuk havlu and bornoz, OEKO-TEX.
  - **Bursa, "Uludağ Bağlantı Elemanları" (otomotiv yan sanayi):** galvanizli çelik cıvata ve somun, ISO 9001 and IATF 16949.
  - Write realistic Turkish descriptions. Use royalty-free placeholder photos if you can get them. Otherwise generate simple labelled placeholder images with Pillow and say so.
  - Also seed the knowledge base (section 5.2) and the demo leads (phase 4).
  - Demo logins use the password from `SEED_PASSWORD`.

**UI style**
- Clean, trustworthy, government-adjacent but modern. Primary colour #C8102E, used sparingly. Lots of white space, navy text, large tap targets. A TR | EN language switch sits in the header and applies to every producer screen. Turkish characters (ş ğ ı İ ö ü ç) must render everywhere, so use a font that includes them.

**Acceptance**
- [ ] Register, accept KVKK, log out, log back in.
- [ ] The 3-step onboarding works with photos at 375 px width with no layout breaks.
- [ ] The dashboard shows the company, the three cards and the roadmap strip.
- [ ] The TR / EN switch changes every producer screen, and the choice survives logout and login.
- [ ] Logging in as a seeded demo company shows its data.
- [ ] `/api/health` reports the LLM status. The admin test endpoint returns validated JSON (tested with a mock).
- [ ] The floor price is absent from every non-owner response (test).
- [ ] pytest passes.

### Phase 2 — Dijital Vitrin (storefront)

Key design decision: the AI produces a structured `site_config` JSON, and our own templates render it. Never generate raw HTML or React code per user.

**Intake ("Vitrinimi oluştur")**
- Pre-filled from the company and products. A large text box, plus a microphone button that uses the Web Speech API with `tr-TR` for dictation. Hide the button if the browser does not support it.
- Positioning: **B2B Toptan** (wholesale catalogue, the default) or **B2C Perakende** (retail-style showcase). Both end in a quote request. There is no checkout.

**Generation (`storefront_service`)**
A visible multi-step agent. Each step is logged to `agent_runs` and shown with AgentSteps (phase 5).
1. **Ürün analizi:** send photos and Turkish text to the LLM (vision). Extract attributes, selling points, quality signals and suitable buyer types.
2. **Pazar uyarlaması:** adapt the message to German B2B buyers: precise specs, certifications, MOQ, lead time, packaging, Incoterms offered, reliability over hype. Avoid superlatives that German consumer law could treat as misleading ("best in the world").
3. **İçerik üretimi:** produce `site_config` in German (de) and English (en), plus a review copy (`review`) in the producer's UI language. Sections:
   - hero: headline, sub-headline, call to action "Angebot anfordern"
   - about: story, city, year, team size, certification badges
   - product cards: name, short and long description, specs table, MOQ, packaging, photos
   - why us: three or four factual points
   - export info: Incoterms offered, lead time, sample policy. Use only what the producer gave. Mark missing fields as missing. Never invent them.
   - RFQ form
   - footer and legal links
   - SEO: page title, meta description, slug suggestion
4. **Tema:** choose one of three templates by sector. The user can change it. `industrial` (Bursa: dark navy, technical), `natural` (food: warm cream and green), `textile` (soft, light, photo-heavy).

Validate `site_config` with Pydantic. Retry on failure. If it still fails, use the deterministic template so the demo never shows a blank page.

**Editor**
- Split view. Left: the section list with editable fields, in tabs DE / EN / Review (read-only, in the producer's UI language). Right: a live preview with a desktop and mobile toggle.
- "Bu bölümü yeniden yaz" regenerates one section, with an optional instruction ("daha kısa", "daha teknik").
- Reorder and remove photos.
- Fields the AI marked as missing are yellow, with the label "Bu bilgiyi siz girmelisiniz" / "You need to enter this".

**Publish**
- "Yayınla" publishes to `/s/{slug}` with no login. Unpublish is possible.
- The slug is made from the company name with Turkish transliteration (ş→s, ğ→g, ı→i, ö→o, ü→u, ç→c). It must be unique and editable.
- Public storefront: language switcher (DE / EN), responsive, `<html lang>` set, OpenGraph tags, favicon from the logo.
- Legal pages: an **Impressum** (filled from company data; the producer sees a checklist of required fields) and a **Datenschutzerklärung** covering the RFQ form. Both are linked in the footer. Show this note in the producer's language: "Bu metinler şablondur; yayın öncesi bir hukukçuya kontrol ettiriniz." / "These texts are templates; have a lawyer check them before publishing."
- **RFQ form:** company name, contact name, email, country, product(s) of interest, quantity, message, and a required GDPR consent checkbox. Include a honeypot field and a rate limit. A submission creates a lead (source `rfq`, badge "Sıcak lead") and a dashboard notification.
- After publishing, a success screen shows the URL, a QR code and a "Paylaş" button. Use the Web Share API, and copy the link as the fallback.

**Acceptance**
- [ ] For the seeded Gaziantep company, generation takes under about 60 seconds, and each step shows live.
- [ ] The German text uses only facts from the input. Missing fields appear as missing in the editor.
- [ ] Edit text, regenerate one section, switch template and publish.
- [ ] `/s/{slug}` works logged out, on mobile and desktop, in DE and EN.
- [ ] The Impressum and privacy pages exist and are linked in the footer.
- [ ] An RFQ submission creates a lead visible on the dashboard.
- [ ] With the LLM key removed, generation falls back to the template instead of crashing.

### Phase 3 — Mevzuat Bekçisi (compliance and incentives)

**Architecture rule (critical):** this is retrieval-grounded, not free generation. The LLM may (a) suggest HS codes with reasoning, (b) select which knowledge-base records apply and explain them in plain language in the producer's UI language, and (c) personalize next steps. It must never output a rule, tariff rate, deadline or support amount that is not in the record it was given. Enforce this in the prompt and in code: every checklist item must reference an existing `kb_rules.id`, and every incentive must reference an existing `kb_incentives.id`. Drop anything that does not.

**Knowledge base:** section 5.3. The admin edits a rule and marks it verified, and the badge changes.

**Flow ("Uygunluk kontrolü yap")**
Inputs: the product, the channel (B2B by default, or B2C), and a `structural_use` checkbox (default off). The flow is a visible agent, and each step is logged.

1. **GTİP tahmini:** the LLM receives the product name, description, material, processing (roasted or raw) and photos. It returns the top three HS6 candidates, each with Turkish reasoning and a confidence level (yüksek | orta | düşük). Validate the format `NNNN.NN`. Mark candidates that appear in `kb_hs_codes` as "listemizde mevcut". Show the warning and a link to the Ticaret Bakanlığı tariff page. The user must choose one before continuing. Demo moment: for "kavrulmuş Antep fıstığı", explain why 2008.19 is suggested rather than 0802.51.
2. **Kural eşleştirme:** first a deterministic filter (section 5.2 rule matching). Then the LLM receives only the filtered records and returns, for each one: applies (yes or no), a one-sentence personalized reason, and a personalized next step. Drop any id that is not in the filtered set.
3. **Teşvik eşleştirme:** the same pattern over `kb_incentives`, filtered by sector. The LLM gets the company profile and the checklist as context. For example, an OEKO-TEX requirement points to I1. Drop unknown ids.
4. **Rapor:** the results page shows:
   - the confirmed GTİP and the candidates
   - the checklist, grouped into "Türkiye tarafı" / "Turkish side" and "Hedef pazar" / "Target market". Each item has a badge (zorunlu / koşullu / önerilen; Mandatory / Conditional / Recommended in English), its source link and its "son doğrulama" date, and a checkbox "Bu bende var / tamamlandı".
   - the incentives, each with "Neden uygun?" and a source link
   - **Hazırlık skoru:** deterministic, not from the LLM. The weighted percentage of applicable items ticked, with weights zorunlu = 3, koşullu = 2, önerilen = 1. Show the formula in a tooltip. It recalculates live as boxes are ticked.
   - **Sonraki 3 adım:** the LLM picks the three most important unticked items and writes a short plan. Validate the ids.
   - **PDF indir:** a branded İhracat Hazırlık Raporu (Export Readiness Report) in the producer's UI language, with the footer "Bu rapor bilgilendirme amaçlıdır; resmi mevzuat ve gümrük müşaviri görüşü esastır." / "This report is for information only; official regulations and a customs broker's advice take precedence."
5. **No match:** if no rule matches (unsupported country or product), show "Bu ürün/ülke için doğrulanmış verimiz henüz yok" / "We do not yet have verified information for this product and country", and the contacts İhracatçı Birliği, İTO/İSO and Ticaret Müşavirliği. Never improvise a rule.

**Test cases from the seed data**
- Gaziantep roasted pistachio → top suggestion 2008.19 with an explanation. Checklist includes R1, R3, R7, R8, and R9 and R10 only for B2C.
- Denizli towels → 6302.60. Checklist includes R1, R2, R4, R5, R6. Incentives include I1.
- Bursa bolts → 7318.15. Checklist includes R1, R2, R12, R13.

**Acceptance**
- [ ] The seed loads. The admin edits a rule, marks it verified, and the badge changes.
- [ ] The three test cases above pass.
- [ ] Every checklist item links to its source. A test confirms no item exists without a knowledge-base id.
- [ ] Ticking items changes the score, and the formula is visible.
- [ ] The PDF downloads with Turkish characters rendered correctly.
- [ ] A test with a mocked LLM that returns an invented rule id shows the id is dropped.

### Phase 4 — Alıcı Ajanı (buyer outreach, human-approved)

The agent researches, drafts and calculates. The producer approves every outbound message and every quote. Nothing leaves the system without an explicit click on "Onayla ve Gönder".

**Lead sources (no scraping)**
- **RFQ submissions** from the storefront. These are the highest priority and are shown first with the "Sıcak lead" badge.
- **CSV import** with column mapping (company, country, contact name, email, website, notes). Each import asks for a `source_note` ("Bu kişiyi nereden buldunuz?" / "Where did you find this contact?", for example "Anuga 2025 fuar kataloğu", "Kolay İhracat Platformu alıcı listesi", "kartvizit"). Explain why it is needed, in the current UI language: GDPR requires knowing where business contact data came from.
- **Manual add** form, which also requires a `source_note`.
- **Demo leads:** six fictional German importers per demo company, marked "DEMO – kurgusal firma" everywhere, with `@example.com` emails. Invent names that do not match real companies. Set `is_demo: true`.

**Scoring (`scoring`, deterministic, 0–100, no LLM)**
- Source: RFQ 40, csv_import 20, manual 15.
- Product match, 0–30: keyword overlap between the lead's notes or website and the product names and keywords. Document the exact rule in code.
- Country equals the target market: 15.
- Contact email present: 15.
- Show the breakdown on hover. The lead table is sortable.

**Statuses** (codes in brackets): Yeni / New (new) → Taslak hazır / Draft ready (draft_ready) → Gönderildi / Sent (sent) → Yanıt geldi / Reply received (replied) → Teklif verildi / Quote sent (quoted) → Kazanıldı / Won (won); Kaybedildi / Lost (lost). "İletişim kurma" / "Do not contact" (do_not_contact) is a blocking status (see the reply assistant).

**Outreach drafting ("İlk teması hazırla")**
- The LLM drafts a short first-contact email in the buyer's language: German for DE, English otherwise. It uses only data from the company, product and storefront: who we are, what we make, two or three concrete facts (certifications, MOQ, lead time), the storefront link, an offer to send samples, and a polite opt-out line in the same language ("If this is not relevant for you, just let us know and we will not contact you again.").
- For RFQ leads, the draft answers their actual request instead of a cold introduction.
- Show side by side: the DE or EN text (editable) and a translation into the producer's UI language (read-only, regenerated after each edit).
- Tone controls: "Daha resmi" / "More formal", "Daha kısa" / "Shorter", "Numune teklifini vurgula" / "Emphasise the sample offer".
- Hard rules, in the prompt and in code: no prices in a first cold email, never mention the floor price, no false claims, about 150 words at most.

**Approval queue ("Onay Bekleyenler")**
- A page and a dashboard counter list every draft (messages and quotes). Actions: Onayla ve Gönder, Düzenle, Reddet (with a reason).
- "Onayla ve Gönder" in mailto mode sets `status: sent`, `approved_by`, `approved_at` and `delivery_channel: mailto`. It then opens the producer's mail client with the subject and body filled in, or copies them to the clipboard. The UI label is "Mail uygulamasına aktarıldı" / "Handed to your mail app".
- Add the `EMAIL_PROVIDER` flag, off by default, and an interface for a future sending provider. Do not build a provider.
- Rate limit: at most 20 cold outreach approvals per day per company.

**Reply assistant**
- The producer pastes a buyer's reply in any language. The agent returns: a translation into the producer's UI language; a three-bullet summary; the intent (codes: interested | asks_price | asks_samples | not_interested | other, labelled in the UI language); the buyer's requested terms (quantity, Incoterm, delivery date, certifications); red flags (upfront payment requests to unusual accounts, pressure tactics, mismatched domains, which are common export scams); and a suggested reply that goes into the approval queue.
- If the intent is not_interested, or the buyer asks not to be contacted, set the lead to do_not_contact ("İletişim kurma" / "Do not contact") and block further drafts for that lead.

**Quote builder ("Teklif hazırla")**
- Inputs: product; quantity; unit price (default suggestion = floor price × 1.25, editable); currency (EUR | USD); Incoterm (EXW, FCA, FOB, CIF, DAP, each with a one-line explanation in both languages of who pays what); payment terms (dropdown: "Peşin" / "Cash in advance", "%30 avans %70 yükleme öncesi" / "30% advance, 70% before loading", "Akreditif (L/C)" / "Letter of credit (L/C)", "Vesaik mukabili" / "Documents against payment"); validity date.
- Refuse a unit price below the floor price and explain why, in the current UI language. The floor value must never appear in buyer-facing text or in the PDF.
- **Logistics estimator (`logistics_service`):** deterministic, labelled "tahmini", Turkey → Germany by road.
  - Gross weight = `unit_weight_kg` × quantity × (1 + packaging %). Packaging % comes from the rate table. If `unit_weight_kg` is missing, ask for it before estimating.
  - Use an admin-editable table, `logistics_rates`. Seed it with obviously illustrative placeholder values, labelled "ÖRNEK – gerçek forwarder teklifiyle değiştirin":
    - Parsiyel (LTL): per-kg rate band by weight bracket
    - Komple tır (FTL): flat rate per truck. Trucks = ceil(gross kg ÷ truck capacity kg). Capacity is in the table.
    - Numune (express courier): per-kg rate with a minimum charge
  - Show the calculation line by line.
  - Include freight in the price only for CIF and DAP.
- **Output:** a quote or proforma PDF in the buyer's language (DE or EN), with branding, a product table, Incoterm, payment terms, validity and a preview for the producer in their UI language. A quote goes into the approval queue before it can be sent.
- **Sample request:** one click creates a "Numune gönderimi" task with a courier estimate and a checklist (proforma for samples, labelling, courier booking).

**Pipeline view**
- A kanban board of leads by status, with counters from real database counts: leads, approved messages sent, replies, quotes sent, deals won.

**Acceptance**
- [ ] An RFQ from the storefront shows as a hot lead. "İlk teması hazırla" produces German text and a translation in the producer's UI language.
- [ ] A test confirms no message reaches `sent` without approval fields.
- [ ] A test confirms the quote builder refuses a unit price below the floor, and the floor never appears in generated text or the PDF.
- [ ] The logistics estimate shows its formula and the "tahmini" label. An admin can edit the rates.
- [ ] Pasting a German reply returns a translation, the intent, the extracted terms and a draft reply in the queue.
- [ ] Demo leads are marked as fictional everywhere they appear.
- [ ] The quote PDF renders correctly in German, and the producer's preview is available in their UI language.

### Phase 5 — Demo mode, reliability and polish

**Canlı Demo**
- A hidden admin-only route, `/demo`, with three buttons: Gaziantep, Denizli, Bursa. Each resets that demo company to a clean state (profile and product filled in, no storefront, no report, demo leads present) in under 3 seconds. On reset, send one LLM ping so the first real call is not cold.
- A floating "Demo rehberi" / "Demo guide" panel, toggled with `Ctrl+Shift+D`, shows the next script step and a stopwatch.

**Demo script (about 3 minutes, Gaziantep → Germany)**
1. (0:00) The dashboard for Bozkurt. The roadmap is at 1/4.
2. (0:15) Dijital Vitrin: dictate one sentence with the mic, then generate. The agent steps animate. Publish, then show `/s/bozkurt-pistazien` in German on a phone frame with the QR code.
3. (1:15) Mevzuat Bekçisi: the agent proposes 2008.19 and explains roasted against raw. The checklist shows aflatoxin and the increased official controls, with sources. Incentives are matched. Then the readiness score and the PDF.
4. (2:15) Open the storefront in a second tab and submit an RFQ as a German buyer. It appears on the dashboard as a hot lead. Then "İlk teması hazırla" gives German text and its translation. Then a quote with the DAP Germany logistics estimate, and "Onayla ve Gönder".
5. (3:00) The dashboard: roadmap at 4/4, counters updated with real data.

**Reliability**
- **Cached fallback:** for the three demo companies, store the last successful output of each AI step in `demo_cache`. If a live call fails or passes the demo timeout (25 s), use the cached output. Show only a small dot in the demo panel, visible to the presenter.
- Show streaming or step progress for every long operation. Nothing freezes the UI.
- A global React error boundary with a friendly Turkish message and a retry button.
- Test the layout at 1280×720, 1920×1080 and 375 px.

**AgentSteps component**
- A vertical list of steps. States: bekliyor / waiting, çalışıyor / running, tamamlandı / done, yedek kullanıldı / fallback used. Each step shows its elapsed time and a one-line explanation in both languages, for example "Fotoğraflardan ürün özellikleri çıkarılıyor…" or "Alman alıcı beklentilerine göre metin uyarlanıyor…" / "Adapting the text to German buyer expectations…". Use it in all three modules.

**Etki (impact) panel: honest version**
- Per company: time from signup to published storefront, to readiness report, and to first approved outreach. Use real timestamps.
- Admin: platform-wide counts of companies, storefronts published, reports generated, approved messages and RFQs received. Real counts only.
- Do not show projected national figures in the app.

**Polish**
- Both languages complete: every string in `tr.json` and `en.json`, checked by the key-parity test, with the wording read through in both. Empty states with a clear next action. Loading skeletons.
- Accessibility: proper labels, focus states, WCAG AA contrast, keyboard navigation for the main flows.
- Storefront Lighthouse mobile performance of 90 or more: lazy-load and compress images. Run Lighthouse if you can. If you cannot, say so.
- **Security:** rate limits on auth and RFQ endpoints; input validation; CORS restricted to `FRONTEND_ORIGIN`; upload type checks; no secrets in the frontend bundle; an ownership check on every company-scoped endpoint.
- **KVKK and GDPR:** account deletion removes the company's data (products, storefront, leads, messages, quotes, files) after a confirmation step. Data export as JSON, covering the user's own data and excluding the password hash. A privacy notice page (Aydınlatma metni) in the producer app.
- **`docs/RUNNING.md`:** how to run locally on Windows (PowerShell), the environment variables, how to seed, and how to reset the demo.

**Acceptance**
- [ ] The full five-step demo script takes 3.5 minutes or less, and runs twice in a row after a `/demo` reset.
- [ ] After one successful run has filled the cache, the demo completes with the LLM key removed.
- [ ] The ownership tests pass. The floor price never leaks.
- [ ] The storefront's Lighthouse mobile score is 90 or more, or the docs say it was not measured.
- [ ] Switching to English leaves no Turkish UI text on producer screens. The producer's own typed input is the only exception. Walk through every screen in both languages and list any gaps.

## 7. Cross-cutting tests (pytest, mocked LLM, no network)

- **Ownership:** user A cannot read user B's products, leads, storefronts or floor prices, on every company-scoped endpoint.
- **Floor price:** absent from non-owner responses, LLM prompts, PDFs and generated text. A quote below the floor is refused.
- **Approval gate:** no message reaches `sent` without approval fields. The cold outreach limit of 20 per day is enforced.
- **Knowledge-base guard:** every checklist and incentive item has an existing id. A mocked LLM that returns an invented id or invented rule has it dropped.
- **Logistics math:** gross weight, FTL trucks, LTL bands, and freight only for CIF and DAP.
- **Scoring:** each lead score component, and the readiness formula with its weights.
- **Slugs:** Turkish characters are transliterated and slugs are unique.
- **Schemas:** JSON validation, and retry on invalid output.
- **Language:** `tr.json` and `en.json` have identical keys. Every KB record has both language fields. The `ui_language` value reaches every explanation prompt.
- **Seed cases:** the three Phase 3 test cases.

## 8. Final report

Write `docs/ACCEPTANCE.md` and repeat the summary in your final message: per phase, PASS or FAIL for each criterion with evidence; what you skipped or simplified; the decisions you made; the Windows run commands; and the step-by-step UI test script.
