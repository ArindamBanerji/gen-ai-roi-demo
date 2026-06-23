# SOC Campaign Phase 4 CONTINUES Plan v1

## Executive Decision

Phase 4 is ready for implementation after GPT-5.5 plan review. The implementation should be narrow: add forward-only, idempotent `(:Campaign)-[:CONTINUES]->(:Campaign)` writes from the existing locked campaign write path, cache temporal chain context in `CampaignAsyncState` when metadata is safely available, and leave v6 advisory display wiring for the following package.

Phase 4 is temporal context assembly, not scorer intelligence. It must not change recommendations, tensors, DK, conservation, scorer factors, or GraphStore protocols.

## Design Authority

Primary authority:

`C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\copilot-sdk\docs\design\soc_campaign_v6_context_injection_v2_2.md`

Version confirmed: v2.2.

## Step 1 Accepted Status

Step 1 analyst_action instrumentation is accepted with GPT-5.5 `PASS_WITH_P3`.

Carry-forward P3: the auxiliary in-memory audit ledger still treats any supplied `analyst_action` as `analyst_override`; durable v7 measurement uses `Decision.was_override`, not that audit metadata.

## Current Constraints

- Do not implement v7 scorer/tensor changes.
- Do not add campaign scorer factors.
- Do not modify scorer, DK, conservation, or GraphStore protocol/stores.
- Do not create `BELONGS_TO`.
- Preserve `MEMBER_OF` as canonical alert-to-campaign membership.
- Preserve 1b-2 advisory-lock and MATCH-then-CREATE write safety.
- Preserve Phase 3B M8 hot-path budget: p95 <= 5ms, preferred <= 3ms.
- Add no hot-path AGE reads.
- First implementation is forward-only. No historical mutating backfill.
- Phase 4 edge-write package must not implement final v6 advisory display. It may only populate cache fields that a later display package can consume.
- Production `CONTINUES` writes must use transaction/advisory-lock protected campaign write paths. Do not add an unlocked non-transaction production write fallback.

## Discovered Code Anchors

### Campaign Identity

`backend/app/domains/soc/campaigns.py`

- `Campaign` includes `rule_type`, `derived_entity_key`, `category`, and `time_bucket`.
- `campaign_time_bucket(ts, window_seconds)` returns epoch-aligned integer buckets.
- `make_campaign_identity_key(rule_type, derived_entity_key, category, time_bucket)` returns `L1-<sha256-prefix>`.
- `make_campaign_seed_key(rule_type, derived_entity_key, category, time_bucket)` returns `S1-<sha256-prefix>`.
- `campaign_seed_candidate(event, window_seconds, rule_type="shared_entity")` builds seed/campaign identity fields.
- `CampaignCorrelationEngine._build_campaign(...)` now populates identity dimensions on materialized `Campaign` objects.

### Campaign and Seed Properties

`CampaignSeed` nodes currently store:

- `seed_key`
- `campaign_id`
- `rule_type`
- `derived_entity_key`
- `category`
- `time_bucket`
- `status`
- `alert_ids`
- first/last alert fields
- first/last/created/updated epoch fields

`Campaign` nodes currently write:

- `campaign_id`
- `first_seen`
- `last_seen`
- `alert_count`
- `category_sequence`
- `shared_entities`
- `technique_sequence`
- `confidence`
- `trigger_rule`
- `rule_type`
- `derived_entity_key`
- `category`
- `time_bucket`
- `severity`
- `correlation_window_hours`
- `nl_summary`
- `updated_at_epoch`

Live read-only AGE count observed current mixed graph state:

- Campaign nodes: 262
- MEMBER_OF edges: 524
- CampaignSeed nodes: 109
- CONTINUES edges: 0
- BELONGS_TO edges: 0
- Campaigns with `derived_entity_key/category/time_bucket`: 111
- Rule distribution: 111 shared_entity keyed, 147 temporal legacy/null-key, 4 null/null legacy.

Implication: Phase 4 v1 should be forward-only and should only link campaigns with complete identity dimensions. Historical backfill requires separate review because older Campaign rows are mixed and often lack key dimensions.

### AGE Write Path

`CampaignRepository._write_campaign_locked(run_cypher, campaign)` is the preferred future anchor:

- It runs inside `_run_campaign_locked_transaction(...)` for transaction-capable AGE clients.
- It MATCH-then-CREATEs/updates `Campaign`.
- It rechecks and creates missing `MEMBER_OF` edges idempotently.
- It is called from `materialize_seed_campaign(...)` via `_materialize_seed_campaign_locked(...)`.
- Public `write_campaign(...)` routes transaction-capable clients through the same locked implementation.

`CampaignRepository.persist_campaign_seed(...)` is separately locked by seed key and should remain unchanged except for tests that prove it is not affected.

### Async Materialization Path

`CampaignMatcher.check_alert(...)` is the hot path. It:

1. fetches the alert event once,
2. checks in-memory materialized cache,
3. checks pending provisional seed,
4. falls back to keyed AGE materialized campaign lookup,
5. schedules background materialization only on true miss.

Background materialization calls `_materialize_alert(...)`, which persists a seed, correlates recent events, materializes the campaign through the repository, then updates `CampaignAsyncState` context.

### Cache State

`CampaignAsyncState` currently stores:

- `bg_tasks`
- `pending_seeds`
- `pending_seed_campaigns`
- `materialized_campaigns`
- `campaign_contexts`

Phase 4 should extend this with a positive temporal chain cache, not a negative cache.

## Recommended CONTINUES Semantics

### Edge Meaning

`(:Campaign {campaign_id: older})-[:CONTINUES]->(:Campaign {campaign_id: newer})`

Meaning: the newer campaign bucket is a temporal continuation of the same entity/category/rule stream from an older campaign bucket.

### Node Types

Connect `Campaign` to `Campaign`, not `CampaignSeed` and not alert nodes. `CampaignSeed` remains materialization staging. `MEMBER_OF` remains Alert-to-Campaign membership.

### Required Match Dimensions

Create `CONTINUES` only when both campaigns have:

- same `derived_entity_key`
- same `category`
- same `rule_type` or effective `trigger_rule`
- same domain/graph
- complete non-null `time_bucket`

Do not link across entity, category, rule, or domain.

### Time Gap Rule

Initial v1 rule:

- Strict adjacent bucket only: `newer.time_bucket - older.time_bucket == 1`.
- Do not allow bounded missed-day gaps in v1. A `<= N` bucket continuation rule requires a later Roadmap decision because it changes semantics from strict continuity to inferred continuity.

Because the current bucket length is the campaign engine window, the implementation should compute expected gap against `campaign.correlation_window_hours` or the engine window seconds. Do not assume calendar-day labels if the configured window changes.

### Idempotency Rule

Use MATCH-then-CREATE, no `MERGE`:

1. Match older and newer Campaign nodes by campaign_id.
2. Check whether `(older)-[:CONTINUES]->(newer)` exists.
3. Create only if absent.

Production AGE writes must run inside the same transaction/advisory lock used for the locked campaign write path.

### Reset and Archive Behavior

Do not delete `CONTINUES` in normal seed cleanup. Seed cleanup remains non-destructive. Domain resets/archive behavior should be audited separately before adding any cleanup. Initial graph integrity should assert no cross-domain edges and no duplicate edges.

### Historical Backfill

Forward-only first. No mutating backfill in Phase 4 v1.

Backfill can be designed later as a separate Roadmap-approved package because the current graph contains legacy campaigns with missing identity dimensions.

## Review-Locked Defaults

These replace the previous open questions and should be treated as implementation requirements:

1. Gap policy: strict adjacent bucket only for v1.
2. Rule coverage: any campaign may link if it has complete identity fields, but it must match on derived entity, category, and effective rule. Do not special-case `shared_entity` only.
3. Required edge properties: `created_at_epoch`, `gap_buckets`, and `rule_type`. Optional diagnostic properties such as `category` or `derived_entity_key` may be added only if they use the same safe serialization style as existing AGE writes.
4. Display warmup: cache-only graceful degradation. Do not add hot-path AGE warmup or chain reads for v6 display.
5. Reset/archive: do not delete `CONTINUES` in v1. Cleanup or archival mutation requires a separate audit and implementation prompt.

## Write-Path Plan

Add a repository helper such as `_write_continues_locked(run_cypher, campaign)` and call it from the shared locked campaign write implementation so both seed materialization and public locked `write_campaign(...)` use the same semantics.

Preferred anchor:

- Invoke the helper inside `CampaignRepository._write_campaign_locked(run_cypher, campaign)` after the current `Campaign` node has been MATCH-then-CREATEd/updated and its `MEMBER_OF` edges are reconciled.
- Preserve public return contracts. Public `write_campaign(...)`, `materialize_seed_campaign(...)`, and `persist_campaign_seed(...)` must keep their existing return types and advisory-lock behavior. If the implementation needs temporal metadata, plumb it through a private result object or private side channel without changing public API semantics.
- Do not put the only `CONTINUES` call in `_materialize_seed_campaign_locked(...)`; that misses direct locked campaign writes and creates inconsistent graph semantics.

Algorithm:

1. If current campaign lacks `derived_entity_key`, `category`, `rule_type/trigger_rule`, or `time_bucket`, skip.
2. Query for the nearest older Campaign with:
   - same `derived_entity_key`
   - same `category`
   - same effective rule
   - `time_bucket == current.time_bucket - 1`
3. If no older campaign, skip.
4. Check existing `(older)-[:CONTINUES]->(current)`.
5. Create `CONTINUES` only if absent, with required properties `created_at_epoch`, `gap_buckets`, and `rule_type`.
6. Return temporal context metadata for cache update: previous id, chain start id/bucket, chain length, total alert count.

For legacy non-transaction local/test clients:

- Do not add an unlocked production fallback that can create duplicate-prone `CONTINUES` edges.
- Unit tests may use explicit fake transaction-capable clients or a narrow fake helper that models the locked path.
- If a non-transaction client cannot provide locked semantics, skip `CONTINUES` and report/record that Phase 4 edge creation requires the transaction-capable path.

## Cache and Context Plan

Extend `CampaignAsyncState` with a temporal context cache, for example:

```python
@dataclass
class CampaignTemporalContext:
    campaign_id: str
    previous_campaign_id: str | None = None
    chain_start_campaign_id: str | None = None
    chain_start_bucket: int | None = None
    chain_length_buckets: int = 1
    total_alert_count: int = 0
    member_count_by_campaign: dict[str, int] = field(default_factory=dict)
```

Store by current campaign id:

`temporal_contexts: dict[str, CampaignTemporalContext]`

Update after successful locked campaign write and `CONTINUES` evaluation when temporal metadata is available. The cache should be positive-only and process-local, matching Phase 3B/v6 assumptions. If cache is cold, v6 advisory can degrade to same-day context only; do not add a hot-path AGE chain read.

Cache update must not require a new AGE read from `CampaignMatcher.check_alert(...)`. If temporal metadata cannot be safely plumbed from the locked write path without changing public repository return types, keep the cache update scoped to data already in memory and defer richer chain reconstruction to a later off-path package.

Single-worker assumption remains acceptable for demo/pilot. Production hardening would require shared cache/outbox or startup warmup, but that is out of scope.

## Performance Budget

- Hot path AGE reads added: zero.
- Check-alert cache-hit path must remain alert fetch plus in-memory lookups.
- Expected added latency: approximately zero on check_alert path.
- Required validation after implementation:
  - M8 pooled `CampaignMatcher.check_alert` / `check_alert_timed` p95 <= 5ms.
  - Preferred p95 <= 3ms.
  - Unit/mock timing test proves no new AGE lookup on cache hit.
  - Tests prove CONTINUES write occurs off hot path during background materialization.
  - Do not use full HTTP analyze latency as M8.

## Graph Integrity Plan

Keep strict:

- duplicate seed keys = 0
- duplicate `MEMBER_OF` for same alert/campaign = 0
- duplicate `CONTINUES` for same older/newer pair = 0
- `BELONGS_TO` = 0
- no cross-domain `CONTINUES`
- no cross-entity `CONTINUES`
- no cross-category `CONTINUES`
- no cross-rule `CONTINUES`

Phase 4 intentionally changes the old invariant from `CONTINUES == 0` to:

- pre-Phase4 tests should stop treating any `CONTINUES` existence as globally forbidden once Phase 4 is implemented, except in explicitly isolated flows where Phase 4 is disabled or not reachable;
- Phase 4 tests assert expected `CONTINUES` count and duplicate count zero;
- validation reports after Phase 4 should report `CONTINUES total` separately from `duplicate CONTINUES pairs`.

Duplicate validation should be by `(older.campaign_id, newer.campaign_id)` pair, not by total edge count. `BELONGS_TO` remains a hard zero invariant.

## Advisory Context Plan

Phase 4 edge writing should feed, but not implement, final v6 advisory display.

Fields to expose later:

- `day N` / chain length buckets
- active since / chain start
- total alerts across chain
- current campaign member count
- previous campaign ids, bounded
- current bucket/campaign id

Language guardrails:

- Say "temporal intelligence" or "ongoing incident context".
- Do not say "compounding intelligence".
- Keep "we advise, you decide".
- Do not change scorer recommendation.

## Tests

Create `backend/tests/test_campaign_phase4_continues.py`.

Required unit/integration tests:

1. Same entity/category/rule adjacent buckets creates one `CONTINUES`.
2. Repeated materialization does not create duplicate `CONTINUES`.
3. Different entity does not link.
4. Different category does not link.
5. Different rule_type does not link.
6. Non-adjacent buckets do not link in v1.
7. Missing identity fields skip safely.
8. `BELONGS_TO` remains absent.
9. Duplicate seed keys remain prevented.
10. CONTINUES write runs in the locked materialization path for transaction-capable clients.
11. Direct public locked `write_campaign(...)` path also uses the shared CONTINUES semantics or explicitly skips only when transaction semantics are unavailable.
12. Edge properties include `created_at_epoch`, `gap_buckets`, and `rule_type`.
13. Async background materialization returns without waiting for CONTINUES write on hot path.
14. Temporal context cache updates after success when metadata is available.
15. Cache reset clears temporal state in tests.
16. No new AGE campaign/chain lookup on cache-hit check_alert path.
17. M8 mock timing remains below 5ms and is labeled unit/mock.

Existing tests to update cautiously:

- `test_campaign_phase3_async.py` currently asserts no `CONTINUES` text in Phase 3 queries; keep for Phase 3 paths or version-gate only if needed.
- `test_campaign_seed_materialization.py` currently asserts no `CONTINUES`; preserve for seed-only and pre-Phase4 flows, add Phase 4 tests separately.
- `test_campaign_engine.py` comment says CONTINUES later-phase work; update only in implementation if assertions/comments become stale.

## Implementation Prompt Draft

Task: SOC Campaign Phase 4 CONTINUES edge-write and temporal cache. Implementation + tests.

Read first:

- `copilot-sdk/docs/design/soc_campaign_v6_context_injection_v2_2.md`
- `docs/implementation_plans/soc_campaign_phase4_continues_plan_v1.md`

Strict non-goals:

- Do not implement v7 scorer/tensor.
- Do not modify scorer, DK, conservation, or GraphStore protocol/stores.
- Do not add campaign factors.
- Do not implement v6 advisory display.
- Do not add `BELONGS_TO`.
- Do not run live AGE proof.
- Do not create historical backfill.

Allowed files:

- `backend/app/domains/soc/campaigns.py`
- `backend/tests/test_campaign_phase4_continues.py`
- existing campaign tests only if needed to adjust pre-Phase4 integrity expectations.

Implementation requirements:

1. Add `CampaignTemporalContext` and process-local positive temporal cache to `CampaignAsyncState`.
2. Add repository helper for idempotent `CONTINUES` write under the existing campaign advisory transaction.
3. Anchor the helper in the shared locked campaign write path so materialized seed writes and direct locked campaign writes are consistent.
4. Link older -> newer Campaign nodes only when same derived entity, category, effective rule, and strict adjacent bucket.
5. Use MATCH-then-CREATE, no MERGE.
6. Preserve public `write_campaign`, `materialize_seed_campaign`, and `persist_campaign_seed` return types and advisory-lock semantics.
7. Keep check_alert return type unchanged.
8. Add no hot-path AGE reads.
9. Do not change scorer/tensor/DK/conservation.
10. Tests must cover idempotency, negative dimensions, phase boundary, async hot path, cache update, direct locked write path, edge properties, and graph integrity.

Validation:

- `python -m pytest tests/test_campaign_phase4_continues.py -v --timeout=60`
- campaign suite with phase3/seed/materialization tests
- full backend once if product code changed

## Review Prompt Draft

Task: GPT-5.5 review of SOC Campaign Phase 4 CONTINUES implementation. Code review only, no edits.

Review:

- semantics older -> newer
- same entity/category/rule/strict-adjacent-bucket constraints
- idempotent MATCH-then-CREATE
- transaction/advisory-lock preservation
- no `BELONGS_TO`
- no scorer/tensor/DK/conservation/GraphStore changes
- no v6 advisory display
- no hot-path AGE reads
- cache update correctness
- tests prove duplicate prevention and phase boundary
- M8 readiness

Verdict options:

- PASS
- PASS_WITH_P3
- FAIL_NEEDS_FIXER

## Open Questions

No blocking implementation questions remain after GPT-5.5 plan review. The review-locked defaults above are authoritative for Phase 4 v1.

Deferred Roadmap questions:

1. Whether to support bounded missed-day gaps after v1.
2. Whether to run a separate historical CONTINUES backfill.
3. Whether to add a cold-start temporal cache warmup for v6 display.
4. Whether domain reset/archive should delete, mark, or preserve CONTINUES.

## Guardrails

Do not implement v7 scorer/tensor. Do not change ProfileScorer. Do not modify DK/conservation. Do not add campaign factors. Do not add `BELONGS_TO`. Do not create mutating backfill. Do not add hot-path AGE reads. Do not claim compounding intelligence.
