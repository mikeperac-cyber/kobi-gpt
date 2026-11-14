# Decisions

1. **No local MongoDB found** (`mongod` not on PATH, `MONGO_URI` unset on the build machine). Tests use `mongomock-motor`; the running app needs `MONGO_URI` (local `mongod` or Atlas).
2. **Git repo** was initialised before Task 1 (branch `build/mvp`); every task ends in a commit.
3. **Live step progress = polling.** Long AI flows create a `jobs` document; the frontend polls `GET /api/jobs/{id}` every 700 ms. No SSE/websockets.
4. **LLM providers via raw `httpx`** (no vendor SDKs). Default `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-5-5`.
5. **Prompt templates use `string.Template` (`$var`)** so JSON braces in schemas need no escaping. `render_prompt` raises if the context contains a `price_floor` key anywhere.
6. **Rate limiting is an in-memory fixed-window counter** (shortcut: per-process only, swap for Redis when running >1 worker).
7. **Readiness score is computed server-side only**; each tick is a PATCH that returns the new score (optimistic UI). One formula, no duplicate in TS.
8. **OpenGraph tags are set client-side** on `/s/{slug}` (shortcut: crawlers that don't run JS won't see them; server-render the head if link previews matter).
9. **Seed photos are Pillow-generated labelled placeholders** (no downloads).
10. **i18n key parity is checked by pytest** (reads `frontend/src/i18n/*.json`). No frontend unit-test framework; frontend is verified by `npm run build` (tsc) and browser walk-throughs.
11. **Demo companies** carry `is_demo_company: true`; the demo timeout and `demo_cache` apply only to them.
12. **Quote PDF and readiness PDF both go through `pdf_service`**, which takes already-public dicts (never a product document), so the floor cannot reach it.
13. **CERTS includes "IATF 16949"** (added to the spec list for the Bursa fastener seed company).
14. **In-memory dev database** (`MONGO_URI=mongomock://`) uses mongomock-motor and seeds on startup so the app runs with no MongoDB installed. Data is lost on restart; use real MongoDB for persistence.
15. **Storefront regeneration keeps status and slug.** One storefront per (company, DE), unique-indexed on `slug` and `(company_id, country)`; regenerating never unpublishes or moves a published URL. `unique_slug` is retried once on `DuplicateKeyError`.
16. **Theme step is deterministic**: recorded with source `template`, never `llm`. The LLM's own `missing`, `template` and CTA strings are ignored; code forces the CTAs, recomputes `missing`, and re-applies DB photos/product ids (generation and section regeneration).
17. **Floor-number detection is defence in depth.** Generated de/en/review text or a regenerated section containing the floor as a number triggers the fallback. Limitation: exact decimal forms only (9.5 / 9,5 / 9.50), not rounded or thousand-formatted variants; the floor never enters any prompt, so the model cannot know it.
18. **`regenerate-section` returns `{section, fallback, missing}`** and persists the section only when not a fallback. `PUT /storefronts/mine` re-slugs through `slugify_tr` (junk becomes `shop`) and recomputes `missing` server-side.
19. **`LocalStorage.read` is root-confined** (only `/uploads/...` files under the storage root; else None). Analysis sends at most 3 product photos.

## Task 14: publish, public API, RFQ
- Public storefront payload is an explicit allow-list (`site_config.{de,en,template}`, company name/city/logo/contact/founded_year, legal, slug); `review`, `missing`, ids and floors are never read into the response.
- Impressum `representative` and `register` are not collected yet: returned as null, checklist marks `present: false` (producer adds via Firmam later; out of scope now).
- RFQ: honeypot `website_hp` non-empty returns 204 and stores nothing; 5/hour per client IP + slug (in-memory); lead `score` is 0 until Task 25 back-fills; every RFQ lead is `is_hot` and carries `source_note`.
- Unpublished slugs 404 for both GET and RFQ POST (checked before honeypot/rate limit, so slug existence of drafts is not leaked).
