# SOC shared-graph domain-scoping retrofit v1

Status: implementation contract
Date: 2026-07-25

## 1. Executive summary

SOC predates the shared graph. Its application uses a direct `AGEClient`
compatible query object (`neo4j_client`) rather than the SDK GraphStore
factory. `gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py:486-540`.

That was safe while `soc_graph` contained only SOC data. It is unsafe now that
Trading, Purchasing, DataOps, and S2P also write there. Every Decision and
Outcome read, write, count, aggregate, and destructive operation must be
explicitly scoped to SOC and must apply the active/archived rule appropriate to
the operation.

The retrofit is a predicate-injection and write-contract change. It does not
change the SOC scoring algorithm, category names, or public response shapes.
The migration must preserve the current SOC verified count (`V_soc = 4,862`)
and prove that no non-SOC decision can enter a SOC result.

## 2. Inventory and classification

The inventory covers 89 Decision `MATCH` touchpoints in the listed files;
50 require a predicate or mutation change (UNSCOPED). The remainder are
already scoped or are graph-health telemetry explicitly excluded from SOC
Decision metrics.

### Predicate vocabulary

Use these exact fragments for Decision alias `d`:

```cypher
(d.domain = 'soc' OR d.domain IS NULL)
```

The `IS NULL` branch preserves legacy SOC rows. For active reads append:

```cypher
AND (d.archived IS NULL OR d.archived <> true)
```

For historical reads use `AND d.archived = true`. For a query that is only
about a Decision-to-Alert topology relationship, the same domain predicate
must be placed in the `WHERE` clause after the relationship match.

### `app/db/neo4j.py`

| Lines | Current query/operation | Classification | Consumer | Required form |
|---|---|---|---|---|
| 209-225 | `CREATE (d:Decision {...})` | PARTIALLY_SCOPED | SOC decision trace writer | Add `domain: 'soc'` property. |
| 231-235 | `MATCH (d:Decision {decision_id: ...})` | PARTIALLY_SCOPED | Playbook edge | Add `WHERE (d.domain='soc' OR d.domain IS NULL)`; retain ID predicate. |
| 259-275 | `MATCH (decision:Decision {decision_id: $triggered_by})` | PARTIALLY_SCOPED | Evolution edge | Add SOC domain predicate before creating the event edge. |
| 311-318 | `MATCH (d:Decision) ... D2 ...` | SCOPED | V_soc | Keep SOC/null and active predicates. |
| 334-338 | `MATCH (d:Decision) ... correct` | SCOPED | Correct SOC count | Keep SOC/null and active predicates. |
| 354-357 | `MATCH (d:Decision) WHERE d.outcome IS NOT NULL ...` | UNSCOPED | GraphSnapshot category counts | Add SOC/null and active predicates. |
| 378-385 | `MATCH (d:Decision) WHERE d.outcome IS NOT NULL` | UNSCOPED | Outcome statistics | Add SOC/null and active predicates. |
| 441-444 | `MATCH (d:Decision) WHERE d.source_id=...` | UNSCOPED | Rapid-succession rule | Add SOC/null and active predicates. |
| 470-474 | `MATCH (d:Decision) ...` | UNSCOPED | Cross-category rule | Add SOC/null and active predicates. |
| 516-518 | `MATCH (d:Decision) WHERE d.correct = true` | UNSCOPED | AGE shim correct count | Add SOC/null and active predicates. |

`count_verified_decisions` and `count_correct_decisions` are implemented in
both the AGE client and the Neo4j compatibility class. The AGE client version
already scopes V_soc, but `count_decisions_by_category` remains global.
`ci-platform/ci_platform/graph/age_client.py:672-725`.

### `app/main.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 202-205 | `MATCH (n) RETURN count(n)` | SCOPED only as graph-health telemetry | Keep as total graph-node health, but never expose as SOC Decision count. Rename output to `graph_nodes_total`. |
| 229-235 | `MATCH (d:Decision) WHERE d.outcome IS NOT NULL`; `MATCH (d:Decision) WHERE d.correct = true` | UNSCOPED | Add SOC/null and active predicates. |
| 321-323 | `MATCH (d:Decision) RETURN count(d)` | UNSCOPED | Add SOC/null and active predicates; this initializes SOC learning state. |
| 340-344 | `count_verified_decisions()` | SCOPED | Keep; this is the authoritative V_soc sync. |

### `app/routers/soc.py`

The following Decision queries are all SOC user-facing or tab-content paths:

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 665 | `MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)` | PARTIALLY_SCOPED | Add `WHERE (d.domain='soc' OR d.domain IS NULL)`. |
| 777 | `MATCH (d:Decision) RETURN count(d)` | UNSCOPED | Add SOC/null and active predicates. |
| 811-812 | `MATCH (d:Decision) WHERE d.confidence IS NOT NULL` | UNSCOPED | Add SOC/null and active predicates. |
| 916 | `MATCH (d:Decision) RETURN count(d)` | UNSCOPED | Add SOC/null and active predicates. |
| 922-923 | `MATCH (d:Decision) WHERE d.correct = true` | UNSCOPED | Add SOC/null and active predicates. |
| 1012-1017 | `MATCH (d:Decision) WHERE d.verified_at_epoch IS NOT NULL` | UNSCOPED | Add SOC/null and active predicates and `ORDER BY`. |
| 1098-1099 | `MATCH (d:Decision {decision_id: $decision_id})` | PARTIALLY_SCOPED | Add `AND (d.domain='soc' OR d.domain IS NULL)` to the lookup. |
| 1165-1166 | `MATCH (d:Decision {category: $category}) WHERE d.outcome IS NOT NULL` | UNSCOPED | Add SOC/null and active predicates. |
| 1179-1181 | Decision-to-alert traversal by ID | PARTIALLY_SCOPED | Add SOC/null predicate on `d`. |
| 2015 and 2748 | `MATCH (d:Decision)` blocks | UNSCOPED | Add SOC/null and active predicates. |
| 2847 | confidence filter | UNSCOPED | Add SOC/null and active predicates. |
| 3167-3171 | category/outcome override aggregate | UNSCOPED | Add SOC/null and active predicates. |
| 3184 | outcome total | UNSCOPED | Add SOC/null and active predicates. |
| 3247 | total decisions | UNSCOPED | Add SOC/null and active predicates. |
| 3266-3269 | timestamp min/max/count | UNSCOPED | Add SOC/null and active predicates. |
| 3283 | correct count | UNSCOPED | Add SOC/null and active predicates. |
| 3715 | module-level Decision query | UNSCOPED | Add SOC/null and active predicates. |

### `app/routers/evolution.py`

| Lines | Current query/operation | Classification | Fix |
|---|---|---|---|
| 65 | `MATCH (d:Decision)-[:DECIDED_ON]->() RETURN count(d)` | UNSCOPED | Add SOC/null and active predicates. |
| 221-266 | `CREATE (d:Decision ...)`, then `MATCH ... decision_id` and `SET` | PARTIALLY_SCOPED | Add `domain: 'soc'` to CREATE and domain predicate to the MATCH/SET. |
| 676 | Decision-to-alert aggregate | UNSCOPED | Add SOC/null and active predicates. |
| 919 | total Decision count | UNSCOPED | Add SOC/null and active predicates. |

### `app/routers/metrics.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 208-216 | Decision-to-alert totals/correct totals | UNSCOPED | Add SOC/null and active predicates to both. |
| 247-253 | `origin='zero_day_synthetic'` totals | PARTIALLY_SCOPED | Add SOC/null and active predicates. |
| 277 | Decision-to-alert evolution query | UNSCOPED | Add SOC/null and active predicates. |
| 479 | Decision-to-alert metric | UNSCOPED | Add SOC/null and active predicates. |
| 534 | timestamp range | UNSCOPED | Add SOC/null and active predicates. |
| 584-590 | total/correct counts | UNSCOPED | Add SOC/null and active predicates. |
| 601-605 | timestamp spread | UNSCOPED | Add SOC/null and active predicates. |
| 699, 730, 761 | topology/metric queries | UNSCOPED | Add SOC/null and active predicates wherever alias `d` is present. |
| 811-822 | total/correct/false-positive aggregate | UNSCOPED | Add SOC/null and active predicates. |
| 872 | Decision metric block | UNSCOPED | Add SOC/null and active predicates. |

### `app/services/iks.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 212 | graph richness total | UNSCOPED | SOC/null plus active predicate. |
| 247 | category maturity | UNSCOPED | SOC/null plus active predicate. |
| 272 | confidence trust coverage | UNSCOPED | SOC/null plus active predicate. |
| 285-289 | verified factor quality | UNSCOPED | SOC/null plus active predicate. |

All four components must use the same active SOC population. Otherwise the
IKS denominator and numerator mix tenants.

### `app/services/executive_narrative.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 191-200 | Decision context queries | UNSCOPED | Add SOC/null and active predicates. |
| 323, 360 | optional verified Decision matches | UNSCOPED | Add SOC/null and active predicates in the OPTIONAL MATCH WHERE. |
| 409 | total Decision count | UNSCOPED | Add SOC/null and active predicates. |
| 428 | correct count | UNSCOPED | Add SOC/null and active predicates. |
| 479-503 | outcome/category aggregate | UNSCOPED | Add SOC/null and active predicates. |
| 520-523 | correct category/action aggregate | UNSCOPED | Add SOC/null and active predicates. |

### `app/services/learning_health.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 483-492 | SOC/null category health query | SCOPED | Add active archived exclusion if the result is intended to be active-only; otherwise document history semantics. |
| 839 | Decision query | UNSCOPED | Add SOC/null and active predicates. |
| 894 | total count | UNSCOPED | Add SOC/null and active predicates. |
| 902-905 | verified count | UNSCOPED | Add SOC/null and active predicates. |
| 922-943 | time-window totals | UNSCOPED | Add SOC/null and active predicates. |

### `app/services/state_manager.py`

`PERSISTENT_FILTER` only distinguishes `origin`; it is not a tenant filter.
`gen-ai-roi-demo-v4-v50/backend/app/services/state_manager.py:48-53`.

| Lines | Current operation | Classification | Fix |
|---|---|---|---|
| 81-94 | deletion safety counts | PARTIALLY_SCOPED | Conjoin SOC/null with the supplied persistent/session filter. |
| 100-102 | REMOVE outcome/correct | PARTIALLY_SCOPED | Conjoin SOC/null before mutation. |
| 106-108 | global total | UNSCOPED | Scope to SOC/null and active/history semantics. |
| 117-124 | persistent count and DETACH DELETE | PARTIALLY_SCOPED | Scope both count and delete to SOC/null. |

### `app/services/graph_explorer.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 63-70 | Decision explorer query | UNSCOPED | Add SOC/null and active predicate. Make domain an explicit service constant. |
| 139-293 | Follow-up graph queries based on the explorer result | PARTIALLY_SCOPED | Carry the SOC predicate through every Decision-derived traversal. |

### `app/services/variant_generator.py`

| Lines | Current query | Classification | Fix |
|---|---|---|---|
| 229-231 | category counts | UNSCOPED | Add SOC/null and active predicate. |
| 414-426 | verified category/action aggregates | UNSCOPED | Add SOC/null and active predicate. |
| 673-674 | category list | UNSCOPED | Add SOC/null and active predicate. |

### `app/services/timestamp_backfill.py`

| Lines | Current operation | Classification | Fix |
|---|---|---|---|
| 27, 47-48 | `origin='zero_day_synthetic'` selection | PARTIALLY_SCOPED | Add SOC/null and archived policy. |
| 65-66 | update by `decision_id` only | UNSCOPED mutation | Add SOC/null to the `WHERE`; refuse ambiguous IDs. |

This service is an operator mutation path and must never update another
tenant's node merely because an ID matches.

### `app/state/graph_snapshot.py`

`GraphSnapshot.from_graph()` delegates to client methods for verified,
correct, category, outcome, and IKS values. `gen-ai-roi-demo-v4-v50/backend/app/state/graph_snapshot.py:61-89`.
The consumer should not receive a new domain argument; fix the source methods
and preserve the snapshot API.

## 3. SOC predicate standard

Introduce one constant/helper in `app/db/neo4j.py` for inline Cypher:

```python
SOC_DOMAIN = "(d.domain = 'soc' OR d.domain IS NULL)"
SOC_ACTIVE = "(d.archived IS NULL OR d.archived <> true)"
```

For parameterized Neo4j Cypher, use `d.domain IN ['soc']` only if legacy NULL
rows have already been backfilled. Until then, every SOC Decision query uses
the exact compatibility predicate above.

Rules:

1. Active analytics: `WHERE SOC_DOMAIN AND SOC_ACTIVE`.
2. Historical/archive analytics: `WHERE SOC_DOMAIN AND d.archived = true`.
3. Mutation by ID: `WHERE SOC_DOMAIN AND d.decision_id = ...`.
4. Decision-to-Outcome or Decision-to-Alert traversals: scope `d`, even when
   the target node has a different label.
5. Whole-graph node/relationship counts are allowed only for infrastructure
   telemetry and must not feed SOC metrics.

## 4. Write-path contract

`create_decision_trace` must add `domain: 'soc'` to the Decision property map
and keep the existing alert match. `gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py:209-225`.

The evolution Decision CREATE must also add `domain: 'soc'` and its follow-up
MATCH/SET must require SOC/null domain. `gen-ai-roi-demo-v4-v50/backend/app/routers/evolution.py:221-266`.

All other Decision/Outcome CREATE, SET, REMOVE, and DELETE operations in the
inventory must use the same mutation predicate. New SOC writes must never rely
on a missing domain property.

## 5. Domain backfill decision

Recommendation: YES, but only after a read-only census and backup.

The census must report NULL-domain Decision IDs, their origins, and whether
they are linked to SOC Alerts. The expected population is the legacy SOC
population, but this must be proven before mutation.

If the census proves all NULL-domain rows are legacy SOC, run this idempotent
AGE statement in batches:

```cypher
MATCH (d:Decision)
WHERE d.domain IS NULL
  AND d.origin IN ['zero_day_synthetic', 'bootstrap', 'soc']
SET d.domain = 'soc'
RETURN count(d) AS updated
```

If origins are not sufficient to prove ownership, do not backfill. Retain
`(d.domain = 'soc' OR d.domain IS NULL)` permanently and require the census
result as an operational artifact. The migration must never assign SOC to a
NULL-domain row belonging to another tenant.

## 6. Implementation order

1. Run the NULL-domain census and AGE clean-slate/backup checks.
2. Apply the approved domain backfill, or lock in the compatibility predicate.
3. Fix Decision CREATE paths (`neo4j.py`, `evolution.py`).
4. Fix `neo4j.py` count/aggregate/rule methods.
5. Fix startup queries in `main.py`.
6. Fix `soc.py`, `evolution.py`, and `metrics.py` route queries.
7. Fix services: IKS, narrative, learning health, state manager, graph
   explorer, variant generator, timestamp backfill.
8. Keep `GraphSnapshot` unchanged; validate its source methods instead.
9. Add regression tests and run the five-domain live query audit.

Each step is independently deployable, but the write-path change must land
before enabling any new SOC writes against the shared graph.

## 7. Verification contract

Required gates:

- `V_soc` remains exactly 4,862 on the migration snapshot and does not change
  merely because other domains are present. The source predicate is
  `gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py:311-318`.
- Every SOC analytics endpoint returns the same values as the pre-shared-graph
  baseline when evaluated against the SOC subset.
- A query audit proves no SOC Decision result contains a Trading, Purchasing,
  DataOps, or S2P domain.
- A mutation audit proves every new SOC Decision has `domain='soc'`.
- Active counts exclude archived decisions; archive reports include only
  `d.archived = true`.
- Add regression tests that seed one Decision per domain and assert every SOC
  count, category aggregate, detail lookup, explorer result, and mutation
  affects only SOC.

## 8. AGE index

Create/verify an index on the Decision domain property before performance
sign-off. AGE uses PostgreSQL indexes on the underlying label relation; use
the project's AGE deployment DDL convention rather than inventing a Cypher
`CREATE INDEX` statement. The exact operational SQL must be tested against the
deployed PostgreSQL/AGE version.

At minimum benchmark:

```sql
CREATE INDEX IF NOT EXISTS decision_domain_idx
ON "Decision" (domain);
```

If the deployment stores labels in an AGE-specific relation name, substitute
the actual relation discovered from `\d`/catalog inspection. Run `EXPLAIN`
for SOC active verified, category, and archive queries before and after.

## 9. Risks and mitigations

- Missing one of the many raw queries leaves a cross-domain leak. Mitigation:
  repeat the repository-wide `MATCH ... Decision|Outcome|HAS_OUTCOME` audit
  after implementation.
- Adding `WHERE` in the wrong place can change OPTIONAL MATCH cardinality.
  Mitigation: test each query with one SOC and one non-SOC fixture.
- Backfilling NULL domains can mislabel data. Mitigation: census, backup,
  explicit origin/link evidence, idempotent bounded mutation.
- Archived rows can re-enter active metrics if the archived predicate is
  omitted. Mitigation: separate active/history helpers and assertions.
- Index DDL differs across AGE versions. Mitigation: execute deployment-specific
  SQL and capture query plans.

## 10. Reading log

Fully reviewed for this contract:

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
