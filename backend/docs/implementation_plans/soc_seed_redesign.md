# SOC Seed Redesign

READY_FOR_PROMPT_B: YES

## 1. Executive Summary

The current SOC seed data is a large static JSON file at `support/setup/zero_day_decisions_v5.json`. It is compatible with `app.graph_schema.seed_graph()`, but it has grown through one-off enrichment and alert-pool expansion scripts. The redesign replaces ad hoc seed editing with a deterministic generator that produces the same schema, derives metadata from generated arrays, validates every generated record before graph writes, and makes unmapped alert types structurally impossible.

Prompt B should implement:

- a deterministic seed package under `app/seed/`;
- a `scripts/generate_seed.py` entry point;
- generated output compatible with `support/setup/zero_day_decisions_v5.json`;
- a full validation gate invoked before `seed_graph()` writes to AGE;
- an audit timestamp path that preserves generated decision timestamps through graph rebuild and evidence-room APIs.

Out of scope for Prompt B:

- changing frontend behavior;
- changing Playwright tests;
- reseeding AGE as part of implementation;
- changing SOC scoring semantics;
- changing demo alert reset behavior;
- replacing graph storage.

## 2. Current-State Findings

### Seed JSON Shape

Precheck `_pc1.py` loaded `support/setup/zero_day_decisions_v5.json` and found these top-level keys:

`metadata`, `users`, `assets`, `attack_patterns`, `threat_indicators`, `campaigns`, `alerts`, `demo_alerts`, `decisions`.

Current counts:

- `users`: 21
- `assets`: 16
- `attack_patterns`: 7
- `threat_indicators`: 9
- `campaigns`: 4
- `alerts`: 543
- `demo_alerts`: 102
- `decisions`: 4862

Current metadata from `_pc1.py`:

- `generator`: `enrich_zero_day_v5`
- `version`: `5.0`
- `total_alerts`: 543
- `total_demo_alerts`: 102
- `total_decisions`: 4862
- `total_users`: 21
- `total_assets`: 16
- `total_attack_patterns`: 7
- `total_threat_indicators`: 9
- `total_campaigns`: 4
- `days_simulated`: 90
- `category_order`: six SOC categories
- `action_order`: `escalate`, `investigate`, `suppress`, `monitor`
- `rng_seed`: 42
- `overall_correct_rate`: 0.816

### Entity Field Schemas

Prechecks `_pc1.py` and `_pc12.py` found these current field sets.

`users`:

- `user_id`
- `name`
- `department`
- `risk_level`
- `origin`

`assets`:

- `asset_id`
- `hostname`
- `criticality`
- `asset_type`
- `origin`

`attack_patterns`:

- `pattern_id`
- `name`
- `mitre_id`
- `tactic`
- `category`
- `origin`

`threat_indicators`:

- `indicator`
- `indicator_type`
- `severity`
- `source`
- `origin`

`campaigns`:

- `campaign_id`
- `name`
- `severity`
- `confidence`
- `trigger_rule`
- `category_sequence`
- `shared_entities`
- `technique_sequence`
- `nl_summary`
- `member_alert_ids`
- `alert_count`
- `correlation_window_hours`
- `first_seen`
- `last_seen`
- `origin`
- `alert_ids`

`alerts`:

- `alert_id`
- `category`
- `severity`
- `alert_type`
- `timestamp_epoch`
- `origin`
- `source_location`
- `user_id`
- `status`
- `asset_id`
- `attack_pattern_id`
- `indicator_ids`

`demo_alerts`:

- `alert_id`
- `category`
- `severity`
- `alert_type`
- `timestamp_epoch`
- `origin`
- `source_location`
- `user_id`
- `asset_id`
- `user_name`
- `asset_hostname`
- `attack_pattern_id`
- `indicator_ids`
- `status`

`decisions`:

- `decision_id`
- `alert_id`
- `category`
- `action`
- `factor_vector`
- `confidence`
- `correct`
- `outcome`
- `timestamp_epoch`
- `origin`
- `source_id`
- `user_id`
- `timestamp`

### SOC Categories, Actions, and Alert-Type Routing

`SOC_CATEGORIES` has six categories in `app/domains/soc/config.py:79`: `credential_access`, `malware_execution`, `lateral_movement`, `data_exfiltration`, `insider_threat`, `cloud_infrastructure`.

`SCORER_ACTIONS` is the four-action scorer list in `app/domains/soc/config.py:50`: `escalate`, `investigate`, `suppress`, `monitor`. `SOC_ROUTING_ACTIONS` adds `refer_to_analyst` for routing at `app/domains/soc/config.py:55`; seed decisions should use `SCORER_ACTIONS` unless a future prompt explicitly generates route-only decisions.

`BOOTSTRAP_CATEGORY_WEIGHTS` is defined at `app/domains/soc/config.py:94` and sums to 1.0:

- credential_access: 0.30
- lateral_movement: 0.20
- data_exfiltration: 0.15
- insider_threat: 0.15
- cloud_infrastructure: 0.10
- malware_execution: 0.10

`ALERT_TYPE_CATEGORY_MAP` is the routing source of truth at `app/domains/soc/config.py:253`. It currently contains 25 entries. Precheck `_pc2.py` grouped them as:

- credential_access: `anomalous_login`, `ambiguous_login_location`, `brute_force`, `credential_stuffing`, `credential_access`
- malware_execution: `threat_intel_match`, `phishing`, `malware_detection`, `malware_execution`, `c2_beacon`
- lateral_movement: `privilege_escalation`, `internal_scan_ambiguous`, `lateral_movement`
- data_exfiltration: `data_exfil`, `data_exfiltration`
- insider_threat: `insider_threat`, `insider_threat_detected`, `anomalous_behavior`
- cloud_infrastructure: `cloud_config`, `cloud_iam_privilege_escalation`, `cloud_storage_public_exposure`, `cloud_config_drift`, `cloud_unused_resource_anomaly`, `cloud_permission_change_review`, `cloud_infrastructure`

Unknown alert types are intentionally routed to `unclassified` with a `ROUTING_UNCLASSIFIED` warning by `resolve_alert_category()` at `app/domains/soc/config.py:295` through `app/domains/soc/config.py:318`. The seed generator must not rely on this fallback.

### SituationType Cross-Check

`SituationType` values are defined at `app/services/situation.py:17` through `app/services/situation.py:33`. Precheck `_pc3.py` found only `insider_threat_detected` is directly mapped in `ALERT_TYPE_CATEGORY_MAP`; the other 13 SituationType values are not alert types:

- `travel_login_anomaly`
- `known_phishing_campaign`
- `malware_on_critical_asset`
- `vip_after_hours`
- `data_exfil_attempt`
- `unknown`
- `brute_force_attack`
- `privilege_escalation_detected`
- `credential_stuffing_attack`
- `c2_communication`
- `threat_intel_indicator`
- `anomalous_network_behavior`
- `cloud_misconfiguration`

This should not block seed generation. Prompt B should validate SituationType coverage with an explicit excluded list because these are situation classifications, not raw alert types. `insider_threat_detected` is both a SituationType and a mapped alert type.

### Decision Density and Referential Integrity

Precheck `_pc13.py` found:

- unique alerts across `alerts + demo_alerts`: 645
- decisions: 4862
- average decisions per alert: 7.5
- decisions referencing nonexistent alerts: 0
- min decisions per referenced alert: 1
- max decisions per referenced alert: 9
- median decisions per referenced alert: 9

The current seed is training-decision heavy. Prompt B should default to generating decisions for training alerts only unless a deliberate demo-decision use case is added, because current `graph_schema._validate_json()` validates decisions against `alerts` only at `app/graph_schema.py:399` through `app/graph_schema.py:405`.

### Current `seed_graph()` Flow

`seed_graph(json_path, clean=False, client=None)` starts at `app/graph_schema.py:421`. It reads JSON, calls `_validate_json(data)` before touching graph state at `app/graph_schema.py:441`, and only then extracts arrays at `app/graph_schema.py:446` through `app/graph_schema.py:453`.

Current creation phases:

- Phase 1 clean handling starts at `app/graph_schema.py:467`.
- Phase 2 creates `User` nodes at `app/graph_schema.py:517`.
- Phase 3 creates `Asset`, `AttackPattern`, and `ThreatIndicator` nodes at `app/graph_schema.py:530`.
- Phase 4 creates `Campaign` nodes at `app/graph_schema.py:569`.
- Phase 5 creates training `Alert` nodes at `app/graph_schema.py:585`.
- Phase 6 creates demo `Alert` nodes at `app/graph_schema.py:606`.
- Phase 7 creates edges for all alerts at `app/graph_schema.py:625`.
- Phase 8 creates `Decision` nodes and `DECIDED_ON` edges at `app/graph_schema.py:736`.
- Phase 9 verifies the graph at `app/graph_schema.py:767`.

Current JSON validation is too shallow for generated data. `_validate_json()` checks required top-level keys at `app/graph_schema.py:368` through `app/graph_schema.py:372`, checks required fields only on the first three items per section at `app/graph_schema.py:377` through `app/graph_schema.py:397`, and checks decision alert references only against `alerts` at `app/graph_schema.py:399` through `app/graph_schema.py:405`.

### Current Graph Contract Fields

`app/graph_schema.py` defines graph contract required fields for `Alert` at `app/graph_schema.py:78` through `app/graph_schema.py:83`:

- `alert_id`
- `category`
- `severity`
- `status`
- `origin`
- `timestamp_epoch`
- `user_id`
- `asset_id`
- `alert_type`
- `source_location`
- `attack_pattern_id`

It defines `Decision` required fields at `app/graph_schema.py:85` through `app/graph_schema.py:89`:

- `decision_id`
- `category`
- `action`
- `factor_vector`
- `confidence`
- `outcome`
- `timestamp_epoch`

Optional `Decision` fields include `correct`, `origin`, `source_id`, `user_id`, `alert_id`, and audit-related metadata at `app/graph_schema.py:90` through `app/graph_schema.py:101`.

### Audit Timestamp Pipeline

This is the critical current weakness.

The static JSON includes both `timestamp_epoch` and ISO `timestamp` for decisions, as shown by `_pc12.py`. However, `seed_graph()` only writes `timestamp_epoch` for Decision nodes at `app/graph_schema.py:748`; it does not write the JSON `timestamp` string in the Decision create block at `app/graph_schema.py:740` through `app/graph_schema.py:752`.

Evidence-room output depends on audit rows. `EvidenceRoomService._collect_audit()` calls `reconstruct_from_memory()` and `get_decision_rows()` at `app/services/evidence_room.py:120` through `app/services/evidence_room.py:124`. `_format_summary_entry()` and `_format_export_entry()` read `row.get("timestamp")` at `app/services/evidence_room.py:156` and `app/services/evidence_room.py:168`.

Audit rebuild has two graph-backed paths:

- `rebuild_chain_from_graph(client)` queries `d.timestamp_epoch AS ts` at `app/framework/audit.py:246` through `app/framework/audit.py:257`, but appends ledger entries without passing a timestamp at `app/framework/audit.py:267` through `app/framework/audit.py:276`.
- `rebuild_from_age()` queries `d.timestamp_epoch AS ts` at `app/framework/audit.py:293` through `app/framework/audit.py:305`, converts it to ISO at `app/framework/audit.py:324` through `app/framework/audit.py:329`, and passes it into `_LEDGER.append(..., timestamp=ts_iso)` at `app/framework/audit.py:331` through `app/framework/audit.py:342`.

`app/services/timestamp_backfill.py` exists because prior synthetic Decision nodes were seeded with a shared epoch. Its module docstring states that all 4860 synthetic Decision nodes were seeded with the same `timestamp_epoch` and needed a spread across 90 days at `app/services/timestamp_backfill.py:1` through `app/services/timestamp_backfill.py:7`.

Prompt B should make timestamp uniqueness a generator invariant and remove the need for backfill as a correctness mechanism.

### Existing SOC-ALERT-POOL Artifact

`scripts/expand_demo_alerts.py` currently expands only `demo_alerts`. It reads `support/setup/zero_day_decisions_v5.json`, targets 17 demo alerts per category, preserves schema keys from the first existing demo alert, and writes deterministic alert timestamps from a fixed base and step. It hardcodes category metadata rather than deriving alert types from `ALERT_TYPE_CATEGORY_MAP`.

Prompt B should subsume this script into the new generator. The script may remain temporarily for compatibility, but its behavior should be replaced by a single source-of-truth generator that handles training alerts, demo alerts, decisions, metadata, and validation together.

### Baseline

Current backend baseline command:

`python -m pytest tests/ -q --timeout=300`

Result:

- `1614 passed`
- `3 skipped`
- `3304 warnings`
- runtime: `207.34s`

No current red baseline forces an emergency code workaround.

## 3. SeedConfig Dataclass Design

Create `app/seed/config.py`.

```python
@dataclass(frozen=True)
class SeedConfig:
    n_training_alerts: int = 543
    n_demo_alerts: int = 102
    n_decisions: int = 4862
    n_users: int = 21
    n_assets: int = 16
    n_campaigns: int = 4
    n_attack_patterns: int = 7
    n_threat_indicators: int = 9
    time_range_days: int = 90
    accuracy_target: float = 0.816
    decisions_per_alert_mean: float = 7.5
    max_decisions_per_alert: int = 9
    seed: int = 42
    category_weights: Mapping[str, float] = field(default_factory=lambda: dict(BOOTSTRAP_CATEGORY_WEIGHTS))
    include_demo_alerts: bool = True
    include_training_alerts: bool = True
    base_epoch_ms: int = 1741046400000
    demo_base_epoch_ms: int = 1748217600000
    demo_status: str = "pending"
    training_status: str = "decided"
    training_origin: str = "zero_day_synthetic"
    demo_origin: str = "zero_day_demo"
    timestamp_step_ms: int | None = None
```

Defaults mirror current counts and metadata from `_pc1.py`. `timestamp_step_ms` is an optional override, not the normal path. When it is `None`, Prompt B must derive timestamp spacing from `time_range_days`, `n_decisions`, and the configured start/end timestamps:

```python
total_window_ms = time_range_days * 24 * 60 * 60 * 1000
timestamp_step_ms = max(1, total_window_ms // max(n_decisions - 1, 1))
```

Generated decision timestamps must span the full configured time range, not a fixed 90-second cadence. The existing `app/services/timestamp_backfill.py` exists because prior seeded synthetic Decision nodes needed to be spread across a 90-day period; the new generator must preserve or replace that behavior at generation time rather than relying on backfill after graph writes.

Validation rules for config:

- all counts are non-negative integers;
- `n_decisions == 0` is valid only if `include_training_alerts` is false or `n_training_alerts > 0`;
- category weights cover exactly `SOC_CATEGORIES`;
- category weights sum to 1.0 within a small epsilon;
- `accuracy_target` is between 0 and 1;
- origins must be `zero_day_synthetic` and `zero_day_demo` unless a migration explicitly changes graph semantics.
- if `timestamp_step_ms` is provided, it must still produce at least 10 unique decision timestamps and must be explicitly documented as a small-fixture override.

## 4. EntityGenerator Design

Create `app/seed/entities.py`.

Use a two-layer architecture:

1. Curated template layer.
   - Keep current users, assets, attack patterns, threat indicators, and campaign archetypes as curated templates.
   - These are meaningful demo entities and are already compatible with graph creation.

2. Generated layer.
   - Generate scalable alert and decision records using templates as pools.
   - Keep generated records deterministic from `SeedConfig.seed`.

Prompt B should preserve the current entity schemas listed in section 2. It should not invent new graph fields unless `seed_graph()` is updated to consume them.

Recommended functions:

- `load_curated_templates(existing_data: dict) -> EntityTemplates`
- `generate_users(config, templates) -> list[dict]`
- `generate_assets(config, templates) -> list[dict]`
- `generate_attack_patterns(config, templates) -> list[dict]`
- `generate_threat_indicators(config, templates) -> list[dict]`

For Prompt B, keep current curated users/assets/patterns/indicators as templates and only trim/extend by deterministic cycling if config counts change. This reduces risk while allowing scalable generation.

## 5. AlertGenerator Design

Create `app/seed/alerts.py`.

The alert generator must use `ALERT_TYPE_CATEGORY_MAP` as the source of truth.

Algorithm:

1. Import `ALERT_TYPE_CATEGORY_MAP`, `SOC_CATEGORIES`, and `BOOTSTRAP_CATEGORY_WEIGHTS`.
2. Invert the map into `category_to_alert_types`.
3. Assert every category in `SOC_CATEGORIES` has at least one alert type.
4. Draw alert category from `SeedConfig.category_weights`.
5. Draw alert type only from `category_to_alert_types[category]`.
6. Assign `category = ALERT_TYPE_CATEGORY_MAP[alert_type]`.
7. Validate the generated pair before returning the alert.

This makes unmapped alert types structurally impossible during normal generation.

### SituationType Coverage

Prompt B should add validation:

- every generated `alert.alert_type` must be in `ALERT_TYPE_CATEGORY_MAP`;
- every `SituationType` value that is intended to be a raw alert type must be in `ALERT_TYPE_CATEGORY_MAP`;
- explicitly exclude SituationType-only values that are classifier outputs, not raw alert types.

Initial excluded SituationType values are the 13 unmapped values from `_pc3.py`. The validation should fail if a future developer adds a new SituationType and forgets either to map it or explicitly classify it as not-a-raw-alert-type.

### Alert Field Schema

Training alerts must match current `alerts` keys:

- `alert_id`
- `category`
- `severity`
- `alert_type`
- `timestamp_epoch`
- `origin`
- `source_location`
- `user_id`
- `status`
- `asset_id`
- `attack_pattern_id`
- `indicator_ids`

Demo alerts must match current `demo_alerts` keys and include the display denormalizations:

- `user_name`
- `asset_hostname`

Training alert defaults:

- `origin = "zero_day_synthetic"`
- `status = "decided"`

Demo alert defaults:

- `origin = "zero_day_demo"`
- `status = "pending"`

The training/demo split should remain because the reset endpoint resets only `zero_day_demo` alerts, while synthetic training data is protected by the state manager and graph cleanup rules. `/api/alerts/reset` filters on `alert.origin = 'zero_day_demo'` in `app/routers/triage.py`.

## 6. CampaignGenerator Design

Create `app/seed/campaigns.py`.

Campaign generation should keep the current campaign field schema from `_pc12.py`.

Design:

- Generate `n_campaigns` campaign records.
- Each campaign owns a deterministic category pattern, such as repeated credential access or multi-stage credential-to-lateral-to-exfiltration.
- Use temporal bursts within `time_range_days`.
- Populate `member_alert_ids` and `alert_ids` from generated training alerts.
- Keep `alert_count = len(member_alert_ids)`.
- Set `first_seen` and `last_seen` from member alert timestamps.
- Relate campaigns to attack patterns by choosing `attack_pattern_id` values whose category matches campaign categories when possible.
- Attach threat indicators through the alert `indicator_ids` list, not by inventing new campaign fields.

`seed_graph()` already creates `Campaign` nodes in Phase 4 and `MEMBER_OF` edges from alerts to campaigns in Phase 7, so Prompt B should preserve these fields rather than changing graph semantics.

Current-state caveat: the existing seed JSON references `attack_pattern_id: "T1537"` in alert records, while the current attack pattern templates list does not include a `T1537` `pattern_id`. Prompt B must resolve this before strict validation can pass by either adding a curated `T1537` attack-pattern template or changing generated/reused alerts so no alert references `T1537`. The validation gate remains strict: every non-empty `attack_pattern_id` must reference an existing attack pattern template.

## 7. DecisionGenerator Design

Create `app/seed/decisions.py`.

Decision generation must be derived from generated training alerts.

Rules:

- Every decision references an existing training alert ID.
- Do not generate decisions for demo alerts by default because current validation checks decision references against `alerts` only.
- Decision `category` must equal the referenced alert category.
- Decision `action` must come from `SCORER_ACTIONS`.
- Decision `factor_vector` length must equal `N_FACTORS`, currently six from `SOC_FACTORS`.
- Decision `timestamp_epoch` must be unique enough for audit and sorted across the configured time range.
- Decision `timestamp` must be an ISO string derived from `timestamp_epoch`.
- `origin = "zero_day_synthetic"`.
- `source_id = "synthetic"`.
- `user_id` should match the referenced alert `user_id`.

Temporal distribution must be derived from `time_range_days` and `n_decisions`. With the default 4,862 decisions and 90-day window, generated timestamps should spread from the configured start epoch through the configured end window using a computed step. A fixed 90-second cadence is not acceptable as the normal path because it covers only a small fraction of the 90-day seed period.

Decision density should use the current observed distribution from `_pc13.py`:

- mean around 7.5 decisions per alert;
- cap at 9 decisions per alert by default;
- spread residual decisions across categories according to category weights.

Accuracy curve:

- early decisions start below `accuracy_target`;
- later decisions converge toward `accuracy_target`;
- per-category accuracy varies around `metadata.p_correct_by_cat` if present;
- generated `correct` is deterministic from seeded RNG and category target probability;
- `outcome = "correct"` when `correct is True`, otherwise `"incorrect"`.

Factor vector generation:

- use category/action centroid shape where available from `SOC_PROFILE_CENTROIDS`;
- add deterministic bounded noise;
- clip values to `[0.0, 1.0]`;
- do not update live centroids.

## 8. Audit Timestamp Pipeline Design

Recommended Prompt B approach: **A. Fix graph-backed audit reconstruction to use Decision timestamps from graph.**

Rationale:

- `seed_graph()` already writes `Decision.timestamp_epoch` from JSON at `app/graph_schema.py:748`.
- `rebuild_from_age()` already converts `timestamp_epoch` into ISO timestamps and passes that into `_LEDGER.append()` at `app/framework/audit.py:324` through `app/framework/audit.py:342`.
- `rebuild_chain_from_graph(client)` reads `d.timestamp_epoch AS ts` but currently drops it when appending ledger entries at `app/framework/audit.py:246` through `app/framework/audit.py:276`.
- Evidence-room APIs read audit row timestamps from ledger entries through `row.get("timestamp")` at `app/services/evidence_room.py:156` and `app/services/evidence_room.py:168`.

Prompt B should:

1. Generate unique, monotonically increasing `decision.timestamp_epoch` values across the configured `SeedConfig.time_range_days` window using derived spacing from `time_range_days` and `n_decisions`.
2. Generate ISO `decision.timestamp` from each epoch for JSON readability and metadata checks.
3. Update `seed_graph()` only if needed to also store `d.timestamp` as an optional property; the primary graph-backed source remains `timestamp_epoch`.
4. Update `rebuild_chain_from_graph(client)` to mirror `rebuild_from_age()` timestamp conversion and pass `timestamp=ts_iso` into `_LEDGER.append()`.
5. Keep `timestamp_backfill.py` as a defensive legacy migration, but no longer rely on it for generated seed correctness.

Generated decision timestamps must flow into audit/evidence timestamps over the same configured window. Prompt B should verify the min/max evidence-room audit timestamps cover the generated seed window after graph-backed audit rebuild.

Regression tests:

- `test_timestamp_uniqueness`
- `test_audit_reconstruct_uses_decision_timestamps`
- `test_rebuild_chain_from_graph_preserves_decision_timestamp_order`

The generator validation gate should require at least 10 unique `decision.timestamp_epoch` values and should fail if all generated decisions share one timestamp. It should also require `max(timestamp_epoch) - min(timestamp_epoch)` to cover at least 80% of `SeedConfig.time_range_days` unless the config explicitly marks a smaller fixture window.

## 9. MetadataDeriver Design

Create `app/seed/metadata.py`.

All metadata counts must be derived from arrays immediately before writing JSON. Do not hand-maintain counts.

Derived fields:

- `generator`
- `version`
- `total_alerts = len(alerts)`
- `total_demo_alerts = len(demo_alerts)`
- `total_decisions = len(decisions)`
- `total_users = len(users)`
- `total_assets = len(assets)`
- `total_attack_patterns = len(attack_patterns)`
- `total_threat_indicators = len(threat_indicators)`
- `total_campaigns = len(campaigns)`
- `days_simulated = config.time_range_days`
- `category_order = list(SOC_CATEGORIES)`
- `action_order = list(SCORER_ACTIONS)`
- `p_correct_by_cat = computed per category from decisions`
- `rng_seed = config.seed`
- `overall_correct_rate = correct decisions / total decisions`

The metadata derivation function should accept the full data dict and return a new metadata dict. It must not trust stale existing metadata.

## 10. Validation Gate Design

Create `app/seed/validate.py`.

Validation must run before `seed_graph()` proceeds. Prompt B should make `app/graph_schema.py` call the full seed validator after JSON load and before graph cleanup/writes.

Required checks:

- every top-level required key exists;
- every required field exists on every record, not only the first three;
- every `alert.alert_type` is in `ALERT_TYPE_CATEGORY_MAP`;
- every `alert.category` equals `ALERT_TYPE_CATEGORY_MAP[alert.alert_type]`;
- every `alert.category` is in `SOC_CATEGORIES`;
- every `decision.category` is in `SOC_CATEGORIES`;
- every `decision.action` is in `SCORER_ACTIONS`;
- every decision `factor_vector` length is `N_FACTORS`;
- every decision `alert_id` exists in generated training `alerts`;
- every alert `user_id` exists;
- every alert `asset_id` exists;
- every alert `attack_pattern_id` exists when non-empty;
- every alert `indicator_ids` value exists in threat indicators;
- every campaign `member_alert_ids` value exists in training alerts;
- no duplicate IDs in users/assets/alerts/demo_alerts/decisions/campaigns/attack_patterns;
- metadata count fields match actual arrays;
- unique decision timestamps count is at least 10;
- decision timestamp min/max span covers at least 80% of the configured time window unless intentionally using a smaller fixture;
- category distribution includes all six categories when counts are large enough;
- `origin` values are only `zero_day_synthetic` or `zero_day_demo`;
- demo alerts are `status = "pending"`;
- training alerts are not `status = "pending"` unless explicitly configured.

Failure behavior:

- validator returns a structured `SeedValidationResult`;
- `seed_graph()` raises `ValueError` with a concise error summary before any graph mutation;
- no partial writes on invalid JSON.

## 11. Consolidation with SOC-ALERT-POOL

`scripts/expand_demo_alerts.py` should be subsumed by `app/seed/alerts.py` and `app/seed/runner.py`.

Migration path:

1. Keep `expand_demo_alerts.py` temporarily for reference.
2. Implement demo alert generation in `AlertGenerator` using `ALERT_TYPE_CATEGORY_MAP`.
3. Add tests proving demo category coverage and `>= 100` demo alerts.
4. Update docs and workflow instructions to run `scripts/generate_seed.py` instead of `scripts/expand_demo_alerts.py`.
5. Remove or deprecate `expand_demo_alerts.py` in a later cleanup prompt after generator adoption.

The new generator should preserve the current demo behavior:

- `origin = "zero_day_demo"`;
- `status = "pending"`;
- reset endpoint compatibility;
- display fields `user_name` and `asset_hostname`.

## 12. File Layout for Prompt B

Prompt B should create:

```text
backend/
  app/seed/
    __init__.py
    config.py
    entities.py
    alerts.py
    campaigns.py
    decisions.py
    metadata.py
    validate.py
    runner.py
  scripts/generate_seed.py
```

Prompt B should modify:

```text
backend/
  app/graph_schema.py
  app/framework/audit.py
  support/setup/zero_day_decisions_v5.json
```

Prompt B should add tests under:

```text
backend/tests/
  test_seed_generator.py
  test_seed_validation.py
  test_seed_graph_validation_gate.py
  test_audit_seed_timestamps.py
```

No frontend, SDK, S2P, ci-platform, or GAE files are needed.

## 13. Migration Plan

Phase 1: Generator produces compatible output.

- Implement `SeedConfig`, entity templates, alert generation, decision generation, metadata derivation, and runner.
- Generate into memory first.
- Validate generated output without writing graph.

Phase 2: Compatibility tests.

- Assert generated schema matches current JSON field sets.
- Assert generated JSON can be read by `seed_graph()` validation.

Phase 3: Replace static JSON with generated output.

- Run `python scripts/generate_seed.py --output support/setup/zero_day_decisions_v5.json`.
- Preserve stable formatting with `json.dumps(..., indent=2) + "\n"`.

Phase 4: Validation gate before `seed_graph()`.

- Add full seed validation call immediately after JSON load in `seed_graph()`.
- Keep or wrap existing `_validate_json()` for backwards compatibility.

Phase 5: Consolidate alert pool generator.

- Make generated `demo_alerts` satisfy the existing alert-pool tests.
- Mark `scripts/expand_demo_alerts.py` as legacy or remove in a follow-up only after review.

Phase 6: Audit timestamp path.

- Ensure generated decisions have unique epoch and ISO timestamps.
- Make graph-backed audit rebuild preserve `timestamp_epoch` as ledger timestamps.
- Keep timestamp backfill as legacy protection, not a primary mechanism.

## 14. Test Plan

1. `test_generated_schema_matches_current`: generated section keys match current JSON section keys.
2. `test_alert_generator_uses_alert_type_map`: every generated alert type is in `ALERT_TYPE_CATEGORY_MAP`.
3. `test_alert_category_matches_alert_type_map`: generated category equals mapped category.
4. `test_situation_types_covered_by_alert_type_map`: every raw-alert SituationType is mapped or explicitly excluded.
5. `test_metadata_counts_derived`: metadata counts equal actual array lengths.
6. `test_decisions_reference_existing_alerts`: every decision references a training alert.
7. `test_alerts_reference_existing_users_assets`: every alert references existing user and asset IDs.
8. `test_campaign_member_alerts_exist`: every campaign member alert exists.
9. `test_indicator_refs_exist`: every alert indicator ID exists.
10. `test_timestamp_uniqueness`: generated decisions have at least 10 unique timestamps and preferably all unique.
11. `test_seed_validation_rejects_unmapped_alert_type`: validator fails a bad alert type.
12. `test_seed_validation_rejects_stale_metadata`: validator fails stale `total_demo_alerts`.
13. `test_seed_validation_rejects_orphan_decision`: validator fails nonexistent `decision.alert_id`.
14. `test_seed_graph_refuses_invalid_seed`: `seed_graph()` raises before graph writes on invalid data.
15. `test_audit_reconstruct_uses_decision_timestamps`: graph-backed audit rows expose generated timestamps.
16. `test_generator_deterministic_same_seed`: same seed yields byte-stable JSON.
17. `test_generator_changes_with_different_seed`: different seed changes generated IDs or ordering predictably.
18. `test_generator_scalable_counts`: custom counts produce requested section sizes.
19. `test_demo_training_origin_split_preserved`: training/demo origins and statuses match reset semantics.
20. `test_no_orphan_decisions_after_generated_seed`: generated data has no orphan decisions.
21. `test_demo_alert_pool_has_100`: generated demo alert count remains at least 100.
22. `test_all_six_categories_present`: alerts and demo alerts cover all six SOC categories.

## 15. Prompt B Implementation Plan

First implementation slice:

1. Implement `app/seed/config.py`.
2. Implement `app/seed/entities.py` by loading current curated templates.
3. Implement `app/seed/alerts.py` using inverted `ALERT_TYPE_CATEGORY_MAP`.
4. Implement `app/seed/decisions.py` with unique timestamps.
5. Implement `app/seed/metadata.py`.
6. Implement `app/seed/validate.py`.
7. Implement `app/seed/runner.py` and `scripts/generate_seed.py`.
8. Add generator and validation tests.
9. Update `app/graph_schema.py` to call full validation before graph mutation.
10. Update `app/framework/audit.py::rebuild_chain_from_graph()` to pass ISO timestamps into ledger entries.
11. Run generator once to update `support/setup/zero_day_decisions_v5.json`.

Defer if too large:

- deleting `scripts/expand_demo_alerts.py`;
- replacing timestamp backfill;
- generating new campaign narratives beyond current templates;
- adding CLI flags beyond config/output/validate.

Validation commands for Prompt B:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python scripts\generate_seed.py --output support\setup\zero_day_decisions_v5.json
python -m pytest tests\test_seed_generator.py tests\test_seed_validation.py tests\test_seed_graph_validation_gate.py tests\test_audit_seed_timestamps.py -v --timeout=300
python -m pytest tests\test_alert_pool_size.py tests\test_jdoe_discovery.py::test_jdoe_seed_metadata_counts_match_sections -v --timeout=300
python -m pytest tests\ -q --timeout=300
```

Expected manual reseed command after Prompt B review, not during Prompt B unless explicitly requested:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m app.graph_schema --seed support\setup\zero_day_decisions_v5.json --clean
```

If the repository does not currently expose a `python -m app.graph_schema --seed ...` CLI, Prompt B must report the actual existing reseed command rather than inventing one.

## 16. Risks and Open Questions

- The current `seed_graph()` Decision create block ignores JSON `decision.timestamp`; Prompt B must decide whether to store it as a graph property or rely only on `timestamp_epoch`.
- `rebuild_chain_from_graph(client)` and `rebuild_from_age()` overlap; Prompt B should confirm which path runs on startup before editing only one.
- Current `_validate_json()` validates decisions against `alerts` only, not `demo_alerts`; the generator design intentionally keeps decisions on training alerts unless requirements change.
- Current seed data references `attack_pattern_id: "T1537"` but does not include a matching `T1537` attack-pattern template. Prompt B must either add the template or stop generating/reusing that reference before strict validation is enabled.
- The 4862-decision baseline passed, but live graph state may still differ from JSON after manual experiments. Generator validation should test JSON, not live AGE.
- Large generated JSON should remain git-trackable. Use deterministic ordering and stable indentation.
- Performance for 10,000+ decisions should be measured before increasing default counts.
- `SituationType` contains classifier labels, not just raw alert types; validation must keep the explicit exclusion list clear to avoid false positives.
- `scripts/expand_demo_alerts.py` hardcodes category metadata. Keeping it around temporarily can confuse future maintainers unless documentation marks it legacy.

## 17. READY_FOR_PROMPT_B

YES.

Prompt B has enough information to implement without rediscovering architecture:

- current schema fields are known;
- `ALERT_TYPE_CATEGORY_MAP` is the alert type source of truth;
- SituationType coverage behavior is known;
- seed graph phases and validation gaps are known;
- audit timestamp weakness and recommended fix are known;
- timestamp spacing must be derived from config, with no fixed default cadence;
- the `T1537` attack-pattern template/reference mismatch is identified and must be resolved;
- file layout and test plan are concrete.
