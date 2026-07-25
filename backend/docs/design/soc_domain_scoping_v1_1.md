# SOC shared-graph domain-scoping retrofit v1.1

Status: authoritative implementation contract
Date: 2026-07-25
Supersedes: soc_domain_scoping_v1.md

## 1. Executive summary

SOC uses a direct AGEClient-compatible query layer, not the SDK GraphStore
factory (`gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py:486-540`). It was
safe only while soc_graph contained SOC data. The graph now contains five
domains, so every Decision and Outcome read, write, count, aggregate, and
mutation must be SOC-scoped.

The locked SOC verified baseline is **V_soc = 4,899**, not 4,862. The parent
PF-6 census found 1,139 Decisions already tagged `domain='soc'` (37 verified)
and 5,114 with `domain IS NULL` (4,862 verified). The compatibility predicate
used by the current query includes both populations:
`(d.domain = 'soc' OR d.domain IS NULL)`. Therefore its result is 4,862 + 37
= 4,899. The 4,862 number is the NULL-only subpopulation and must not be used
as the SOC gate.

This document owns the SOC domain backfill, makes the parent plan's D8 depend
on it, and requires the backfill before any other copilot migrates. Predicate
emission is centralized in one helper. After the backfill proves that no
legitimate NULL-domain rows remain, the helper switches to exact
`d.domain = 'soc'`; the transitional NULL branch is not permanent.

## 2. Inventory

The v1 inventory audited 89 Decision MATCH touchpoints in the listed files;
50 require a predicate or mutation change. The implementation target remains
those same 13 files:

`db/neo4j.py`, `main.py`, `routers/soc.py`, `routers/evolution.py`,
`routers/metrics.py`, `services/iks.py`, `services/executive_narrative.py`,
`services/learning_health.py`, `services/state_manager.py`,
`services/graph_explorer.py`, `services/variant_generator.py`,
`services/timestamp_backfill.py`, and `state/graph_snapshot.py`.

The complete line inventory is retained from v1. Key classes are below; every
UNSCOPED entry must call `soc_decision_where()` from section 3 rather than
hand-editing a predicate.

### `app/db/neo4j.py`

- `CREATE (d:Decision {...})`: `:209-225`, UNSCOPED write; add domain.
- ID-only playbook/evolution matches: `:231-235`, `:259-275`, PARTIALLY_SCOPED;
  add the helper predicate.
- V_soc D2 query: `:311-318`, SCOPED and active.
- Correct count: `:334-338`, SCOPED in the Neo4j class.
- Category and outcome aggregates: `:354-385`, UNSCOPED.
- Referral Decision counts: `:441-474`, UNSCOPED.
- AGE runtime correct-count shim: `:511-523`, UNSCOPED.

### `app/main.py`

- Bootstrap correct/verified queries: `:229-235`, UNSCOPED.
- Learning-state total sync: `:321-323`, UNSCOPED.
- Scoped verified sync: `:340-344`, SCOPED.
- Whole-graph `MATCH (n)` health count at `:202-205` is infrastructure
  telemetry only and must not feed an SOC metric.

### Routers and services

- `routers/soc.py`: Decision counts and confidence at `:775-812`, analytics
  at `:914-925`, verified/category/detail queries at `:1010-1181`, tab queries
  at `:2015`, `:2748`, `:2847`, `:3166-3185`, and `:3245-3285` are unscoped or
  only ID/category scoped.
- `routers/evolution.py`: totals and Decision CREATE/SET at `:65`, `:221-266`,
  `:676`, and `:919` require the helper and domain property.
- `routers/metrics.py`: Decision-to-alert, totals, correctness, timestamps,
  and false-positive queries at `:208-277`, `:479`, `:534`, `:584-605`,
  `:699-872` require the helper.
- `services/iks.py`: all four IKS components at `:211-289` require the helper.
- `services/executive_narrative.py`: Decision context and aggregates at
  `:191-200`, `:323`, `:360`, and `:409-523` require the helper.
- `services/learning_health.py`: the already SOC-scoped query at `:481-492`
  must add active/archive semantics; queries at `:839`, `:893-943` require
  the helper.
- `services/state_manager.py`: session filters and mutations at `:80-124`
  require SOC scoping in both safety checks and DELETE/REMOVE statements.
- `services/graph_explorer.py`: Decision explorer and follow-up traversals at
  `:63-70` and `:139-293` must carry the helper predicate.
- `services/variant_generator.py`: Decision aggregates at `:229-231`,
  `:414-426`, and `:673-674` require the helper.
- `services/timestamp_backfill.py`: selection at `:27`, `:47-48` and ID-only
  mutation at `:65-66` require SOC scoping.
- `state/graph_snapshot.py`: source methods are consumed at `:61-89`; the
  consumer API stays unchanged while its sources are fixed.

## 3. Single predicate-emitting helper

Add one helper in `app/db/neo4j.py` and import it where raw Cypher is built:

```python
def soc_decision_where(
    alias: str = "d",
    *,
    active_only: bool = True,
    transitional: bool = True,
) -> str:
    domain = (
        f"({alias}.domain = 'soc' OR {alias}.domain IS NULL)"
        if transitional
        else f"{alias}.domain = 'soc'"
    )
    parts = [domain]
    if active_only:
        parts.append(f"({alias}.archived IS NULL OR {alias}.archived <> true)")
    return " AND ".join(parts)
```

This function is the only permitted source of SOC Decision predicates. All 50
sites call it; none retypes the domain or archived expression. For queries
whose `WHERE` already contains another condition, append `AND ` plus the
helper result. For OPTIONAL MATCH, place the helper in the relevant `WHERE`
without changing the optional-match cardinality.

### 3.1 Transitional-to-exact transition

Before backfill, every call uses `transitional=True`. After the backfill gate
in section 5 proves zero NULL-domain Decisions, change the single default (or
the application configuration) to `transitional=False`. The resulting exact
predicate is `d.domain = 'soc'`. This makes a future domainless write by any
copilot impossible to leak into SOC results.

The transition is a release gate, not a best-effort cleanup: backfill,
zero-NULL verification, helper flip, and regression tests must complete in that
order.

## 4. Write-path contract

`create_decision_trace` must add `domain: 'soc'` to its Decision property map
(`app/db/neo4j.py:209-225`). Its playbook match and every follow-up edge must
require the helper domain predicate (`:231-235`).

The evolution Decision CREATE must add the same property and its MATCH/SET
must require SOC scope (`app/routers/evolution.py:221-266`). Any other
Decision/Outcome CREATE, SET, REMOVE, or DELETE found by the inventory audit
must use the helper. New SOC writes therefore have an explicit domain even
after the compatibility branch is removed.

## 5. Backfill ownership and ordering (parent D8)

This document is the **single owner** of the SOC domain backfill. Parent-plan
D8 must reference this procedure and must not implement a second all-NULL
mutation. The backfill runs before any other copilot migrates or writes to the
shared graph; at that point the NULL population is still exclusively SOC by
the week-1 constraint.

### 5.1 Preflight

1. Run a read-only census of NULL-domain Decision IDs, origins, linked Alerts,
   outcomes, and archived state.
2. Confirm the census matches the PF-6 ownership evidence. Abort on any row
   that cannot be proven SOC-owned.
3. Back up the graph and record the 4,899 verified baseline.

### 5.2 Mutation

Use a bounded, idempotent AGE mutation after the census:

```cypher
MATCH (d:Decision)
WHERE d.domain IS NULL
  AND d.origin IN ['zero_day_synthetic', 'bootstrap', 'soc']
SET d.domain = 'soc'
RETURN count(d) AS updated
```

The implementation must batch IDs if the deployed AGE parser or transaction
limits require it. Every batch is committed and checkpointed. A rerun updates
zero rows.

### 5.3 Mandatory post-backfill gate

Run:

```cypher
MATCH (d:Decision) WHERE d.domain IS NULL RETURN count(d) AS null_domains
```

The result must be zero. If nonzero, stop; do not flip the helper to exact
mode. Once zero is proven, set `transitional=False` in the one helper and add
a regression test asserting that no NULL-domain Decision exists after startup.

## 6. Startup, snapshot, and count fixes

Fix source queries, not the consumers:

- `main.py:229-235` and `:321-323` call `soc_decision_where()`.
- `neo4j.py:354-385` calls the helper for category and outcome aggregates.
- `GraphSnapshot.from_graph()` remains unchanged and consumes corrected
  methods (`state/graph_snapshot.py:61-89`).

The authoritative direct-Cypher SOC V query is the one at
`app/db/neo4j.py:311-318`, whose compatibility predicate returns **4,899**.
The SDK AGE adapter is a separate path: its `count_verified` delegates to
`AGEGraphStore.count_verified` (`ci-platform/ci_platform/graph/age_sdk_adapter.py:288-295`),
whose standard domain-scoped implementation is at
`ci-platform/ci_platform/graph/age_graph_store.py:1598-1613`. The parent-plan
integration observed that adapter path returning zero for SOC; SOC must not
use that value as its gate until the adapter bug is separately fixed. SOC V_soc
comes from direct `neo4j.py` Cypher, not the SDK adapter.

## 7. Baseline reconstruction and verification

Because foreign data already exists, do not compare against an unscoped live
number. Before any further writes:

1. Run the newly scoped queries against the current graph.
2. Capture V_soc = 4,899, the PF-1 correct/incorrect split (3,749 correct and
   1,150 incorrect), and the PF-1 category histogram in a versioned JSON
   baseline artifact.
3. Compare every retrofit endpoint to that artifact using the SOC-only query
   population.
4. After the backfill and exact-predicate cutover, rerun the same artifact
   queries. V_soc must remain 4,899; only explicitly recorded live SOC
   verification events may change it.
5. Seed one Decision for each other domain and assert that no SOC endpoint,
   aggregate, explorer, or snapshot contains those IDs.

## 8. Implementation order and index discovery

1. Census, backup, and ownership sign-off.
2. Execute this document's backfill before other copilot migration.
3. Verify zero NULL-domain Decisions; switch the helper to exact mode.
4. Fix Decision writes and `neo4j.py` count/aggregate methods.
5. Fix routers (`soc.py`, `evolution.py`, `metrics.py`).
6. Fix services (IKS, narrative, learning health, state manager, explorer,
   variant generator, timestamp backfill).
7. Run baseline and cross-domain regression tests.
8. Discover the AGE label relation before creating an index: inspect the
   deployed PostgreSQL catalog and AGE label metadata, then run `EXPLAIN` on
   the scoped queries. Do not assume `"Decision"` is the physical relation
   name. Create the PostgreSQL index on the discovered relation and `domain`
   column using the deployment's AGE-compatible DDL. Re-run `EXPLAIN` and
   latency benchmarks before production sign-off.

## 9. Risks and mitigations

- Manual predicates across 50 sites can drift. Mitigation: all sites call the
  helper; code review rejects literal SOC/archived predicates outside it.
- A permanent `IS NULL` branch would allow any future domainless writer to leak
  into SOC. Mitigation: zero-NULL gate, exact-mode helper flip, and regression
  assertion.
- Backfill ownership overlap with parent D8 could double-mutate or diverge.
  Mitigation: this document is the sole owner; D8 references it.
- The direct AGE client and SDK adapter have different observed V behavior.
  Mitigation: SOC gates use direct Cypher until adapter parity is proven.
- Optional-match predicate placement can change row cardinality. Mitigation:
  fixture tests with one SOC and one foreign Decision for every changed query.
- AGE physical relation names vary. Mitigation: catalog discovery is an
  explicit pre-index step, not a hard-coded SQL assumption.

## 10. Reading log

The complete v1 reading log remains authoritative for the source ranges:

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

