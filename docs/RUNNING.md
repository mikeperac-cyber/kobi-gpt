# Running KOBİ-GPT locally (Windows, PowerShell)

Commands below were run on Windows 11 / PowerShell with Python 3.12 and Node 26. The only things not run on this machine are
the ones that need a real MongoDB or an LLM key (marked "not run here").

## 1. Prerequisites

- Python 3.11 or newer.
- Node.js LTS (includes npm).
- A database, one of:
  - local MongoDB (`mongodb://localhost:27017`), or
  - a MongoDB Atlas connection string, or
  - **in-memory dev mode** (no install): `MONGO_URI=mongomock://`, see section 5. Data is lost on every restart.
- Optional: an LLM key (Anthropic, OpenAI or Gemini). Without one every AI step uses its built-in fallback and says so.

## 2. Backend setup

```powershell
cd C:\path\to\KOBI-GPT\backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If PowerShell blocks `.venv\Scripts\Activate.ps1`, skip activation and call `.venv\Scripts\python.exe` directly, as above.

## 3. Environment file

The backend reads `.env` from the **repository root** (not from `backend\`).

```powershell
cd C:\path\to\KOBI-GPT
Copy-Item .env.example .env
```

| Variable | Meaning |
|----------|---------|
| `MONGO_URI` | MongoDB connection string. `mongomock://` = in-memory dev DB (seeded on startup, lost on restart). |
| `MONGO_DB` | Database name (default `kobigpt`). |
| `JWT_SECRET` | Signs the login cookie. Empty = built-in dev default, accepted only when `FRONTEND_ORIGIN` is localhost / 127.0.0.1. For any other origin the app refuses to start unless it is 32+ random characters. Generate one: `[Convert]::ToBase64String((1..48 \| % {Get-Random -Max 256}))` |
| `LLM_PROVIDER` | `anthropic` (default), `openai` or `gemini`. Selects which key below is used. |
| `LLM_MODEL` | Model name for that provider (default `claude-sonnet-5-5`). |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | Key for the chosen provider. Leave all empty to run on fallbacks and the demo cache only. Never commit it. |
| `LLM_TIMEOUT_SECONDS` | Timeout for a normal LLM call (default 45). |
| `DEMO_LLM_TIMEOUT_SECONDS` | Timeout for demo companies before the cached output is used (default 25). |
| `FRONTEND_ORIGIN` | The only origin allowed by CORS, also used in links inside drafts (default `http://localhost:5173`). |
| `EMAIL_PROVIDER` | Leave empty. No email is ever sent by the server; "Onayla ve Gönder" opens a `mailto:` draft. |
| `SEED_PASSWORD` | Password for the seeded demo accounts. Leave empty in `.env.example`; with real MongoDB you must set it before `python -m app.seed` (that value is the password). With `MONGO_URI=mongomock://` and `SEED_PASSWORD` empty the password is `demo12345`; if you set it, your value applies. |
| `ADMIN_EMAIL` | Email of the seeded admin account (default `admin@kobi-gpt.local`). |

## 4. Seed the database (real MongoDB)

```powershell
cd C:\path\to\KOBI-GPT\backend
$env:SEED_PASSWORD="choose-a-demo-password"   # or put it in .env
.venv\Scripts\python.exe -m app.seed
```

It creates the admin, three demo producers, 6 products, 18 demo leads, 15 compliance rules, 9 incentives, 8 GTİP records and
the logistics rates. It is idempotent. Against an in-memory DB the command works but changes nothing you can keep.
Not run here against real MongoDB (none installed); run here against `mongomock://` only.

## 5. Start the backend

```powershell
cd C:\path\to\KOBI-GPT\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

In-memory dev mode (no MongoDB):

```powershell
cd C:\path\to\KOBI-GPT\backend
$env:MONGO_URI="mongomock://"
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

`$env:MONGO_URI` stays set for the whole PowerShell session (later runs stay in-memory until you `Remove-Item Env:MONGO_URI`).

Check it: `curl.exe http://localhost:8000/api/health` (in PowerShell plain `curl` is an alias of `Invoke-WebRequest`; or use `Invoke-RestMethod http://localhost:8000/api/health`) returns `{"status":"ok","llm":{"provider":...,"key_set":...}}`.

**Behind a reverse proxy:** the rate limiter keys on the client IP. Start uvicorn with `--proxy-headers --forwarded-allow-ips="<proxy ip>"`,
otherwise every visitor shares the proxy's IP and limits trigger early. The in-memory limiter is per process, so use one worker.

## 6. Start the frontend

```powershell
cd C:\path\to\KOBI-GPT\frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` and `/uploads` to port 8000.

Production build, served locally (also proxies `/api` to 8000):

```powershell
npm run build
npx vite preview --port 4173
```

`npm run build` type-checks (`tsc`) and writes `frontend\dist`. For a real deployment serve `dist` from any static host and route `/api` and `/uploads` to the backend.

## 7. Tests

```powershell
cd C:\path\to\KOBI-GPT\backend
.venv\Scripts\python.exe -m pytest -q
```

Uses `mongomock-motor` and a fake LLM; needs no MongoDB, no key and no network. There is no frontend unit-test suite; the frontend is checked by `npm run build`.

## 8. Demo logins

Password: real MongoDB = the `SEED_PASSWORD` you seeded with. `mongomock://` = `demo12345` if `SEED_PASSWORD` is empty, otherwise your `SEED_PASSWORD`.

| Role | Email | Company |
|------|-------|---------|
| Producer | `bozkurt@demo.local` | Bozkurt Antep Fıstığı (Gaziantep, food) |
| Producer | `pamukkale@demo.local` | Pamukkale Havlu Atölyesi (Denizli, textile) |
| Producer | `uludag@demo.local` | Uludağ Bağlantı Elemanları (Bursa, fasteners) |
| Admin | `admin@kobi-gpt.local` (or `ADMIN_EMAIL`) | none |

## 9. Resetting the demo

1. Log in as admin and open `/demo` (the page is hidden from producers).
2. Press Gaziantep, Denizli or Bursa. That company returns to the clean seed state (profile and product filled in, no storefront, no report, demo leads present). It takes well under a second here; the page also sends one LLM ping (silently skipped without a key).
3. Log out, log in as that producer, and run the script. After the first full run has filled `demo_cache`, a failed or slow live call (over `DEMO_LLM_TIMEOUT_SECONDS`) is served from the cache; the presenter sees a small dot in the demo guide.
4. `Ctrl+Shift+D` toggles the floating "Demo rehberi / Demo guide" panel with the next script step and a stopwatch.

## 10. Honest limits

- `mongomock://` data is lost on restart; persistence across restarts is **not verified** (no real MongoDB was used).
- No live LLM call has been verified (no key was available). All checks ran on the fallbacks and with a fake LLM in tests.
- Sending is a `mailto:` hand-off to the producer's own mail client; the app never sends mail itself.
- Uploaded files go to local `uploads\` (behind `storage_service`, swappable for S3).
- PDFs were checked for text and fonts, not looked at visually; microphone dictation, a real phone and a screen reader were not tested.
- GTİP codes, compliance rules and incentives come only from the curated seed data and need expert confirmation (gümrük müşaviri, İhracatçı Birliği).

## 10. Before the jury

- Do one full run with a live LLM key so `demo_cache` is filled (the cache only holds outputs from successful live calls).
- Web-check the firm names of the demo leads: they must not point at a real company that could be bothered.
- Tick a few checklist items live in the readiness report (the score starts at 0).
- On a 1280x720 screen, collapse the demo guide before presenting.

## 11. Deploying (Vercel frontend + container backend)

The backend cannot run as Vercel serverless functions: AI jobs keep running after the response (`agent_steps.spawn`) and uploads/PDFs are written to disk. Run it as a long-lived container instead; Vercel serves the frontend and forwards `/api` and `/uploads` to it, so the login cookie stays on one domain.

1. **Database:** create a MongoDB Atlas cluster and copy its connection string.
2. **Backend:** deploy `backend/Dockerfile` (build context `backend/`) on Render, Railway, Fly.io or Cloud Run.
   - Attach a persistent disk at `/srv/uploads`, or photos and PDFs vanish on redeploy.
   - Env vars: `MONGO_URI`, `JWT_SECRET` (long random; weak secrets are refused on https origins), `FRONTEND_ORIGIN=https://<app>.vercel.app`, `LLM_PROVIDER` + its API key (e.g. `ANTHROPIC_API_KEY`), `SEED_PASSWORD`, `ADMIN_EMAIL`.
   - Seed once from the host's shell: `python -m app.seed`.
3. **Frontend:** in `frontend/vercel.json` replace both `YOUR-BACKEND-HOST` with the backend's host name, commit, then import the GitHub repo in Vercel with **Root Directory = `frontend`**. Build settings come from `vercel.json`.
4. **Check:** log in, generate a storefront, open `/s/<slug>`; `/uploads/quotes/...` must return 404.
5. **Link previews:** WhatsApp/LinkedIn/Telegram bots are routed to `/api/public/storefronts/<slug>/share` (rule at the top of `frontend/vercel.json`); test with `curl -A WhatsApp https://<app>/s/<slug>` — the HTML must contain `og:title`.

Free tiers that sleep when idle add ~30 s to the first request: warm the backend up before a live demo.
