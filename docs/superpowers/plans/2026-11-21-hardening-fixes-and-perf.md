# Hardening: High-Impact Fixes and Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the six highest-impact bugs from the 2026-11-21 review and the three backend performance hot spots, without changing any product principle in `AGENTS.md`.

**Architecture:** Every fix lands in the module that owns the behaviour (storefront_service, storefronts/quotes/dashboard/leads routers, llm_service, main.py, three frontend files). No new services, no new dependencies. The pre-publish checklist is computed server-side next to `compute_missing` and travels to the editor inside `site_config`, so the rule exists once.

**Tech Stack:** FastAPI + Motor (mongomock in tests), pytest, httpx; React 19 + react-router 7 + Vite (no frontend test runner: frontend tasks verify with `npm run build`, `npm run lint` and the browser pane).

**Spec:** No separate spec file. The source is the review notes pasted with this request; each task header quotes the finding it fixes. `AGENTS.md` principles 1–7 still apply.

## Global Constraints

- Turkish-first bilingual UI: every new producer-facing string goes into both `frontend/src/i18n/tr.json` and `en.json`. Buyer-facing strings go into `frontend/src/storefront/strings.ts` (`de` and `en`), never producer i18n.
- `price_floor` never leaves the server and never enters a buyer-facing payload or error message.
- Error responses keep the existing shape `{"code": ..., "message_key": "errors.<code>"}`.
- No new dependencies (backend or frontend).
- Run backend tests from `backend/`: `python -m pytest -q`. Run frontend checks from `frontend/`: `npm run build` and `npm run lint`.
- Commit after each task; one task = one commit. No attribution lines in commit messages.

## Out of Scope (separate plans, each needs its own brainstorming/spec first)

- Edge caching for `/api/public/storefronts/{slug}`, CDN for uploads, responsive images.
- Whole commercialization roadmap: real outbound email, billing/plan limits, SSR/SEO, product-name localization fields on products, verified KB workflow, real freight rates, multi-market, document pack, lead credits, report credits, white-label, storefront analytics. Two of these touch `AGENTS.md` §4 (payments; "fully autonomous emailing") and need the owner's decision before a spec.
- Quote PDF still prints `name_tr` to a German buyer (`routers/quotes.py` `pdf`). Same bug class as Task 1, but it needs a localized product name source that does not exist until the localization roadmap item; note it, do not fix here.

## Review Focus

1. **Existing published storefronts that fail the new checklist** — a storefront published before Task 2 must stay published and publicly visible; only a new `publish` call is blocked. (Test in Task 2.)
2. **A brand name that is identical in Turkish and German** (e.g. a product literally called "Bozkurt") — Task 1 nulls it and the checklist then asks the producer to type it in the editor; the producer can re-enter the same text and save, and it must then be kept. (Test in Task 1.)
3. **Pipeline page with more leads than one page** — `Pipeline.tsx` must still see every lead it shows today (up to 500), not silently the first page. (Test in Task 8.)
4. **Quote created without a weight after a previous quote supplied one** — must fail with `needs_weight` again rather than reuse the earlier quote's weight. (Test in Task 3.)
5. **LLM provider returning 429 on every attempt** — the call must stop after the bounded retries and raise `LLMProviderError`, so the agent step falls back instead of hanging the demo. (Test in Task 9.)

---

### Task 1: German/English storefront never shows Turkish product names

Finding: "`storefront_service._content` builds DE/EN product blocks from `name_tr`; the deterministic fallback emits Turkish names on a German buyer storefront."

**Files:**
- Modify: `backend/app/services/storefront_service.py` (`_content`, `fallback_site_config`, `generate_site_config`)
- Test: `backend/tests/test_storefront_pure.py`, `backend/tests/test_storefront_generation.py`

**Interfaces:**
- Produces: `_content(t, company, products, intake, own_text)` — product `name`/`short` come from `name_tr` **only when `own_text is not None`** (the Turkish review copy); for de/en they are `None`, so `compute_missing` lists `products.<i>.name`.
- Produces: `drop_untranslated_names(cfg: SiteConfig, products: list[dict]) -> None` — for `cfg.de` and `cfg.en` blocks, sets `name` (and `short` if it contains the Turkish name) to `None` when `tr_fold(name) == tr_fold(product["name_tr"])`. Blocks are matched to products by `block.product_id == str(p.get("id") or p["_id"])` (DB docs carry `_id` ObjectIds, test dicts may carry `id`). Recompute `cfg.missing` after the call. Called in `generate_site_config` after the content step (covers LLM output and cache hits). Not called from `put_mine`: a name the producer types in the editor is kept even if identical.

- [ ] **Step 1: Write the failing tests**

```python
# test_storefront_pure.py
def test_fallback_never_puts_turkish_name_in_de_en():
    cfg = fallback_site_config(COMPANY, [{"id": "p1", "name_tr": "Kabuklu Antep Fıstığı", "moq": 500, "unit": "kg"}],
                               "b2b", "tr")
    for lang in (cfg.de, cfg.en):
        b = lang.products[0]
        assert b.name is None and b.short is None
        assert "Fıstığı" not in lang.model_dump_json()
    assert cfg.review.products[0].name == "Kabuklu Antep Fıstığı"
    assert "products.0.name" in cfg.missing

def test_drop_untranslated_names_keeps_translated():
    cfg = fallback_site_config(COMPANY, [{"id": "p1", "name_tr": "Pamuk Havlu"}], "b2b", "tr")
    cfg.de.products[0].name, cfg.en.products[0].name = "Pamuk Havlu", "Cotton towel"
    drop_untranslated_names(cfg, [{"_id": "p1", "name_tr": "Pamuk Havlu"}])
    assert cfg.de.products[0].name is None and cfg.en.products[0].name == "Cotton towel"
```

```python
# test_storefront_generation.py — LLM returns the Turkish name in de; saved config has de name None
async def test_llm_turkish_name_is_dropped(...):  # reuse the module's existing fake_llm content setup
    ...
    assert cfg.de.products[0].name is None
```

Review Focus 2 (in `test_publish_rfq.py` or a storefront router test): PUT `/api/storefronts/mine` with `de.products[0].name == name_tr` → response keeps that name and `products.0.name` is not in `missing`.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_storefront_pure.py tests/test_storefront_generation.py -q`
Expected: FAIL (Turkish name present; `drop_untranslated_names` undefined).

- [ ] **Step 3: Implement** the two interfaces above. `why_moq` and `seo.description` already skip `None` names; keep that.

- [ ] **Step 4: Run the whole backend suite** — `python -m pytest -q` → all pass (update any existing assertion that expected `name_tr` in de/en; that expectation was the bug).

- [ ] **Step 5: Commit** — `fix: never show Turkish product names on DE/EN storefronts`

---

### Task 2: Pre-publish checklist (server guard + editor mirror)

Finding: "A producer can publish with zero products, missing hero/about facts, or no RFQ intro."

**Files:**
- Modify: `backend/app/models/storefront.py` (`SiteConfig`), `backend/app/services/storefront_service.py`, `backend/app/routers/storefronts.py` (`put_mine`, `regenerate`, `publish`)
- Modify: `frontend/src/pages/storefront/Editor.tsx`, the `Storefront`/`SiteConfig` TS type it imports, `frontend/src/i18n/tr.json`, `en.json`
- Test: `backend/tests/test_publish_rfq.py` (and fix its `_published` fixture)

**Interfaces:**
- Produces: `publish_blockers(cfg: SiteConfig) -> list[str]` in `storefront_service`. Returns, deduped, in this order: `"products"` if `cfg.de.products` is empty; for each of `de`, `en`: `"hero.headline"`, `"about.story"`, `"rfq.intro"` when `None`/blank, and `"products.<i>.name"` per unnamed block. Optional facts (founded_year, lead_time, …) never block.
- Produces: `SiteConfig.blockers: list[str] = []`, set everywhere `cfg.missing = compute_missing(cfg)` is set (fallback, generation, `put_mine`, `regenerate`). Not included in the public payload (public router already whitelists `de`/`en`/`template`).
- Produces: `POST /api/storefronts/mine/publish` → `422 {"code": "publish_blocked", "message_key": "errors.publish_blocked", "blockers": [...]}` when `publish_blockers` of the stored config is non-empty. `unpublish` is never blocked. Already-published storefronts are not touched.
- Editor: after `save()` in `publish`, if `r.site_config.blockers.length`, show the checklist (one line per blocker, labelled with the existing section/field i18n where available) and do not call publish. Also render that list above the Publish button whenever `cfg.blockers` is non-empty, and disable Publish then. `save()` must return the saved `Storefront`, not just the slug, so `publish` can read blockers.

- [ ] **Step 1: Update the `_published` fixture** in `test_publish_rfq.py` to insert a complete `site_config` (build it with `fallback_site_config(...)` then set de/en product names), so existing publish tests keep meaning "publishable".

- [ ] **Step 2: Write the failing tests**

```python
def test_publish_blockers_lists_required_only():
    cfg = fallback_site_config(COMPANY_NO_YEAR, [], "b2b", "tr")
    b = publish_blockers(cfg)
    assert b[0] == "products"
    assert "about.founded_year" not in b

async def test_publish_blocked_returns_422_with_list(producer, db):
    # storefront with zero products
    r = await c.post("/api/storefronts/mine/publish")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "publish_blocked"
    assert "products" in r.json()["detail"]["blockers"]
    assert (await db.storefronts.find_one({...}))["status"] == "draft"

async def test_already_published_stays_public(producer, db, client):  # Review Focus 1
    # insert status "published" with an incomplete config → public GET is 200
```

(Match the error envelope the app actually returns — check `_err`/`validation_handler`; assert on the same path the other 422 tests use.)

- [ ] **Step 3: Run** `python -m pytest tests/test_publish_rfq.py -q` → FAIL.
- [ ] **Step 4: Implement** backend interfaces; add `errors.publish_blocked` and the checklist labels to both i18n files; implement the editor behaviour.
- [ ] **Step 5: Verify** — `python -m pytest -q` passes; `npm run build && npm run lint` clean; in the browser pane, open the editor of a storefront with an empty DE product name: Publish is disabled and the list shows the field; fill it, save, Publish works.
- [ ] **Step 6: Commit** — `feat: pre-publish checklist enforced on server and shown in editor`

---

### Task 3: Quote weight stays on the quote

Finding: "`POST /api/quotes` persists `unit_weight_kg` from one quote onto the product."

**Files:**
- Modify: `backend/app/routers/quotes.py` (`create`)
- Test: `backend/tests/test_quotes.py`

**Interfaces:**
- Produces: quote document gains `unit_weight_kg: float` (the weight actually used). The `db.products.update_one(... unit_weight_kg ...)` call is deleted. Product weight changes only through the product form (`ProductForm.tsx`, already supported).

- [ ] **Step 1: Failing tests** — create a quote with `unit_weight_kg=2.0` for a product without weight: product doc still has no `unit_weight_kg`, quote doc has `unit_weight_kg == 2.0`. Then create a second quote with no weight → `422 needs_weight` (Review Focus 4).
- [ ] **Step 2: Run** `python -m pytest tests/test_quotes.py -q` → FAIL.
- [ ] **Step 3: Implement.** Check `QuoteBuilder.tsx:102` still asks for weight when the product has none (it reads `product.unit_weight_kg`, so it will — no change expected).
- [ ] **Step 4: Run** full backend suite → pass.
- [ ] **Step 5: Commit** — `fix: keep quote weight on the quote, not the product`

---

### Task 4: Generated PDFs are not publicly reachable

Finding: "`/uploads` is static; generated PDFs rely on UUID secrecy." DECISIONS.md #51.

Fact that sets the design: no frontend code reads `pdf_url`; quote and report PDFs are always streamed by authenticated endpoints. The files on disk are only an audit copy (and are deleted by the KVKK flow). So: keep writing them, stop serving them.

**Files:**
- Modify: `backend/app/main.py` (static mount), `docs/DECISIONS.md` (#51)
- Test: `backend/tests/test_storage.py`

**Interfaces:**
- Produces: `PRIVATE_PREFIXES = ("quotes/", "reports/")` and a `StaticFiles` subclass in `main.py` whose `get_response(path, scope)` raises `HTTPException(404)` when the normalised path starts with a private prefix; mounted at `/uploads` instead of plain `StaticFiles`.

- [ ] **Step 1: Failing test** — write a file under `UPLOADS/quotes/t/x.pdf` and `UPLOADS/products/t/x.webp` (clean up in `finally`); `GET /uploads/quotes/t/x.pdf` → 404, the webp → 200. Also `GET /uploads/./quotes/t/x.pdf` and `/uploads/QUOTES/...` → 404 on Windows-insensitive paths (normalise with `os.path.normpath(path).replace("\\", "/").lower()` before the prefix check).
- [ ] **Step 2: Run** `python -m pytest tests/test_storage.py -q` → FAIL.
- [ ] **Step 3: Implement**; rewrite DECISIONS #51 to: generated PDFs are written under `/uploads/quotes|reports` but never served statically; only the authenticated PDF endpoints return them. Signed URLs/S3 remain the upgrade path.
- [ ] **Step 4: Run** full backend suite → pass.
- [ ] **Step 5: Commit** — `fix: stop serving generated PDFs from the public uploads mount`

---

### Task 5: Public app catch-all 404

Finding: "`/s/{slug}/unknown` renders blank."

**Files:**
- Modify: `frontend/src/PublicApp.tsx`

**Interfaces:**
- Consumes: `STR` from `frontend/src/storefront/strings.ts` (`STR.de.notFound`, `STR.en.notFound`).
- Produces: `<Route path="*" element={<PublicNotFound />} />` where `PublicNotFound` (local to `PublicApp.tsx`) renders both `STR.de.notFound` and `STR.en.notFound` (no language is known on an unknown path), centred like `PublicStorefront`'s error `<p>`.

- [ ] **Step 1: Implement.**
- [ ] **Step 2: Verify** — `npm run build && npm run lint` clean; browser pane: `/s/<demo-slug>/unknown` and `/s/` show the message; `/s/<demo-slug>` and `/s/<demo-slug>/impressum` unchanged.
- [ ] **Step 3: Commit** — `fix: public storefront shows not-found for unknown paths`

---

### Task 6: No ref writes during render

Finding: "`AgentSteps.tsx` mutates `began.current` during render; `useSpeech.ts` assigns `cb.current` during render."

**Files:**
- Modify: `frontend/src/components/AgentSteps.tsx`, `frontend/src/hooks/useSpeech.ts`

**Interfaces:**
- AgentSteps: the `steps.forEach(... began.current[s.key] ??= Date.now())` line moves into `useEffect(..., [steps])`. Render keeps reading `began.current[s.key] ?? now`, which shows 0.0 s for the first frame of a running step — acceptable.
- useSpeech: `cb.current = onFinal` moves into `useEffect(() => { cb.current = onFinal }, [onFinal])`.

- [ ] **Step 1: Implement.**
- [ ] **Step 2: Verify** — `npm run build && npm run lint` clean; browser pane: generate a storefront in demo mode and watch the step timers count up; voice input (Chrome) still fills the field on a final result.
- [ ] **Step 3: Commit** — `fix: move ref writes out of render`

---

### Task 7: Dashboard computes counts in the database

Finding: "`dashboard.py` loads up to 5,000 leads and scans products/reports/messages."

**Files:**
- Modify: `backend/app/routers/dashboard.py` (`dashboard` only; `impact` unchanged)
- Test: `backend/tests/test_dashboard.py`

**Interfaces (response shape unchanged):**
- `leads.count` ← `db.leads.count_documents({"company_id": cid})`.
- `pending_approvals` ← `messages.count_documents({"company_id": cid, "status": "draft"})` + `quotes.count_documents({"company_id": cid, "status": "draft"})`; `sent_quote` ← `quotes.count_documents({"company_id": cid, "status": "sent"})`. (Same filter style as `leads.pipeline_stats`.)
- `roadmap.profile` ← `await db.products.find_one({"company_id": cid}, {"_id": 1}) is not None`; product ids fetched with projection `{"_id": 1}` only for the report query.
- latest report ← `find_one({"product_id": {"$in": pids}}, sort=[("created_at", -1)])`.
- notifications ← `find(...).sort("created_at", -1).limit(20)`.

- [ ] **Step 1: Add a test** that seeds a draft message and a draft quote **for a different company** and asserts they are not counted in `pending_approvals` (guards the switch from lead-id to company-id filtering). Existing dashboard tests must keep passing unchanged.
- [ ] **Step 2: Run** `python -m pytest tests/test_dashboard.py -q` — new test may already pass; that is fine, it is a regression guard.
- [ ] **Step 3: Implement.** Before switching filters, grep `insert_one`/`insert_many` into `messages` and `quotes` (incl. `app/seed`) and confirm every writer sets `company_id`; if one does not, fix that writer in this task.
- [ ] **Step 4: Run** full backend suite → pass.
- [ ] **Step 5: Commit** — `perf: dashboard counts via count_documents and sorted find_one`

---

### Task 8: Leads list sorted and paginated in the database

Finding: "`leads.list_leads` loads up to 5,000 docs and sorts in Python."

**Files:**
- Modify: `backend/app/routers/leads.py` (`list_leads`), `backend/app/core/db.py` (`ensure_indexes`)
- Modify: `frontend/src/pages/leads/LeadsTable.tsx`, `frontend/src/pages/pipeline/Pipeline.tsx`, i18n files
- Test: `backend/tests/test_leads.py`

**Interfaces:**
- `GET /api/leads?sort=&status=&limit=&offset=` — `limit: int = Query(100, ge=1, le=500)`, `offset: int = Query(0, ge=0)`. Body stays a JSON array; total goes in response header `X-Total-Count` (from `count_documents(q)`); add it to CORS `expose_headers` in `main.py`.
- Sort specs: `score` → `[("score", -1), ("created_at", -1)]`; `created_at` → `[("created_at", -1)]`; default → `[("is_hot", -1), ("score", -1), ("created_at", -1)]`. Add `_id` `-1` as final tiebreaker to all three so pages are stable.
- Index: `leads` `[("company_id", 1), ("created_at", -1)]`.
- `LeadsTable.tsx`: keeps current page in state, shows "N / total" and a "Daha fazla yükle / Load more" button while `leads.length < total`, appending the next page. The `api` helper must expose headers — if it does not, read `X-Total-Count` by adding a minimal option to `frontend/src/api`, not a second fetch path.
- `Pipeline.tsx`: requests `limit=500` (today's effective ceiling was 5000; 500 is the new cap — note it in DECISIONS.md).

- [ ] **Step 1: Failing tests** — seed 3 leads with distinct score/hot/created_at; assert default order, `sort=score` order, `limit=2` returns 2 with `X-Total-Count: 3`, `offset=2` returns the third; `limit=501` → 422. Review Focus 3: `?sort=score&limit=500` returns all 3.
- [ ] **Step 2: Run** `python -m pytest tests/test_leads.py -q` → FAIL.
- [ ] **Step 3: Implement** backend, then frontend.
- [ ] **Step 4: Verify** — full backend suite passes; `npm run build && npm run lint` clean; browser pane: leads page lists demo leads in the same order as before; pipeline page unchanged.
- [ ] **Step 5: Commit** — `perf: DB-level sort and pagination for leads`

---

### Task 9: Shared LLM HTTP client with bounded retries

Finding: "`llm_service._post` creates a new `httpx.AsyncClient` per call; reuse a client and add bounded retries for 429/5xx/timeouts."

**Files:**
- Modify: `backend/app/services/llm_service.py` (`_post`), `backend/app/main.py` (`lifespan` closes the client)
- Test: `backend/tests/test_llm_service.py`

**Interfaces:**
- Produces: module-level `_http: httpx.AsyncClient | None`, `def _client() -> httpx.AsyncClient` (lazy create, no client-level timeout), `async def aclose() -> None` (called after `yield` in `lifespan`). Tests inject `llm_service._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))`.
- `_post(url, headers, body, timeout)` keeps its signature and errors. Per-request `timeout=timeout`. Retries: `_BACKOFF = (0.5, 1.5)` seconds → at most 3 attempts. Retry on status 429 and 5xx and on `httpx.ConnectError`/`httpx.ConnectTimeout`. **Do not retry `ReadTimeout`/other timeouts**: `agent_steps.run_ai_step` owns the demo time budget and falls back on `LLMTimeout`; retrying a read timeout would triple a slow step. (This narrows the finding's "timeouts" on purpose — principle 7.) Honour a numeric `Retry-After` header only if ≤ the backoff slot, else use the slot.

- [ ] **Step 1: Failing tests** (monkeypatch `_BACKOFF` to `(0, 0)`):
  - 503 then 200 → returns the 200 JSON, handler called twice.
  - 429 three times → raises `LLMProviderError`, handler called exactly 3 times (Review Focus 5).
  - 400 → raises immediately, called once.
  - `httpx.ReadTimeout` → raises `LLMTimeout`, called once.
  - two `_post` calls reuse the same client object.
- [ ] **Step 2: Run** `python -m pytest tests/test_llm_service.py -q` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** full backend suite → pass.
- [ ] **Step 5: Commit** — `perf: reuse LLM HTTP client, retry 429/5xx/connect errors`

---

## Final Check

- [ ] `cd backend && python -m pytest -q` — all pass.
- [ ] `cd frontend && npm run build && npm run lint` — clean.
- [ ] Browser pane demo run (`docs/RUNNING.md`): onboarding → storefront generate (fallback path: set an invalid LLM key) → DE tab shows no Turkish product names, Publish blocked until names filled → publish → `/s/<slug>` loads, `/s/<slug>/x` shows not-found → leads page → quote with weight → dashboard numbers match before/after.
