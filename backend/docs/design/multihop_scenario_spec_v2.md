# Multi-Hop Conditional Scenario Generation — Spec v2
## Corrected from `chat_prompt_multihop_scenarios.md`
## Date: 2026-09-09

---

## 0. What this dataset is, and is not

**It is a POSITIVE CONTROL**: a synthetic set where conditional structure is planted by
construction, used to verify that the VLD instrument detects conditional structure when it
is present, and does not detect it when it is absent.

**It is NOT a measurement of VLD's value.** No result from this dataset may be quoted as
evidence that VLD helps on real decisions. That question is R1/R2/R4 on real cases
(`vld_graph_reasoning_architecture_v3.md` §8). Any deck slide or memo line derived from this
set carries the tag `PLANTED / POSITIVE CONTROL`.

Why the distinction matters: v1 of this prompt asked the generator to author
`single_pass_correct: false` and then required it to be false for ≥4/5 variations. Running
VLD on that set and observing that VLD wins measures generator compliance, not mechanism.
Everything below exists to remove that circularity.

---

## 1. Three changes to the v1 design

### 1.1 Single-pass is COMPUTED, not authored

The generator emits the alert, the tree, and the ground truth. It does **not** emit
`single_pass_action` or `single_pass_correct`. A separate scoring pass fills those in:

```
single_pass_action = argmin_a d(v_0, mu[category, a])      # real scorer, real centroids
single_pass_correct = (single_pass_action == ground_truth_action)
```

Instances where single-pass happens to be right **stay in the set** and are reported.
The observed single-pass accuracy on the set is a reported number, not a target.

Removed fields: `single_pass_action`, `single_pass_correct`, `why_single_pass_fails`
(the last becomes a computed diagnostic, not an author's assertion).

### 1.2 Every instance declares its branching kind

```
"branching_kind": "content_keyed" | "prerequisite" | "score_keyed"
```

- **content_keyed** — the evidence at hop t literally names the next read
  ("mismatch_type = price" -> check contract). A rule resolves it with rho = 1.
  Valuable, but this is the RULE COMPARATOR arm, not VLD's claim.
- **prerequisite** — reads must follow a fixed order because each read reveals the ADDRESS
  of the next (pointer-following, dependency chains). Multi-step traversal without scorer
  feedback resolves it. GraphRAG territory; real, but not VLD-specific.
- **score_keyed** — the branch is NOT legible in the evidence; only the scorer's
  intermediate state v_t against the centroids indicates which read is productive.
  **This is the only arm that tests VLD's distinctive claim.**

Results are reported separately per kind. If VLD's advantage appears only on
content_keyed instances, the correct conclusion is "invest in rule-based routing."

Target mix (the v1 template list is roughly 70% content_keyed as written):

| Kind | Share | Role |
|---|---:|---|
| score_keyed | >= 40% | treatment arm |
| content_keyed | ~35% | rule comparator |
| prerequisite | ~25% | traversal comparator |

### 1.3 rho is a swept parameter, not a constant

v1 plants rho = 1: the hop-1 evidence always points to the correct branch. That cannot
calibrate anything and cannot exercise the failure mode.

Each score_keyed instance carries:

```
"rho_planted": 0.30 | 0.50 | 0.70 | 0.90 | 1.00
```

`rho_planted` is the probability that the routing signal at hop 1 points to the correct
branch. At 0.30 the surface evidence points at the WRONG branch (the confidently-wrong
case). At 0.50 the signal is uninformative — VLD must not beat a coin flip there, and if
it does, the instrument is leaking.

**Acceptance test for the whole dataset (the thing that makes it a control rather than a
demo):** VLD's advantage over the budget-appropriate comparator must track
(rho_planted - 0.5) with the right sign, and must vanish within noise at rho = 0.50.
If it doesn't, the instrument is wrong and no other result from it counts.

---

## 2. Additional required fields

Beyond the v1 schema, every instance carries:

```json
{
  "branching_kind": "score_keyed",
  "rho_planted": 0.70,

  "available_branches": {
    "1": ["identity_path", "asset_path", "timing_path"],
    "2": ["campaign_db", "process_tree", "network_flow"]
  },
  "correct_branches": {
    "1": ["identity_path"],
    "2": ["campaign_db", "process_tree"]
  },

  "read_costs": {
    "identity_path": 1, "asset_path": 1, "timing_path": 1,
    "campaign_db": 3, "process_tree": 2, "network_flow": 2
  },
  "budget": 3,

  "misleading_branches": ["asset_path"],

  "surface_only_resolvable": false,
  "notes_for_analysis": "asset_path returns evidence that pulls v toward 'suppress'"
}
```

Field notes:

- **available_branches / correct_branches** — required for a random baseline. Without the
  denominator (how many branches were on offer) there is no chance-level to beat.
  `correct_branches` may hold more than one acceptable branch.
- **read_costs / budget** — v1 makes reads free, which means "read everything" weakly
  dominates and breadth wins by construction. The interesting regime is
  `budget < sum(cost of all branches)`. Set budget so that at least one branch must be
  skipped on >= 60% of instances.
- **misleading_branches** — at least one branch per template whose evidence pulls the
  vector toward the WRONG action. Without this, wrong-branch reads are harmless and
  adaptivity has nothing to buy.
- **surface_only_resolvable** — true for the deliberate flat controls (see §3).

### Criterion correction

v1's `hops_needed >= 2` does not guarantee conditionality: a fixed 3-hop chain is flat
from VLD's perspective. Replace with:

```
branching factor >= 2 at >= 1 hop, AND at least two distinct terminal actions
reachable from that hop
```

---

## 3. Required controls inside the dataset

The v1 set is all-treatment. Add, per copilot:

| Control | Count | Purpose |
|---|---:|---|
| **Flat instances** (`surface_only_resolvable: true`, 1 hop, no branching) | ~15% of set | VLD must NOT beat single-pass here. If it does, leakage. |
| **rho = 0.50 instances** | >= 10 per copilot | VLD must not beat chance. Instrument check. |
| **rho < 0.50 instances** | >= 10 per copilot | The confidently-wrong case. Tests the O-3 fallback detector: can the system tell it is in a low-rho case at inference time and fall back to single-pass? |
| **budget >= branches instances** | >= 10 per copilot | Breadth should match or beat VLD (Sim 2). If VLD still wins, the comparator is strawmanned. |

The "single-pass happens to be correct" variation from v1 rule 5 is kept, but it now
arises naturally from computing single-pass rather than being authored.

---

## 4. Comparator arms (all must be run on every instance)

v1 has no comparator besides single-pass. Minimum four arms:

1. **single_pass** — score v_0, emit. (current production)
2. **breadth / random-k** — read k branches chosen without scorer feedback, same budget.
3. **content_rule** — a frozen rule that routes on the evidence content, given the same
   first-read evidence and the same budget. *This is the honest comparator* — an
   evidence-informed VLD beating an alert-type-only rule proves nothing.
4. **vld** — score-conditioned routing.

Optional fifth: **prerequisite_traversal** (multi-hop, no scorer feedback) to separate
"iteration helps" from "score-conditioning helps."

Report per arm, per `branching_kind`, per `rho_planted` bucket. The headline number is
`accuracy(vld) - accuracy(content_rule)` on the **score_keyed** subset — not
`accuracy(vld) - accuracy(single_pass)` on everything.

---

## 5. Template list — reclassified

The v1 templates are kept, retagged. Corrections where v1's framing was wrong:

**SOC** — score_keyed: #1 (which vector is primary), #2 (insider vs compromised — same
indicators, opposite actions), #8 (misconfig vs active attack — same CloudTrail event),
#10 (shared service account vs lateral movement), #13 (automated vs hijacked service
account), #14 (returned employee vs compromised dormant account).
content_keyed: #4 (maintenance window says so), #6 (volume threshold), #9 (patch status),
#15 (device registration), #16 (honeypot — the asset IS the decoy), #18 (test environment
tag), #11 (destination is known or not).
prerequisite: #5 (privilege chain), #3 and #7 (temporal correlation — fixed sequence),
#17 (DNS tunneling: reputation -> volume -> destination), #19, #20.
#12 (time-of-day x geography) is content_keyed if a travel record exists, score_keyed if
not — split it into two templates.

**DataOps** — score_keyed: #3 (related or independent?), #5 (recurring vs novel), #7 (bad
data vs slow disk), #12 (spike vs drift), #14 (query vs pipeline — the "wrong
investigation direction" is exactly the score-keyed case).
prerequisite: #1, #2, #4, #6, #8, #10, #13, #15 (all dependency/lineage chains).
content_keyed: #9 (migration window), #11 (deploy record dated yesterday).

**S2P** — score_keyed: #5 (in-transit vs shortfall — receipt data looks identical),
#9 (retroactive adjustment pending vs genuine error), #4 (duplicate vs legitimate
resubmission).
prerequisite: #1 (amendment chain), #2 (split GR), #7 (BPO consumption), #10
(subcontractor chain).
content_keyed: #6, #8, #11, #12, #3.

**Trading** — score_keyed: #5 (sector-wide vs stock-specific), #9 (momentum vs
mean-reversion), #4 (rotation vs panic), #1 (has the thesis changed, or is the trade
wrong?).
content_keyed: #3 (earnings date is a fact), #6 (tax lots), #8 (ex-date).
prerequisite: #2, #7, #10.
NOTE: Trading and Purchasing are flagged NOT demo-ready in the current program
(no entity wiring, low m_topological). Generate them, but hold them out of any
headline analysis until the wiring lands.

**Purchasing** — score_keyed: #3 (shelf-life vs over-ordering — same waste number),
#8 (premium shipping vs wait), #2 (switch cost vs quality history).
content_keyed: #1, #4, #6, #9.
prerequisite: #5, #7, #10.

---

## 6. Volume

The v1 target (~335 instances, 67 templates x 5) is fine as a *ceiling* but wrong as a
starting point. Generate in two stages:

**Stage 1 — 40 instances, SOC only, hand-reviewed.** 8 templates x 5 variations, covering
all three branching kinds and the full rho sweep. Run the four arms. Check the acceptance
test in §1.3. If the instrument fails the rho = 0.50 check, the remaining 295 instances
are wasted work.

**Stage 2 — remainder, after Stage 1 passes.** Generate per copilot, in the §1.2 mix,
with the §3 controls.

Do not generate 335 instances before the instrument has passed its own calibration.

---

## 7. Deliverables

Per copilot:
- `{copilot}_multihop_scenarios.json` — array of instances, WITHOUT single-pass fields
- `{copilot}_multihop_schema_extensions.json` — new node/edge types
- `{copilot}_singlepass_scored.json` — output of the scoring pass (§1.1), joined by
  `scenario_id`

Plus, once:
- `multihop_analysis.md` — per-arm accuracy, split by branching_kind and rho bucket,
  with the rho = 0.50 and flat-instance control results stated first.

Every file header carries: `PLANTED SYNTHETIC — POSITIVE CONTROL — NOT A MEASUREMENT OF
VLD VALUE ON REAL DECISIONS.`

---

## 8. One-paragraph summary for whoever runs the generator

Generate scenarios with planted conditional structure, a declared branching kind, a swept
routing-signal informativeness (rho), real read costs against a binding budget, and at
least one misleading branch per template. Do not author whether single-pass fails — the
scorer decides that. Include flat controls and rho = 0.5 controls so the dataset can prove
it discriminates. Run four arms, and report the score-keyed subset against the
content-rule comparator as the headline. Stage 1 is 40 SOC instances; everything else
waits on the calibration check.
