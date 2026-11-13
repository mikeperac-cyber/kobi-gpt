# PROMPT 03 — Module 2: Mevzuat ve Gümrük Bekçisi (Reg-AI)

---

Build Phase 3: for a product + target country, the app suggests the GTİP/HS code, produces a compliance checklist and matches Turkish export incentives, then produces an "İhracat Hazırlık Raporu" (Export Readiness Report) as a PDF.

**Architecture rule (critical):** this is retrieval-grounded, not free generation. The LLM may only (a) suggest HS codes with reasoning, (b) select which knowledge-base records apply to this product and explain them in plain Turkish, (c) personalize next steps. It must never output a rule, tariff rate, deadline or support amount that is not in the knowledge-base record it was given. Enforce this in the prompt AND in code: every checklist item in the output must reference a `kb_rules._id` that exists; drop any item that does not.

## Build

### 1. Knowledge base (admin-editable)
Collections:
- `kb_hs_codes` — hs6, description_en, description_tr, notes, sector
- `kb_rules` — id, title_tr, summary_tr (plain Turkish, 2–4 sentences), applies_to {countries[], hs_prefixes[], sectors[], channel: b2b | b2c | both}, side (TR = Turkish-side requirement | DEST = destination market), level (zorunlu | koşullu | önerilen), what_to_do_tr, documents[], source_name, source_url, last_verified (date or null), verified (bool)
- `kb_incentives` — id, name_tr, provider (Ticaret Bakanlığı | KOSGEB | Türk Eximbank | TİM), summary_tr, eligible_if_tr, applies_to {sectors[], stages[]: ilk_ihracat | sertifika | fuar | e_ihracat | finansman}, source_url, last_verified, verified
- Admin pages (admin flag only): list / add / edit / mark verified, CSV import/export.
- **Every record seeded below starts with `verified: false`.** In the UI, unverified records show a grey badge "Demo verisi – doğrulanmadı" until an admin verifies them. This is deliberate: we will verify each one against the official source before the jury presentation.

### 2. Seed data (insert exactly these; do not add rules of your own)

**kb_hs_codes (HS6 level — national 12-digit GTİP must be checked in the Türk Gümrük Tarife Cetveli)**

| hs6 | description | note |
|---|---|---|
| 0802.51 | Pistachios, fresh or dried, in shell | raw/dried, not roasted |
| 0802.52 | Pistachios, fresh or dried, shelled | raw/dried, not roasted |
| 2008.19 | Nuts (incl. mixtures), otherwise prepared or preserved — e.g. roasted | roasted/salted pistachios usually fall here |
| 6302.60 | Toilet and kitchen linen, of terry towelling, of cotton | towels |
| 6207.91 | Men's bathrobes, dressing gowns etc., of cotton | |
| 6208.91 | Women's/girls' bathrobes, dressing gowns etc., of cotton | |
| 7318.15 | Other screws and bolts, of iron or steel | |
| 7318.16 | Nuts, of iron or steel | |

**kb_rules (country DE unless stated; source URLs are the official entry points)**

| # | title_tr | applies to | side | level | source |
|---|---|---|---|---|---|
| R1 | İhracatçı Birliği üyeliği | all | TR | zorunlu | https://tim.org.tr |
| R2 | AB–Türkiye Gümrük Birliği: sanayi ürünlerinde A.TR dolaşım belgesi | sectors tekstil, otomotiv_yan_sanayi | TR | zorunlu | https://trade.ec.europa.eu/access-to-markets/en/home |
| R3 | Tarım ürünleri Gümrük Birliği kapsamı dışında: gümrük vergisi ve menşe belgesi (EUR.1) TARIC'ten kontrol edilmeli | hs 0802, 2008 | DEST | zorunlu | https://ec.europa.eu/taxation_customs/dds2/taric/ |
| R4 | Tekstil lif etiketlemesi – Yönetmelik (AB) 1007/2011 (Almanya için Almanca etiket) | hs 6302, 6207, 6208 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg/2011/1007/oj |
| R5 | REACH Ek XVII – tekstilde yasaklı azo boyalar | hs 6302, 6207, 6208 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg/2006/1907/oj |
| R6 | OEKO-TEX Standard 100 (alıcılar sıkça ister) | hs 6302, 6207, 6208 | DEST | önerilen | https://www.oeko-tex.com |
| R7 | Aflatoksin azami limitleri – Yönetmelik (AB) 2023/915 | hs 0802, 2008 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg/2023/915/oj |
| R8 | Türkiye menşeli fıstıkta artırılmış resmi kontrol / özel şartlar – Uygulama Yönetmeliği (AB) 2019/1793 (resmi sertifika + analiz raporu; güncel kontrol sıklığını kontrol edin) | hs 0802, 2008 | DEST | zorunlu | https://eur-lex.europa.eu/eli/reg_impl/2019/1793/oj |
| R9 | Gıda etiketleme – Yönetmelik (AB) 1169/2011 (perakende ambalajda Almanca etiket, alerjen vurgusu) | hs 0802, 2008; channel b2c | DEST | koşullu | https://eur-lex.europa.eu/eli/reg/2011/1169/oj |
| R10 | Almanya Ambalaj Kanunu (VerpackG) – LUCID kaydı (ürünü Almanya'da piyasaya ilk süren taraf için) | all; channel b2c | DEST | koşullu | https://lucid.verpackungsregister.org |
| R11 | AB Genel Ürün Güvenliği Yönetmeliği (GPSR) 2023/988 – tüketiciye satışta AB'de sorumlu ekonomik operatör | sectors tekstil, diger; channel b2c | DEST | koşullu | https://eur-lex.europa.eu/eli/reg/2023/988/oj |
| R12 | Sınırda Karbon Düzenleme Mekanizması (SKDM / CBAM) – Yönetmelik (AB) 2023/956: AB'li ithalatçı gömülü emisyon verisi isteyecek (2026'dan itibaren kesin dönem; ithalatçı bazında yıllık eşik var – güncelini kontrol edin) | hs 7318 | DEST | zorunlu | https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en |
| R13 | Araç Ömrünü Tamamlamış Araçlar Direktifi 2000/53/AT – otomotiv müşterileri altı değerlikli krom (Cr VI) içermeyen kaplama ister | hs 7318; sector otomotiv_yan_sanayi | DEST | koşullu | https://eur-lex.europa.eu/eli/dir/2000/53/oj |
| R14 | IMDS malzeme verisi girişi (otomotiv OEM tedarik zincirlerinde yaygın talep) | sector otomotiv_yan_sanayi | DEST | önerilen | https://www.mdsystem.com |
| R15 | Yapısal (inşaat) kullanım için cıvata setlerinde CE işareti – Yapı Malzemeleri Yönetmeliği | hs 7318 (only if structural use) | DEST | koşullu | https://single-market-economy.ec.europa.eu/sectors/construction/construction-products-regulation-cpr_en |

**kb_incentives** (amounts intentionally omitted — link to the source)

| # | name_tr | provider | stages | source |
|---|---|---|---|---|
| I1 | Pazara Giriş Belgeleri Desteği (sertifika, test, analiz giderleri) | Ticaret Bakanlığı | sertifika | https://ticaret.gov.tr/destekler |
| I2 | E-İhracat Destekleri (e-ticaret pazar yeri üyeliği, dijital pazarlama) | Ticaret Bakanlığı | e_ihracat | https://ticaret.gov.tr/destekler |
| I3 | Yurt Dışı Fuar Katılım Desteği | Ticaret Bakanlığı | fuar | https://ticaret.gov.tr/destekler |
| I4 | Pazar Araştırması ve Pazara Giriş Desteği | Ticaret Bakanlığı | ilk_ihracat | https://ticaret.gov.tr/destekler |
| I5 | Tasarım Desteği | Ticaret Bakanlığı | ilk_ihracat (sector tekstil) | https://ticaret.gov.tr/destekler |
| I6 | KOSGEB KOBİ destek programları (uluslararasılaşma) | KOSGEB | ilk_ihracat | https://www.kosgeb.gov.tr |
| I7 | Sevk Öncesi İhracat Kredisi | Türk Eximbank | finansman | https://www.eximbank.gov.tr |
| I8 | İhracat Kredi Sigortası (alıcının ödememe riskine karşı) | Türk Eximbank | finansman, ilk_ihracat | https://www.eximbank.gov.tr |
| I9 | Kolay İhracat Platformu – ücretsiz pazar raporu ve potansiyel alıcı listeleri (e-Devlet ile giriş) | Ticaret Bakanlığı | ilk_ihracat | https://www.kolayihracat.gov.tr |

Write the `summary_tr`, `what_to_do_tr` and `documents` fields for each seed record yourself in plain Turkish, staying strictly within what the title and source imply. Keep them short. Mark them all unverified.

### 3. Flow ("Uygunluk kontrolü yap")
Visible multi-step agent, each step logged to `agent_runs`:

1. **GTİP tahmini** — LLM gets product name, description, material, processing (e.g. roasted vs raw!), photos. Returns top 3 HS6 candidates with description, reasoning in Turkish and confidence (yüksek / orta / düşük). Validate format (`NNNN.NN`). Mark candidates found in `kb_hs_codes` as "listemizde mevcut". Show a warning: "Kesin GTİP (12 hane) için gümrük müşavirinize danışın" with a link to the Ticaret Bakanlığı tariff page. The user must pick/confirm one before continuing. (Demo moment: for "kavrulmuş Antep fıstığı" the agent should explain why 2008.19 rather than 0802.51.)
2. **Kural eşleştirme** — deterministic filter first (country, hs prefix, sector, channel), then the LLM receives only the filtered records and returns, for each: applies yes/no + one-sentence personalized reason + personalized next step. Code drops any id not in the filtered set.
3. **Teşvik eşleştirme** — same pattern with `kb_incentives`, based on company profile and the checklist (e.g. needs OEKO-TEX → I1).
4. **Rapor** — results page:
   - Confirmed GTİP + candidates
   - Checklist grouped: Türkiye tarafı / Hedef pazar; badges zorunlu / koşullu / önerilen; source link and "son doğrulama" date on every item; a checkbox per item "Bu bende var / tamamlandı".
   - Incentives list with "Neden uygun?" and source link.
   - **Hazırlık skoru (readiness score)** — deterministic, NOT from the LLM: weighted % of applicable items the user ticked (zorunlu = 3, koşullu = 2, önerilen = 1). Show the formula in a tooltip. Recomputes live as boxes are ticked.
   - "Sonraki 3 adım" — LLM picks the three most important unticked items and writes a short plan.
   - "PDF indir" — a clean branded İhracat Hazırlık Raporu PDF with a disclaimer footer: "Bu rapor bilgilendirme amaçlıdır; resmi mevzuat ve gümrük müşaviri görüşü esastır."
5. If no rules match (e.g. unsupported country or product), show: "Bu ürün/ülke için doğrulanmış verimiz henüz yok" plus recommended contacts (İhracatçı Birliği, İTO/İSO, Ticaret Müşavirliği) — never improvise rules.

## Acceptance criteria
- [ ] Seeded data loads; admin can edit a rule and mark it verified, and the badge changes.
- [ ] Gaziantep roasted pistachio → top suggestion 2008.19 with explanation; checklist includes R1, R3, R7, R8 (and R9/R10 only if channel B2C).
- [ ] Denizli towels → 6302.60; checklist includes R1, R2, R4, R5, R6; incentives include I1.
- [ ] Bursa bolts → 7318.15; checklist includes R1, R2, R12, R13.
- [ ] Every checklist item links to its source; no item exists without a kb id (write a test).
- [ ] Ticking items changes the score; score formula is visible.
- [ ] PDF downloads with Turkish characters rendered correctly.
