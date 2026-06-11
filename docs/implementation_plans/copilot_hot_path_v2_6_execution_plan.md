# Copilot Decision Hot-Path Architecture v2.6 Execution Plan

**Date:** 2026-06-09  
**Status:** READY_FOR_REVIEW  
**Scope:** Implementation planning only; no product code changes in this document.  
**Design basis:**

- `copilot-sdk/docs/copilot_analyze_route_architecture_v2_6.md`
- `copilot-sdk/docs/design/dk_runtime_execution_plan_v6_8.md`
- `copilot-sdk/docs/design/math_synopsis_v18.md`
- `copilot-sdk/docs/design/soc_campaign_identity_architecture_v1_3.md`
- `copilot-sdk/docs/design/trading_copilot_product_definition_v1.md`
- `copilot-sdk/docs/design/purchasing_copilot_pd_v1_3.md`
- `copilot-sdk/docs/design/dataops_copilot_design_v1_6.md`
- `copilot-sdk/docs/design/s2p_copilot_unified_v1_3.md`

## Operating Rules

- Use Windows PowerShell.
- Activate the existing Python environment with `act.ps1`; do not create a new virtual environment.
- Do not install packages automatically. If Package 1 needs `psycopg_pool` or an equivalent, implementation prompts must ask for approval or provide a no-pool fallback.
- Do not use git.
- Do not run long proofs from Codex-owned backend processes. Use the T1/T2 lifecycle:
  - T1: user manually starts/stops backend with `demo.py` or direct uvicorn.
  - T2: Codex verifies contract/health and runs validation/proof only.
- Every implementation prompt must carry the relevant design docs forward, not rely on chat memory.
- No DK, L5, conservation, campaign semantic, frontend, or forced SDK AGE-migration redesign is in scope.

## Validated Gates

### Design v2.6 Final Re-Verification

- P1 drift: None
- P2 drift: None
- Executability gate: ready for Step 0 and C9B sequencing

### Step 0 AGE Connection-Model Spike

- Fresh AGE read: approximately 83.16 ms/query
- Warm reused AGE read: approximately 1.10 ms/query
- Connection tax: approximately 82.06 ms
- Rolled-back single write: approximately 13.04 ms
- Branch: `cache_model_viable`
- Rollback clean: `SpikeDummy` count 0 before and 0 after
- Caveat: `psycopg_pool` was unavailable, so this measured warm connection reuse, not the exact future pool package.

### Fresh C9B/SOC Proof Baseline

- Graph: `soc_graph_c9b_pre_hotpath_2`
- Prefix: `C9B-PRE-HOTPATH2`
- Verdict: `EXTERNAL_DIAGNOSTIC_F_PASS`
- Proof passed: true
- Valid outcomes: 250
- Decisions / verified / outcome_present: 250 / 250 / 250
- L5Centroid / SHAPED_BY / L5DKWeight: 1 / 1 / 1
- DK Welford rows: 1
- max_n_decisions_used: 250
- avg_analyze_seconds: 1.767
- max_analyze_seconds: 3.334
- avg_outcome_seconds: 1.492
- max_outcome_seconds: 4.517

## Performance Interpretation

The connection-tax result is the headline: almost all fresh-read latency was connection/session setup, not keyed query execution. This validates the low-blast-radius first move: pool or reuse AGE connections before refactoring the entire route into `copilot_core`.

Do not publish the v2.6 projected target numbers as committed latency claims yet. The Step 0 write result was a single rolled-back CREATE statement; it did not measure committed Phase-3 transaction cost, WAL/fsync, or pilot-like storage.

Pooling is the first bankable runtime package after Package 0 evidence. Package 0 is not a product optimization; it is the pre-build measurement that prevents the plan from turning a rolled-back write datapoint into a committed latency claim.

## Execution Gates

### Gate 1: Evidence Gate

Complete committed Phase-3 transaction measurement on a scratch graph. Do not use proof graphs. Distinguish measured, projected, and buyer-facing numbers.

### Gate 2: Pooling Gate

Implement pooled AGE connection reuse behind a compatibility fallback. Preserve graph semantics. Demonstrate connection-tax win with targeted perf checks and no C9B path regression.

### Gate 3: Counter/Cache Gate

Materialized counters and EntityCache must pass correctness, reconciliation, invalidation, and flat-latency checks across 25/250/1000 decision traces.

### Gate 4: SOC Adoption Gate

Adopt `DecisionPipeline` through `USE_COPILOT_CORE` side-by-side parity. The old path remains available until action, confidence, factors, and decision-critical metadata parity are proven.

## Measurement Plan

### Committed Phase-3 Transaction Measurement

Add a diagnostic-only spike against a scratch graph such as `soc_graph_phase3_commit_spike_1`. Measure a durable transaction:

1. `BEGIN`
2. Create synthetic Decision
3. Create synthetic audit node/edge or closest existing audit write shape
4. Set or increment a synthetic materialized counter
5. `COMMIT`

Also measure a rollback comparison with the same shape. Report p50, p95, max, and warnings that WSL2 dev-box fsync can differ from pilot storage.

The committed shape must be close enough to Phase 3 to be useful, but still isolated from product semantics:

- Use synthetic labels/properties or a clearly prefixed scratch-only Decision/audit/counter shape.
- Do not touch proof graphs or production-like graph names.
- Do not weaken later Package 2 counter design by treating the synthetic counter as the final schema.
- Verify committed rows exist before cleanup, and verify cleanup or graph isolation afterward.

### Avoiding Proof Graph Pollution

- Never write the committed spike to `soc_graph_diag_f8`, `soc_graph_c9b_pre_hotpath_2`, or any C9B proof graph.
- Use a scratch graph and prefix all synthetic data.
- Verify cleanup or explicitly leave the scratch graph documented as scratch-only.
- If graph drop is unavailable or unsafe, leave the graph isolated and record exact scratch graph name, prefix, run id, and row counts.

### Number Classification

- Measured: Step 0 spike, C9B proof, committed Phase-3 spike, and 25/250/1000 traces.
- Projected: v2.6 target waterfall until implemented and measured.
- Buyer-facing: only after committed write measurement and pilot-like storage confirmation.

## Recommended Staging

### Package 0: Durable Phase-3 Measurement

**Goal:** Measure real committed write cost before publishing target latency claims.  
**Why now:** Opus feedback blocks extrapolating from rolled-back single write.  
**Likely files touched:** `gen-ai-roi-demo-v4-v50/scripts/diagnostics/perf/*`, reports under `docs/implementation_plans/perf/`.  
**Cross-copilot impact:** Measurement pattern reusable; no runtime assumption baked in.  
**Tests:** `--help`, `py_compile`, optional scratch validation.  
**Performance check:** committed Phase-3 p50/p95/max.  
**Blast radius:** diagnostic-only, scratch graph.  
**Rollback:** delete or ignore script/report; no product path touched.

### Package 1: Pooled AGE Adapter

**Goal:** Remove per-query connection/session tax while preserving AGE semantics.  
**Why here:** First bankable runtime win after Package 0 evidence; lowest blast radius and highest-confidence improvement.  
**Likely files touched:** `ci-platform/ci_platform/graph/age_client.py`, possibly new pooled adapter module, ci-platform tests.  
**Cross-copilot impact:** SOC uses now; SDK copilots adopt at AGE migration.  
**Tests:** connection lifecycle, fallback without `psycopg_pool`, transaction rollback/commit, concurrency, no query semantic changes.  
**Performance check:** fresh vs pooled point reads; SOC 25-outcome trace.  
**Blast radius:** adapter layer only.  
**Rollback:** env flag or constructor option to use current per-query client.

### Package 2: Materialized CounterStore

**Goal:** Replace O(N) sequence/cross-category scans with AGE-authoritative O(1) counter reads.  
**Why here:** Eliminates remaining growth source after pooling.  
**Likely files touched:** new `ci_platform/copilot_core/counters.py`, AGE helper tests, SOC counter adapter tests.  
**Cross-copilot impact:** shared CounterStore API; per-copilot CounterDef declarations.  
**Tests:** distinct vs total counters, transactional increment, reconciliation, multi-worker coherence strategy.  
**Performance check:** 25 vs 250 average analyze <= 1.2x for counter-dependent path.  
**Blast radius:** additive read model; raw Decision graph remains source of truth.  
**Rollback:** read old scan path if feature flag disabled; counter nodes ignored.

Counter implementation guardrails:

- Counters are never memory-authoritative and are not stored in `EntityCache`.
- Distinct counters must use AGE-compatible MATCH-then-CREATE edges, not MERGE.
- Counter reads must be keyed O(1) reads from materialized nodes.
- Phase-3 increments must be transactional with Decision and audit persistence once Package 5 adopts the pipeline.

### Package 3: EntityCache

**Goal:** Read-through bounded LRU for recurring context, never subjects or counters.  
**Why here:** Benefits increase after pooled fallback and counter correctness are stable.  
**Likely files touched:** `ci_platform/copilot_core/cache.py`, DomainProfile cache declarations, ingestion invalidation call sites.  
**Cross-copilot impact:** backend-agnostic pattern; each copilot declares cacheable context.  
**Tests:** cold miss, hit, eviction, invalidation on entity writes, subject/counter non-cache.  
**Performance check:** cache-hit context read near-zero; cold miss pooled read acceptable.  
**Blast radius:** stale-data risk if invalidation is incomplete.  
**Rollback:** bypass cache to pooled AGE reads.

### Package 4: BackgroundTaskManager

**Goal:** Safe retained fire-and-forget Phase-4 enrichment only.  
**Why here:** After Phase 1-3 semantics are stable, move only non-critical work.  
**Likely files touched:** `ci_platform/copilot_core/tasks.py`, later SOC campaign/RL/telemetry call sites.  
**Cross-copilot impact:** shared task manager; each domain chooses Phase-4 work.  
**Tests:** retained task set, done-callback logging, no decision-critical gate deferral.  
**Performance check:** response returns before enrichment completes.  
**Blast radius:** async failure observability.  
**Rollback:** run enrichment synchronously or disable Phase-4 tasks.

### Package 5: DecisionPipeline / DomainProfile and SOC Adoption

**Goal:** Framework-first four-phase pipeline with SOC side-by-side parity.  
**Why here:** Largest blast radius; should wait until pool, counters, and cache are proven.  
**Likely files touched:** new `ci_platform/copilot_core/pipeline.py`, `domain_profile.py`, SOC adapter, `backend/app/routers/triage.py`.  
**Cross-copilot impact:** shared interfaces now; SDK route adoption deferred until AGE migration unless backend-agnostic tests are safe.  
**Tests:** response parity, action/confidence/factors/decision-critical metadata, C9B proof, 25/250/1000 perf.  
**Performance check:** flat latency and no proof regression.  
**Blast radius:** high, route orchestration.  
**Rollback:** `USE_COPILOT_CORE=false` old route remains.

## Shared copilot_core Boundaries

Belongs in shared `ci-platform` layer:

- Pooled AGE adapter abstractions
- `CounterStore`
- `EntityCache`
- `BackgroundTaskManager`
- `DecisionPipeline`
- `DomainProfile` protocol/interface
- Shared test fakes for graph/cache/counters/tasks

Remains domain-specific:

- Factor definitions
- Entity-key derivation and fallback
- Counter definitions and category/action semantics
- Scorer selection
- Decision-critical gate list and gate behavior
- Enrichment tasks
- Route response schema adaptation

Shared code must not assume SOC alert fields, SOC categories, SOC campaign behavior, or AGE availability for SDK copilots before their migration.

## DomainProfile Expectations

### SOC

- Reads Alert subject.
- Derives recurring context from source/entity/user/asset.
- Supplies SOC factors, categories, actions, referral gates, RL exploration, and enrichment hooks.
- First adopter for pooled AGE, counters, cache, and side-by-side `DecisionPipeline`.

### Trading

- Current backend remains unchanged until AGE migration.
- Future profile should cache recurring instrument/account/portfolio context, not one-shot score request subjects.

### Purchasing

- Current backend remains unchanged until AGE migration.
- Future profile should cache vendor/supplier/procurement context, not transient request subjects.

### DataOps

- Current backend remains unchanged until AGE migration.
- Future profile must enumerate ERP/Celonis ingestion invalidation call sites before cache adoption.

### S2P

- Current backend reality remains respected.
- Vendor context is the likely recurring cache target; invoices remain read-once subjects.

## Pooled AGE Client Strategy

- Prefer `psycopg_pool` or an explicitly approved equivalent.
- If dependency is unavailable, provide a safe fallback to current per-query connection behavior.
- Default pool sizing follows v2.6: `min_size=2`, `max_size=8` per copilot unless deployment constraints require adjustment.
- Add an explicit transaction API for Phase-3 writes.
- Do not alter Cypher semantics, graph labels, or write ordering.
- Pool errors must surface as real failures, not silent semantic changes.

## CounterStore Strategy

- AGE-authoritative; no memory counter cache.
- O(1) point reads from materialized entity nodes.
- Increment inside Phase-3 transaction with Decision and audit persistence.
- Distinct counters use AGE-compatible MATCH-then-CREATE edge pattern, not MERGE.
- Reconciliation is required: recount raw Decision data, compare, correct, stamp `last_reconciled`.
- Multi-worker coherence is preserved by reading counters from AGE, not process memory.

## EntityCache Strategy

- Read-through bounded LRU.
- Cold miss falls back to pooled AGE read.
- Subject is not cached.
- Counters are not cached.
- Each copilot declares cacheable context and invalidation call sites.
- Missing invalidation is a correctness bug; Package 3 must include a call-site discovery checklist.

## BackgroundTaskManager Strategy

- Retain task set to avoid task garbage-collection footgun.
- Done-callback logs failures at WARNING or higher.
- Only Phase-4 enrichment/telemetry work uses it.
- Low-confidence gate, referral veto, RL exploration, and composite auto-approval metadata remain synchronous as specified by v2.6.

## SOC Adoption Strategy

- Add `USE_COPILOT_CORE` feature flag.
- Run old and new paths side-by-side before serving new response.
- Parity fields: action, confidence, factors, and decision-critical metadata.
- Old route remains available until parity over 250+ decisions and C9B proof are complete.
- No DK/L5/conservation/campaign semantic redesign during adoption.

## Cross-Copilot Adoption Strategy

- SOC is first measured AGE adopter.
- Trading, Purchasing, DataOps, and S2P remain on current backends until AGE migration unless backend-agnostic pieces are safe now.
- Shared artifacts now: interfaces, tests, fakes, docs, task/cache/counter contracts.
- Deferred artifacts: per-domain AGE CounterDefs, graph-backed context loaders, route replacement.

| Copilot | Shared now | Deferred to AGE migration or domain pass |
|---|---|---|
| SOC | Pooling, counters, cache, task manager, DomainProfile, side-by-side pipeline adoption | None for the measured hot path, except broader v6 campaign/scorer integration |
| Trading | DomainProfile contract review, fake graph tests, shared pipeline/cache/task interfaces | AGE pooling, AGE CounterDefs, graph-backed loaders, route replacement |
| Purchasing | DomainProfile contract review, fake graph tests, shared pipeline/cache/task interfaces | AGE pooling, AGE CounterDefs, graph-backed loaders, route replacement |
| DataOps | DomainProfile contract review, invalidation checklist shape, fake graph tests | ERP/Celonis-specific invalidation wiring, AGE pooling/counters/loaders, route replacement |
| S2P | DomainProfile contract review, supplier-context cache design notes, fake graph tests | AGE backend adoption details, supplier/vendor graph loaders, route replacement |

## Test Strategy

- Unit tests for pool lifecycle, cache, counters, task manager, and DomainProfile contract.
- Fake graph tests for query sequencing and transaction boundaries.
- AGE integration tests for pooled reads, committed writes, distinct counters, and reconciliation.
- Parity tests comparing old SOC route and new pipeline.
- Performance tests at 25/250/1000 decisions.
- Multi-worker counter coherence strategy, even if full two-worker harness is staged.
- Runner/proof infrastructure tests for seed visibility and backend contract handling.
- Rollback tests proving `USE_COPILOT_CORE=false` returns to the old SOC path and counter/cache bypasses read from the authoritative graph.
- Cross-copilot contract tests proving shared `copilot_core` interfaces do not require SOC alert fields, SOC categories, or AGE-only objects.
- Storage-sensitive performance notes: dev WSL2 measurements are engineering evidence, not buyer-facing latency commitments until confirmed on pilot-like storage.

## Runner and Test Infrastructure Simplification

- Use T1/T2 lifecycle:
  - T1: user manually starts/stops backend with `demo.py` or direct uvicorn.
  - T2: Codex verifies contract/health and runs proof/validation.
- Do not make future Codex prompts own backend startup unless explicitly requested.
- Keep seed visibility barrier.
- Keep explicit backend contract checks.
- Add faster proof/perf scripts only where correctness is not weakened.
- Prefer short diagnostic/perf runs during implementation packages; reserve fresh 250-outcome C9B proof for meaningful gates.
- Keep backend contract validation explicit: graph name, port, redacted DSN, and health via `http://127.0.0.1`.

## Blast Radius and Rollback

- Feature flag fallback for SOC route adoption.
- Counter nodes/edges are additive read models.
- No irreversible schema change in early packages.
- No DK/L5/conservation redesign.
- No campaign semantic redesign.
- No frontend dependency.
- Each package has a bypass or old-path fallback.

## Risks

### P1

- Route parity drift when Package 5 adopts `DecisionPipeline`.
- Counter transaction semantics wrong, causing referral decisions to change.
- Missing EntityCache invalidation returning stale decision-critical context.

### P2

- `psycopg_pool` dependency unavailable or pool behavior differs from warm-connection spike.
- Committed write latency higher than rolled-back Step 0 due to WAL/fsync.
- Multi-worker counter coherence test harness is non-trivial.

### P3

- v2.6 authority references still mention v6.9/MAP v5.44 while in-repo context uses v6.8.
- SDK copilot adoption timing may need per-domain backend audits.
- Buyer-facing latency claims need pilot-like storage reconfirmation.

## First Implementation Prompt Draft

```text
/model gpt-5.3
Echo the current model name in the first line of output.

TASK: Implement Package 0 committed Phase-3 SOC AGE transaction measurement
TASK TYPE: Diagnostic measurement tooling only. NO product behavior changes.

ENVIRONMENT:
- This is Windows PowerShell.
- Run `act.ps1` before Python validation or measurement commands.
- Do not create a new virtual environment.
- Do not install packages automatically.

CONTEXT:
v2.6 passed final verification, Step 0 connection-tax spike passed, and C9B pre-hotpath proof passed on soc_graph_c9b_pre_hotpath_2. Opus feedback requires measuring committed durable Phase-3 write cost before publishing target latency claims.

DESIGN DOCS TO READ:
- copilot-sdk/docs/copilot_analyze_route_architecture_v2_6.md
- copilot-sdk/docs/design/dk_runtime_execution_plan_v6_8.md
- copilot-sdk/docs/design/math_synopsis_v18.md
- copilot-sdk/docs/design/soc_campaign_identity_architecture_v1_3.md

GLOBAL RULES:
- Do NOT use git.
- Do NOT change product routes, scorer, DK, L5, conservation, campaign semantics, graph-store semantics, or frontend.
- Do NOT run proof.
- Do NOT seed proof graphs.
- Preserve Network Split Rule: AGE DSN uses localhost; HTTP, if needed, uses 127.0.0.1.
- Use scratch graph only, e.g. soc_graph_phase3_commit_spike_1.
- Diagnostic script only.

IMPLEMENT:
- scripts/diagnostics/perf/soc_perf_03_phase3_commit_spike.py
- README/update only if needed under scripts/diagnostics/perf/

SCRIPT REQUIREMENTS:
- CLI: --graph-name default soc_graph_phase3_commit_spike_1, --graph-dsn default localhost DSN, --reps default 10, --prefix default PHASE3-SPIKE, --json-output optional, --md-output optional.
- Enforce Rule #40.
- Ensure scratch graph exists.
- Measure:
  1. fresh connection SELECT/RETURN baseline if useful
  2. warm reused connection baseline
  3. committed transaction: BEGIN -> CREATE synthetic Decision -> CREATE synthetic audit node/edge or closest existing audit write shape -> SET/increment synthetic materialized counter node -> COMMIT
  4. rollback comparison with same shape
- Do not write to proof graphs.
- Mark all nodes with prefix/run_id so scratch cleanup/readback is explicit.
- Before cleanup, verify committed rows were durable and report counts.
- After cleanup, verify zero remaining spike rows, or clearly document scratch graph isolation if graph cleanup is intentionally skipped.
- Report p50/p95/max and warnings that dev WSL2 fsync may differ from pilot storage.
- Write JSON/MD under docs/implementation_plans/perf/.
- Do not claim buyer-facing latency targets.

VALIDATION:
- python .\scripts\diagnostics\perf\soc_perf_03_phase3_commit_spike.py --help
- python -m py_compile .\scripts\diagnostics\perf\soc_perf_03_phase3_commit_spike.py
- Run the spike only against scratch graph if explicitly included in this prompt's validation section; do not run C9B or backend.

FINAL OUTPUT:
MODEL:
FILES_CHANGED:
MEASUREMENT_SUMMARY:
VALIDATION_RUN:
REPORTS:
NO_PRODUCT_CODE_CHANGED:
NEXT_GATE:
```

## Do Not Implement Yet

This document is the execution plan only. No product code changes are part of this plan-writing step.
