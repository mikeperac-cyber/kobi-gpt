# KOBİ-GPT & Otonom İhracat Ajanı — MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full KOBİ-GPT MVP (auth + onboarding, AI storefront, KB-grounded compliance checker, human-approved buyer outreach, demo mode) so it survives a live 3-minute jury demo with or without an LLM key.

**Architecture:** FastAPI + Motor backend with one service per module; every LLM call goes through `llm_service` and every AI step through `run_ai_step`, which supplies the timeout → demo cache → deterministic fallback chain. Long AI flows run as background jobs whose step states the React SPA polls and renders with `AgentSteps`. The public storefront is a route of the same SPA, lazy-split from producer code.

**Tech Stack:** Python 3.12 (env has 3.12.10), FastAPI, Pydantic v2, pydantic-settings, Motor, PyJWT, bcrypt, httpx, ReportLab, Pillow, qrcode; tests: pytest, pytest-asyncio, mongomock-motor, pypdf. Node 26 (env), React 18 + Vite + TypeScript, Tailwind, React Router, react-i18next.

**Spec:** `prompts/full-build-prompt.md` (wins over `AGENTS.md` and the phase files where they differ).

## Global Constraints

- Do not touch root `README.md`, `prompts/`, or `AGENTS.md`. Run instructions go to `docs/RUNNING.md`; decisions to `docs/DECISIONS.md`; evidence to `docs/ACCEPTANCE.md`.
- Code, comments and docs in English. Producer UI: Turkish (`tr`, default) and English (`en`), no hard-coded UI strings. Storefront content: German and English.
- Dates/numbers formatted with `tr-TR` / `en-GB`.
- `price_floor` never appears in any API response except to its owner, in any LLM prompt, in any generated text, or in any PDF.
- Every LLM prompt is a file in `backend/app/prompts/` with role, task, exact JSON schema, and the line "do not invent facts that are not in the provided context". Every producer-readable prompt takes `ui_language` (tr | en); cache keys include it.
- Every LLM call is logged to `agent_runs` (type, company_id, input_summary, output, status, duration_ms, error, created_at).
- `LLM_TIMEOUT_SECONDS` default 45, `DEMO_LLM_TIMEOUT_SECONDS` default 25; `generate_json` retries up to 2 times on invalid JSON.
- Tests mock the LLM and pass with no network and no API keys.
- PDF: ReportLab only, with a bundled Noto Sans TTF (OFL) — no system fonts, no WeasyPrint.
- Uploads: jpg/png/webp by file signature, ≤ 8 MB, resized when wider or taller than 1600 px, stored as WebP.
- Auth: bcrypt, JWT in httpOnly SameSite=Lax cookie. `is_admin` only via seed/env.
- Primary colour `#C8102E` used sparingly; navy text; font with full Turkish glyphs.
- Mailto approval label: "Mail uygulamasına aktarıldı" / "Handed to your mail app", never "Gönderildi" / "Sent".
- Demo storefront slug for Bozkurt: `bozkurt-pistazien`.
- Admins never read another company's products, leads or floor prices.
- KB: insert exactly the spec §5.2 records, all `verified: false`, `last_verified: null`; no amounts, rates, deadlines or thresholds beyond the titles.
- GTİP warning always shown: "Kesin GTİP (12 hane) için gümrük müşavirinize danışın."
- Out of scope: payments, e-Devlet/MERSİS, Kolay İhracat integration (link only), scraping, autonomous sending, fine-tuning, native apps.

## Decisions made by this plan (copy into `docs/DECISIONS.md` in Task 1)

1. **No local MongoDB found.** Tests use `mongomock-motor`; the running app needs `MONGO_URI` (local `mongod` or Atlas). Task 1 records what is missing.
2. **Not a git repo yet.** Task 1 runs `git init`; every task ends in a commit.
3. **Live step progress = polling.** Long AI flows create a `jobs` document; the frontend polls `GET /api/jobs/{id}` every 700 ms. No SSE/websockets.
4. **LLM providers via raw `httpx`** (no vendor SDKs). Default `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-5-5`.
5. **Prompt templates use `string.Template` (`$var`)** so JSON braces in schemas need no escaping. `render_prompt` raises if the context contains a `price_floor` key anywhere.
6. **Rate limiting is an in-memory fixed-window counter** (`shortcut: per-process only, swap for Redis when running >1 worker`).
7. **Readiness score is computed server-side only**; each tick is a PATCH that returns the new score (optimistic UI). One formula, no duplicate in TS.
8. **OpenGraph tags are set client-side** on `/s/{slug}` (`shortcut: crawlers that don't run JS won't see them; server-render the head if link previews matter`).
9. **Seed photos are Pillow-generated labelled placeholders** (no downloads).
10. **i18n key parity is checked by pytest** (reads `frontend/src/i18n/*.json`), so one suite covers it. No frontend unit-test framework; frontend is verified by `npm run build` (tsc) and browser walk-throughs.
11. **Demo companies** carry `is_demo_company: true`; the demo timeout and `demo_cache` apply only to them.
12. **Quote PDF and readiness PDF both go through `pdf_service`**, which takes already-public dicts (never a product document), so the floor cannot reach it.

## Review Focus

1. **Email case** — `Ali@Firma.com` registered, `ali@firma.com` logs in: must work and must not create a duplicate. → Task 3 test `test_email_is_case_insensitive`.
2. **Turkish dotted/dotless I in slugs and keyword matching** — Python's `"İ".lower()` yields `"i̇"` (i + combining dot); `"İzmir Iğdır"` must slug to `izmir-igdir`, and keyword overlap must treat `İÇ`/`iç` as equal. → Task 11 `test_slug_turkish_capitals`, Task 25 `test_product_match_turkish_case`.
3. **LLM HS-code formats** — models return `"200819"`, `"2008.19.00"`, `"2008 19"`. Expect normalization to `2008.19`; garbage (`"20A8"`) dropped, not crashing. → Task 19 `test_hs_code_normalization`.
4. **Excel-exported CSVs** — UTF-8 with BOM or Windows-1254 with Turkish characters, `;` delimiter. Expect correct `Müller GmbH` / `Şahin`, not mojibake or a 500. → Task 25 `test_csv_import_bom_cp1254_semicolon`.
5. **Quote edge inputs** — quantity 0/negative, missing `unit_weight_kg`, weight exactly at a band edge or truck capacity. Expect 422 / "ask for weight", not a zero-cost estimate; band edges deterministic. → Task 28 `test_logistics_edges`.

---

## File Structure

```
.gitignore  .env.example
backend/requirements.txt  backend/pytest.ini
backend/app/main.py                       app factory, CORS, static /uploads, routers
backend/app/core/config.py                Settings (pydantic-settings, reads ../.env)
backend/app/core/db.py                    get_db / set_db, indexes
backend/app/core/security.py              hashing, JWT, current_user/current_company/require_admin deps
backend/app/core/ratelimit.py             RateLimiter
backend/app/core/serialize.py             doc→json (ObjectId→str), public_product()
backend/app/models/*.py                   Pydantic request/response + AI output schemas, per area
backend/app/routers/{health,auth,company,products,uploads,dashboard,jobs,storefronts,public,
                     compliance,admin_kb,leads,messages,quotes,logistics,demo,account,admin}.py
backend/app/services/llm_service.py       providers, render_prompt, generate_text/json, logging
backend/app/services/agent_steps.py       jobs + run_ai_step (timeout → cache → fallback)
backend/app/services/storage_service.py   Storage protocol + LocalStorage
backend/app/services/storefront_service.py  slugify, fallback config, generation, regen section
backend/app/services/regai_service.py     match_rules, filter_incentives, gtip, explain, next steps
backend/app/services/scoring.py           readiness_score, lead_score
backend/app/services/outreach_service.py  drafts, translation, approval gate, reply analysis, EmailProvider
backend/app/services/logistics_service.py estimate()
backend/app/services/pdf_service.py       readiness_pdf, quote_pdf
backend/app/services/demo_service.py      reset_demo_company, demo cache read/write
backend/app/prompts/*.md                  one file per LLM prompt
backend/app/seed/__main__.py  seed/data/*.json  seed/images.py
backend/app/assets/fonts/NotoSans-{Regular,Bold}.ttf
backend/tests/conftest.py  tests/test_*.py
frontend/  (Vite) src/main.tsx App.tsx api/client.ts i18n/{index.ts,tr.json,en.json}
frontend/src/components/{Layout,LanguageSwitch,ErrorBoundary,AgentSteps,DemoGuide,ui/*}.tsx
frontend/src/pages/{auth,onboarding,dashboard,company,products,storefront,compliance,leads,
                    approvals,quotes,pipeline,admin,demo,account,privacy}/...
frontend/src/storefront/{StorefrontView,PublicStorefront,LegalPages,RfqForm,themes}.tsx
uploads/  docs/{RUNNING,DECISIONS,ACCEPTANCE}.md
```

All API routes are under `/api`. Error bodies are `{"detail": {"code": str, "message_key": str}}` where `message_key` is an i18n key; the frontend translates it (keeps backend messages bilingual-free).

---

# Phase 1 — Foundation

### Task 1: Repo scaffold, config, health, test harness

**Files:**
- Create: `.gitignore` (`.env`, `uploads/*` except `.gitkeep`, `node_modules`, `__pycache__`, `.venv`, `dist`), `.env.example` (every key in spec §4.3 plus `ADMIN_EMAIL`), `backend/requirements.txt`, `backend/pytest.ini` (`asyncio_mode = auto`), `backend/app/main.py`, `backend/app/core/{config,db,serialize}.py`, `backend/app/routers/health.py`, `backend/tests/conftest.py`, `docs/{DECISIONS,ACCEPTANCE,RUNNING}.md`, `uploads/.gitkeep`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `get_settings() -> Settings` (fields: `mongo_uri, mongo_db, jwt_secret, llm_provider, llm_model, openai_api_key, gemini_api_key, anthropic_api_key, llm_timeout_seconds=45, demo_llm_timeout_seconds=25, frontend_origin="http://localhost:5173", email_provider="", seed_password, admin_email`; property `llm_key -> str|None` picks the key matching the provider).
- `get_db() -> AsyncIOMotorDatabase`, `set_db(db)` (tests inject mongomock).
- `create_app() -> FastAPI`; `app = create_app()`.
- `to_json(doc) -> dict` (`_id` → `id` str, ObjectId/datetime → str).
- conftest fixtures: `db` (fresh mongomock-motor DB per test), `client` (`httpx.AsyncClient` over ASGI), `fake_llm` (see Task 2), `producer(client, name) -> dict` (registers+logs in, returns `{"user","company","client"}`) — `producer` lands in Task 5 once endpoints exist.

- [ ] **Step 1:** `git init`; create venv `backend/.venv`; write requirements (`fastapi uvicorn[standard] pydantic pydantic-settings motor pyjwt bcrypt httpx python-multipart pillow qrcode reportlab pytest pytest-asyncio mongomock-motor pypdf`); `pip install -r backend/requirements.txt`. Check whether `mongod` exists or `MONGO_URI` is set; write the result and Decisions 1–12 into `docs/DECISIONS.md`.
- [ ] **Step 2: Write the failing test**

```python
async def test_health_reports_provider_without_key(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-123")
    get_settings.cache_clear()
    r = await client.get("/api/health")
    body = r.json()
    assert r.status_code == 200
    assert body == {"status": "ok", "llm": {"provider": "anthropic", "key_set": True}}
    assert "sk-secret-123" not in r.text
```

- [ ] **Step 3:** Run `cd backend; .venv\Scripts\python -m pytest tests/test_health.py -v` → FAIL (import error).
- [ ] **Step 4:** Implement config (`lru_cache` on `get_settings`), db, `create_app()` (CORS `allow_origins=[settings.frontend_origin]`, `allow_credentials=True`; mount `/uploads` StaticFiles), health router.
- [ ] **Step 5:** Run the test → PASS.
- [ ] **Step 6:** Commit `chore: scaffold backend, config, health`.

### Task 2: `llm_service` and `agent_runs` logging

**Files:**
- Create: `backend/app/services/llm_service.py`, `backend/app/prompts/admin_ping.md`, `backend/app/routers/admin.py` (test endpoint only for now), `backend/app/core/security.py` (stub `require_admin` dependency finished in Task 3)
- Test: `backend/tests/test_llm_service.py`

**Interfaces:**
- Produces:
  - Errors: `LLMError(Exception)`; subclasses `LLMNotConfigured`, `LLMTimeout`, `LLMInvalidOutput`, `LLMProviderError`.
  - `class Provider(Protocol): async def complete(self, prompt: str, images: list[bytes], timeout: float, json_mode: bool) -> str`
  - `set_provider(p: Provider | None)` — test hook; `None` = build from settings.
  - `render_prompt(name: str, context: dict) -> str` — loads `prompts/{name}.md`, `string.Template.substitute`; raises `ValueError("price_floor in prompt context")` if the key appears at any depth; non-str values are `json.dumps(..., ensure_ascii=False)`.
  - `async generate_text(name, context, *, run_type: str, company_id: str|None, images: list[bytes]=(), timeout: float|None=None) -> str`
  - `async generate_json(name, context, schema: type[M], *, run_type, company_id, images=(), timeout=None) -> M` — strips ```json fences, validates with `schema.model_validate_json`, up to 2 retries (3 attempts) appending the validation error to the prompt; then `LLMInvalidOutput`.
  - Each call inserts one `agent_runs` doc: `input_summary` = prompt name + first 300 chars of rendered prompt.
- `FakeLLM` in conftest: `FakeLLM(responses: list[str] | Callable[[str], str])`, records `.prompts: list[str]`; fixture `fake_llm` installs it via `set_provider`.
- Admin route `POST /api/admin/llm-test` → `generate_json("admin_ping", {}, PingOut)` where `PingOut = {ok: bool, echo: str}`.

- [ ] **Step 1: Write failing tests**

```python
async def test_generate_json_retries_then_succeeds(db, fake_llm):
    fake_llm.responses = ["not json", '{"ok": true, "echo": "x"}']
    out = await generate_json("admin_ping", {}, PingOut, run_type="test", company_id=None)
    assert out.ok and len(fake_llm.prompts) == 2
    run = await db.agent_runs.find_one({"type": "test"})
    assert run["status"] == "ok" and run["duration_ms"] >= 0

async def test_generate_json_gives_up_after_two_retries(db, fake_llm):
    fake_llm.responses = ["x", "y", "z"]
    with pytest.raises(LLMInvalidOutput):
        await generate_json("admin_ping", {}, PingOut, run_type="test", company_id=None)
    assert len(fake_llm.prompts) == 3
    assert (await db.agent_runs.find_one({"type": "test"}))["status"] == "error"

async def test_no_key_raises_typed_error(db, monkeypatch):
    set_provider(None); monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False); get_settings.cache_clear()
    with pytest.raises(LLMNotConfigured):
        await generate_text("admin_ping", {}, run_type="test", company_id=None)

def test_render_prompt_rejects_price_floor():
    with pytest.raises(ValueError):
        render_prompt("admin_ping", {"product": {"name": "x", "price_floor": 5}})

async def test_admin_llm_test_endpoint(admin_client, fake_llm):
    fake_llm.responses = ['{"ok": true, "echo": "pong"}']
    r = await admin_client.post("/api/admin/llm-test")
    assert r.json() == {"ok": True, "echo": "pong"}
```

(`admin_client` fixture is added in Task 3; mark that last test `xfail` until then or write it in Task 3.)
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Providers: `AnthropicProvider` (`POST https://api.anthropic.com/v1/messages`, header `x-api-key`, `anthropic-version: 2023-06-01`, images as base64 `image` blocks), `OpenAIProvider` (`/v1/chat/completions`, `response_format={"type":"json_object"}` when json_mode, images as data URLs), `GeminiProvider` (`generateContent`, `inline_data`). `httpx.TimeoutException` → `LLMTimeout`; non-2xx → `LLMProviderError`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: llm_service with schema retry, typed errors, run logging`.

### Task 3: Auth, language preference, auth rate limit

**Files:**
- Create: `backend/app/routers/auth.py`, `backend/app/core/ratelimit.py`, `backend/app/models/auth.py`
- Modify: `backend/app/core/security.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces:
  - `hash_password(p) -> str`, `verify_password(p, h) -> bool`, `create_token(user_id: str) -> str` (HS256, 7 days), cookie name `kobi_session`.
  - Deps: `current_user -> dict` (401 if missing), `require_admin -> dict` (403 unless `is_admin`).
  - `RateLimiter(limit: int, window_s: int).check(key: str) -> None` raises `HTTPException(429)`. Auth: 10/min per IP+email.
  - `POST /api/auth/register {name, email, password(min 8), kvkk_consent: true}` → 201 user; sets cookie; `ui_language="tr"`, `kvkk_consent_at=now`. Email stored lowercased+stripped; duplicate → 409 `email_taken`. `kvkk_consent` false → 422.
  - `POST /api/auth/login {email, password}`, `POST /api/auth/logout`, `GET /api/auth/me` → `{id, name, email, is_admin, ui_language, has_company}`.
  - `PATCH /api/auth/me {ui_language: "tr"|"en"}`.
  - conftest: `admin_client` fixture (user with `is_admin=True` inserted directly).

- [ ] **Step 1: Write failing tests** — `test_register_requires_kvkk`, `test_password_min_8`, `test_register_login_logout_cycle` (me → 200, logout → me 401, login → 200), `test_email_is_case_insensitive` (register `Ali@Firma.com`, login `ali@firma.com` → 200; register `ALI@firma.com` → 409), `test_ui_language_persists_across_login` (PATCH en, logout, login, me.ui_language == "en"), `test_auth_rate_limit` (11th bad login in a minute → 429), `test_cookie_flags` (`httponly` and `samesite=lax` in `set-cookie`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS (also un-xfail the Task 2 admin test).
- [ ] **Step 5:** Commit `feat: auth with KVKK consent, JWT cookie, ui_language`.

### Task 4: `storage_service` and uploads

**Files:**
- Create: `backend/app/services/storage_service.py`, `backend/app/routers/uploads.py`
- Test: `backend/tests/test_storage.py`

**Interfaces:**
- Produces: `class Storage(Protocol): async def save(self, data: bytes, prefix: str) -> str` (returns public URL `/uploads/...`), `async def delete(self, url: str) -> None`. `LocalStorage(root="uploads")`. `get_storage() -> Storage`.
- `validate_and_process_image(data: bytes) -> bytes` — signature check (`\xff\xd8\xff`, `\x89PNG\r\n\x1a\n`, `RIFF....WEBP`), > 8 MB → `ValueError("too_large")`, unknown → `ValueError("bad_type")`; `ImageOps.exif_transpose`, convert CMYK/P/LA to RGB/RGBA, `thumbnail((1600,1600))`, save WebP quality 80.
- `POST /api/uploads/image` (multipart `file`, auth) → `{url}`; 422 with code `bad_type` / `too_large`.

- [ ] **Step 1: Write failing tests** — `test_rejects_renamed_text_file` (`b"hello"` named `x.jpg` → bad_type), `test_rejects_over_8mb`, `test_resizes_large_png` (2400×1200 → max side 1600, output starts with `RIFF`), `test_converts_cmyk_jpeg_and_rgba_png`, `test_upload_endpoint_requires_auth`.
- [ ] **Steps 2–4:** fail → implement → pass. **Step 5:** Commit `feat: image storage with signature checks and WebP`.

### Task 5: Company, products, markets API with ownership and floor secrecy

**Files:**
- Create: `backend/app/routers/{company,products}.py`, `backend/app/models/{company,product}.py`
- Modify: `backend/app/core/security.py` (`current_company`), `backend/app/core/serialize.py` (`public_product`, `owner_product`)
- Test: `backend/tests/test_company_products.py`, `backend/tests/test_ownership.py` (grows in later tasks)

**Interfaces:**
- Produces:
  - Dep `current_company -> dict` (the caller's company; 404 `no_company` if none).
  - `owned(collection: str, id: str, company_id: str) -> dict` helper: returns doc or raises 404 (never 403, to avoid existence leaks). Every company-scoped endpoint uses it.
  - `public_product(doc) -> dict` drops `price_floor`; `owner_product(doc) -> dict` keeps it. Only `GET/PUT /api/products*` for the owner use `owner_product`.
  - Models: `CompanyIn` (spec §5.1 fields; `sector` enum; `city` must be in `TR_PROVINCES` (81 names, in `backend/app/models/provinces.py`, mirrored in `frontend/src/data/provinces.ts`); `certifications` subset of `CERTS = ["ISO 9001","ISO 22000","BRC","IFS","OEKO-TEX","Helal","Organik","CE","IATF 16949","Diğer"]` — IATF added for the Bursa seed, recorded as a decision).
  - `ProductIn`: `name_tr, description_tr, material_or_ingredients, unit (kg|adet|metre|koli), moq: float>0, unit_weight_kg: float>0|None, price_floor: float>0, photos: list[str] (1–6 at onboarding; 0–6 on edit)`.
  - Routes: `POST /api/onboarding {company, product, market: {country_code:"DE"}}` (one call, writes all three; markets other than DE → 422), `GET/PUT /api/company`, `GET/POST /api/products`, `GET/PUT/DELETE /api/products/{id}`.

- [ ] **Step 1: Write failing tests** — `test_onboarding_creates_company_product_market`, `test_only_de_market_allowed`, `test_owner_sees_floor`, `test_other_user_gets_404_on_product` (B reads/edits A's product → 404), `test_floor_absent_from_non_owner_responses` (helper `assert_no_floor(obj)` walks any JSON for key `price_floor`; reused in every later ownership/floor test — put it in `tests/helpers.py`), `test_city_must_be_province`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: company/product/market API with ownership and floor secrecy`.

### Task 6: Seed script (all seed data for every phase)

**Files:**
- Create: `backend/app/seed/__main__.py`, `backend/app/seed/images.py`, `backend/app/seed/data/{companies,kb_hs_codes,kb_rules,kb_incentives,demo_leads,logistics_rates}.json`
- Test: `backend/tests/test_seed.py`

**Interfaces:**
- Produces: `async seed(db) -> dict[str,int]` (counts); `python -m app.seed` runs it on the configured DB. Idempotent: upsert by stable key (user email, company name, KB `id`, lead email, rate `key`).
- Users: admin (`ADMIN_EMAIL` or `admin@kobi-gpt.local`, `is_admin`), `bozkurt@demo.local`, `pamukkale@demo.local`, `uludag@demo.local`; password `SEED_PASSWORD` (error out if unset).
- Companies (`is_demo_company: true`): spec Phase 1 three firms with realistic Turkish descriptions; products: Bozkurt — "Kabuklu Kavrulmuş Antep Fıstığı" (1 kg & 10 kg packs, kg, unit_weight 1.0) and "İç Antep Fıstığı"; Pamukkale — "%100 Pamuk Havlu", "Pamuk Bornoz"; Uludağ — "Galvanizli Çelik Cıvata M8", "Galvanizli Çelik Somun M8". Each has a `price_floor`, `moq`, and 2 placeholder photos from `images.make_placeholder(label: str, color: str) -> bytes` (Pillow, 1200×900, label text drawn with the bundled Noto Sans).
- KB: exactly R1–R15, I1–I9, 8 HS6 codes from spec §5.2, with `id`, `title_tr/title_en` (rules), `name_tr/name_en` (incentives), `summary_tr/summary_en`, `what_to_do_tr/what_to_do_en`, `documents_tr/documents_en` (rules), `description_tr/description_en` (HS), constraint fields `country: "DE"`, `hs_prefixes: list[str]`, `sectors: list[str]`, `channel: "b2b"|"b2c"|None`, `structural_use: bool|None`, `side: "TR"|"DEST"`, `level: "zorunlu"|"koşullu"|"önerilen"`, `source_url`, `verified: false`, `last_verified: null`. R1 has no `country` constraint (Turkish side, applies everywhere) — record as decision. Incentives: `provider`, `stages: list`, `sectors: list` (empty = all).
- Demo leads: 6 per demo company, `is_demo: true`, `source: "demo"`, `email` `@example.com`, fictional German names (check none matches a well-known real firm), `country: "DE"` for 5 and `"AT"` for 1 (exercises the country score).
- Logistics rates (see Task 28 for shape) with `label_tr: "ÖRNEK – gerçek forwarder teklifiyle değiştirin"`.
- Bundle font: download `NotoSans-Regular.ttf` and `NotoSans-Bold.ttf` from the `notofonts/notofonts.github.io` repo into `backend/app/assets/fonts/` with `OFL.txt`.

- [ ] **Step 1: Write failing tests** — `test_seed_is_idempotent` (run twice, counts identical, no duplicate users), `test_kb_ids_exact` (`{r["id"]} == {f"R{i}" for i in 1..15}`, I1–I9, 8 HS codes), `test_kb_records_bilingual` (every record has non-empty `*_tr` and `*_en` pairs; `verified is False`), `test_demo_leads_marked` (all `is_demo` and `@example.com`), `test_no_storefronts_seeded`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: idempotent seed with demo firms, KB, leads, rates`.

### Task 7: Frontend scaffold, i18n, auth screens, layout

**Files:**
- Create: `frontend/` via `npm create vite@latest frontend -- --template react-ts`; add `tailwindcss`, `react-router-dom`, `i18next`, `react-i18next`, `@fontsource/noto-sans`. `vite.config.ts` proxies `/api` and `/uploads` to `http://localhost:8000`.
- Create: `src/api/client.ts`, `src/i18n/{index.ts,tr.json,en.json}`, `src/auth/AuthContext.tsx`, `src/components/{Layout,LanguageSwitch,ErrorBoundary,ProtectedRoute}.tsx`, `src/components/ui/{Button,Input,Select,Card,Badge,Modal,Field,Skeleton}.tsx`, `src/pages/auth/{Login,Register}.tsx`, `src/pages/privacy/PrivacyNotice.tsx` (Aydınlatma Metni content as i18n keys, used in the register modal and as a page)
- Test: `backend/tests/test_i18n.py`

**Interfaces:**
- Produces:
  - `api<T>(path: string, init?: RequestInit & {json?: unknown}): Promise<T>` — `credentials: "include"`; throws `ApiError {status, code, messageKey}`.
  - `useAuth(): {user, refresh(), login(email,pw), logout(), setLanguage(lang)}` — `setLanguage` calls `i18n.changeLanguage` and `PATCH /api/auth/me` when logged in; on login, applies `user.ui_language`.
  - `formatDate(d)`, `formatNumber(n)`, `formatMoney(n, cur)` in `src/i18n/format.ts` using `tr-TR` / `en-GB`.
  - Key namespaces in the JSON: `common, auth, nav, onboarding, dashboard, company, products, storefront, compliance, leads, approvals, quotes, pipeline, admin, demo, account, errors, agent`.
  - Tailwind theme: `brand: #C8102E`, `navy: #0B1F3A`; body font Noto Sans.
  - `ErrorBoundary` shows `errors.boundary_title` ("Bir şeyler ters gitti") + retry button that resets state.

- [ ] **Step 1: Write failing test** (`backend/tests/test_i18n.py`)

```python
def flat(d, p=""): ...  # dotted keys
def test_tr_en_key_parity():
    tr, en = load("tr"), load("en")
    assert set(flat(tr)) == set(flat(en)), set(flat(tr)) ^ set(flat(en))
def test_no_empty_strings():
    for lang in ("tr", "en"):
        assert all(v.strip() for v in flat(load(lang)).values())
```

- [ ] **Step 2:** Run → FAIL (files missing). **Step 3:** Implement scaffold, auth pages (register: name, email, password ≥ 8, KVKK checkbox required with link opening the Aydınlatma Metni modal), header with company name + TR | EN switch.
- [ ] **Step 4:** `pytest tests/test_i18n.py` → PASS; `cd frontend; npm run build` → no TS errors. Start both servers, register, log out, log in, switch to EN, log out/in → still EN.
- [ ] **Step 5:** Commit `feat: frontend scaffold with bilingual auth`.

### Task 8: Onboarding wizard, Firmam, Ürünlerim

**Files:**
- Create: `src/pages/onboarding/{Wizard,StepCompany,StepProduct,StepMarket}.tsx`, `src/components/PhotoPicker.tsx`, `src/pages/company/CompanyPage.tsx`, `src/pages/products/{ProductsPage,ProductForm}.tsx`, `src/data/{provinces,certifications}.ts`

**Interfaces:**
- Consumes: Task 5 routes, Task 4 upload.
- Produces: `<ProductForm value onChange mode="onboarding"|"edit" />` (reused in wizard step 2 and Ürünlerim); `<PhotoPicker urls max={6} onChange />` with previews, remove, reorder (up/down buttons — keyboard accessible; reused by the storefront editor in Task 15).
- StepCompany includes the optional logo upload (single image through `POST /api/uploads/image`, stored as `companies.logo_url`).
- Copy fixed by spec: description hint "Ürününüzü bir müşteriye anlatır gibi yazın"; floor tooltip "Bu fiyat alıcılara asla gösterilmez; ajan bunun altına teklif vermez."; markets Hollanda, Fransa, ABD, BAE, Irak disabled with "Yakında" / "Coming soon". Logged-in users without a company are redirected to the wizard.

- [ ] **Step 1:** Implement. **Step 2:** `npm run build` passes; `pytest tests/test_i18n.py` passes.
- [ ] **Step 3:** Browser at 375×812: complete all three steps with two photos; no horizontal scroll (`document.documentElement.scrollWidth <= 375`). Edit company on Firmam, add a product on Ürünlerim. Repeat in EN.
- [ ] **Step 4:** Commit `feat: onboarding wizard and company/product pages`.

### Task 9: Dashboard ("İhracat Panosu") and notifications

**Files:**
- Create: `backend/app/routers/dashboard.py`, `src/pages/dashboard/{Dashboard,ModuleCard,Roadmap,Notifications}.tsx`, placeholder pages `src/pages/{storefront,compliance,leads}/Index.tsx`
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Produces: `GET /api/dashboard` →
  `{company: {name, country_code}, storefront: {status: "none"|"draft"|"published", slug}, compliance: {score: int|None}, leads: {count, pending_approvals}, roadmap: {profile, storefront, compliance, first_quote: bool}, notifications: [{id, type, message_key, params, read, created_at}]}`.
  Roadmap: profile = company+product exist; storefront = published; compliance = a readiness report exists; first_quote = any quote with status `sent`. `pending_approvals` = drafts in messages + quotes.
- `POST /api/notifications/{id}/read`.
- Notifications store `type` + `params` (e.g. `{"lead_company": "..."}`) and the UI renders `dashboard.notif.<type>` — spec's `message_tr` field is kept too for the record (decision: keys rendered client-side so EN works).

- [ ] **Step 1: Write failing tests** — `test_dashboard_fresh_company` (roadmap profile only → 1/4; storefront "none"; score None), `test_dashboard_counts_real` (insert 2 leads, 1 draft message, 1 draft quote → count 2, pending 2), `test_dashboard_scoped_to_owner`.
- [ ] **Steps 2–4**, then browser check of cards, badges (Taslak/Yayında, Yapılmadı/Hazırlık skoru %X, N lead / M onay bekleyen mesaj), roadmap strip in both languages.
- [ ] **Step 5:** Commit `feat: export dashboard with roadmap and notifications`.

### Task 10: Phase 1 acceptance

- [ ] Run the full pytest suite → all pass. Start backend (`uvicorn app.main:app --reload`) against a real Mongo, run `python -m app.seed`, start frontend.
- [ ] Walk each Phase 1 criterion; write PASS/FAIL with evidence (test names, response JSON excerpts, UI steps) in `docs/ACCEPTANCE.md`. Mark FAIL (not PASS) for anything not run, e.g. if no Mongo is reachable.
- [ ] Commit `docs: phase 1 acceptance`.

---

# Phase 2 — Dijital Vitrin

### Task 11: Slugs, `site_config` schema, deterministic fallback config

**Files:**
- Create: `backend/app/models/storefront.py`, `backend/app/services/storefront_service.py` (pure parts)
- Test: `backend/tests/test_storefront_pure.py`

**Interfaces:**
- Produces:
  - `tr_fold(s: str) -> str` — map `ş Ş→s, ğ Ğ→g, ı I İ→i, ö Ö→o, ü Ü→u, ç Ç→c` *before* lowercasing (avoids Python's `"İ".lower() == "i̇"`), then lowercase, NFKD, drop combining marks. Reused by lead keyword matching (Task 25).
  - `slugify_tr(text: str) -> str` — `tr_fold`, keep `[a-z0-9]`, collapse the rest to `-`, strip, max 60.
  - `async unique_slug(db, base: str, exclude_id: str|None=None) -> str` — appends `-2`, `-3`…
  - `MissingStr = str | None` convention: a field the AI could not fill is `None` and listed in `SiteConfig.missing: list[str]` (dotted paths like `export_info.lead_time`).
  - `class LocalizedContent(BaseModel)`: `hero{headline, subheadline, cta}`, `about{story, city, founded_year, team_size, certifications[]}`, `products[{product_id, name, short, long, specs: list[{label,value}], moq, packaging, photos[]}]`, `why_us: list[str]` (3–4), `export_info{incoterms: list[str], lead_time, sample_policy}`, `rfq{title, intro}`, `footer{note}`, `seo{title, description}`.
  - `class SiteConfig(BaseModel)`: `de: LocalizedContent, en: LocalizedContent, review: LocalizedContent, review_language: "tr"|"en", slug_suggestion: str, template: "industrial"|"natural"|"textile", missing: list[str], positioning: "b2b"|"b2c"`.
  - `template_for_sector(sector) -> str` — otomotiv_yan_sanayi→industrial, gida→natural, tekstil→textile, diger→industrial.
  - `fallback_site_config(company, products: list[public_product], positioning, ui_language) -> SiteConfig` — fixed German/English/review sentence templates in `backend/app/seed/data/storefront_fallback.json`, filled with raw data; `lead_time`, `sample_policy`, `incoterms` → `None` + in `missing` unless the producer supplied them in intake (`IntakeIn.lead_time`, `.sample_policy`, `.incoterms`).

- [ ] **Step 1: Write failing tests** — `test_slug_transliteration` (`"Bozkurt Antep Fıstığı"` → `bozkurt-antep-fistigi`), `test_slug_turkish_capitals` (`"İzmir IĞDIR Çağ"` → `izmir-igdir-cag`), `test_unique_slug_suffix`, `test_fallback_marks_missing` (no lead time → `export_info.lead_time` in `missing` and value None in de/en), `test_fallback_has_no_floor` (`assert_no_floor`, and floor value string absent from `model_dump_json()`), `test_template_by_sector`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: storefront schema, TR slugs, fallback config`.

### Task 12: Jobs and `run_ai_step`

**Files:**
- Create: `backend/app/services/agent_steps.py`, `backend/app/routers/jobs.py`
- Test: `backend/tests/test_agent_steps.py`

**Interfaces:**
- Produces:
  - `async create_job(db, company_id, kind: str, steps: list[str]) -> str` — doc `{_id, company_id, kind, status: "running"|"done"|"error", steps: [{key, status: "waiting"|"running"|"done"|"fallback", elapsed_ms}], result: None}`.
  - `async run_ai_step(job_id: str|None, step: str, company: dict, call: Callable[[float], Awaitable[T]], fallback: Callable[[], T], cache_key: str|None=None) -> tuple[T, bool]` — marks step running; `timeout = demo_llm_timeout_seconds if company.get("is_demo_company") else llm_timeout_seconds`; wraps `call(timeout)` in `asyncio.wait_for(..., timeout)`; on `LLMError`/`TimeoutError`/`ValidationError` → (Phase 5 inserts demo-cache lookup here) → `fallback()`; marks `done` or `fallback`; returns `(value, used_fallback)`. Never raises for LLM failures.
  - `async finish_job(job_id, result: dict)`, `spawn(coro)` — `asyncio.create_task` holder set so tasks aren't GC'd.
  - `GET /api/jobs/{id}` (owned) → job doc.

- [ ] **Step 1: Write failing tests** — `test_step_done_on_success`, `test_step_fallback_on_llm_error` (fake_llm raises `LLMProviderError`), `test_step_fallback_on_timeout` (call sleeps > timeout; set timeout via monkeypatched settings to 0.05), `test_job_not_visible_to_other_company`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: agent jobs with timeout and fallback steps`.

### Task 13: Storefront generation, editing, section regeneration

**Files:**
- Create: `backend/app/prompts/{sf_product_analysis,sf_market_adaptation,sf_content,sf_regen_section}.md`, `backend/app/routers/storefronts.py`
- Modify: `backend/app/services/storefront_service.py`
- Test: `backend/tests/test_storefront_generation.py`

**Interfaces:**
- Consumes: `run_ai_step`, `generate_json`, `fallback_site_config`, `public_product`.
- Produces:
  - `IntakeIn {text: str, positioning: "b2b"|"b2c" = "b2b", lead_time: str|None, sample_policy: str|None, incoterms: list[str] = []}`.
  - `POST /api/storefronts/generate` → `{job_id}`; job steps `["analysis","adaptation","content","theme"]`. Analysis: `ProductAnalysis {attributes[], selling_points[], quality_signals[], buyer_types[]}` with product photos as image input. Adaptation: `MarketAdaptation {key_messages_de[], avoid[]}`. Content: `SiteConfig`. Theme: deterministic `template_for_sector`. Result: upserts `storefronts` doc (one per company+country, status `draft`, slug `unique_slug(site_config.slug_suggestion or slugify_tr(company.name))`).
  - Prompt context contains only `company`, `public_product` list, intake, `ui_language` (from user). Prompts state: German B2B tone, no superlatives ("weltbeste" etc.), use only given facts, set unknown fields to null and list them in `missing`.
  - After content returns, code enforces: `missing` ⊇ every None field (recomputed by walking the model), so the editor yellow-flags are never AI-dependent.
  - `GET /api/storefronts/mine`, `PUT /api/storefronts/mine {site_config, slug, template}` (slug re-validated via `slugify_tr` + uniqueness; 409 `slug_taken`).
  - `POST /api/storefronts/mine/regenerate-section {section: str, lang: "de"|"en", instruction: str|None}` → updated section (sync call through `run_ai_step(None, ...)`; on failure returns the unchanged section + `fallback: true`).

- [ ] **Step 1: Write failing tests** — `test_generate_happy_path` (FakeLLM returns fixture JSONs per prompt name → job done, storefront draft, 4 steps done), `test_generate_falls_back_when_llm_fails` (no key → job done, steps `fallback`, storefront exists with fallback config), `test_generation_prompts_exclude_floor` (all `fake_llm.prompts` lack the floor value and the word `price_floor`), `test_ui_language_in_prompts` (user en → every prompt contains `ui_language: en`), `test_missing_recomputed` (FakeLLM returns null lead_time but empty `missing` → stored `missing` contains it), `test_regenerate_section_passes_instruction`, `test_slug_conflict_409`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: multi-step storefront generation and editing`.

### Task 14: Publish, public storefront API, legal data, RFQ

**Files:**
- Create: `backend/app/routers/public.py`
- Modify: `backend/app/routers/storefronts.py`
- Test: `backend/tests/test_publish_rfq.py`

**Interfaces:**
- Produces:
  - `POST /api/storefronts/mine/publish` (status published, `published_at`), `POST /api/storefronts/mine/unpublish` (`unpublished_at`). `GET /api/storefronts/mine/qr.png` → PNG of `{FRONTEND_ORIGIN}/s/{slug}` via `qrcode`.
  - `GET /api/storefronts/mine/impressum-checklist` → `[{field, present: bool}]` for name, address(city), phone, email, owner/representative name, register info (always flagged as to-check).
  - `GET /api/public/storefronts/{slug}` (no auth; 404 unless published) → `{site_config: {de, en, template}, company: {name, city, logo_url, contact, founded_year}, legal: {impressum fields}}` — explicitly excludes `review`, `missing`, owner ids, floors.
  - `POST /api/public/storefronts/{slug}/rfq {company_name, contact_name, email, country, products: list[str], quantity, message, gdpr_consent: true, website_hp: ""}` — honeypot `website_hp` non-empty → 204 and nothing stored; 5/hour per IP+slug; creates lead (`source: "rfq"`, `status: "new"`, `is_hot: true`, `score` via Task 25's `lead_score` — until then store 0 and Task 25 back-fills via function call) and notification `type: "rfq"`.

- [ ] **Step 1: Write failing tests** — `test_public_404_until_published`, `test_unpublish_hides`, `test_public_payload_has_no_private_fields` (`assert_no_floor`; no `review`, `missing`, `owner_id`), `test_rfq_creates_lead_and_notification`, `test_rfq_requires_gdpr`, `test_rfq_honeypot_drops`, `test_rfq_rate_limited`, `test_rfq_on_unpublished_404`, `test_qr_png`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: publish storefront, public API, RFQ intake`.

### Task 15: `AgentSteps`, intake, editor, publish success (frontend)

**Files:**
- Create: `src/components/AgentSteps.tsx`, `src/hooks/useJob.ts`, `src/pages/storefront/{Intake,Editor,SectionEditor,PublishSuccess}.tsx`, `src/hooks/useSpeech.ts`

**Interfaces:**
- Produces:
  - `useJob(jobId|null): {job, done: boolean}` — polls every 700 ms until `status !== "running"`.
  - `<AgentSteps steps={[{key, status, elapsed_ms}]} labels={(key) => string} explain={(key) => string} />` — states bekliyor/çalışıyor/tamamlandı/yedek kullanıldı (`agent.state.*`), live elapsed timer while running. Fallback state looks calm (grey "yedek" text, no red); the presenter dot is Task 32.
  - `useSpeech(lang="tr-TR"): {supported, listening, start(), stop(), transcript}` — Web Speech API; mic button hidden when `!supported`.
  - Editor: left pane tabs DE / EN / Review (review read-only, labelled in UI language); fields whose dotted path is in `missing` get yellow background + `storefront.must_enter` ("Bu bilgiyi siz girmelisiniz"); clearing the flag when filled. "Bu bölümü yeniden yaz" with optional instruction chips "daha kısa"/"daha teknik". Template selector. Photo reorder/remove via `PhotoPicker`. Right pane: `<StorefrontView config lang template device="desktop"|"mobile" />` (Task 16) inside a 390 px phone frame in mobile mode. Legal note: "Bu metinler şablondur; yayın öncesi bir hukukçuya kontrol ettiriniz."
  - PublishSuccess: URL, QR image, "Paylaş" (`navigator.share` → fallback `navigator.clipboard.writeText` + toast).
- [ ] **Step 1:** Implement (Task 16's `StorefrontView` can start as a stub then be completed). **Step 2:** `npm run build`; i18n parity test.
- [ ] **Step 3:** Browser: Bozkurt → Vitrinimi oluştur → steps animate → editor shows yellow missing fields → edit headline → regenerate "why us" with "daha kısa" → switch template → publish → QR + share. Repeat with LLM key removed: steps show yedek, editor still populated.
- [ ] **Step 4:** Commit `feat: storefront intake, agent steps, editor, publish flow`.

### Task 16: Public storefront, legal pages, RFQ form (frontend)

**Files:**
- Create: `src/storefront/{StorefrontView,PublicStorefront,LegalPages,RfqForm,themes}.tsx`, `src/storefront/strings.ts` (buyer-facing de/en UI strings — not in producer i18n, since storefront chrome is German/English only)
- Modify: `src/App.tsx` — producer routes via `React.lazy`; `/s/:slug`, `/s/:slug/impressum`, `/s/:slug/datenschutz` in a separate lazy chunk that doesn't import i18n producer bundles.

**Interfaces:**
- Produces: `StorefrontView({config: LocalizedContent, template, lang, company, onRfq?})` — one component; `themes.ts` maps template → Tailwind class set (industrial: navy/steel; natural: cream `#FAF5EA` + green; textile: light, large photo grid). Images `loading="lazy"` `decoding="async"` with width/height.
- PublicStorefront: DE/EN switch (default de), sets `document.documentElement.lang`, `document.title`, meta description, `og:title/og:description/og:image`, favicon from `logo_url`. Footer links Impressum + Datenschutzerklärung (template text in `strings.ts`, filled with company data; Datenschutz covers RFQ form data: purpose, legal basis Art. 6(1)(b)/(f) GDPR wording kept generic, contact).
- RfqForm fields per spec + hidden honeypot `website_hp` (`tabIndex=-1`, `aria-hidden`, off-screen) + required GDPR checkbox.
- [ ] **Step 1:** Implement. **Step 2:** `npm run build`; confirm the `/s/` chunk does not include producer pages (inspect `dist/assets` chunk names / sizes).
- [ ] **Step 3:** Logged-out browser: `/s/bozkurt-pistazien` (after setting that slug in editor) at 375 px and 1280 px, DE and EN; Impressum/Datenschutz reachable from footer; submit RFQ → dashboard shows notification and hot lead.
- [ ] **Step 4:** Commit `feat: public storefront, legal pages, RFQ form`.

### Task 17: Phase 2 acceptance

- [ ] Run pytest; walk every Phase 2 criterion including the timed Gaziantep generation (record seconds) and the no-key fallback; record in `docs/ACCEPTANCE.md`. Commit `docs: phase 2 acceptance`.

---

# Phase 3 — Mevzuat Bekçisi

### Task 18: Deterministic rule/incentive matching and readiness score

**Files:**
- Create: `backend/app/services/scoring.py` (readiness part), `backend/app/services/regai_service.py` (pure part)
- Test: `backend/tests/test_regai_matching.py`, `backend/tests/test_scoring.py`

**Interfaces:**
- Produces:
  - `match_rules(rules: list[dict], *, country: str, hs6: str, sector: str, channel: "b2b"|"b2c", structural_use: bool) -> list[dict]` — every present constraint must hold: `country` (absent = any), `hs_prefixes` (empty = any; else any prefix with `hs6.startswith(p)`), `sectors` (empty = any), `channel` (None = both), `structural_use` (None = any; True requires flag). Sorted by `id` numerically.
  - `filter_incentives(incentives, sector) -> list[dict]` — empty `sectors` = all.
  - `LEVEL_WEIGHTS = {"zorunlu": 3, "koşullu": 2, "önerilen": 1}`; `readiness_score(items: list[{level, applies: bool, done: bool}]) -> int` = round(100 × Σw(done∧applies) / Σw(applies)); 0 when nothing applies.
- Seed-case expectations (spec §6 Phase 3), loaded from the real seed JSON:

```python
def test_pistachio_b2b(): ids(match(hs6="2008.19", sector="gida", channel="b2b")) ⊇ {"R1","R3","R7","R8"}; R9, R10 ∉
def test_pistachio_b2c(): ... ⊇ {"R1","R3","R7","R8","R9","R10"}
def test_towels(): hs6="6302.60", sector="tekstil" ⊇ {"R1","R2","R4","R5","R6"}
def test_bolts(): hs6="7318.15", sector="otomotiv_yan_sanayi" ⊇ {"R1","R2","R12","R13"}; R15 ∉ ; with structural_use → R15 ∈
def test_unknown_country_only_turkish_side(): country="US" → only R1  (→ UI shows no-match block, see Task 20)
def test_readiness_weights(): [zorunlu done, koşullu not, önerilen done] → round(100*4/6) == 67
```

- [ ] **Steps 1–4** (write tests, fail, implement, pass). **Step 5:** Commit `feat: deterministic KB matching and readiness score`.

### Task 19: GTİP suggestion and confirmation

**Files:**
- Create: `backend/app/prompts/gtip_suggest.md`, `backend/app/routers/compliance.py` (GTİP routes), `backend/app/models/compliance.py`
- Modify: `backend/app/services/regai_service.py`
- Test: `backend/tests/test_gtip.py`

**Interfaces:**
- Produces:
  - `normalize_hs6(code: str) -> str|None` — digits only; need ≥ 6 digits; return `NNNN.NN` from the first 6; else None.
  - `GtipCandidate {code, description, confidence: "yüksek"|"orta"|"düşük", reasoning, in_kb: bool}`; LLM schema `GtipOut {candidates: list[{code, description, confidence, reasoning}] (max 3)}`.
  - `async suggest_gtip(product, company, processing: "roasted"|"raw"|"na"|None, ui_language, job_id) -> list[GtipCandidate]` — via `run_ai_step`; normalize, drop invalid, dedupe, mark `in_kb`. Fallback: `kb_hs_codes` with matching sector; if `processing` given, rank codes whose note says "not roasted" (0802.*) first for raw and 2008.19 first for roasted (rank map in code: `{"roasted": ["2008.19"], "raw": ["0802.51","0802.52"]}`), confidence `orta`, reasoning = `description_{ui_language}`.
  - `POST /api/compliance/gtip {product_id, processing}` → `{job_id}`; result stored in `classifications`. `POST /api/compliance/gtip/confirm {product_id, code}` — code must be one of the stored candidates or in `kb_hs_codes` (normalized); sets `classifications.confirmed_code/at` and `products.hs_code_confirmed`.
  - Prompt includes the KB HS list as reference and an explicit roasted-vs-raw rule of thumb lifted from the KB `note` fields only.

- [ ] **Step 1: Write failing tests** — `test_hs_code_normalization` (`"200819"`, `"2008.19.00"`, `"2008 19"` → `2008.19`; `"20A8"` → None), `test_suggest_marks_in_kb_and_drops_invalid`, `test_fallback_roasted_ranks_200819_first` (no key), `test_confirm_requires_known_code` (random `"9999.99"` not a candidate → 422), `test_gtip_prompt_has_ui_language`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: GTİP suggestion with fallback and confirmation`.

### Task 20: Checklist explanation, incentives, next steps, report and ticks

**Files:**
- Create: `backend/app/prompts/{rules_explain,incentives_explain,next_steps}.md`
- Modify: `backend/app/services/regai_service.py`, `backend/app/routers/compliance.py`
- Test: `backend/tests/test_compliance_report.py`

**Interfaces:**
- Produces:
  - LLM schemas: `RuleExplainOut {items: list[{rule_id, applies: bool, reason, next_step}]}`, `IncentiveExplainOut {items: list[{incentive_id, applies: bool, why}]}`, `NextStepsOut {steps: list[{rule_id, text}]}` (max 3).
  - Guard: `keep_known(items, allowed_ids: set[str], key: str) -> list` drops unknown ids; anything else in the LLM output (e.g. invented titles) is ignored because the checklist is built from KB records joined by id — the LLM only contributes `applies/reason/next_step`.
  - `POST /api/compliance/check {product_id, channel="b2b", structural_use=False}` → `{job_id}`; steps `["rules","incentives","next_steps"]` (GTİP confirmed beforehand, else 409 `gtip_not_confirmed`). Rule fallback: all filtered rules apply, reason = `summary_{lang}`, next_step = `what_to_do_{lang}`. Incentive fallback: all filtered incentives, why = `summary_{lang}`. Next-steps fallback: top 3 unticked applicable items by weight then id, text = `what_to_do_{lang}`.
  - Report doc (`readiness_reports`): `{product_id, country, channel, structural_use, hs6, candidates, checklist: [{rule_id, title_tr, title_en, side, level, source_url, last_verified, verified, applies, reason, next_step, done: false}], incentives: [{incentive_id, name_tr, name_en, provider, source_url, why}], next_steps, score, no_match: bool, ui_language, created_at}`. `no_match = not any(side=="DEST")` for the filtered rules.
  - `PATCH /api/compliance/reports/{id}/items/{rule_id} {done: bool}` → `{score}`. `POST /api/compliance/reports/{id}/next-steps` re-runs next steps for current ticks.
  - `GET /api/compliance/reports/latest?product_id=`.

- [ ] **Step 1: Write failing tests** — `test_invented_rule_id_dropped` (FakeLLM returns R1, R99 and a made-up `{"rule_id":"X1","title":"Fake rule"}` → checklist ids ⊆ filtered KB ids, no "Fake rule" anywhere in report), `test_invented_incentive_dropped`, `test_every_item_has_kb_id_and_source`, `test_towel_incentives_include_I1` (FakeLLM selects I1; fallback also includes I1 since tekstil filter keeps it), `test_tick_updates_score`, `test_no_match_for_unsupported_country`, `test_prompts_carry_ui_language_and_no_floor`, `test_fallback_next_steps_top3_by_weight`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: KB-grounded compliance report with id guard`.

### Task 21: PDF service (readiness report)

**Files:**
- Create: `backend/app/services/pdf_service.py`, `backend/app/pdf_strings.json` (tr/en labels for PDFs; buyer-language de/en for quotes)
- Modify: `backend/app/routers/compliance.py` (`GET /api/compliance/reports/{id}/pdf`)
- Test: `backend/tests/test_pdf.py`

**Interfaces:**
- Produces: `register_fonts()` (once, `NotoSans`/`NotoSans-Bold` from `app/assets/fonts`); `readiness_pdf(report: dict, company_public: dict, lang: "tr"|"en") -> bytes` (Platypus: brand header in `#C8102E`, GTİP + warning, checklist grouped Türkiye tarafı / Hedef pazar with level, source URL, son doğrulama, done tick, incentives, score + formula, next steps, footer string from spec). Saves via storage, sets `pdf_url`.
- [ ] **Step 1: Write failing tests** — `test_readiness_pdf_turkish_glyphs` (extract with `pypdf`; text contains `"Türkiye tarafı"` and `"ğ"`/`"ş"`/`"İ"` intact), `test_readiness_pdf_footer_en` (lang en → English footer), `test_pdf_has_no_floor` (floor value string absent from extracted text).
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: readiness report PDF with bundled Noto Sans`.

### Task 22: Admin knowledge base

**Files:**
- Create: `backend/app/routers/admin_kb.py`, `src/pages/admin/{KbList,KbForm,KbImportExport}.tsx`, `src/components/VerifiedBadge.tsx`
- Test: `backend/tests/test_admin_kb.py`

**Interfaces:**
- Produces: `GET/POST /api/admin/kb/{kind}` (kind ∈ rules|incentives|hs_codes), `PUT /api/admin/kb/{kind}/{id}`, `POST /api/admin/kb/{kind}/{id}/verify` (sets `verified: true`, `verified_by` admin id, `last_verified` now), `GET /api/admin/kb/{kind}/export.csv`, `POST /api/admin/kb/{kind}/import` (CSV, upsert by `id`; list columns `;`-joined inside the cell). Editing a record resets `verified` to false (decision: changed content is no longer verified).
- `<VerifiedBadge verified lastVerified />` — grey "Demo verisi – doğrulanmadı" / "Demo data – not verified"; green "Doğrulandı · {formatDate}" / "Verified · {date}". Used in admin list and on every checklist item.
- No admin endpoint returns products, leads or floors; admin is a normal user for `/api/products` (sees only own company, i.e. none).
- [ ] **Step 1: Write failing tests** — `test_non_admin_403`, `test_verify_sets_fields`, `test_edit_resets_verified`, `test_csv_roundtrip`, `test_admin_cannot_read_other_products` (admin GET `/api/products/{bozkurt_product}` → 404).
- [ ] **Steps 2–4** + browser: edit R7, mark verified, badge switches. **Step 5:** Commit `feat: admin knowledge base with verification`.

### Task 23: Mevzuat Bekçisi frontend

**Files:**
- Create: `src/pages/compliance/{ComplianceStart,GtipStep,ReportPage,ChecklistItem,ScoreBadge,NoMatch}.tsx`

**Interfaces:**
- Consumes: Tasks 19–21 routes, `AgentSteps`, `useJob`, `VerifiedBadge`.
- Produces: start form (product, channel B2B/B2C, `structural_use` checkbox, processing question "kavrulmuş mu, çiğ mi?" shown for gıda); GTİP step shows candidates with confidence label (`compliance.confidence.*`: Yüksek/Orta/Düşük — High/Medium/Low), reasoning, "listemizde mevcut" badge, the fixed warning, link to the Ticaret Bakanlığı tariff page, mandatory radio choice before continue. Label "GTİP (ürününüzün gümrük kodu)" / "HS code (your product's customs code)". Report: two groups, level badges translated, source link, son doğrulama via `VerifiedBadge`, checkbox "Bu bende var / tamamlandı" (optimistic PATCH), score with tooltip showing the formula, incentives with "Neden uygun?", next 3 steps, "PDF indir". NoMatch block text from spec with İhracatçı Birliği, İTO/İSO, Ticaret Müşavirliği.
- [ ] **Step 1:** Implement. **Step 2:** build + parity. **Step 3:** Browser: run the three seed cases (Bozkurt roasted B2B then B2C, Pamukkale towels, Uludağ bolts), tick boxes and watch score, download PDF, in TR and EN. **Step 4:** Commit `feat: compliance checker UI`.

### Task 24: Phase 3 acceptance

- [ ] pytest; walk criteria; record in `docs/ACCEPTANCE.md`; commit `docs: phase 3 acceptance`.

---

# Phase 4 — Alıcı Ajanı

### Task 25: Lead scoring and leads API (RFQ, CSV, manual, demo)

**Files:**
- Modify: `backend/app/services/scoring.py`, `backend/app/routers/public.py` (call `lead_score` on RFQ)
- Create: `backend/app/routers/leads.py`, `backend/app/models/lead.py`
- Test: `backend/tests/test_leads.py`, extend `test_scoring.py`

**Interfaces:**
- Produces:
  - Consumes `tr_fold` from Task 11 (`storefront_service`); move it to `backend/app/core/text.py` if the import feels wrong.
  - `product_keywords(products) -> set[str]` — folded tokens ≥ 3 chars from `name_tr`, `material_or_ingredients`, plus a static de/en synonym map per sector in `backend/app/seed/data/keywords.json` (e.g. gida: pistazien, pistachio; tekstil: handtuch, towel, bademantel, bathrobe; otomotiv_yan_sanayi: schraube, bolt, mutter, nut).
  - `lead_score(lead, products, target_country) -> {total, breakdown: {source, product_match, country, email}}` — source: rfq 40, csv_import 20, manual 15, demo 0 (decision: demo leads score on content only; recorded); product_match = `min(30, 10 × |overlap(tokens(notes+website+message), keywords)|)` (documented in a docstring); country == target → 15; email present → 15.
  - `parse_csv(data: bytes) -> tuple[list[str], list[dict]]` — try `utf-8-sig`, fall back to `cp1254`; `csv.Sniffer` for `,`/`;`.
  - Routes: `GET /api/leads?sort=score|created_at&status=` (RFQ/hot first by default), `GET /api/leads/{id}`, `POST /api/leads {…, source_note (required)}`, `POST /api/leads/import/preview` (multipart → headers + first 5 rows), `POST /api/leads/import {file_id|rows, mapping: {company_name, country, contact_name, email, website, notes}, source_note (required)}`, `PATCH /api/leads/{id} {status}` (status in the spec enum; `do_not_contact` cannot be left by PATCH — decision: once opted out, stays).
- [ ] **Step 1: Write failing tests** — `test_score_components` (each component isolated), `test_product_match_turkish_case` (notes "İÇ FISTIK Pistazien" vs product "İç Antep Fıstığı" → overlap counted), `test_rfq_lead_scored_on_create`, `test_manual_requires_source_note`, `test_csv_import_requires_source_note`, `test_csv_import_bom_cp1254_semicolon` (cp1254 bytes `"Şahin Handels GmbH;DE"` → `Şahin`), `test_leads_ownership` (B cannot list/read/patch A's leads), `test_default_sort_rfq_first`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: deterministic lead scoring and lead sources`.

### Task 26: Outreach drafts, approval gate, send limit

**Files:**
- Create: `backend/app/prompts/{outreach_first_contact,outreach_translate}.md`, `backend/app/services/outreach_service.py`, `backend/app/routers/messages.py`
- Test: `backend/tests/test_outreach.py`, `backend/tests/test_approval_gate.py`

**Interfaces:**
- Produces:
  - `buyer_language(country) -> "de"|"en"` (DE, AT, CH → de).
  - `DraftOut {subject, body}`; `TranslationOut {text}`.
  - `async draft_first_contact(lead, company, products_public, storefront_url, tone: list["formal"|"shorter"|"samples"], ui_language) -> message doc` — RFQ leads pass the RFQ message and the prompt answers it. Fallback: template in `backend/app/seed/data/outreach_fallback.json` (de/en) filled with company facts + opt-out line. Post-checks in code (`enforce_outreach_rules(body, floor: float) -> str`): reject (→ fallback) if body contains a currency amount regex (`\d[\d.,]*\s?(€|EUR|USD|\$|TL)`) or the floor value; truncate to ~150 words at a sentence boundary; append the opt-out line if missing.
  - `body_tr` holds the translation into the producer's UI language (field name kept from spec; plus `translation_language`).
  - Messages carry `kind: "cold"|"rfq_answer"|"reply"` (only `cold` counts toward the daily limit). Creating a draft sets lead status `draft_ready`.
  - Routes: `POST /api/leads/{id}/draft {tone[]}` → message (409 `do_not_contact` if blocked), `PUT /api/messages/{id} {subject, body}` (re-translates), `GET /api/approvals` (messages + quotes in draft), `POST /api/messages/{id}/approve` , `POST /api/messages/{id}/reject {reason}`.
  - **The single place status becomes `sent`:** `async approve_and_send(db, message_id, user) -> dict` — sets `status: "sent"`, `approved_by`, `approved_at`, `delivery_channel: "mailto"` (or provider name if `EMAIL_PROVIDER` set → `get_email_provider().send(...)`); lead status → `sent`. Enforces 20 cold-outreach approvals/day/company (count of messages with `kind: "cold"` approved since UTC midnight) → 429 `daily_limit`. A Mongo-level guard: `assert_sent_has_approval(doc)` called before every update that sets `sent`.
  - `class EmailProvider(Protocol): async def send(self, to, subject, body) -> str`; `get_email_provider() -> EmailProvider|None` (always None in MVP).
- [ ] **Step 1: Write failing tests** — `test_draft_german_for_de_with_translation`, `test_rfq_draft_uses_rfq_message` (prompt contains the RFQ text), `test_draft_rejects_prices_and_floor` (FakeLLM body includes "12,50 €" → stored body is fallback, no amount), `test_draft_word_limit_and_optout`, `test_no_sent_without_approval_fields` (scan: every message with `status == "sent"` in db after all flows has `approved_by` and `approved_at`; and direct `PUT` with `status: "sent"` is ignored/422), `test_daily_limit_20` (21st approval → 429), `test_do_not_contact_blocks_draft`, `test_approvals_ownership`, `test_prompts_exclude_floor`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: human-approved outreach drafts with send gate`.

### Task 27: Reply assistant

**Files:**
- Create: `backend/app/prompts/reply_analyze.md`
- Modify: `backend/app/services/outreach_service.py`, `backend/app/routers/messages.py`
- Test: `backend/tests/test_reply.py`

**Interfaces:**
- Produces: `ReplyAnalysisOut {translation, summary: list[str] (3), intent: "interested"|"asks_price"|"asks_samples"|"not_interested"|"other", terms: {quantity, incoterm, delivery_date, certifications: list[str]}, red_flags: list[str], suggested_reply: {subject, body}, opt_out: bool}`.
- `POST /api/leads/{id}/reply {text}` → stores inbound message, analysis, and a draft outbound (`kind: "reply"`, not counted in cold limit) in the approval queue; lead → `replied`. If `intent == "not_interested"` or `opt_out` → lead `do_not_contact`, no draft created. Fallback: translation = `null` with `fallback: true`, intent `other`, no draft except a polite template acknowledgment draft. Code-level red-flag heuristics run regardless of LLM (`detect_red_flags(text, lead) -> list[str]` keys: `payment_change` (IBAN/"new account"/"neues Konto"), `urgency` ("sofort", "urgent", "immediately"), `domain_mismatch` (email domains in text ≠ lead email domain)), merged with LLM flags.
- [ ] **Step 1: Write failing tests** — `test_reply_german_interested_creates_draft`, `test_not_interested_sets_do_not_contact`, `test_red_flag_heuristics_without_llm`, `test_reply_translation_in_ui_language` (prompt has `ui_language`).
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: reply assistant with intent, terms, red flags`.

### Task 28: Logistics estimator, quotes, quote PDF, sample task

**Files:**
- Create: `backend/app/services/logistics_service.py`, `backend/app/routers/{quotes,logistics}.py`, `backend/app/models/quote.py`
- Modify: `backend/app/services/pdf_service.py` (`quote_pdf`)
- Test: `backend/tests/test_logistics.py`, `backend/tests/test_quotes.py`

**Interfaces:**
- Produces:
  - `logistics_rates` docs: `{key: "packaging_pct", value: 0.08}`, `{key: "ltl_bands", bands: [{max_kg: 500, eur_per_kg}, {max_kg: 3000, …}, {max_kg: 12000, …}]}`, `{key: "ftl", eur_per_truck, truck_capacity_kg: 24000}`, `{key: "courier", eur_per_kg, min_eur}`, each with `label_tr/label_en` "ÖRNEK – …". Values: obviously round placeholders.
  - `estimate(unit_weight_kg: float|None, quantity: float, rates: dict, mode: "auto"|"ltl"|"ftl"|"courier") -> Estimate` where `Estimate {gross_kg, mode, trucks: int|None, freight_eur, lines: list[{label_key, formula, value}], estimated: True}`; raises `NeedsWeight` if weight missing, `ValueError` if quantity ≤ 0. Gross = w × q × (1 + pct). LTL band = first band with `gross ≤ max_kg`; auto picks LTL when gross ≤ top band max, else FTL with `trucks = ceil(gross / capacity)`.
  - `freight_included(incoterm) -> bool` — only CIF, DAP.
  - `GET /api/quotes/suggest?product_id=` → `{unit_price: round(floor × 1.25, 2)}` (owner only; the floor itself is not returned here).
  - `POST /api/quotes {lead_id, product_id, quantity, unit_price, currency: EUR|USD, incoterm: EXW|FCA|FOB|CIF|DAP, payment_terms: cash_advance|30_70|lc|cad, valid_until, unit_weight_kg?}` — `unit_price < floor` → 422 `below_floor` (message key only, no number); supplying `unit_weight_kg` saves it to the product. Stores `logistics_estimate` and total (freight added only if `freight_included`). Status `draft` → approval queue.
  - `POST /api/quotes/{id}/approve` → same gate pattern as messages (`approved_by/at`, status `sent`, lead → `quoted`); `GET /api/quotes/{id}/pdf` — buyer PDF in `buyer_language(lead.country)`; `?preview=1` renders in the producer's UI language. `quote_pdf(quote_public: dict, company_public, product_public, lang) -> bytes` — receives no floor.
  - `GET/PUT /api/admin/logistics-rates` (admin).
  - `POST /api/leads/{id}/sample-task` → `tasks` doc `{type: "numune_gonderimi", checklist: [proforma, labelling, courier_booking], courier_estimate: estimate(..., mode="courier")}`.
- [ ] **Step 1: Write failing tests** — `test_gross_weight`, `test_ftl_trucks_ceil` (24001 kg → 2 trucks), `test_ltl_band_edges` (exactly 500 kg → first band), `test_courier_min_charge`, `test_freight_only_cif_dap` (EXW/FCA/FOB excluded), `test_logistics_edges` (quantity 0 → 422; missing weight → 422 `needs_weight`), `test_quote_below_floor_refused_without_number` (response text doesn't contain floor), `test_quote_pdf_german_no_floor` (pypdf text has "Angebot" / German labels, no floor value), `test_quote_preview_ui_language`, `test_quote_not_sent_without_approval`, `test_rates_admin_only`, `test_sample_task_created`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: logistics estimator, quote builder, quote PDF`.

### Task 29: Buyer-agent frontend

**Files:**
- Create: `src/pages/leads/{LeadsTable,LeadDetail,LeadForm,CsvImport,ScoreBreakdown,DemoBadge}.tsx`, `src/pages/leads/{OutreachDraft,ReplyAssistant}.tsx`, `src/pages/approvals/ApprovalQueue.tsx`, `src/pages/quotes/QuoteBuilder.tsx`, `src/pages/pipeline/Pipeline.tsx`, `src/pages/admin/LogisticsRates.tsx`, `src/data/incoterms.ts`

**Interfaces:**
- Consumes: Tasks 25–28 routes.
- Produces:
  - `<DemoBadge />` "DEMO – kurgusal firma" (also in EN `demo` namespace: "DEMO – fictional company") rendered wherever a lead with `is_demo` appears (table, detail, pipeline card, approval item, quote builder header).
  - Leads table: sortable columns, "Sıcak lead" badge for RFQ, score with hover/focus breakdown. CSV import: upload → column mapping selects → `source_note` with the GDPR explanation text.
  - OutreachDraft: editable DE/EN text left, read-only translation right (refreshes after save), tone buttons "Daha resmi" / "Daha kısa" / "Numune teklifini vurgula".
  - ApprovalQueue: Onayla ve Gönder / Düzenle / Reddet (reason). On approve: build `mailto:` URL (`encodeURIComponent` subject/body); if URL > 1800 chars, copy to clipboard instead; toast "Mail uygulamasına aktarıldı" / "Handed to your mail app". For quotes, mailto cannot attach files: the mail body gets a short cover note and the UI downloads the buyer PDF at the same moment with a hint to attach it (record as decision).
  - QuoteBuilder: fields per spec; Incoterm one-liners from `incoterms.ts` keys; payment-term dropdown labels from spec; inline refusal for below-floor; asks for unit weight when `needs_weight`; logistics panel with line-by-line formula and "tahmini" label; PDF preview link; "Numune gönderimi" button.
  - Pipeline: kanban columns per status; counters from `GET /api/pipeline/stats` (`{leads, messages_sent, replies, quotes_sent, won}` — add this tiny route to `leads.py`, real counts).
- [ ] **Step 1:** Implement. **Step 2:** build + parity. **Step 3:** Browser: RFQ hot lead → İlk teması hazırla → German + translation → approve (mailto) → paste a German reply → intent + terms + draft in queue → quote DAP with estimate → approve → pipeline counters move. Check demo badges on every screen. Repeat key screens in EN. **Step 4:** Commit `feat: buyer agent UI`.

### Task 30: Phase 4 acceptance

- [ ] pytest; walk criteria; record; commit `docs: phase 4 acceptance`.

---

# Phase 5 — Demo mode, reliability, polish

### Task 31: Demo reset, LLM ping, demo cache

**Files:**
- Create: `backend/app/services/demo_service.py`, `backend/app/routers/demo.py`
- Modify: `backend/app/services/agent_steps.py` (cache lookup/write), every `run_ai_step` caller passes `cache_key`
- Test: `backend/tests/test_demo.py`

**Interfaces:**
- Produces:
  - `cache_key = f"{step}:{ui_language}:{discriminator}"` (e.g. product id + processing). In `run_ai_step`: on success for a demo company, upsert `demo_cache {company_id, step: cache_key, output, created_at}`; on failure, if a cache entry exists use it and mark step status `fallback` with `source: "cache"` (else deterministic fallback, `source: "template"`). Job doc exposes `steps[].source` for the presenter dot.
  - `async reset_demo_company(db, key: "gaziantep"|"denizli"|"bursa") -> {elapsed_ms}` — deletes storefronts, classifications, readiness_reports, messages, quotes, tasks, notifications, non-demo leads for that company; restores company/products from seed JSON (resets `hs_code_confirmed`); restores the 6 demo leads to `new`; keeps `demo_cache`; fires `spawn(generate_text("admin_ping", ...))` as warm-up without awaiting.
  - `POST /api/demo/reset/{key}` (admin) .
- [ ] **Step 1: Write failing tests** — `test_reset_clean_state_under_3s`, `test_reset_twice_idempotent`, `test_cache_used_when_llm_fails` (run generation with FakeLLM success → cache filled; then no key → result equals cached output, step `source == "cache"`), `test_cache_key_includes_language`, `test_demo_reset_admin_only`.
- [ ] **Steps 2–4.** **Step 5:** Commit `feat: demo reset and cached fallback`.

### Task 32: `/demo` page and Demo guide panel

**Files:**
- Create: `src/pages/demo/DemoPage.tsx`, `src/components/DemoGuide.tsx`, `src/demo/script.ts`
- Modify: `src/components/AgentSteps.tsx` (presenter dot)

**Interfaces:**
- Produces: `/demo` (admin route, not linked in nav) with three reset buttons and a link to log in as each demo user. `DemoGuide` toggled with `Ctrl+Shift+D` (global keydown listener, `preventDefault`), shows the 5 script steps from spec Phase 5 with times, current step (manual next/prev), stopwatch (start/pause/reset), and a small dot listing steps that used cache/template in the current job. The dot in `AgentSteps` renders only while DemoGuide is open (state in a tiny context), so the jury never sees it.
- [ ] **Step 1:** Implement. **Step 2:** build + parity. **Step 3:** Browser: reset Gaziantep < 3 s, open guide, run script once. **Step 4:** Commit `feat: demo page and presenter guide`.

### Task 33: Impact panel and admin stats

**Files:**
- Create: `src/pages/dashboard/ImpactPanel.tsx`, `src/pages/admin/AdminStats.tsx`
- Modify: `backend/app/routers/dashboard.py`, `backend/app/routers/admin.py`
- Test: `backend/tests/test_impact.py`

**Interfaces:**
- Produces: `GET /api/dashboard/impact` → `{signup_at, storefront_published_at, first_report_at, first_approved_outreach_at, durations_s: {to_storefront, to_report, to_outreach}}` (null when not reached; from real timestamps). `GET /api/admin/stats` → `{companies, storefronts_published, reports, approved_messages, rfqs}` counts only.
- [ ] **Step 1: Write failing tests** — `test_impact_null_until_events`, `test_impact_durations_from_timestamps`, `test_admin_stats_counts_only` (no company names, `assert_no_floor`).
- [ ] **Steps 2–4** + UI. **Step 5:** Commit `feat: honest impact panel and admin stats`.

### Task 34: Account deletion, data export, security sweep

**Files:**
- Create: `backend/app/routers/account.py`, `src/pages/account/AccountPage.tsx`
- Test: `backend/tests/test_account.py`, extend `backend/tests/test_ownership.py`

**Interfaces:**
- Produces: `GET /api/account/export` → JSON attachment of user (no `password_hash`), company, products (with own floor), markets, storefront, classifications, reports, leads, messages, quotes, tasks, notifications. `DELETE /api/account {confirm: "SİL"|"DELETE", password}` → removes all those docs + uploaded files via `Storage.delete` + the user; clears cookie.
- Ownership sweep test: parametrized over every company-scoped route (list them by introspecting `app.routes` for paths with `{id}` under company routers, so new routes can't be forgotten) — user B gets 404 on A's ids, and no response body contains `price_floor`.
- [ ] **Step 1: Write failing tests** — `test_export_excludes_password_hash`, `test_delete_requires_confirmation`, `test_delete_removes_everything_and_files`, `test_ownership_all_routes`, `test_cors_only_frontend_origin` (preflight from `http://evil.test` gets no `access-control-allow-origin`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement; also grep `frontend/dist` after build for `API_KEY`/`sk-` → none.
- [ ] **Step 4:** PASS. **Step 5:** Commit `feat: KVKK export/delete and security checks`.

### Task 35: Polish pass, final verification, docs

**Files:**
- Modify: frontend pages as needed (empty states with a next-action button, `Skeleton` loaders, focus rings, labels), `docs/RUNNING.md`, `docs/ACCEPTANCE.md`, `docs/DECISIONS.md`

- [ ] **Step 1:** Empty states + skeletons on dashboard, leads, approvals, pipeline, compliance, admin lists.
- [ ] **Step 2:** Accessibility: every input has a `<label>`; visible focus ring; keyboard-only run of register → onboarding → generate → publish. Check `#C8102E` on white for text ≥ 4.5:1 (it is ≈ 5.9:1) and navy text.
- [ ] **Step 3:** Layout at 1280×720, 1920×1080, 375×812 on every producer screen and the storefront; fix overflow.
- [ ] **Step 4:** English walk-through of every producer screen; list any Turkish leftovers (other than user input) in `docs/ACCEPTANCE.md` and fix them.
- [ ] **Step 5:** Lighthouse mobile on `/s/bozkurt-pistazien` (production build served by `vite preview`, via the chrome-devtools Lighthouse tool or `npx lighthouse`); record the score, or record "not measured" with the reason.
- [ ] **Step 6:** Full demo script twice in a row after `/demo` reset, timed (≤ 3.5 min each); then remove the LLM key and run once more on cache. Record times.
- [ ] **Step 7:** Write `docs/RUNNING.md` (PowerShell: venv, `pip install`, `.env` from `.env.example`, Mongo options, `python -m app.seed`, `uvicorn app.main:app --reload --port 8000`, `npm install; npm run dev`, `pytest`, demo reset). Finalize `docs/ACCEPTANCE.md` (PASS/FAIL + evidence per criterion, all phases) and `docs/DECISIONS.md`.
- [ ] **Step 8:** Full pytest run → green; commit `docs: final acceptance, running guide`. Final message per spec §0.7.
