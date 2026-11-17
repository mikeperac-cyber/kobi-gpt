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
| `JWT_SECRET` | Signs the login cookie. Set a long random value outside local dev. |
| `LLM_PROVIDER` | `anthropic` (default), `openai` or `gemini`. Selects which key below is used. |
| `LLM_MODEL` | Model name for that provider (default `claude-sonnet-5-5`). |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | Key for the chosen provider. Leave all empty to run on fallbacks and the demo cache only. Never commit it. |
| `LLM_TIMEOUT_SECONDS` | Timeout for a normal LLM call (default 45). |
| `DEMO_LLM_TIMEOUT_SECONDS` | Timeout for demo companies before the cached output is used (default 25). |
| `FRONTEND_ORIGIN` | The only origin allowed by CORS, also used in links inside drafts (default `http://localhost:5173`). |
| `EMAIL_PROVIDER` | Leave empty. No email is ever sent by the server; "Onayla ve Gönder" opens a `mailto:` draft. |
| `SEED_PASSWORD` | Password for the seeded demo accounts. Required by `python -m app.seed`. In `mongomock://` mode it defaults to `demo12345` when empty. |
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

Check it: `curl http://localhost:8000/api/health` returns `{"status":"ok","llm":{"provider":...,"key_set":...}}`.

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

Password = `SEED_PASSWORD` (`demo12345` in `mongomock://` mode when unset).

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
