# KOBİ-GPT & Otonom İhracat Ajanı — Build Kit

A set of prompts you give to an AI coding agent, one phase at a time, so it builds the MVP for you.

## What the MVP is

A web app where a small Turkish producer:
1. **Dijital Vitrin:** describes a product in Turkish, uploads photos and gets a published export storefront in German and English, with a quote-request form.
2. **Mevzuat Bekçisi:** gets GTİP/HS code suggestions, a compliance checklist for Germany with a source on every item, matched state incentives and a readiness report PDF.
3. **Alıcı Ajanı:** manages leads, gets outreach emails and quotes drafted in the buyer's language, and **approves every message before it goes out**.

Demo target: one producer (Gaziantep pistachios), live, Germany as the market, about 3 minutes.

## How to use the prompts

| Order | File | What gets built | Rough effort for the agent |
|---|---|---|---|
| 0 | [00-project-context.md](prompts/00-project-context.md) | Nothing. The agent learns the project and rules | 1 message |
| 1 | [01-foundation.md](prompts/01-foundation.md) | Accounts, onboarding, dashboard, LLM plumbing, demo companies | 1–2 sessions |
| 2 | [02-digital-storefront.md](prompts/02-digital-storefront.md) | Storefront generator, editor and public pages | 1–2 sessions |
| 3 | [03-reg-ai.md](prompts/03-reg-ai.md) | Knowledge base, GTİP suggestions, checklist, incentives, PDF | 1–2 sessions |
| 4 | [04-buyer-agent.md](prompts/04-buyer-agent.md) | Leads, drafting, approval queue, reply assistant, quotes | 2 sessions |
| 5 | [05-demo-and-polish.md](prompts/05-demo-and-polish.md) | Demo mode, offline fallbacks, polish, security | 1 session |
| — | [helper-prompts.md](prompts/helper-prompts.md) | Prompts for checking work, debugging and staying on track | as needed |

**Rules of thumb**
- Paste **one phase at a time**. Don't start the next phase until the agent has reported back and you've clicked through the acceptance criteria yourself.
- After each phase, paste the **verification** prompt from `helper-prompts.md`.
- When the agent asks questions, answer them. Its questions usually point at real gaps.
- Keep the agent inside scope. Payments, E-Devlet and fully automatic emailing are deliberately left out.

### Setup with a local coding agent (Claude Code, Cursor, Antigravity…)
1. Save Prompt 00's content as `AGENTS.md` in this folder so the agent re-reads it every session. Claude Code reads `CLAUDE.md` instead, so save a copy under that name if you use it.
2. Give it Prompts 01 → 05 one at a time. The prompts assume React + FastAPI + MongoDB, so you'll need Node.js, Python 3.11+, MongoDB (local or Atlas free tier) and an LLM API key in `.env`.

## ⚠️ Before you present to a jury

- **Verify the regulatory seed data.** Every rule and incentive in Prompt 03 starts as "Demo verisi – doğrulanmadı". Have an export consultant, İhracatçı Birliği expert or customs broker check each one against its source link, then mark it verified in the admin panel. The jury will include people who know this field.
- **Replace the illustrative logistics rates** with real quotes from 1–2 freight forwarders for Türkiye → Germany.
- **Kolay İhracat Platformu has no public API** (as of this writing). In the pitch, present integration with it as the **partnership ask** ("with your data, this becomes official"), not as something that already works.
- **Present the big numbers as targets.** "50,000 SMEs" and "\$15,000 saved per SME" belong in the deck, labelled as goals with a stated basis. The in-app impact panel shows only real measured numbers. That honesty works in your favour.
- **Human approval is part of the story.** "The agent does 90% of the work; the producer keeps control and signs off" answers the jury's biggest worry about autonomous agents. It's also what keeps outreach to EU buyers GDPR-compliant.
