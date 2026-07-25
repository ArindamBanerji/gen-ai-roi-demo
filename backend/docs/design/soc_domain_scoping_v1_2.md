# SOC shared-graph domain-scoping retrofit v1.2

Status: authoritative implementation contract
Date: 2026-07-25
Supersedes: soc_domain_scoping_v1_1.md

## 1. Executive summary

SOC uses a direct AGEClient-compatible query layer, not the SDK GraphStore
factory (`gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py:486-540`). It was
safe only while soc_graph contained SOC data. The graph now contains five
domains, so every Decision and Outcome read, write, count, aggregate, and
mutation must be SOC-scoped.

The live July 25, 2026 census is authoritative:

| Domain | Decisions | Verified | Correct |
|---|---:|---:|---:|
| NULL | 0 | 0 | 0 |
| soc | 4,882 | 4,862 | 3,712 |
| trading | 1,299 | - | - |
| purchasing | 1,042 | - | - |
| dataops | 721 | - | - |
| s2p | 25,104 | - | - |
| Total | 33,048 | - | - |

The sum is 33,048, equal to the graph total. Therefore **V_soc = 4,862**
and correct SOC decisions equal 3,712. The parent PF-1 values (4,899 and
3,749) came from a different snapshot. The historical 37 discrepancy is
consistent with the former split of 37 tagged verified rows plus 4,862 NULL
verified rows; the current graph has zero NULL-domain rows and all 4,862 are
now explicitly tagged.

No compatibility NULL branch or domain backfill is required. The helper in
section 3 emits exact `d.domain = 'soc'` matching only.

## 2. Inventory and classification

The v1 inventory audited 89 Decision MATCH touchpoints in the listed files;
50 require a predicate or mutation change. The implementation target remains
these 13 files:

`db/neo4j.py`, `main.py`, `routers/soc.py`, `routers/evolution.py`,
`routers/metrics.py`, `services/iks.py`, `services/executive_narrative.py`,
`services/learning_health.py`, `services/state_manager.py`,
`services/graph_explorer.py`, `services/variant_generator.py`,
`services/timestamp_backfill.py`, and `state/graph_snapshot.py`.

Every UNSCOPED entry must call `soc_decision_where()` from section 3.

### `app/db/neo4j.py`

- Decision CREATE: `:209-225`, UNSCOPED write; add `domain: 'soc'`.
- ID-only playbook/evolution matches: `:231-235`, `:259-275`, PARTIALLY_SCOPED;
  add the exact helper predicate.
- V_soc D2 query: `:311-318`, currently scoped but must use the helper.
- Correct count: `:334-338`, scoped in the Neo4j class but must use helper.
- Category/outcome aggregates: `:354-385`, UNSCOPED.
- Referral Decision counts: `:441-474`, UNSCOPED.
- AGE runtime correct-count shim: `:511-523`, UNSCOPED.

### `app/main.py`

- Bootstrap correct/verified queries: `:229-235`, UNSCOPED.
- Learning-state total sync: `:321-323`, UNSCOPED.
- Verified sync: `:340-344`, source is scoped and authoritative.
- Whole-graph node health count at `:202-205` is infrastructure telemetry,
  not an SOC Decision metric.

### `routers/soc.py`

Decision counts/confidence at `:775-812`, analytics at `:914-925`, verified,
category, and detail queries at `:1010-1181`, and tab queries at `:2015`,
`:2748`, `:2847`, `:3166-3185`, and `:3245-3285` are unscoped or only
ID/category scoped. Add the helper to each Decision alias `d`.

### `routers/evolution.py`

Totals and Decision CREATE/SET at `:65`, `:221-266`, `:676`, and `:919` need
the helper and an explicit SOC domain property on CREATE.

### `routers/metrics.py`

Decision-to-alert, totals, correctness, timestamps, and false-positive queries
at `:208-277`, `:479`, `:534`, `:584-605`, and `:699-872` need the helper.

### Services and state

- IKS components at `services/iks.py:211-289`.
- Executive narrative at `services/executive_narrative.py:191-200`, `:323`,
  `:360`, and `:409-523`.
- Learning health at `services/learning_health.py:481-492`, `:839`, and
  `:893-943`.
- State-manager safety checks and mutations at `services/state_manager.py:80-124`.
- Explorer at `services/graph_explorer.py:63-70`, `:139-293`.
- Variant aggregates at `services/variant_generator.py:229-231`, `:414-426`,
  `:673-674`.
- Timestamp selection/mutation at `services/timestamp_backfill.py:27`,
  `:47-48`, `:65-66`.
- GraphSnapshot source calls at `state/graph_snapshot.py:61-89`; keep the
  consumer API and fix its source methods.

## 3. Exact predicate-emitting helper

Add one helper in `app/db/neo4j.py` and import it wherever raw Cypher is built:

```python
def soc_decision_where(alias: str = "d", active_only: bool = True) -> str:
    parts = [f"{alias}.domain = 'soc'"]
    if active_only:
        parts.append(f"({alias}.archived IS NULL OR {alias}.archived <> true)")
    return " AND ".join(parts)
```

This is exact matching only. There is no `IS NULL` compatibility parameter and
no transitional mode: the census proved `NULL = 0`. All 50 retrofit sites
call this helper. No site may retype the domain or archived predicate. For a
query with an existing filter, append `AND ` plus the helper result. For an
OPTIONAL MATCH, place the helper in the correct `WHERE` without changing row
cardinality.

Active analytics use `active_only=True`. History queries use
`active_only=False` and append `d.archived = true` explicitly. Whole-graph
node/relationship counts remain infrastructure telemetry and must not feed an
SOC metric.

## 4. Write-path contract

`create_decision_trace` must add `domain: 'soc'` to the Decision property map
(`app/db/neo4j.py:209-225`). Its playbook match and every follow-up edge must
call the helper (`:231-235`).

The evolution Decision CREATE must add the same property and its MATCH/SET
must call the helper (`app/routers/evolution.py:221-266`). Every other
Decision/Outcome CREATE, SET, REMOVE, or DELETE found by the inventory audit
must use the helper. New SOC writes must never be domainless.

## 5. Census result: backfill unnecessary

The live census found zero NULL-domain Decisions, zero NULL verified rows, and
zero NULL correct rows. All 4,882 SOC Decisions already have
`domain='soc'`. Consequently this version owns no backfill mutation and no
backfill Cypher is permitted.

The parent D8 backfill is dispositioned as **not applicable for this live
baseline**. Before any future migration run, repeat the NULL-domain census. If
it ever becomes nonzero, stop all copilot migration and create a separately
approved, ownership-proven backfill plan before writing to soc_graph.

Required evidence artifact:

```cypher
MATCH (d:Decision)
RETURN coalesce(d.domain, '<NULL>') AS domain,
       count(d) AS decisions,
       count(CASE WHEN d.status IN ['confirmed','overridden']
                  OR (d.status IS NULL AND d.outcome IS NOT NULL)
                  THEN 1 END) AS verified,
       count(CASE WHEN d.correct = true OR d.outcome = 'correct'
                  THEN 1 END) AS correct
ORDER BY domain
```

The output must match the census table before implementation starts.

## 6. Startup and snapshot fixes

Fix source queries, not consumers:

- `main.py:229-235` and `:321-323` call `soc_decision_where()`.
- `neo4j.py:311-385` uses the helper for V_soc, correct, category, and outcome
  aggregates.
- `GraphSnapshot.from_graph()` remains unchanged while its source methods are
  corrected (`state/graph_snapshot.py:61-89`).

The direct SOC V query is `app/db/neo4j.py:311-318`; with exact domain scope it
must return 4,862. The SDK adapter is a separate path: it forwards
`count_verified` at `ci-platform/ci_platform/graph/age_sdk_adapter.py:288-295`
to `AGEGraphStore.count_verified` at `ci-platform/ci_platform/graph/age_graph_store.py:1598-1613`.
The parent-plan observation that this adapter path returns zero for SOC remains
a separate adapter bug. SOC's authoritative V_soc comes from direct Cypher,
not the adapter.

## 7. Baseline reconstruction and verification

Foreign data is already present, so reconstruct the baseline with exact
domain-scoped queries rather than an unscoped live total:

1. Capture the census artifact from section 5.
2. Record `V_soc = 4,862`, `correct_soc = 3,712`, `soc_decisions = 4,882`,
   and the PF-1 SOC category histogram.
3. Run every changed endpoint and aggregate against `d.domain = 'soc'` and
   compare with this artifact.
4. After deployment, V_soc must remain 4,862 unless a real SOC verification
   event occurs. Foreign Decision IDs must never appear in SOC results.
5. Seed one Decision for each other domain and assert that SOC counts,
   category aggregates, explorer results, snapshots, and mutations exclude
   those IDs.

## 8. Implementation order and AGE index discovery

1. Record and sign the live census artifact.
2. Add the exact helper and replace every manual predicate.
3. Fix Decision CREATE and SET paths.
4. Fix `neo4j.py` count/aggregate/rule methods and startup queries.
5. Fix routers (`soc.py`, `evolution.py`, `metrics.py`).
6. Fix services and state sources (IKS, narrative, learning health, state
   manager, explorer, variant generator, timestamp backfill).
7. Run baseline and cross-domain regression tests.
8. Discover the physical AGE label relation before creating an index: inspect
   the deployed PostgreSQL catalog and AGE label metadata, then run `EXPLAIN`
   on the exact scoped queries. Do not assume `"Decision"` is the relation
   name. Create the PostgreSQL index on the discovered relation and `domain`
   column using the deployed AGE-compatible DDL. Re-run plans and latency
   benchmarks before sign-off.

## 9. Risks and mitigations

- Manual predicates across 50 sites can drift. Mitigation: all sites call the
  helper; code review rejects literal SOC/archived predicates outside it.
- A future domainless writer would be a leak only if a query uses NULL as SOC;
  this design uses exact matching and therefore fails closed.
- The parent D8 operation is unnecessary for the current census. Any future
  NULL rows require a new ownership review before mutation.
- Direct AGE and SDK adapter V counts differ in the observed parent bug.
  Mitigation: SOC gates use direct Cypher until adapter parity is proven.
- Optional-match placement can change cardinality. Mitigation: fixture tests
  with one SOC and one foreign Decision for every changed query.
- AGE physical relation names vary. Mitigation: catalog discovery is a
  required pre-index step.

## 10. Reading log

- `gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py:1-540`
- `gen-ai-roi-demo-v4-v50/backend/app/main.py:1-480`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/soc.py:1-3755`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/evolution.py:1-950`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/metrics.py:1-900`
- `gen-ai-roi-demo-v4-v50/backend/app/services/iks.py:1-370`
- `gen-ai-roi-demo-v4-v50/backend/app/services/executive_narrative.py:1-540`
- `gen-ai-roi-demo-v4-v50/backend/app/services/learning_health.py:1-950`
- `gen-ai-roi-demo-v4-v50/backend/app/services/state_manager.py:1-220`
- `gen-ai-roi-demo-v4-v50/backend/app/services/graph_explorer.py:1-310`
- `gen-ai-roi-demo-v4-v50/backend/app/services/variant_generator.py:1-700`
- `gen-ai-roi-demo-v4-v50/backend/app/services/timestamp_backfill.py:1-90`
- `gen-ai-roi-demo-v4-v50/backend/app/state/graph_snapshot.py:1-190`
- `ci-platform/ci_platform/graph/age_sdk_adapter.py:268-298`
- `ci-platform/ci_platform/graph/age_graph_store.py:1598-1613`

