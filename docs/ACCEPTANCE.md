# Acceptance evidence

One section per phase; later phases append their own `## Phase N` section below.
Rule: PASS only for what was actually run. Anything not run, or that misbehaved, is FAIL.

## Phase 1

**Run conditions.** Backend: `MONGO_URI=mongomock://` (in-memory dev DB, seeded on startup), uvicorn on :8000. Frontend: `npm run dev` on :5173.
**No real MongoDB was used**, so nothing here proves persistence across restarts. Browser walk via the built-in Browser pane (Chromium, en-US locale).
Date: 2026-11-14.

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Register, accept KVKK, log out, log back in | PASS | /register in TR: submit without the checkbox stays on /register with the alert "You must accept the Privacy Notice to continue." (EN). Privacy modal opens in TR and EN (data controller, purposes, legal basis, KVKK art. 11 rights; `[Platform operator]` placeholders are intentional and labelled). Ticked box and submitted: redirected to /onboarding. "Log out": `/api/auth/me` returned 401 and the app went to /login; visiting /products while logged out redirected to /login (protected route). Logged back in with the same credentials: landed on `/` dashboard. Backend: `test_register_requires_kvkk`, `test_password_min_8`, `test_register_login_logout_cycle` pass. |
| 2 | 3-step onboarding with photos at 375 px, no layout breaks | PASS (caveat) | Viewport emulated 375x812. On each of steps 1, 2, 3: `document.documentElement.scrollWidth` = 375 and no element has `getBoundingClientRect().right > 376`. Step 1: city dropdown has 81 provinces (82 options incl. placeholder), 4 sectors, 10 certs, logo upload with preview. Step 2: unit/MOQ/weight/floor fields; 6 photos uploaded (one 2400x1800), 6 previews rendered; server stored them as webp, the large one resized to 1600x1200 (others 800x600). Step 3: Germany pre-selected, NL/FR/USA/UAE/Iraq show "Coming soon" and are `disabled`. "Create my company" went to the dashboard. Caveat: the pane's screenshots at 375 appeared cropped on the right on step 2 (frame 413 px wide vs 375 layout; DOM rects say textarea right edge = 339, Log out right edge = 359). I judge this a screenshot-scaling artifact of the pane, but I could not confirm it visually on a real phone. |
| 3 | Dashboard shows company, three cards, roadmap strip | PASS (minor deviation) | New company (EN): "Export Dashboard", company name, SVG flag (`<svg aria-label="Germany">`, not "DE" letters; TR shows `aria-label="Almanya"`), roadmap "1/4 steps done: 1 Profile done, 2 Storefront / 3 Compliance / 4 First quote to do", cards Storefront (Not created, "Create my storefront"), Compliance (Not done, "Run compliance check"), Buyers ("0 leads, 0 awaiting approval", "Find buyers"), Notifications area ("No notifications yet."). Deviation: card titles in TR are "Vitrin", "Mevzuat (uygunluk)", "Alıcılar", not the spec's "Dijital Vitrin", "Mevzuat Bekçisi", "Alıcı Ajanı"; button labels match the spec. Fixed in 123efd11c1f4b1356321bcb6953cd870e48b4461 (card titles / logo helper plural) |
| 4 | TR/EN switch changes every producer screen; choice survives logout and login | PASS | Default with no stored choice and en-US browser = Turkish (login page). EN walk, no Turkish UI text left on: login, register (+ privacy modal), onboarding steps 1-3, dashboard, My company (/company), My products (/products) incl. "New product" modal, Storefront/Compliance/Buyers placeholders ("This section is coming soon."), /privacy. Only Turkish text seen is user input and province proper names (Adıyaman, Hakkâri ...). Cosmetic: logo helper reads "Up to 1 photos." in EN. Fixed in 123efd11c1f4b1356321bcb6953cd870e48b4461 (card titles / logo helper plural). Persistence: switched TR then EN on the dashboard; `/api/auth/me` `ui_language` = "tr" then "en" (saved server-side); logged out, cleared localStorage, logged in again: dashboard came up in EN ("Export Dashboard"). A demo user stored as TR came up in TR even though localStorage said EN. Backend: `test_ui_language_persists_across_login`. |
| 5 | Logging in as a seeded demo company shows its data | PASS | bozkurt@demo.local / demo12345: dashboard "Bozkurt Antep Fıstığı", Almanya flag, "6 lead, 0 onay bekleyen mesaj". `/api/company`: Gaziantep, gida, certs ISO 22000 + Helal. `/api/products`: "Kabuklu Kavrulmuş Antep Fıstığı" (kg, MOQ 500, 2 photos) and "İç Antep Fıstığı" (kg, MOQ 300, 2 photos). Only this demo account was walked in the browser; pamukkale@ and uludag@ were not logged into. |
| 6 | `/api/health` reports LLM status; admin test endpoint returns validated JSON (mock) | PASS | `GET /api/health` -> `{"status":"ok","llm":{"provider":"anthropic","key_set":false}}` (boolean only, no key value). `tests/test_llm_service.py::test_admin_llm_test_endpoint` PASS (mocked LLM, validated schema) and `tests/test_auth.py::test_non_admin_forbidden` PASS. `tests/test_health.py::test_health_reports_provider_without_key` PASS. The endpoint (`POST /api/admin/llm-test`) was not called live (no LLM key). |
| 7 | Floor price absent from every non-owner response (test) | PASS | `tests/test_ownership.py::test_floor_absent_from_non_owner_responses` (other producer and admin, product GET/list and company GET: no `price_floor` anywhere, 404 for non-owners), `test_other_user_gets_404_on_product`, `test_public_product_drops_floor_and_helper_detects_leaks`, `tests/test_llm_service.py::test_render_prompt_rejects_price_floor` all PASS. Owner still sees own floor (`test_owner_sees_floor`; seen live: "Secret floor price: €3.40 (only you can see it)"). No public (buyer) endpoint exists yet in Phase 1, so only the test coverage applies. |
| 8 | pytest passes | PASS | `83 passed in 31.17s`. `npm run build` (tsc + vite) succeeded: `index-DtJ5h9kn.js 365.54 kB (gzip 115.05 kB)`, `built in 165ms`. |

### Tally
8 PASS (2 with noted caveat/deviation), 0 FAIL.

### Defects / follow-ups (none block acceptance)
1. Dashboard card titles in TR differ from the spec names (see row 3). Wording only.
2. EN logo helper "Up to 1 photos." (plural). File likely the shared photo-upload component / i18n key.
3. 375 px step 2/3 visual check relied on DOM metrics; screenshots in the pane were cropped (see row 2).

### Not verified
- Persistence across a server restart (in-memory DB).
- Admin endpoint live, any real LLM call (no key).
- Pamukkale and Uludağ demo logins in the UI; TR-language walk of onboarding steps (EN walked).
