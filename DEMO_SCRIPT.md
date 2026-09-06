# APilot — Demo Script (2:50–3:00)

**Presenter setup before the clock starts**

- AO desktop dashboard open on the **apilot project → Sessions** list
  (project dashboard showing orchestrator `apilot-1` + worker sessions
  `apilot-2`…`apilot-9`).
- Backend running: `python -m apilot` → <http://127.0.0.1:8000>.
- Control Desk running: `cd frontend && npm run dev` → <http://localhost:3000>.
- Terminal open in the repo root, `python -m apilot.evaluate` typed but not
  yet run.
- (Optional) `APILOT_LLM_KEY` configured **only** if you want the extract
  demo; otherwise skip beat 5 and say extraction is optional.
- Have `data/labels.json` / `data/audit.json` reachable to back any claim.

Keep each beat tight; total is **~2:50**. If you run long, cut beat 5 first.

---

## Beat 1 — 0:00–0:20 · The build story (AO dashboard, live session count)

**Say:** "We built APilot with Agent Orchestrator — an orchestrator that
spawned isolated worker sessions, each in its own git worktree and branch."

**Show:** the AO dashboard for the `apilot` project — the live session list.

**Say (reading numbers off the screen):** "Right now the dashboard shows
**1 orchestrator session (`apilot-1`) and 8 worker sessions** — 9 sessions
total on this project. Each worker owned a slice: repo skeleton, synthetic
labeled dataset, three-way matcher, decision engine, audit trail, evaluation,
the review dashboard, and this submission kit. Every worker ran the full
`pytest` suite before landing — no merge without green tests."

> Live rule: whatever the dashboard shows is what you say. If a session count
> differs from 9, read the live number — the story is "parallel, isolated,
> test-gated agent workers," not the exact count.

## Beat 2 — 0:20–0:40 · The desk and the controlled book

**Show:** Control Desk at <http://localhost:3000> — the three summary cards.

**Say:** "This is the AP Control Desk for analysts and controllers. The demo
book is **120 controlled synthetic invoices** — fixed seed, committed to the
repo, reproducible. The engine auto-posted **80** — that's **66.7% touchless**
— and routed **40** to human review. Controllers own the exceptions; the
machine never silently posts a finding."

## Beat 3 — 0:40–1:05 · Exception evidence (why it needs a human)

**Show:** *Needs review* tab is active. Click a price-mismatch invoice (e.g.
**INV-0074**, Ember Packaging, PO-0036).

**Say:** "Here's an exception. The **Exact findings** panel says PRICE_MISMATCH
— medium severity — one SKU invoiced above the PO price, past the ±0.5%
tolerance. The **Comparable evidence** table puts the invoice, PO, and receipt
side by side and highlights the offending cell. The suggested resolution tells
the analyst exactly what to reconcile. No black box: every verdict traces to a
rule."

## Beat 4 — 1:05–1:30 · Human review and the audit trail

**Show:** click a high-severity exception (e.g. **INV-0101**, Acme Supplies —
MISSING_RECEIPT, PO-0007). Type a short reason and click **Hold** (or Escalate).

**Say:** "High severity: no goods receipt on file for this PO — we hold it.
The review — verdict, reviewer, timestamp, reason — is written to the review
history instantly. Every action lands in an audit trail. Persistence here is
demo-only, local JSON — deliberately not an ERP claim."

## Beat 5 — 1:30–1:50 · Clean auto-post (optional extract can be skipped)

**Show:** switch the queue tab to **Auto-posted**, open a clean invoice (e.g.
**INV-0001**, Ferrum Steel, PO-0001).

**Say:** "The 80 auto-posts are the no-findings population: full three-way
match, zero findings — `AUTO_POST`. A controller can still open any of them.
And the optional LLM piece is only an input helper — paste raw invoice text,
it extracts a structured invoice, and the same deterministic matcher decides."

**Only if configured:** demo the **Extract invoice** dialog with one pasted
text block, show the returned action.

## Beat 6 — 1:50–2:35 · Honest evaluation

**Show:** the repo terminal; run `python -m pytest` (flash the 45 passed),
then `python -m apilot.evaluate`.

**Say (honest framing — do not skip):** "The evaluator compares the audit
trail against ground-truth labels and shows **100% action accuracy** — but
read that honestly: this is a **closed synthetic set scored against its own
generator**. Perfect accuracy is the *expected* result of a deterministic
engine, and it proves determinism and auditability — not production
performance. There is **no ERP, no real customer data, no production accuracy
claim**. Note the evaluator's own time-saved line is an assumption, labeled
*'not measured'*."

## Beat 7 — 2:35–2:50 · Close

**Say:** "What's real: a deterministic, explainable, auditable AP exception
engine, a control desk a controller would actually use, 45 passing tests, and
a reproducible benchmark — 120 invoices, 80 auto, 40 review, 66.7% touchless.
Built entirely by AO worker sessions. The code is at
`github.com/emmaGH1/APilot`."

---

### If you are short on time

Cut beat 5 (optional extract) entirely and compress beat 1 to 15 seconds —
the demo still lands on: **AO build → desk → exception evidence → review →
honest eval**.
