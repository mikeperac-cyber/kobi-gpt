# M2 Photo-First Products Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A producer adds product photos first, taps "Fotoğraftan doldur", and gets an AI draft of the product name, description, material and unit to check and edit. The demo companies can show real product photos instead of the coloured placeholders.

**Architecture:** One synchronous endpoint `POST /api/products/draft` runs a single image-capable LLM call through `agent_steps.run_ai_step` (timeout, demo cache, fallback, `agent_runs` logging all come for free) and returns a draft or an empty fallback. `ProductForm` moves photos to the top and fills only blank fields from the draft. Seed and demo reset read owner-supplied photo files when present and fall back to placeholders.

**Tech Stack:** FastAPI + Motor (mongomock), pytest with the `fake_llm` fixture; React 19 + Tailwind; node `--experimental-strip-types` `.check.ts` files run from `backend/tests/test_frontend_checks.py`.

**Spec:** `docs/superpowers/plans/2026-11-23-contest-roadmap.md` (M2) and `AGENTS.md` §3 (principles 2, 6, 7: no invented facts, honest labels, visible progress + fallback).

## Global Constraints

- The draft is a suggestion: UI labels it "Yapay zekâ önerisi — lütfen kontrol edin" / "AI suggestion — please check", and it never overwrites text the producer typed.
- The model never proposes MOQ, weight, price, certifications, origin claims or brand names; the prompt says so and the schema has no field for numbers.
- `price_floor` never enters the prompt (`render_prompt` already refuses it).
- Producer strings in `tr.json` and `en.json`. Error shape `{"code", "message_key"}`. No new dependencies.
- Backend: `cd backend && .venv/Scripts/python.exe -m pytest -q`. Frontend: `cd frontend && npm run build && npm run lint` (no new warnings in touched files).
- One commit per task, no attribution lines.

## Review Focus

1. **Producer typed a name, then taps "Fotoğraftan doldur"** — typed text stays; only blank fields fill. (Check file in Task 2.)
2. **Photo shows nothing recognisable (blurry, a wall)** — the model returns nulls; the UI says it found nothing and the form is unchanged. (Check file + browser in Task 2.)
3. **Model returns a unit outside `kg|adet|metre|koli` or malformed JSON** — schema rejects, `generate_json` retries, then the empty fallback; the endpoint still answers 200. (Test in Task 1.)
4. **Six photos selected** — at most the first 3 go to the model (cost/latency bound like `storefront_service._photos`). (Test in Task 1.)
5. **Demo reset when owner photo files exist** — reset uses the real photos too, not placeholders. (Test in Task 3.)

---

### Task 1: Product draft endpoint

**Files:**
- Create: `backend/app/prompts/product_draft.md`
- Create: `backend/app/models/product_draft.py`
- Modify: `backend/app/routers/products.py`
- Modify: `backend/tests/conftest.py` (`FakeLLM.complete` also appends `images` to `self.images: list[list[bytes]]`)
- Test: `backend/tests/test_product_draft.py`

**Interfaces:**
- Produces model `ProductDraftOut(BaseModel)`: `name_tr: str | None = Field(None, max_length=200)`, `description_tr: str | None = Field(None, max_length=1500)`, `material_or_ingredients: str | None = Field(None, max_length=500)`, `unit: Literal["kg", "adet", "metre", "koli"] | None = None`.
- Produces model `DraftIn(BaseModel)`: `photos: list[str] = Field(min_length=1, max_length=6)`.
- Produces `POST /api/products/draft` (declare **before** `/{pid}` routes) → 200 `{"draft": ProductDraftOut-as-dict, "source": "llm" | "cache" | "template"}`. Steps: `require_owned(db, body.photos, company["owner_id"])` (existing 422 `bad_photo`); read bytes of the first 3 photos with `get_storage().read`; none readable → 422 `bad_photo`; `run_ai_step(None, "product_draft", company, call, fallback, key, ProductDraftOut.model_validate)` with `call = generate_json("product_draft", {"ui_language", "company": {"name", "sector", "city"}}, ProductDraftOut, run_type="product_draft", company_id=cid, images=..., timeout=t)`, `fallback = ProductDraftOut()` (all None), `key = agent_steps.cache_key("product_draft", ui, *body.photos[:3])`. `source` mirrors `regenerate_section`: `"llm"` on success, `"cache"` when a demo-cache hit replaced a failure, else `"template"`.
- Prompt `product_draft.md` (same shape as `sf_product_analysis.md`): role (export assistant for a Turkish SME), task (from the attached photos write a short Turkish product name, a 1–3 sentence Turkish description of what is visible, the visible material/ingredients, and the most likely sales unit), rules: describe only what is visible; if unsure use `null`; no numbers, prices, MOQ, weights, certifications, origin or quality claims, brand names; "do not invent facts that are not in the provided context"; exact JSON schema; `$ui_language`, `$company` placeholders.

- [ ] **Step 1: Failing tests** in `test_product_draft.py` (use `producer` + `fake_llm`; the producer's onboarding photo `/uploads/products/a.webp` is registered but its file does not exist — write real bytes to it under `storage_service.set_root(tmp_path)`; add 3 more owned photos via `db.uploads.insert_one` + files for test 4):
  - `test_draft_from_photo`: fake responds `{"name_tr": "Kavrulmuş Antep Fıstığı", "description_tr": "Kabuklu, kavrulmuş fıstık.", "material_or_ingredients": "Antep fıstığı", "unit": "kg"}` → 200, `source == "llm"`, draft equals that dict; one `agent_runs` doc with `type == "product_draft"`; the prompt starts with `# product_draft` and contains no `price_floor`.
  - `test_draft_bad_unit_falls_back` (Review Focus 3): fake always returns `{"unit": "ton"}` → 200, `source == "template"`, all draft fields `None`.
  - `test_draft_llm_down_falls_back`: fake raises `LLMProviderError` three times → 200, `source == "template"`.
  - `test_draft_sends_at_most_three_photos` (Review Focus 4): 4 owned photos → `len(fake_llm.images[-1]) == 3`.
  - `test_draft_rejects_foreign_photo`: photo URL registered to another user → 422 `bad_photo`; `photos: []` → 422.
  - `test_draft_demo_cache`: company flagged `is_demo_company`; first call succeeds; second call with the fake raising → `source == "cache"` and the same draft.
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest -q tests/test_product_draft.py` → FAIL (404).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** full suite → pass.
- [ ] **Step 5: Commit** — `feat: AI product draft from photos`

---

### Task 2: Photo-first product form

**Files:**
- Create: `frontend/src/components/productDraft.ts`, `frontend/src/components/productDraft.check.ts`
- Modify: `frontend/src/components/ProductForm.tsx`, `frontend/src/i18n/tr.json`, `en.json`
- Test: `backend/tests/test_frontend_checks.py` (`test_product_draft_apply_cases`)

**Interfaces:**
- Consumes: Task 1 endpoint.
- Produces `applyDraft(form: ProductDraft, d: Draft): { next: ProductDraft; filled: string[] }` in `productDraft.ts` with `type Draft = { name_tr: string | null; description_tr: string | null; material_or_ingredients: string | null; unit: string | null }`. Text fields fill only when the form value is blank after `trim()`; `unit` fills only when `form.name_tr` was blank (a fresh product, since `unit` always has a default) and the value is in `UNITS`. `filled` lists the keys that changed.
- `productDraft.check.ts` cases: blank form + full draft → all 4 filled; form with `name_tr: 'Benim adım'` → name kept, `unit` kept, other blanks filled (Review Focus 1); all-null draft → `filled == []`, form unchanged (Review Focus 2); `unit: 'ton'` → unit not filled.
- `ProductForm`: photos section moves to the top. Under it, when `v.photos.length > 0`, a button `t('products.fillFromPhoto')` → `POST /api/products/draft {photos: v.photos}`; while running, the button shows `t('products.fillRunning')` and is disabled (`aria-busy`). Result: `filled.length` → banner `t('products.fillDone')` + a small badge `t('products.aiBadge')` beside each filled field's label until the producer edits it; `source === 'template'` or `filled == []` → `t('products.fillNothing')`; request error → `t(messageKey)`.
- i18n (`products.*`): `fillFromPhoto` "Fotoğraftan doldur" / "Fill in from photo"; `fillRunning` "Fotoğraf inceleniyor…" / "Looking at the photo…"; `fillDone` "Yapay zekâ önerisi — lütfen kontrol edin ve düzeltin." / "AI suggestion — please check and correct it."; `fillNothing` "Fotoğraftan bilgi çıkarılamadı. Alanları kendiniz doldurun." / "Nothing could be read from the photo. Please fill in the fields yourself."; `aiBadge` "YZ önerisi" / "AI suggestion".

- [ ] **Step 1: Write** `productDraft.check.ts` and the pytest wrapper; **Step 2: Run** → FAIL (module missing).
- [ ] **Step 3: Implement** `applyDraft`, the form changes and i18n.
- [ ] **Step 4: Verify** — check passes; build/lint clean; browser pane (no LLM key, so fallback): Products → new product → add a photo → "Fotoğraftan doldur" → running state, then `fillNothing`, form unchanged. Onboarding wizard still validates "photo required".
- [ ] **Step 5: Commit** — `feat: photo-first product form with AI fill`

---

### Task 3: Real photos for the demo companies

**Files:**
- Modify: `backend/app/seed/images.py`, `backend/app/seed/__init__.py`, `backend/app/services/demo_service.py`
- Create: `backend/app/seed/photos/README.md`
- Test: `backend/tests/test_seed.py`

**Interfaces:**
- Produces `PHOTOS_DIR = Path(__file__).parent / "photos"` and `demo_photo(spec_key: str, label: str, color: str) -> bytes` in `images.py`: if `PHOTOS_DIR/<spec_key>/<slugify_tr(label)>.{jpg,jpeg,png,webp}` exists, return `validate_and_process_image(file bytes)` (same pipeline as uploads); otherwise `make_placeholder(label, color)`. Import `slugify_tr` from `app.services.storefront_service` and `validate_and_process_image` from `app.services.storage_service` (neither imports the seed package, so no cycle). Seed and demo reset call `demo_photo(spec["key"], label, spec["color"])` where they call `make_placeholder` today.
- `photos/README.md` (Turkish + English): file naming rule with the expected file names for all 6 demo products' `photo_labels` (e.g. `bozkurt/kabuklu-antep-fistigi.jpg`), and the rule: **only photos you took yourself or hold the rights to; no images from the web**. Photos are committed with the repo.

- [ ] **Step 1: Failing tests** in `test_seed.py`: monkeypatch `images.PHOTOS_DIR` to `tmp_path`, write a 400×300 JPEG (PIL) at `tmp_path/bozkurt/<slugify_tr(first label)>.jpg`; after `seed(db)` the first Bozkurt product's first photo file differs from `make_placeholder(label, color)` and decodes to 400×300 (resized pipeline keeps it). `test_reset_uses_owner_photos` (Review Focus 5): delete the product, `reset_demo_company(db, "gaziantep")` → regenerated photo is the owner photo too. Without the file → placeholder (existing tests already cover).
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest -q tests/test_seed.py tests/test_demo.py` → FAIL.
- [ ] **Step 3: Implement** + README.
- [ ] **Step 4: Run** full suite → pass.
- [ ] **Step 5: Commit** — `feat: demo seed uses owner-supplied product photos when present`

---

## Final Check

- Backend suite and frontend build/lint green.
- Browser pane rehearsal: new product with a photo → "Fotoğraftan doldur" → fallback message (no key). Report that the real LLM draft quality and the actual demo photos depend on the owner's API key and photo files.
