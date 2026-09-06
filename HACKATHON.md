# APilot — Hackathon Submission Notes

**APilot Control Desk**: bounded-autonomous accounts payable exception
handling for AP analysts and controllers — a deterministic three-way match
(invoice vs. PO vs. goods receipt) with a human review queue, comparable
evidence, and an audit trail, demonstrated on 120 controlled synthetic
invoices.

---

## 1. The problem

Accounts payable teams are accountable for the ledger but sit between two bad
defaults: (a) a fully manual review treadmill where 100% of invoices cost
human time, or (b) an "autonomous AI" black box that posts money with no
explanation a controller can audit. AP exceptions — price drift, quantity
over-billing, missing POs, duplicate invoices, missing receipts, tax-style
uplifts — are exactly where accountability matters most.

## 2. The approach: bounded autonomy

APilot's core is **deterministic, explainable, and auditable**; AI is an
optional input helper and is never a decision-maker.

- **Three-way match** (`matcher.py`): every invoice is compared line-by-line
  against its PO and the goods receipt. Duplicate invoices (same vendor +
  invoice number) and uniform ~10% tax-style uplifts are detected explicitly.
- **Decision engine** (`decide.py`): no findings ⇒ `AUTO_POST`
  (confidence 1.0); any finding ⇒ `HUMAN_REVIEW` (confidence 0.0) with one
  suggested-resolution phrase per distinct finding type.
- **Evidence, not verdicts**: the Control Desk shows the exact finding, the
  offending invoice/PO/receipt cells side by side, and a suggested
  resolution. Reviewers approve / hold / escalate with a reason; every action
  is timestamped into a review history.
- **Optional LLM extraction** (`extract.py`): paste raw invoice text and the
  model returns a structured `Invoice` (one OpenAI-compatible call,
  temperature 0, one retry). The result is fed into the *same* deterministic
  matcher. The LLM cannot decide; it only types.

## 3. Controlled demo book — verified numbers

The demo runs on a **fixed, committed, synthetic dataset** generated with a
fixed seed (42), so results are reproducible on every run.

| Metric | Value |
|---|---|
| Total invoices | 120 |
| Auto-posted (`AUTO_POST`) | 80 |
| Human review (`HUMAN_REVIEW`) | 40 |
| **Touchless rate** | **80 / 120 = 66.7%** |
| Exception mix (40 total) | MISSING_RECEIPT 8 · PRICE_MISMATCH 7 · DUPLICATE_INVOICE 7 · QTY_MISMATCH 6 · TAX_MISMATCH 6 · MISSING_PO 6 |

Underlying master data: 80 POs, ~90% with goods receipts, 6 vendors, 50 SKUs
(`apilot/data.py`). All counts are verifiable in the committed files
`data/invoices.json`, `data/labels.json`, and `data/audit.json`.

**Evaluation** (`python -m apilot.evaluate`) is deterministic and read-only:
it compares the audit trail against ground-truth labels. On this controlled
set it reports **overall action accuracy = 1.0** with per-type
precision/recall/F1 = 1.0 across all seven types (CLEAN, PRICE_MISMATCH,
QTY_MISMATCH, MISSING_PO, DUPLICATE_INVOICE, MISSING_RECEIPT,
TAX_MISMATCH). 45 unit tests pass.

> **Honest framing (important):** 1.0 accuracy is expected here, not
> impressive — the deterministic engine is scored against a closed synthetic
> set produced by the same generator. It proves the engine is *deterministic,
> transparent, and self-consistent*. It is **not** evidence of production
> accuracy on real AP traffic. There is no real-customer validation.

## 4. Independent, deterministic policy suite

The decision logic is a single, independently inspectable policy suite
separate from the UI, the data, and the AI layer:

- `matcher.py` owns the *rules*: severity map, ±0.5% price tolerance
  (`PRICE_TOLERANCE = 0.005`), uniform-tax-uplift ratio (`TAX_RATIO = 1.1`),
  and finding order.
- `decide.py` owns the *decision*: findings present or absent →
  `HUMAN_REVIEW` / `AUTO_POST`, plus resolution phrasing.
- `data.py` mirrors those constants so the synthetic exceptions are generated
  with the same semantics the matcher detects — a deliberate closed loop that
  makes the benchmark reproducible.
- `evaluate.py` owns *measurement only*; it never writes files.

This suite is a **demo policy, not a policy framework**: it is code plus
tests, changed by editing code, not by a UI toggle. No future/planned policy
counts or hypothetical capabilities are claimed here — what exists is what is
documented above.

## 5. Control Desk (deliverable demo surface)

- **Next.js 15 + React 19 + TypeScript + Tailwind** frontend in `frontend/`
  (proxy: `/api/*` → `127.0.0.1:8000`).
- **FastAPI** backend in `apilot/api.py`: `GET /api/summary`,
  `GET /api/invoices`, `POST /api/review/{id}`, `POST /api/extract`; serves
  `static/index.html` at `/`.
- UI panels: summary cards; invoice queue with *Needs review* / *All
  invoices* / *Auto-posted* filters and search; invoice detail with **Exact
  findings**, **Comparable evidence** (invoice vs. PO vs. receipt qty),
  **review history**, and **Approve / Hold / Escalate** actions.

## 6. Demo policy (how to demo honestly)

- Demo the **controlled book**: 120 / 80 / 40 / 66.7% are the committed
  numbers — read them off the live summary cards.
- Demo the **exception path**: open a "Needs review" invoice, read the exact
  finding and evidence table, then approve/hold/escalate with a reason and
  watch it appear in the review history.
- Demo the **auto-post path**: switch to "Auto-posted", open a clean invoice,
  show no findings ⇒ `AUTO_POST`.
- Show the **honest evaluation**: `python -m apilot.evaluate` and the
  evaluator's own "ASSUMPTION … not measured" note on time savings.
- Only demo **LLM extraction** if `APILOT_LLM_KEY` is configured; otherwise
  skip it and say so.
- Never imply ERP posting, real data, or production accuracy. See Section 8.

## 7. AO build process (how this was built)

APilot was built with **Agent Orchestrator (AO)** — an orchestrator-plus-
workers build flow, not a single prompt:

- The orchestrator session decomposed the build into task-sized worker
  sessions for the `apilot` project.
- Each **worker session ran in an isolated git worktree on its own AO feature
  branch** (`ao/apilot-N/root`), so parallel work never collided.
- Workers implemented in conventional commits, ran the full `pytest` suite as
  the quality gate before finishing, and reported results back to the
  orchestrator.
- The **AO project dashboard / session list** shows the live evidence: the
  `apilot` project with **9 sessions total — 1 orchestrator (`apilot-1`) + 8
  workers (`apilot-2` … `apilot-9`)** — covering repo skeleton, data models,
  the synthetic labeled dataset, three-way matcher, decision engine, audit
  trail, exception detection, evaluation, the review dashboard, the Control
  Desk UI, and (this) submission kit.
- Git history on `main` reflects the same sequence: 14 commits from
  "chore: bootstrap repo" through "feat: build APilot review dashboard"
  (2026-09-05 → 2026-09-06), each independently reviewed/verified by its
  worker before landing.

The AO session count is read live from the dashboard during the demo (see
[DEMO_SCRIPT.md](DEMO_SCRIPT.md)); treat the numbers shown on screen as
authoritative at demo time.

## 8. Explicit limitations

1. **Synthetic data only.** No real invoices, vendors, POs, or customer data.
2. **One demo policy.** A single deterministic policy suite in code — not a
   configurable, multi-tenant policy framework.
3. **No ERP.** Nothing connects to or posts in an ERP/accounting system.
   `AUTO_POST` is a decision within the demo, not a financial posting.
4. **Demo-only persistence.** Data, audit trail, and review history are local
   JSON files (`data/*.json`, runtime `data/reviews.json`); there is no
   production database, auth, or multi-user access control.
5. **No real-customer validation / no production accuracy claim.** 100% on
   the controlled synthetic benchmark ≠ real-world performance. No claims are
   made about accuracy on real invoices.
6. **LLM layer is optional and unvalidated for production OCR.** If
   `APILOT_LLM_KEY` is absent, extraction returns an error; the core demo
   does not need it.
7. **Time-saved numbers are an assumption** (manual ~5 min vs. ~1 min per
   invoice), flagged "not measured" inside the evaluator output.

## 9. Official citations and sources

All quantitative claims in this submission trace to the repository itself;
external citations are limited to the official documentation of the
components actually used.

- **Repository**: <https://github.com/emmaGH1/APilot> — dataset counts
  (`data/invoices.json`, `data/labels.json`, `data/audit.json`), policy
  constants (`apilot/matcher.py`), decision rules (`apilot/decide.py`),
  evaluator (`apilot/evaluate.py`).
- **FastAPI** (backend API): <https://fastapi.tiangolo.com/>
- **Pydantic** (data models/validation): <https://docs.pydantic.dev/>
- **pytest** (test suite): <https://docs.pytest.org/>
- **Python ≥ 3.11**: <https://docs.python.org/3/>
- **Next.js 15** (Control Desk frontend): <https://nextjs.org/docs>
- **Tailwind CSS** (styling): <https://tailwindcss.com/docs>
- **OpenAI-compatible chat completions** (optional extraction layer, called
  via stdlib `urllib`): <https://platform.openai.com/docs/api-reference/chat>
- **Radix UI primitives** used by the frontend: <https://www.radix-ui.com/>

No third-party benchmark, market statistic, or vendor ROI figure is cited,
because this submission does not rely on unverified external numbers.

## 10. Quick reference

```bash
pip install -e .            # backend deps (repo root)
python -m apilot            # API + HTML dashboard on http://127.0.0.1:8000
cd frontend && npm install && npm run dev   # Control Desk on http://localhost:3000
python -m pytest            # 45 tests
python -m apilot.evaluate   # read-only evaluation of the audit trail
```

See [README.md](README.md) for full setup, [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
for the timed demo, and [DEVPOST_SUBMISSION.md](DEVPOST_SUBMISSION.md) for
paste-ready submission copy.
