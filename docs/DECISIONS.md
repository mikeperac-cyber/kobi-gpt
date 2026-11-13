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
