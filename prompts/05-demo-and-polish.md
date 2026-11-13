# PROMPT 05 — Demo Mode, Reliability & Polish (for the live jury demo)

---

Build Phase 5: make the app impressive and unbreakable for a live 3-minute demo, and polish the whole experience.

## Build

### 1. "Canlı Demo" mode
- A hidden route `/demo` (admin only) with three buttons: Gaziantep / Denizli / Bursa. Clicking one resets that demo company to a clean state (profile + product filled in, no storefront, no report, demo leads present) in under 3 seconds.
- A small floating "Demo rehberi" panel (toggle with a keyboard shortcut, e.g. `Ctrl+Shift+D`) showing the presenter the next step of the script below and a stopwatch.

**Target demo script (≈3 minutes, Gaziantep → Germany):**
1. (0:00) Dashboard of "Bozkurt Antep Fıstığı" — roadmap strip at 1/4.
2. (0:15) Dijital Vitrin → dictate one sentence with the mic → generate. Agent steps animate. Publish → show `/s/bozkurt-pistazien` in German on a phone frame + QR code.
3. (1:15) Mevzuat Bekçisi → agent proposes 2008.19 and explains roasted vs raw → checklist shows aflatoxin + increased official controls with sources → incentives matched → readiness score → PDF.
4. (2:15) Open the storefront on a second device / tab, submit an RFQ as a "German buyer" → it appears on the dashboard as a hot lead → "İlk teması hazırla" → German reply + Turkish translation → quote with DAP Germany logistics estimate → "Onayla ve Gönder".
5. (3:00) Dashboard: roadmap at 4/4, real counters updated.

### 2. Reliability for live demos
- **Cached fallback:** for the three demo companies, store the last successful AI output for each step. If a live LLM call fails or exceeds a timeout (configurable, default 25 s in demo mode), use the cached output and show a subtle indicator only visible to the presenter (e.g. a small dot in the demo panel), not a scary error.
- Pre-warm: when `/demo` resets a company, ping the LLM once so the first call isn't cold.
- All long operations show streaming/step progress; nothing freezes the UI.
- Global error boundary in React with a friendly Turkish message and retry button.
- Works on the venue's projector: test at 1280×720 and 1920×1080, and at 375 px mobile.

### 3. Agent activity visualization
- A reusable `AgentSteps` component: vertical list of steps with icons (bekliyor / çalışıyor / tamamlandı / yedek kullanıldı), elapsed time per step, and a one-line Turkish explanation of what the agent is doing ("Fotoğraflardan ürün özellikleri çıkarılıyor…", "Alman alıcı beklentilerine göre metin uyarlanıyor…").
- Use it in all three modules.

### 4. "Etki" (impact) panel — honest version
- Per company: time from signup to published storefront, to readiness report, to first approved outreach — measured from real timestamps.
- Platform-wide (admin): number of companies, storefronts published, reports generated, approved messages, RFQs received. Real counts only.
- Do NOT show projected national figures (e.g. "50.000 KOBİ") inside the app — those belong in the pitch deck, labelled as targets.

### 5. Polish checklist
- Both languages complete: every string in Turkish and English, no mixed-language labels, friendly empty states with a clear next action, loading skeletons.
- Accessibility: proper labels, focus states, contrast AA, keyboard navigation for the main flows.
- Performance: storefront page Lighthouse ≥ 90 on mobile (lazy-load and compress images).
- Security basics: rate limiting on auth and RFQ endpoints, input validation, CORS restricted, uploads type-checked, no secrets in frontend bundle, ownership checks on every company-scoped endpoint (write tests: user A cannot read user B's products, leads or floor price).
- KVKK/GDPR basics: account deletion that deletes company data, data export (JSON) for the user, privacy notice page for the producer app.
- README: how to run locally, env vars, how to seed, how to reset demo.

## Acceptance criteria
- [ ] I can run the full 5-step script above in ≤ 3.5 minutes, twice in a row, after a `/demo` reset.
- [ ] With the LLM key removed, the demo still completes using cached outputs.
- [ ] Ownership tests pass; floor price never leaks.
- [ ] Storefront Lighthouse mobile performance ≥ 90.
- [ ] Switching to English leaves no Turkish UI text on producer-facing screens, and Turkish stays complete when switched back.
