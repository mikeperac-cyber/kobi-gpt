# Running

Stub. Filled in by later tasks.

Backend tests: `cd backend; .venv\Scripts\python -m pytest`

## Dev without MongoDB (in-memory)

If no MongoDB is installed, run the backend against an in-memory database. It seeds the demo accounts at startup
(`bozkurt@demo.local` etc.; password is `SEED_PASSWORD`, or `demo12345` when unset).

PowerShell: `cd backend; $env:MONGO_URI="mongomock://"; .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`

Data is lost on restart. Use real MongoDB for persistence.
