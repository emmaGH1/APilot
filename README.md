# APilot — Control Desk for Accounts Payable

APilot is a working **accounts payable (AP) control desk** for AP analysts and
controllers. It runs a deterministic three-way match — **invoice vs. purchase
order vs. goods receipt** — against a controlled demo book of **120 synthetic
invoices**, auto-posts the clean ones, and routes everything else to a human
review queue with exact findings, comparable evidence, and a full audit trail.

This repo is a bounded-autonomy demonstration: the **decision engine is
deterministic and fully auditable**, and any AI in the pipeline (an optional
LLM extraction layer) is strictly an input helper — it never decides.

> Scope: this is a **hackathon/demo build**. Data is synthetic, the policy
> suite is a single demo policy in code, there is no ERP connection, and
> persistence is demo-only. Nothing here is validated for production AP or
> real customer data. See [HACKATHON.md](HACKATHON.md) and the Limitations
> section below.

## What the demo shows

| Metric | Value |
|---|---|
| Controlled invoices in the demo book | **120** (committed, seed-fixed) |
| Auto-posted touchless (`AUTO_POST`) | **80** — **66.7% touchless** |
| Routed to human review (`HUMAN_REVIEW`) | **40** — 33.3% |
| Exception mix (of the 40) | MISSING_RECEIPT 8 · PRICE_MISMATCH 7 · DUPLICATE_INVOICE 7 · QTY_MISMATCH 6 · TAX_MISMATCH 6 · MISSING_PO 6 |
| Unit tests | **45 passing** (`python -m pytest`) |

Every number above is reproducible from the committed dataset
(`data/invoices.json`, `data/labels.json`, `data/audit.json`) and the read-only
evaluator — nothing is invented.

## For AP analysts and controllers

The Control Desk UI gives the people accountable for the ledger what they
need:

- **Summary cards** — invoices processed, needing human review, and auto-posted.
- **Invoice queue** — filter to *Needs review*, *All invoices*, or
  *Auto-posted*; search by invoice, vendor, or number.
- **Exact findings** — each exception states the rule that fired
  (price/quantity/PO/receipt/duplicate/tax/vendor), its severity, and a
  human-readable detail.
- **Comparable evidence** — a line-by-line table of invoice vs. PO vs.
  received quantity, with the offending cells highlighted.
- **Review actions + audit trail** — approve / hold / escalate with an
  optional reason; every action lands in a timestamped review history.
- **Extract an invoice** — optional: paste raw invoice text and let an LLM
  produce a structured invoice that is then run through the same deterministic
  matcher (an AI *input* helper only; it never decides).

Design rule: **controllers see the evidence, not just a verdict.** An
auto-post is only ever a "no findings" result, and any invoice can still be
opened and reviewed by a human.

## Bounded-autonomous architecture

```
raw invoice text (optional)
        │  APILOT_LLM_*  (optional extraction helper, never a decision-maker)
        ▼
   ┌─────────────────────────── deterministic core ───────────────────────────┐
   │ extract.py   → Invoice models (optional LLM, stdlib HTTP, temperature 0) │
   │ matcher.py   → three-way match: invoice vs PO vs goods receipt;          │
   │                duplicate-invoice + uniform-tax-uplift detection;         │
   │                price tolerance ±0.5%; severity per finding type          │
   │ decide.py    → no findings ⇒ AUTO_POST (confidence 1.0);                 │
   │                any finding ⇒ HUMAN_REVIEW (confidence 0.0) + one         │
   │                suggested-resolution phrase per distinct finding type     │
   └──────────────────────────────────────────────────────────────────────────┘
        │
        ▼
   audit.py   → writes data/audit.json (full, per-invoice audit trail)
   evaluate.py→ read-only comparison of the audit trail vs. ground-truth labels
```

- The core pipeline is **deterministic** (seeded generation, fixed
  tolerances, no network) — every decision can be explained and re-run.
- The **LLM extraction layer is optional and isolated**: `extract.py` makes
  one OpenAI-compatible `chat/completions` call at temperature 0 with one
  retry, and it only converts text into an `Invoice` model. It cannot change
  any decision.
- **API** (`apilot/api.py`, FastAPI) serves the data and review actions.
- **Two UIs**, same API: the full Next.js Control Desk in `frontend/`, and a
  single-file HTML dashboard in `static/index.html` served at `/` by the API.

### Repository layout

```
apilot/            Python package: models, data, matcher, decide, extract,
                   audit, evaluate, api
data/              Committed demo book: pos.json, receipts.json, invoices.json,
                   labels.json, audit.json (+ runtime reviews.json, see limits)
static/index.html  Single-file HTML dashboard (served by the API at /)
frontend/          Next.js 15 + React 19 + TypeScript + Tailwind Control Desk
tests/             pytest suite (45 tests, incl. per-module + API + extract)
pyproject.toml     Python package metadata (FastAPI, uvicorn, pydantic, pytest)
```

## Local setup

Prerequisites: **Python ≥ 3.11** and **Node.js ≥ 18** (for the Next.js desk).

### 1. Backend + API (required)

```bash
# from the repo root
python -m venv .venv
# Windows:  .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
```

Run the API server (serves `static/index.html` at `/`):

```bash
python -m apilot          # uvicorn apilot.api:app on http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000> for the single-file dashboard, or go to step 2
for the full Control Desk.

### 2. Full Control Desk (Next.js, optional but recommended)

In a second terminal:

```bash
cd frontend
npm install
npm run dev               # http://localhost:3000
```

`frontend/next.config.ts` rewrites `/api/*` to `http://127.0.0.1:8000/api/*`,
so the backend from step 1 must be running. Open <http://localhost:3000>.

### Environment variables (optional, names only)

The deterministic core needs **no** environment variables. They are only read
by the optional LLM text-extraction feature (`POST /api/extract`). Copy
`.env.example` if you want to configure it (see `.env.example` for the names).

| Variable | Purpose | Default if unset |
|---|---|---|
| `APILOT_LLM_KEY` | API key for the extraction model | *(none — feature returns "APILOT_LLM_KEY is not set")* |
| `APILOT_LLM_BASE_URL` | OpenAI-compatible API base URL | `https://api.openai.com/v1` |
| `APILOT_LLM_MODEL` | Model name | `gpt-4o-mini` |

### Reproducing the demo book and results

```bash
python -m pytest          # 45 tests
python -m apilot.data     # regenerate the 120-invoice synthetic book (seed 42)
python -m apilot.audit    # re-run the deterministic audit -> data/audit.json
python -m apilot.evaluate # read-only evaluation vs. ground-truth labels
```

`evaluate.py` never writes files and reports overall action accuracy, per-type
precision/recall/F1, and a clearly-labeled **time-saved assumption** (manual
~5 min vs. APilot ~1 min per invoice — marked *"not measured"* in its own
output).

## Demo policy

The demo book and decision policy are deliberately kept in sync in code:

- Dataset generation and policy constants mirror each other
  (`data.py` ↔ `matcher.py`: same tolerance, same uplift ratio).
- Changing a policy means changing code plus tests and regenerating the audit
  trail — there is no hidden UI switch that can silently change decisions.
- Dashboard review actions persist only to `data/reviews.json` at runtime
  (demo-only persistence) and are never treated as ERP posting.

## Limitations

- **Synthetic data only** — no real invoices, vendors, or customer data.
- **One demo policy** — a single deterministic policy suite in code; not a
  configurable, multi-tenant policy framework.
- **No ERP** — nothing posts to or syncs with an ERP/accounting system;
  "auto-post" means the decision is AUTO_POST within this demo.
- **Demo-only persistence** — audit/reviews live in local JSON files; no
  production database, auth, or multi-user controls.
- **No real-customer validation / production accuracy** — the 100% action
  accuracy on this benchmark is a closed synthetic set scored against its own
  generator; it proves the engine is deterministic and auditable, not that it
  generalizes to real AP traffic.
- **Time-saved figures are an assumption**, explicitly flagged as such in the
  evaluator output.

## References

Official citations and sources are collected in
[HACKATHON.md](HACKATHON.md#official-citations-and-sources).
Demo script: [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Devpost copy:
[DEVPOST_SUBMISSION.md](DEVPOST_SUBMISSION.md).
