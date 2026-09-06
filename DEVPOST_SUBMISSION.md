# APilot — Devpost Submission (paste-ready)

Everything below is formatted to paste directly into a Devpost project.
No angle brackets or field markers remain — trim or reorder freely.

---

## Title

APilot — The Accounts Payable Control Desk: bounded-autonomous AP exception
handling with an auditable trail

## Tagline

80 of 120 controlled invoices auto-posted (66.7% touchless) — and every
exception is routed to a human with the exact evidence, on a deterministic,
fully auditable engine.

## What it does

APilot is a control desk for AP analysts and controllers. It runs a
deterministic three-way match — invoice vs. purchase order vs. goods receipt —
over a controlled book of 120 synthetic invoices. Clean invoices auto-post
(80 / 66.7% touchless); the 40 exceptions (missing PO, missing receipt,
duplicate invoice, price/quantity mismatch, tax-style uplift) go to a human
review queue that shows the exact finding, a line-by-line evidence table
(invoice vs. PO vs. received quantity), a suggested resolution, and
approve / hold / escalate actions with a timestamped review history. An
optional LLM layer extracts structured invoices from raw pasted text — as an
input helper only; it never decides.

## How we built it

- **Deterministic decision core (Python):** three-way matcher
  (`apilot/matcher.py`) with ±0.5% price tolerance, duplicate-invoice and
  uniform ~10% tax-uplift detection, per-finding severity; decision engine
  (`apilot/decide.py`): no findings ⇒ AUTO_POST (confidence 1.0), any finding
  ⇒ HUMAN_REVIEW (confidence 0.0) with a suggested resolution.
- **Audit & evaluation:** every decision written to an audit trail
  (`data/audit.json`); a read-only evaluator scores the trail against
  ground-truth labels with per-type precision/recall/F1.
- **API (FastAPI):** summary, invoice queue, review actions, and extraction
  endpoints; also serves a single-file HTML dashboard.
- **Control Desk UI (Next.js 15 / React 19 / TypeScript / Tailwind / Radix):**
  summary cards, a searchable queue filtered by Needs review / All /
  Auto-posted, an invoice detail view with exact findings and comparable
  evidence, review history, and one-click approve / hold / escalate.
- **Built with Agent Orchestrator:** 9 AO sessions (1 orchestrator + 8
  workers), each worker in its own isolated git worktree and branch,
  test-gated before landing (45 pytest tests passing).

## Results and honest evaluation

Verified, reproducible numbers from the committed synthetic dataset (fixed
seed):

- 120 controlled invoices; **80 auto-posted / 40 human review — 66.7%
  touchless**.
- Exception mix: MISSING_RECEIPT 8 · PRICE_MISMATCH 7 · DUPLICATE_INVOICE 7 ·
  QTY_MISMATCH 6 · TAX_MISMATCH 6 · MISSING_PO 6.
- 45 passing unit tests; read-only evaluator reports 100% action accuracy.

Honest framing: 100% accuracy is expected, not impressive — the deterministic
engine is scored on a closed synthetic set produced by its own generator. It
proves determinism, transparency, and auditability, not production
performance.

## Limitations

- Synthetic data only; no real invoices or customer data.
- One demo policy suite in code (not a configurable policy framework).
- No ERP integration — nothing posts to an accounting system.
- Demo-only persistence (local JSON); no production DB, auth, or multi-user
  controls.
- No real-customer validation / no production accuracy claim. Time-saved
  figures are an assumption explicitly flagged "not measured" in the
  evaluator.

## Built for

AP analysts and controllers who want automation they can audit: every
auto-post is a provably clean three-way match, and every exception arrives
with its evidence attached.

## What's next

- Policy configuration UI (approval matrices, tolerance per vendor/region)
  on top of the deterministic core.
- ERP sandbox connectors (post approval results via API to a demo tenant).
- Red-team the extraction layer against real invoice layouts.
- Multi-user controls: reviewer identity, segregation of duties, SOX-style
  audit export.

## Gallery / assets notes

- Cover: Control Desk screenshot showing the three summary cards
  (120 / 40 / 80) and a selected exception.
- Screenshot 2: Comparable evidence table with a highlighted price mismatch.
- Screenshot 3: AO dashboard session list (orchestrator + 8 workers).
- Screenshot 4: terminal output of `python -m apilot.evaluate`.

## Links

- GitHub: https://github.com/emmaGH1/APilot
- Setup: see the repository README.
- Sources: FastAPI, Pydantic, pytest, Python ≥ 3.11, Next.js 15, Tailwind
  CSS, Radix UI, OpenAI-compatible chat completions (optional extraction).
