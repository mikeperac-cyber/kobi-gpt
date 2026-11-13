# PROMPT 04 — Module 3: Alıcı Ajanı (Buyer Outreach & Quote Agent — human-approved)

---

Build Phase 4: help the producer turn leads into a first deal. The agent researches, drafts and calculates; **the producer approves every outbound message and every quote**. Nothing leaves the system without an explicit click on "Onayla ve Gönder".

## Build

### 1. Lead sources (no scraping)
- **RFQ submissions** from the storefront (already created in Phase 2) — highest priority, shown first with a "Sıcak lead" badge.
- **CSV import** with column mapping (company, country, contact name, email, website, notes). Required field: `source_note` ("Bu kişiyi nereden buldunuz?" e.g. "Anuga 2025 fuar kataloğu", "Kolay İhracat Platformu alıcı listesi", "kartvizit"). Explain in Turkish why: GDPR requires knowing where business contact data came from.
- **Manual add** form.
- **Demo leads**: seed 6 fictional German importers per demo company, clearly marked "DEMO – kurgusal firma" everywhere, with obviously fictional `example.com`-style emails. Never present them as real companies.

### 2. Lead scoring
Deterministic score 0–100 (no LLM): source (RFQ 40, imported 20, manual 15), product match with lead notes/website keywords (0–30), country = target market (15), contact email present (15). Show the breakdown on hover. Sortable lead table with status: Yeni → Taslak hazır → Gönderildi → Yanıt geldi → Teklif verildi → Kazanıldı / Kaybedildi.

### 3. Outreach drafting
On a lead, "İlk teması hazırla":
- LLM drafts a short first-contact email **in the buyer's language** (German for DE, English otherwise) using only data from the company, product and storefront: who we are, what we make, 2–3 concrete facts (certifications, MOQ, lead time), a link to the storefront, an offer to send samples, and a polite opt-out line ("If this is not relevant for you, just let us know and we will not contact you again.").
- For RFQ leads: the draft answers their actual request instead of a cold intro.
- Show side by side: **German/English text (editable)** | **Turkish translation (read-only, regenerated after edits)** so the producer understands exactly what they're sending.
- Tone controls: "Daha resmi", "Daha kısa", "Numune teklifini vurgula".
- Hard rules in the prompt and in code: no prices in the first cold email; never mention the floor price; no false claims; max ~150 words.

### 4. Approval queue ("Onay Bekleyenler")
- A dedicated page + dashboard counter listing every draft (emails and quotes). Actions: Onayla ve Gönder / Düzenle / Reddet (with reason).
- **Sending in the MVP:** "Onayla ve Gönder" marks the message approved and opens it in the user's own mail client via `mailto:` (subject + body prefilled) or copies it to the clipboard. Behind a feature flag `EMAIL_PROVIDER` (e.g. Resend / SMTP) allow real sending from the app later — off by default. Store `approved_by` and `approved_at` for every sent message (audit trail).
- Rate limit: max 20 cold outreach approvals per day per company (anti-spam).

### 5. Reply assistant
- "Gelen yanıtı yapıştır": the producer pastes the buyer's reply (any language).
- Agent returns: Turkish translation, 3-bullet summary, detected intent (ilgileniyor / fiyat istiyor / numune istiyor / ilgilenmiyor / diğer), buyer's requested terms (quantity, Incoterm, delivery date, certifications), red flags (e.g. upfront payment requests to unusual accounts, pressure tactics, mismatched domains — common export scams), and a suggested reply draft that goes into the approval queue.
- If intent = "ilgilenmiyor" or the buyer asks not to be contacted: mark the lead "İletişim kurma" and block further drafts.

### 6. Quote builder ("Teklif hazırla")
- Inputs: product, quantity, unit price (pre-filled suggestion = floor price × 1.25, editable; the app refuses to generate a quote below the floor price and explains why), currency (EUR / USD), Incoterm (EXW, FCA, FOB, CIF, DAP — each with a one-line Turkish explanation of who pays what), payment terms (dropdown incl. "Peşin", "%30 avans %70 yükleme öncesi", "Akreditif (L/C)", "Vesaik mukabili"), validity date.
- **Logistics estimator (`logistics_service`)** — deterministic, clearly labelled "tahmini": Turkey → Germany by road. Use an editable admin rate table, seeded with **illustrative placeholder values** the producer/admin must replace with real forwarder quotes:
  - Parsiyel (LTL): per-kg rate band by weight bracket
  - Komple tır (FTL): flat rate per truck
  - Numune (express courier): per-kg rate, minimum charge
  Compute based on gross weight (from product unit weight × quantity + packaging %). Show the calculation line by line. Include freight in the price only for Incoterms where the seller pays it (CIF/DAP).
- Output: a professional quote/proforma PDF **in the buyer's language** (German or English) with company branding, product table, Incoterm, payment terms, validity, and a Turkish preview for the producer. The quote goes into the approval queue before it can be sent.
- Sample request flow: one click creates a "Numune gönderimi" task with courier cost estimate and a checklist (proforma for samples, labelling, courier booking).

### 7. Pipeline view
Kanban board of leads by status + simple counters: leads, approved messages sent, replies, quotes sent, deals won. These are real counts from the database, never fabricated.

## Acceptance criteria
- [ ] An RFQ from the storefront shows up as a hot lead; drafting a reply produces German text + Turkish translation.
- [ ] No message can reach "sent" status without an approval record (write a test).
- [ ] The quote builder refuses a unit price below the floor price; the floor price never appears in any generated text or PDF (write a test).
- [ ] Logistics estimate shows its formula and the "tahmini" label; rates are editable by admin.
- [ ] Pasting a German reply returns translation, intent, extracted terms and a draft reply in the queue.
- [ ] Demo leads are visibly marked as fictional everywhere they appear.
- [ ] Quote PDF renders correctly in German with Turkish preview available.
