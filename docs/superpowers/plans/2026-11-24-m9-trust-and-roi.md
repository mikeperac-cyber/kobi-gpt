# M9 Trust & ROI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Buyers can tell checked facts from claims ("Dokumente geprüft" vs "Herstellerangabe"), and producers record what each won deal was worth so the app can show the export revenue it helped win.

**Architecture:** Producers upload private documents (tax plate, certificates) to a non-public `documents/` storage prefix and submit them as `verifications`; an admin reviews them in a new admin page. A pure-ish `verification_service.public_trust()` turns verified, unexpired records into a small buyer-facing summary added to the public storefront payload. Marking a lead "won" now requires a deal value and currency; a new `/api/dashboard/roi` sums them per currency (no conversion) for a dashboard panel labelled as self-reported.

**Tech Stack:** FastAPI + Motor (mongomock in tests), pytest; React 19 + Tailwind; existing `storage_service`, `upload_registry`, `require_admin`, `owned`, `tr_fold`, `tr_today`, `PublicUploads`.

**Spec:** `docs/superpowers/plans/2026-11-23-contest-roadmap.md` (M9 row), `docs/monetization-paper.md` (§3 add-ons, §7, §8 trust), `AGENTS.md` §3 (principles 3 source + date, 6 honest numbers).

## Global Constraints

- Buyer-facing wording claims only what was done: documents were **checked**, never "quality certified". German: "Dokumente geprüft am {date}"; English: "Documents checked on {date}". Unverified certificates: "Herstellerangabe" / "Self-declared by the manufacturer".
- Documents are private: never under a publicly served path, never in the public payload (no file URL, reviewer id or reject reason).
- Deal values are self-reported: every place they appear says so ("beyan edilen" / "self-reported"). No currency conversion anywhere.
- No promised review turnaround in UI copy (the owner has not chosen one).
- Producer strings in `tr.json` + `en.json`; buyer strings in `frontend/src/storefront/strings.ts` (`de`, `en`). Errors `{"code", "message_key": "errors.<code>"}` with the key in both i18n files. No new dependencies.
- Backend `cd backend && .venv/Scripts/python.exe -m pytest -q`; frontend `cd frontend && npm run build && npm run lint` (no new warnings in touched files). One commit per task, no attribution lines.

## Review Focus

1. **Certificate name typed differently** in the profile and the submission (`ISO 22000` vs `iso 22000`, Turkish `İ`) — matched with `tr_fold`. (Tests in Tasks 2 and 3.)
2. **Certificate expires after it was verified** — the buyer label drops to "Herstellerangabe" on the day after `valid_until`, with no admin action. (Test in Task 3.)
3. **Producer removes a certification from the profile after verification** — it no longer appears to buyers at all. (Test in Task 3.)
4. **Producer uploads a Word file, HEIC, or an 8 MB+ PDF** — clear `bad_document` / size error, nothing stored. (Test in Task 1.)
5. **Lead marked won with value `0`, negative, `NaN` or 1e12** — 422; won without value — 422 `deal_value_required`; other statuses ignore deal fields. (Test in Task 7.)

---

### Task 1: Private document upload

**Files:**
- Modify: `backend/app/routers/uploads.py`, `backend/app/main.py` (`PRIVATE_DIRS`), `backend/app/services/storage_service.py`
- Test: `backend/tests/test_storage.py`

**Interfaces:**
- Produces `validate_document(data: bytes) -> tuple[bytes, str]` in `storage_service.py`: images (JPEG/PNG/WebP) go through `validate_and_process_image` and return `(webp_bytes, ".webp")`; data starting with `b"%PDF-"` and `<= MAX_BYTES` returns `(data, ".pdf")`; anything else raises `ValueError("bad_document")`; oversize raises the same size error code images use.
- Produces `POST /api/uploads/document` (multipart `file`, `current_user`) → `{"url": "/uploads/documents/<owner_id>/<uuid>.<ext>"}` via `save_file(data, f"documents/{user_id}", ext)` + `record_upload`.
- `PRIVATE_DIRS = ("quotes", "reports", "documents")`.

- [ ] **Step 1: Failing tests:** `test_document_upload_pdf_and_image` (minimal `%PDF-1.4` bytes → `.pdf` URL; JPEG → `.webp`); `test_document_upload_rejects_other` (`PK\x03\x04` docx bytes and random bytes → 422 `bad_document`; 8 MB + 1 → the size error code); `test_documents_not_served_statically` (extend the existing PDF test list with `/uploads/documents/zz-test/x.pdf`).
- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest -q tests/test_storage.py` → FAIL.
- [ ] **Step 3: Implement.** **Step 4:** full suite → pass. **Step 5: Commit** `feat: private document uploads`

---

### Task 2: Verification records (producer + admin API)

**Files:**
- Create: `backend/app/models/verification.py`, `backend/app/routers/verifications.py`, `backend/app/services/verification_service.py`
- Modify: `backend/app/main.py` (include both routers), `backend/app/core/db.py` (index `verifications` on `company_id`, `status`)
- Test: `backend/tests/test_verifications.py`

**Interfaces:**
- `VerificationIn`: `kind: Literal["tax_plate", "certificate"]`, `name: str = Field("", max_length=80)`, `issuer: str = Field("", max_length=120)`, `valid_until: date | None = None`, `file_url: str`.
- Stored doc: `company_id, kind, name` (`"tax_plate"` for tax plates), `issuer, valid_until (ISO str | None), file_url, status ("pending"|"verified"|"rejected"), reject_reason, reviewed_by, reviewed_at, created_at`.
- Producer, `router = APIRouter(prefix="/verifications")`:
  - `POST ""` → 201 doc. `require_owned(file_url)` (must be under `/uploads/documents/`, else 422 `bad_document`); certificate `name` must match one of `company.certifications` by `tr_fold(...).strip()` → else 422 `unknown_certificate`; `valid_until < tr_today()` → 422 `expired_document`. A new submission deletes earlier **pending or rejected** records with the same `kind` + folded `name` (never verified ones).
  - `GET ""` → own records, newest first. `DELETE "/{id}"` → only `pending` (409 `not_pending`).
- Admin, `admin_router = APIRouter(prefix="/admin/verifications", dependencies=[Depends(require_admin)])`:
  - `GET ""?status=pending|verified|rejected` (default pending) → records + `company_name`.
  - `GET "/{id}/file"` → file bytes from `get_storage().read`, `media_type` `application/pdf` or `image/webp`, `Content-Disposition: inline`.
  - `POST "/{id}/verify"` / `POST "/{id}/reject"` (`RejectIn` from `app.models.message`) → only from `pending` (409 `not_pending`); sets `status`, `reviewed_by` = admin id, `reviewed_at`, `reject_reason`.

- [ ] **Step 1: Failing tests** (`producer`, `admin_client`, documents uploaded through Task 1's endpoint): `test_submit_and_verify_lifecycle` (pending → admin verify → GET shows verified with `reviewed_at`); `test_certificate_name_must_be_in_profile` (`"ISO 9001"` not in profile → 422 `unknown_certificate`; profile has `"ISO 22000"`, submitting `"iso 22000"` → 201, Review Focus 1); `test_expired_document_rejected`; `test_resubmit_replaces_pending_and_rejected_not_verified`; `test_admin_only` (producer calling `/api/admin/verifications` → 403); `test_other_company_cannot_touch` (producer B DELETE A's record → 404); `test_reject_needs_reason_and_pending` (empty reason 422; reject a verified one → 409).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4:** full suite → pass. **Step 5: Commit** `feat: supplier document verification API`

---

### Task 3: Trust summary in the public storefront payload

**Files:**
- Modify: `backend/app/services/verification_service.py`, `backend/app/routers/public.py`
- Test: `backend/tests/test_verifications.py`

**Interfaces:**
- Produces `async def public_trust(db, company: dict, today: date) -> dict` → `{"company_verified": bool, "verified_at": "YYYY-MM-DD" | None, "certificates": [{"name": str, "verified": bool, "valid_until": "YYYY-MM-DD" | None}]}`. `certificates` follows `company.certifications` order and names exactly (Review Focus 3); a certificate is verified when a `verified` record with the same folded name has `valid_until` null or `>= today` (Review Focus 2). `company_verified` = a verified, unexpired `tax_plate`; `verified_at` its `reviewed_at` date.
- `public.get_storefront` adds `company.trust = await public_trust(db, co, tr_today())`.

- [ ] **Step 1: Failing tests:** `test_public_trust_labels` (one verified + one unverified certificate → flags match); `test_public_trust_expiry` (set the verified record's `valid_until` to yesterday in the DB → `verified` False); `test_public_trust_follows_profile` (remove the certificate from `company.certifications` → absent); `test_public_payload_trust_has_no_private_fields` (`set(trust) == {"company_verified", "verified_at", "certificates"}`, each certificate's keys exactly `{"name", "verified", "valid_until"}`, no `/uploads/documents` anywhere in the payload).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4:** full suite → pass. **Step 5: Commit** `feat: buyer-facing trust summary`

---

### Task 4: Buyer-facing badges on the storefront

**Files:**
- Modify: `frontend/src/storefront/StorefrontView.tsx` (`CompanyInfo.trust?`), `frontend/src/storefront/strings.ts` (`PublicCompany.trust`, strings), `frontend/src/storefront/PublicStorefront.tsx` (pass it through)

**Interfaces:**
- Consumes Task 3 `trust`.
- Hero, when `trust.company_verified`: a badge `s.verifiedSupplier` with the date ("Dokumente geprüft am {date}" / "Documents checked on {date}"), formatted for the page language.
- About → certificates: verified chip `✓ {name} · {s.certChecked}` (+ `s.validUntil {date}` when set); unverified chip `{name} · {s.selfDeclared}`. Without `trust` (editor preview) chips render as today.
- `strings.ts` keys: `verifiedSupplier`, `certChecked` ("geprüft" / "checked"), `selfDeclared` ("Herstellerangabe" / "self-declared"), `validUntil` ("gültig bis" / "valid until").

- [ ] **Step 1: Implement.** **Step 2: Verify** — build/lint clean; browser pane: storefront with one verified and one unverified certificate (set up via the API) shows the right labels in DE and EN; editor preview unchanged. **Step 3: Commit** `feat: verified-supplier and certificate labels on storefront`

---

### Task 5: Producer verification section

**Files:**
- Create: `frontend/src/pages/company/VerificationSection.tsx`
- Modify: `frontend/src/pages/company/CompanyPage.tsx`, i18n files

**Interfaces:**
- Consumes Tasks 1–2. Lists one row for the tax plate and one per profile certificate, each with status: `verify.status.none|pending|verified|rejected` (rejected shows the reason; verified shows the date and `valid_until`). Row action: file input (`accept=".pdf,image/jpeg,image/png,image/webp"`) + for certificates a `valid_until` date input → `POST /api/uploads/document` then `POST /api/verifications`. Busy state per row; errors through `t(messageKey)`.
- Intro copy: what is checked and why buyers see it ("Belgeleriniz ekibimiz tarafından kontrol edilir; alıcılar yalnızca 'kontrol edildi' etiketini görür, belgenin kendisini görmez." / English equivalent). No turnaround promise.

- [ ] **Step 1: Implement.** **Step 2: Verify** — build/lint clean; browser pane: upload a small PDF for a certificate → row shows "İncelemede"; profile without certificates shows only the tax-plate row. **Step 3: Commit** `feat: producer document verification section`

---

### Task 6: Admin review page

**Files:**
- Create: `frontend/src/pages/admin/Verifications.tsx`
- Modify: `frontend/src/App.tsx` (admin route `/admin/verifications`), `frontend/src/components/Layout.tsx` (admin nav link), i18n files

**Interfaces:**
- Consumes Task 2 admin API. Tabs pending / verified / rejected; each row: company, kind/name, issuer, `valid_until`, submitted date, "Belgeyi aç" (opens `/api/admin/verifications/{id}/file` in a new tab), Verify, Reject (existing `Modal` with a required reason).

- [ ] **Step 1: Implement.** **Step 2: Verify** — browser pane as admin: the pending record from Task 5 opens, verifies, moves to the verified tab; the storefront then shows the checked label. **Step 3: Commit** `feat: admin document review page`

---

### Task 7: Deal value when a lead is won

**Files:**
- Modify: `backend/app/models/lead.py` (`StatusIn`), `backend/app/routers/leads.py` (`patch_lead`), `frontend/src/pages/leads/LeadDetail.tsx`, `frontend/src/pages/leads/types.ts`, i18n files
- Test: `backend/tests/test_leads.py` (update existing "won" patches to send a value)

**Interfaces:**
- `StatusIn`: `status: str`, `deal_value: float | None = Field(None, gt=0, le=1_000_000_000, allow_inf_nan=False)`, `deal_currency: Literal["EUR", "USD", "TRY"] | None = None`.
- `patch_lead`: `status == "won"` without both fields → 422 `deal_value_required`; on won stores `deal_value`, `deal_currency`, `won_at`. Other statuses ignore the deal fields.
- LeadDetail: the "won" confirm modal gets an amount input (parsed with `parseLocaleNumber`) and a currency select (EUR default); confirm disabled until the amount is valid. Lead header shows the recorded value with `t('leads.detail.dealValue')` + "(beyan edilen)".

- [ ] **Step 1: Failing tests** `test_won_requires_deal_value` (Review Focus 5: missing → 422 `deal_value_required`; `0`, `-5`, `1e12` → 422; `NaN` raw JSON → 422; valid `{"status":"won","deal_value":12500,"deal_currency":"EUR"}` → stored with `won_at`); `test_lost_ignores_deal_fields`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** backend + UI. **Step 4:** full suite → pass; build/lint clean; browser pane: mark a demo lead won with `12.500` → header shows `12.500 €`. **Step 5: Commit** `feat: record deal value on won leads`

---

### Task 8: Export revenue panel (self-reported ROI)

**Files:**
- Modify: `backend/app/routers/dashboard.py`, `frontend/src/pages/dashboard/Dashboard.tsx` (or `ImpactPanel.tsx`), i18n files
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Consumes Task 7 fields. `GET /api/dashboard/roi` → `{"won_deals": int, "valued_deals": int, "totals": [{"currency": str, "amount": float}], "first_won_at": ISO | None}`: own company only; `totals` per currency sorted by currency code, rounded to 2 decimals, no conversion; `won_deals` counts every won lead, `valued_deals` those with a value.
- Dashboard panel "İhracat kazanımı" / "Export deals won": count, one line per currency, and the note `t('dashboard.roi.selfReported')` ("Tutarları siz girdiniz; doğrulanmamıştır." / "Amounts entered by you; not verified."). Hidden when `won_deals == 0`.

- [ ] **Step 1: Failing test** `test_roi_totals_per_currency` (two EUR + one USD won deal for A, one legacy won lead without value, one B deal → `won_deals 4`, `valued_deals 3`, totals `[EUR sum, USD]`, B excluded).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4:** full suite → pass; browser pane shows the panel after Task 7's won lead. **Step 5: Commit** `feat: self-reported export revenue panel`

---

## Final Check

- Backend suite, frontend build/lint green.
- Browser rehearsal: producer uploads a certificate → admin verifies → buyer storefront shows "✓ ISO 22000 · geprüft"; an unverified one shows "Herstellerangabe"; mark a lead won with a value → dashboard panel. Report that the review turnaround and any verification fee are the owner's decisions (M10 pricing).
