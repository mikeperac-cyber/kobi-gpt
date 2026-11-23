# Contest Upgrade Roadmap

Goal: win a live 3-minute jury demo (TÜBİTAK / competition) with a product that looks finished, lets the jury take part, and is credible on regulation. Each milestone gets its own plan file when it starts; milestones do not depend on each other's code unless noted. `AGENTS.md` principles 1–7 bind every milestone.

| # | Milestone | What the jury sees | Needs from the owner | Plan |
|---|-----------|--------------------|----------------------|------|
| M0 | **Live AI** (no code) | Real German copy, green ✓ on every AI step | An LLM API key in `.env`; one rehearsal per demo company to fill `demo_cache`; prompt tweaks where copy reads stiff | — |
| M1 | **Jury moment** | A judge scans the QR, opens the German shop on their phone, sends a request; a toast pops on the presenter screen within seconds | A public URL (deploy per `docs/RUNNING.md` §11) or the LAN fallback | `2026-11-23-m1-jury-moment.md` |
| M2 | **Photo-first products** | Owner photographs a product; AI drafts name, material, description; owner confirms | **Licensed real product photos** for the 3 demo companies (we must not scrape or invent them) | later |
| M3 | **Premium storefront** | One polished mobile-first template, certificate trust badges, fast responsive images, Lighthouse mobile ≥ 90, accessibility pass | Brand colours/logo choices | later |
| M4 | **Credibility** | Closing "time to first buyer" impact screen; ~10 real, source-linked EU rules for pistachios | **Expert sign-off** on every rule (gümrük müşaviri / İhracatçı Birliği) before it is seeded as verified | later |
| M5 | **Voice-first + installable** | Dictation on every free-text field; producers can "Add to home screen" (PWA) | — | later |
| M6 | **Buyer-language document pack** | Proforma invoice + packing list as German/English PDFs from a quote | — | later |
| M7 | **Second market (NL)** | Market switch DE → NL storefront + checklist | Sourced, expert-checked NL rules (else skip; principle 2) | later |
| M8 | **Storefront analytics** | Views and RFQ conversion per week, no cookies, no third-party tracker | — | later |

Order: M0 → M1 → M2 → M3 → M4, then M5–M8 as time allows. M1's WhatsApp button and share preview are the extra ideas beyond the earlier list.

Explicitly not planned (no jury value, or out of scope per `AGENTS.md` §4): billing, white-label, custom domains, automatic email sending, payments.
