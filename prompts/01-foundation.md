# PROMPT 01 — Foundation: auth, company onboarding, dashboard, LLM service

---

Build Phase 1 of KOBİ-GPT (see the project context I gave you). Goal: a producer can sign up, describe their company, add products, and land on a dashboard that leads to the three modules. Plus the backend plumbing every later phase relies on.

## Build

### 1. Auth
- Register (name, email, password, KVKK consent checkbox — required, with a short Turkish "Aydınlatma Metni" in a modal), login, logout, JWT stored safely, protected routes.
- Admin flag on users (set via seed / env, no UI needed to grant it).

### 2. Onboarding wizard (Turkish, 3 steps, mobile-friendly)
1. **Firma bilgileri:** company name, city (dropdown of 81 provinces), sector (Tekstil / Gıda / Otomotiv Yan Sanayi / Diğer), employee count, founding year, certifications (multi-select: ISO 9001, ISO 22000, BRC, IFS, OEKO-TEX, Helal, Organik, CE, Diğer), phone, email, website (optional), logo upload (optional).
2. **İlk ürününüz:** product name, free-text description in Turkish ("Ürününüzü bir müşteriye anlatır gibi yazın"), material/ingredients, unit (kg / adet / metre / koli), minimum order quantity, **gizli taban fiyat** (private floor price, with a tooltip: "Bu fiyat alıcılara asla gösterilmez; ajan bunun altına teklif vermez."), 1–6 photo uploads with previews.
3. **Hedef pazar:** pick a target country. Only **Almanya (DE)** is fully supported in the MVP; show others (Hollanda, Fransa, ABD, BAE, Irak) as "Yakında" (coming soon) and disabled.

Save as `companies`, `products`, `markets`. User can edit everything later from a "Firmam" page and add more products from a "Ürünlerim" page.

### 3. Dashboard ("İhracat Panosu")
- Header with company name and target market flag.
- Three large cards, one per module, each with a status badge and a primary button:
  - **Dijital Vitrin** — "Vitrinimi oluştur" / "Vitrini görüntüle" (status: Taslak / Yayında)
  - **Mevzuat Bekçisi** — "Uygunluk kontrolü yap" (status: Yapılmadı / Hazırlık skoru %X)
  - **Alıcı Ajanı** — "Alıcı bul" (status: N lead, M onay bekleyen mesaj)
- An "İhracat yol haritanız" progress strip: Profil → Vitrin → Mevzuat → İlk teklif. Each step turns green when done.
- Placeholder pages for the three modules (built in later phases).

### 4. Backend plumbing
- `llm_service` as described in the context: `generate_text()`, `generate_json(schema)`, image support, timeout (default 45 s), retries on invalid JSON, logging to `agent_runs`. Read provider + model from env.
- `storage_service` for uploads (validate type: jpg/png/webp; max 8 MB; resize large images to max 1600 px).
- Health endpoint `/api/health` that also reports whether the LLM key is configured.
- Seed script: one admin user + three demo companies with products (no storefronts yet):
  - **Gaziantep — "Bozkurt Antep Fıstığı" (gıda):** kabuklu kavrulmuş Antep fıstığı + iç fıstık, 1 kg & 10 kg packs, ISO 22000 + Helal.
  - **Denizli — "Pamukkale Havlu Atölyesi" (tekstil):** %100 pamuk havlu ve bornoz, OEKO-TEX.
  - **Bursa — "Uludağ Bağlantı Elemanları" (otomotiv yan sanayi):** çelik cıvata ve somun (galvanizli), ISO 9001 + IATF 16949.
  Use placeholder product photos (royalty-free or generated) and realistic Turkish descriptions.

### 5. UI style
- Clean, trustworthy, government-adjacent but modern. Primary color deep red (#C8102E) used sparingly, lots of white, navy text. Large tap targets. Turkish characters must render everywhere (ş, ğ, ı, İ, ö, ü, ç).

## Acceptance criteria (verify each before reporting back)
- [ ] I can register, accept KVKK, log out and log back in.
- [ ] I can complete the 3-step onboarding with photos on a phone-sized screen (375 px wide) without layout breaks.
- [ ] The dashboard shows my company, the three module cards and the roadmap strip.
- [ ] Logging in as a seeded demo company shows its data.
- [ ] `/api/health` reports LLM status; a test endpoint (admin only) proves `generate_json` returns validated JSON.
- [ ] The floor price is never returned by any non-owner API response.
- [ ] pytest passes.
