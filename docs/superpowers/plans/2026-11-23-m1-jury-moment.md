# M1 "Jury Moment" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A judge scans a big on-screen QR code, opens the German storefront on their own phone (with a proper link preview if shared), sends a quote request or taps WhatsApp, and the presenter's screen shows a "new request" toast within ~5 seconds while dashboard and leads refresh by themselves.

**Architecture:** One small backend endpoint for "notifications since T" plus a polling hook in the producer `Layout` that raises a toast and a `kobi:rfq` window event; pages that show counts reload on that event. A server-rendered share page gives link-preview bots OG/Twitter/JSON-LD tags, reached through a user-agent rewrite in `frontend/vercel.json`. A reusable full-screen QR modal and a WhatsApp click-to-chat link complete the flow. No new dependencies.

**Tech Stack:** FastAPI + Motor (mongomock in tests), pytest; React 19 + react-router 7 + Tailwind; node `--experimental-strip-types` for frontend `.check.ts` files (run from pytest, see `backend/tests/test_parse_number.py`).

**Spec:** `docs/superpowers/plans/2026-11-23-contest-roadmap.md` (milestone M1) and `AGENTS.md` §3.

## Global Constraints

- Producer UI strings in both `frontend/src/i18n/tr.json` and `en.json`; buyer strings only in `frontend/src/storefront/strings.ts` (`de` and `en`).
- Public/buyer payloads stay allow-listed: never `price_floor`, `review`, `missing`, `blockers`, owner ids.
- Error shape `{"code", "message_key": "errors.<code>"}`. No new dependencies.
- Backend tests: `cd backend && .venv/Scripts/python.exe -m pytest -q`. Frontend: `cd frontend && npm run build && npm run lint` (pre-existing warnings allowed, no new ones in touched files).
- One commit per task, no attribution lines.

## Review Focus

1. **Laptop clock differs from server clock** — alerts must still fire exactly once per RFQ; the client never sends its own clock, only the server's `now` echoed back. (Test in Task 1.)
2. **Presenter tab in the background or laptop asleep** — polling pauses while `document.hidden` and catches up on return without duplicate toasts. (Browser check in Task 2.)
3. **Storefront text containing `"`, `<`, `</script>`** — the share page must not break out of attributes or the JSON-LD block. (Test in Task 3.)
4. **Producer phone stored as `0532 123 45 67`, `+90 (532) …`, or garbage** — WhatsApp link uses `90…` digits, or no button at all; and a demo company never exposes its invented seed number. (Check file + backend test in Task 5.)
5. **QR shown while `FRONTEND_ORIGIN` is still `localhost`** — the QR modal must show the encoded URL in large text so the presenter notices a phone cannot reach it. (Browser check in Task 4.)

---

### Task 1: "Notifications since" endpoint with lead link

**Files:**
- Modify: `backend/app/routers/public.py` (`rfq`: store `lead_id` on the notification)
- Modify: `backend/app/routers/dashboard.py` (new route; include `lead_id` in dashboard notification items)
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Produces: `GET /api/notifications/since?after=<ISO-8601 datetime, optional>` → `{"now": "<ISO>", "items": [{"id", "type", "message_key", "params", "lead_id", "created_at"}]}`. `now` is taken before the query; items have `after < created_at <= now`, own company only, oldest first, max 20. Without `after`: `items: []` (baseline call). Malformed `after` → 422 (FastAPI `datetime` query param).
- Produces: RFQ notification doc gains `"lead_id": str(inserted lead _id)`.

- [ ] **Step 1: Failing tests** in `test_dashboard.py`:
  - `test_since_baseline_then_new_rfq`: publish a storefront for producer A (use `tests.helpers.publishable_site_config()`), `GET /api/notifications/since` → `items == []`, keep `now`; `POST /api/public/storefronts/<slug>/rfq` (body like `test_publish_rfq.rfq()`); `GET …/since?after=<now>` → one item, `type == "rfq"`, `params["company"] == "Müller GmbH"`, `lead_id` equals the new lead's id; calling again with the second response's `now` → `items == []` (Review Focus 1).
  - `test_since_scoped_to_company`: producer B's RFQ never appears for A.
  - `test_since_rejects_bad_after`: `?after=yesterday` → 422.
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest -q tests/test_dashboard.py` → FAIL (404 route).
- [ ] **Step 3: Implement** the route in `dashboard.py` (reuse its notification item shape; build items in one helper used by both routes) and `lead_id` in `public.rfq`. Compare datetimes as UTC-aware (normalise naive values like `_aware` does).
- [ ] **Step 4: Run** full backend suite → pass.
- [ ] **Step 5: Commit** — `feat: notifications-since endpoint with lead link`

---

### Task 2: Live RFQ toast and self-refreshing pages

**Files:**
- Create: `frontend/src/hooks/useRfqAlerts.ts`
- Create: `frontend/src/components/RfqToast.tsx`
- Modify: `frontend/src/components/Layout.tsx`, `frontend/src/pages/dashboard/Dashboard.tsx`, `frontend/src/pages/leads/LeadsTable.tsx`, `frontend/src/pages/pipeline/Pipeline.tsx`, `frontend/src/i18n/tr.json`, `en.json`

**Interfaces:**
- Consumes: Task 1 endpoint.
- Produces: `useRfqAlerts(enabled: boolean): { alerts: RfqAlert[]; dismiss(id: string): void }` with `type RfqAlert = { id: string; company: string; leadId: string | null }`. Polls every 5000 ms while `enabled && !document.hidden`; first call has no `after`; each call sends the previous response's `now`; on `visibilitychange` to visible, polls immediately. Each new `rfq` item adds an alert and dispatches `window.dispatchEvent(new Event('kobi:rfq'))`. Network errors are swallowed (keep last `now`). Alerts auto-dismiss after 10 s.
- `RfqToast` renders alerts fixed bottom-right in a `role="status" aria-live="polite"` region: `t('alerts.newRfq', { company })` + link `t('alerts.open')` to `/leads/<leadId>` (to `/leads` if null) + close button.
- `Layout` calls `useRfqAlerts(!!user?.has_company)` and renders `RfqToast`.
- `Dashboard`, `LeadsTable`, `Pipeline`: `useEffect` subscribing to `kobi:rfq` that calls their existing load function.
- i18n: `alerts.newRfq` = "Yeni teklif talebi: {{company}}" / "New quote request: {{company}}"; `alerts.open` = "Aç" / "Open"; `alerts.close` = "Kapat" / "Close".

- [ ] **Step 1: Implement.**
- [ ] **Step 2: Verify** — `npm run build && npm run lint` clean for touched files. Browser pane: log in as `bozkurt@demo.local`, publish the storefront, keep the dashboard open; in a second tab submit the RFQ form on `/s/bozkurt-pistazien`. Within 6 s: toast appears once, dashboard lead count +1, "Aç" opens that lead. Switch the presenter tab away for 20 s, send another RFQ, switch back: exactly one new toast (Review Focus 2).
- [ ] **Step 3: Commit** — `feat: live RFQ toast and auto-refresh on new requests`

---

### Task 3: Link-preview share page for bots

**Files:**
- Modify: `backend/app/routers/public.py` (new route)
- Modify: `frontend/vercel.json` (bot rewrite, first in `rewrites`)
- Test: `backend/tests/test_publish_rfq.py`

**Interfaces:**
- Produces: `GET /api/public/storefronts/{slug}/share?lang=de|en` (default `de`) → `text/html; charset=utf-8`, 404 when not published. Head contains: `<html lang>`, `<title>`, `meta description`, `og:type=website`, `og:title`, `og:description`, `og:url` = `{FRONTEND_ORIGIN}/s/{slug}`, `og:locale` (`de_DE`/`en_GB`), `og:image` (absolute: `{FRONTEND_ORIGIN}` + first product photo, else logo; omitted if none), `twitter:card=summary_large_image`, `<link rel=canonical>`, and one `<script type="application/ld+json">` with schema.org `Organization` (`name`, `url`, `address.addressLocality` = city, `logo` if any). Title/description from `seo.title`/`seo.description` with the same fallbacks as `PublicStorefront.useHead`. Body: one link to the storefront plus `<meta http-equiv="refresh" content="0;url=/s/{slug}">` for any human who lands there. Escape every value with `html.escape(..., quote=True)`; JSON-LD via `json.dumps(..., ensure_ascii=False).replace("<", "\\u003c")`.
- `vercel.json` rewrite (before the `/api` one):
  `{ "source": "/s/:slug", "has": [{ "type": "header", "key": "user-agent", "value": ".*(WhatsApp|facebookexternalhit|Facebot|Twitterbot|LinkedInBot|Slackbot|TelegramBot|Discordbot|Googlebot|bingbot).*" }], "destination": "https://YOUR-BACKEND-HOST/api/public/storefronts/:slug/share" }`

- [ ] **Step 1: Failing tests** in `test_publish_rfq.py`:
  - `test_share_page_has_preview_tags`: published storefront → 200, `text/html`, contains `og:title`, `og:url" content="http://localhost:5173/s/bozkurt-test"`, `twitter:card`, `application/ld+json`, `"@type": "Organization"`; contains none of `GEHEIM-TR`, `price_floor`, `9.5`.
  - `test_share_page_escapes_text` (Review Focus 3): `de.seo.title = 'A"<script>alert(1)</script>'` → response has no `<script>alert`, has `&quot;` / `&lt;script&gt;`; JSON-LD block contains no raw `</script` before its own closing tag.
  - `test_share_page_404_when_draft`.
  - `test_share_page_lang_en`: `?lang=en` uses the `en` title and `og:locale` `en_GB`.
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest -q tests/test_publish_rfq.py` → FAIL.
- [ ] **Step 3: Implement**; add the `vercel.json` rule; add one line to `docs/RUNNING.md` §11: "Link previews: WhatsApp/LinkedIn bots are routed to `/api/public/storefronts/<slug>/share`; test with `curl -A WhatsApp https://<app>/s/<slug>`."
- [ ] **Step 4: Run** full backend suite → pass.
- [ ] **Step 5: Commit** — `feat: server-rendered share preview for storefront links`

---

### Task 4: Full-screen QR for the jury + demo network runbook

**Files:**
- Create: `frontend/src/components/QrPresenter.tsx`
- Modify: `frontend/src/pages/storefront/PublishSuccess.tsx`, `frontend/src/pages/dashboard/Dashboard.tsx` (storefront card, only when `status === 'published'`), i18n files
- Modify: `docs/RUNNING.md` (§11 "Demo network"), `docs/sunum-rehberi.html` (one line in "Sunumdan önce")
- Modify: `backend/app/routers/storefronts.py` (`GET /mine/qr-url` JSON with the encoded URL)
- Test: `backend/tests/test_publish_rfq.py`

**Interfaces:**
- Produces: `GET /api/storefronts/mine/qr-url` → `{"url": "{FRONTEND_ORIGIN}/s/{slug}"}` (same string `qr_png` encodes; reuse one helper).
- Produces: `<QrPresenter />` — a button `t('qr.show')` that opens the existing `Modal` with `/api/storefronts/mine/qr.png?ts=<Date.now()>` sized `w-[min(70vh,80vw)]`, the URL from `qr-url` in large text under it, and, when the URL host is `localhost` or `127.0.0.1`, a warning line `t('qr.localWarning')` (Review Focus 5).
- i18n: `qr.show` = "QR'ı büyük göster" / "Show QR full screen"; `qr.localWarning` = "Bu adres yalnızca bu bilgisayarda açılır. Telefonla taramak için yayındaki adresi veya aynı Wi-Fi ağ adresini kullanın." / "This address only opens on this computer. For phones, use the deployed URL or the same-Wi-Fi network address."
- Runbook text (RUNNING.md): preferred = deployed URL. LAN fallback: presenter laptop and phones on the same network (a phone hotspot is safer than venue Wi-Fi, which often isolates clients); `npm run dev -- --host`; set `FRONTEND_ORIGIN=http://<laptop-LAN-IP>:5173` and restart the backend; allow Node through Windows Firewall when prompted; open the LAN URL on the laptop too so the session cookie matches.

- [ ] **Step 1: Failing test** `test_qr_url_matches_origin`: published storefront → `GET /api/storefronts/mine/qr-url` == `{"url": "http://localhost:5173/s/bozkurt-test"}`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** backend + component + docs.
- [ ] **Step 4: Verify** — suite passes; build/lint clean; browser pane: Dashboard storefront card shows the button after publishing; modal shows a large QR, the URL and the localhost warning; Escape closes it.
- [ ] **Step 5: Commit** — `feat: full-screen QR presenter and demo network runbook`

---

### Task 5: WhatsApp click-to-chat on the public storefront

**Files:**
- Create: `frontend/src/storefront/whatsapp.ts`, `frontend/src/storefront/whatsapp.check.ts`
- Modify: `frontend/src/storefront/strings.ts` (incl. `PublicCompany.whatsapp: string | null`), `frontend/src/storefront/PublicStorefront.tsx` (pass the link), `frontend/src/storefront/StorefrontView.tsx` (render it)
- Modify: `backend/app/core/config.py`, `backend/app/routers/public.py`
- Test: `backend/tests/test_frontend_checks.py` (new; runs the check like `test_parse_number.py`), `backend/tests/test_publish_rfq.py`

**Interfaces:**
- Produces: `waLink(phone: string | null | undefined, text: string): string | null` in `whatsapp.ts`. Strip everything but digits; leading `00` → drop it; leading single `0` → replace with `90`; 10 digits starting `5` → prefix `90`; result must be 11–15 digits, else `null`. Returns `https://wa.me/<digits>?text=<encodeURIComponent(text)>`.
- `whatsapp.check.ts` cases (`throw` on mismatch, `console.log('ok', n)`): `'0532 123 45 67'` → `https://wa.me/905321234567?text=…`; `'+90 (532) 123-45-67'` → same digits; `'0090 532 123 45 67'` → same; `'5321234567'` → `905321234567`; `'+49 30 1234567'` → `49301234567`; `'abc'`, `''`, `null`, `'123'` → `null`. Text `'Guten Tag & mehr'` encoded as `Guten%20Tag%20%26%20mehr`.
- `strings.ts`: new keys `whatsapp` ("Per WhatsApp schreiben" / "Message on WhatsApp") and `waText` ("Guten Tag, ich interessiere mich für Ihre Produkte ({url})." / "Hello, I am interested in your products ({url})."), `{url}` replaced with `location.href`.
- Backend (`public.get_storefront`, `config.Settings`): new setting `demo_whatsapp_phone: str = ""` (env `DEMO_WHATSAPP_PHONE`). Public payload gains `company.whatsapp`: the company's `contact.phone` for real companies; for `is_demo_company` companies `settings.demo_whatsapp_phone or None` — **the seeded demo numbers are invented and must never be dialled by a judge**. Test in `test_publish_rfq.py` → `test_whatsapp_never_uses_seeded_demo_number`: demo company + empty setting → `company.whatsapp is None`; setting `"+90 555 000 00 00"` → that value; real company → its own phone. Document `DEMO_WHATSAPP_PHONE` (the presenter's own phone) in `docs/RUNNING.md` §11 and one line in `docs/sunum-rehberi.html`.
- `PublicStorefront` builds the link from `company.whatsapp` (not `contact.phone`).
- `StorefrontView` gets optional prop `whatsapp?: string | null`; when set, renders a secondary button next to the hero CTA and in the RFQ section (`target="_blank" rel="noopener noreferrer"`). The editor preview passes nothing, so it never shows there.

- [ ] **Step 1: Write** `whatsapp.check.ts` and `test_frontend_checks.py::test_whatsapp_link_cases` (skip if no node, like `test_parse_number.py`).
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest -q tests/test_frontend_checks.py` → FAIL (module missing).
- [ ] **Step 3: Implement** `waLink`, strings, wiring.
- [ ] **Step 4: Verify** — test passes; full suite passes; build/lint clean; browser pane at mobile width (375×812): `/s/bozkurt-pistazien` shows the WhatsApp button for the seeded phone, link starts `https://wa.me/90`.
- [ ] **Step 5: Commit** — `feat: WhatsApp click-to-chat on public storefront`

---

## Final Check

- Backend suite and frontend build/lint green.
- End-to-end rehearsal in the browser pane: publish → "QR'ı büyük göster" → second tab RFQ → toast within 6 s → open lead → German draft → approve. Note in the final report that the Vercel bot rewrite and phone scanning were not testable locally.
