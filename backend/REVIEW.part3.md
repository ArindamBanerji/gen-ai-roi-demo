# SOC Backend Line-by-Line Review — Part 3

## app/domains/soc/config.py (884 lines)

### Architecture
- This module centralizes SOC domain constants, ProfileScorer geometry, alert-type routing, category/action/factor metadata, policy/situation/prompt/metrics metadata, gate configuration, and calibration formulas (`app/domains/soc/config.py:1-884`).
- Demo and product features depending on it include triage scoring/routing, GAE bootstrap, ProfileScorer construction, outcome feedback pattern selection, domain registry warm-up, simulation, Tab 2 profile/IKS surfaces, campaign correlation defaults, and threshold/gate behavior (`app/domains/soc/config.py:45-120`, `app/domains/soc/config.py:122-230`, `app/domains/soc/config.py:276-312`, `app/domains/soc/config.py:672-745`, `app/domains/soc/config.py:782-884`).
- It encodes compiled SOC expertise as static action/category/factor lists, centroid tensors, W priors, bootstrap distributions, thresholds, alert-type mappings, pattern mappings, campaign settings, and deployment gate formulas. Comments claim constants were extracted from existing services (`app/domains/soc/config.py:1-11`); the active code is now also a primary source for current ProfileScorer action/category/factor contracts.

### Function-by-Function Review

- **SOC_ACTIONS** (line 45)
  - Purpose: Full routing action list.
  - Inputs: None.
  - Logic: Static list `["escalate", "investigate", "suppress", "monitor", "refer_to_analyst"]`.
  - Output: Module constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Defines A=5 routing surface.

- **SCORER_ACTIONS / SOC_SCORING_ACTIONS / SOC_ROUTING_ACTIONS / SOC_N_ACT** (line 50-56)
  - Purpose: Splits A=4 scorer actions from A=5 routing actions.
  - Inputs: None.
  - Logic: `SCORER_ACTIONS` excludes `refer_to_analyst`; aliases and count derive from it.
  - Output: Module constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Scorer geometry must use `SCORER_ACTIONS`; routing/NL can use full list.

- **LEARNING_ENABLED** (line 61)
  - Purpose: Global feature flag for ProfileScorer updates after verified outcomes.
  - Inputs: None.
  - Logic: Static `False`.
  - Output: Bool constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Keeps live ProfileScorer frozen unless changed.

- **SOC_CATEGORIES / BOOTSTRAP_CATEGORY_WEIGHTS** (line 63-83)
  - Purpose: Ordered category axis and bootstrap sampling distribution.
  - Inputs: None.
  - Logic: Six categories and weights summing to 1.0 by inspection.
  - Output: Lists/dicts consumed by scorer/bootstrap.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No runtime assertion checks weight sum or category coverage.

- **SOC_FACTORS / N_FACTORS / N_CATEGORIES / N_ACTIONS / SOC_FACTOR_SIGMA** (line 89-111)
  - Purpose: Ordered factor axis, derived tensor dimensions, and per-factor sigma.
  - Inputs: None.
  - Logic: Factor order is `privileged_identity_context`, `asset_criticality`, `threat_intel_enrichment`, `pattern_history`, `time_anomaly`, `device_trust`; dimensions derive from list lengths; sigma maps by factor name.
  - Output: Constants used by tensor reshape and explainability.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `SOC_PROFILE_CENTROIDS` reshape enforces product size later; no explicit sigma coverage assertion.

- **SOC_BOOTSTRAP_* constants** (line 116-120)
  - Purpose: GAE bootstrap calibration parameters.
  - Inputs: None.
  - Logic: Rounds 10, samples/action 5, sigma 0.08, tolerance 0.01, seed 42.
  - Output: Constants consumed by `gae_state.init_learning_state()`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Static values only.

- **SOC_PROFILE_CENTROIDS / SCORER_PROFILE_CENTROIDS** (line 122-205)
  - Purpose: ProfileScorer centroid tensor.
  - Inputs: None.
  - Logic: Builds a NumPy array and reshapes to `(N_CATEGORIES, N_ACTIONS, N_FACTORS)` = `(6, 4, 6)`; `SCORER_PROFILE_CENTROIDS` aliases it.
  - Output: NumPy tensor.
  - Side effects: Raises at import if reshape size mismatches.
  - GAE calls: None directly; consumed by `ProfileScorer`.
  - Error handling: NumPy reshape errors would propagate at import.
  - Invariants/guards: Shape is enforced by `.reshape(N_CATEGORIES, N_ACTIONS, N_FACTORS)`.

- **SOC_AUTO_APPROVE_THRESHOLDS / SOC_CATEGORY_CONFIDENCE_FLOORS / SOC_AGENT_ZONE_ELEVATED** (line 213-230)
  - Purpose: Triage routing threshold configuration.
  - Inputs: None.
  - Logic: Auto-approve only escalate/investigate/suppress at 0.90; monitor and refer are excluded; credential access floor is 0.95; malware/cloud categories are elevated to agent zone.
  - Output: Dict constants consumed by triage.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `None` values intentionally block auto-approval.

- **ALERT_TYPE_CATEGORY_MAP / DEFAULT_CATEGORY / resolve_alert_category** (line 235-298)
  - Purpose: Single alert-type to SOC category router.
  - Inputs: `resolve_alert_category(alert_type: str)`.
  - Logic: Looks up the map; on missing key logs `ROUTING_FAILURE` and falls back to `"credential_access"`.
  - Output: Category string.
  - Side effects: Error logging on unmapped alert type.
  - GAE calls: None.
  - Error handling: No exception for unknown types; fallback is returned.
  - Invariants/guards: Comments assert this is the single routing point; code does not enforce that no other mappings exist.

- **resolve_alert_category** (line 276-298)
  - Purpose: Explicit function coverage alias for the alert-type router reviewed above.
  - Inputs: `alert_type: str`.
  - Logic: Map lookup with error-log fallback to `DEFAULT_CATEGORY`.
  - Output: SOC category string.
  - Side effects: Error log on missing mapping.
  - GAE calls: None.
  - Error handling: Unknown types do not raise.
  - Invariants/guards: Fallback category is always returned.

- **CATEGORY_PATTERN_MAP** (line 303-312)
  - Purpose: Maps SOC category to canonical pattern ID for feedback.
  - Inputs: None.
  - Logic: Static dict with `_default`.
  - Output: Dict consumed by `get_pattern_for_category()` and feedback.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `_default` fallback exists.

- **SOCDomainConfig.name / display_name / trigger_entity** (line 323-332)
  - Purpose: Domain identity metadata.
  - Inputs: `self`.
  - Logic: Returns `"soc"`, `"SOC Copilot"`, and `"Alert"`.
  - Output: Strings.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Fixed metadata.

- **SOCDomainConfig.factors** (line 348-395)
  - Purpose: Returns human-readable domain factor metadata.
  - Inputs: `self`.
  - Logic: Returns six `DomainFactor` objects.
  - Output: List of `DomainFactor`.
  - Side effects: Allocates new objects on each access.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No assertion that this display order matches `SOC_FACTORS`.

- **SOCDomainConfig.actions** (line 406-443)
  - Purpose: Returns legacy/domain action metadata.
  - Inputs: `self`.
  - Logic: Returns five `DomainAction` objects with time/cost/risk metadata from older action vocabulary.
  - Output: List of `DomainAction`.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Does not match `SCORER_ACTIONS` or `SOC_ACTIONS` IDs.

- **SOCDomainConfig.situation_types** (line 453-508)
  - Purpose: Returns six situation-type descriptors for UI/domain registry.
  - Inputs: `self`.
  - Logic: Static list of `DomainSituationType` objects with IDs, labels, descriptions, colors.
  - Output: List.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No cross-check against `services/situation.py`.

- **SOCDomainConfig.policies** (line 519-561)
  - Purpose: Returns SOC policy descriptors.
  - Inputs: `self`.
  - Logic: Static list of four `DomainPolicy` objects.
  - Output: List.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No cross-check against runtime policy registry.

- **SOCDomainConfig.asymmetry_ratio** (line 571-572)
  - Purpose: Exposes asymmetric reward ratio.
  - Inputs: `self`.
  - Logic: Returns `20.0`.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Hardcoded.

- **SOCDomainConfig.prompt_variants** (line 583-609)
  - Purpose: Returns prompt-variant metadata.
  - Inputs: `self`.
  - Logic: Static list of four `PromptVariant` objects.
  - Output: List.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No runtime sync with evolver state.

- **SOCDomainConfig.metrics_config** (line 617-623)
  - Purpose: Returns business impact constants.
  - Inputs: `self`.
  - Logic: Static dict for saved hours, avoided cost, MTTR reduction, backlog eliminated.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Hardcoded numbers with no source check in code.

- **SOCDomainConfig.get_profile_centroids / get_initial_centroids / get_categories** (line 630-644)
  - Purpose: Accessors for centroid tensor and category order.
  - Inputs: `self`.
  - Logic: Return copies/lists of constants.
  - Output: NumPy tensor copy or category list.
  - Side effects: None.
  - GAE calls: None directly.
  - Error handling: None.
  - Invariants/guards: Tensor access returns copies to prevent direct mutation.

- **SOCDomainConfig.get_category_index** (line 646-654)
  - Purpose: Maps category name to category-axis index.
  - Inputs: Category string.
  - Logic: Uses `SOC_CATEGORIES.index()`; wraps `ValueError` with valid categories.
  - Output: Int.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `ValueError` on unknown category.
  - Invariants/guards: Unknown category guard.

- **SOCDomainConfig.get_auto_approve_threshold / get_pattern_for_category** (line 656-670)
  - Purpose: Lookup helpers for routing threshold and feedback pattern.
  - Inputs: Action or category string.
  - Logic: Returns threshold or `None`; returns category pattern with `_default` fallback.
  - Output: Float/None or pattern ID string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: No exception.
  - Invariants/guards: Pattern fallback; no action validation.

- **SOCDomainConfig.build_profile_scorer** (line 672-689)
  - Purpose: Constructs GAE ProfileScorer for SOC.
  - Inputs: `self`.
  - Logic: Calls `ProfileScorer(mu=SCORER_PROFILE_CENTROIDS.copy(), actions=SCORER_ACTIONS, kernel=KernelType.L2, categories=SOC_CATEGORIES, eta_override=0.01, auto_pause_on_amber=True)`.
  - Output: GAE `ProfileScorer`.
  - Side effects: Allocates scorer.
  - GAE calls: Direct `ProfileScorer` constructor and `KernelType.L2`.
  - Error handling: Constructor exceptions propagate.
  - Invariants/guards: Uses copied centroids and A=4 actions; hardcodes `eta_override=0.01`.

- **SOCDomainConfig.get_actions / get_factor_computers / get_campaign_config** (line 692-718)
  - Purpose: Static accessors for routing actions, ordered factor computers, and campaign defaults.
  - Inputs: None.
  - Logic: Returns copies/new instances. Factor order is `PrivilegedIdentityContextFactor`, `AssetCriticalityFactor`, `ThreatIntelEnrichmentFactor`, `PatternHistoryFactorComputer`, `TimeAnomalyFactor`, `DeviceTrustFactor`.
  - Output: List/dict.
  - Side effects: Allocates factor computers.
  - GAE calls: Returns `FactorComputer` implementations.
  - Error handling: None.
  - Invariants/guards: Factor-computer order matches `SOC_FACTORS`.

- **SOCDomainConfig.get_factor_computers** (line 700-709)
  - Purpose: Explicit method coverage alias for the ordered GAE factor-computer factory reviewed above.
  - Inputs: None.
  - Logic: Instantiates the six scorer factors in `SOC_FACTORS` order.
  - Output: List of factor-computer instances.
  - Side effects: Allocates new objects each call.
  - GAE calls: Returns GAE `FactorComputer` implementations.
  - Error handling: None.
  - Invariants/guards: Order must remain synchronized with centroid factor axis.

- **SOCDomainConfig.get_initial_W / get_temperature** (line 726-745)
  - Purpose: Legacy/GAE W-matrix priors and softmax temperature.
  - Inputs: None.
  - Logic: Returns `(N_ACTIONS, N_FACTORS)` NumPy matrix and `0.1`.
  - Output: Matrix/float.
  - Side effects: None.
  - GAE calls: None directly; consumed by learning-state creation.
  - Error handling: Reshape errors propagate if dimensions mismatch.
  - Invariants/guards: W row order matches `SCORER_ACTIONS`; tau fixed at 0.1.

- **SOCDomainConfig.get_seed_queries / get_graph_query_templates / get_narration_templates** (line 751-761)
  - Purpose: Stub extension points.
  - Inputs: `self`.
  - Logic: Return empty list/dicts.
  - Output: Empty collections.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Explicit TODO stubs.

- **soc_config / MAX_ETA_DELTA** (line 765-775)
  - Purpose: Singleton domain config and eta delta constant.
  - Inputs: None.
  - Logic: Instantiates `SOCDomainConfig`; sets max eta delta to `0.005`.
  - Output: Module globals.
  - Side effects: Singleton allocation at import.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `MAX_ETA_DELTA` mirrors external GAE enforcement by comment, not local code.

- **compute_theta_min** (line 782-795)
  - Purpose: Computes minimum analyst quality threshold.
  - Inputs: `alpha`, `V`.
  - Logic: Returns infinity if either is nonpositive; otherwise `23.53 / (alpha * V)`.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Nonpositive guard.
  - Invariants/guards: Division-by-zero guard.

- **compute_phase3_minimum** (line 802-812)
  - Purpose: Computes minimum verified decisions before self-calibrating gates.
  - Inputs: `V`, `alpha`.
  - Logic: `max(1000, int(20 * V * alpha))`.
  - Output: Int.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Lower bound of 1000 decisions.

- **GateConfig dataclass and fields** (line 820-830)
  - Purpose: Holds deployment gate inputs.
  - Inputs: `n_decisions`, optional `V`, `alpha`, `vol_std`, `per_analyst_precision`.
  - Logic: Dataclass stores fields with defaults.
  - Output: Config object.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Uses `default_factory=dict` for per-analyst precision.

- **GateConfig.n_min / calibrated / spike_sigma / eta_cap / eta_weights / summary** (line 833-884)
  - Purpose: Derived gate properties and summary serialization.
  - Inputs: `self`.
  - Logic: `n_min` calls `compute_phase3_minimum`; `calibrated` compares decisions; `spike_sigma` returns 5.0 before calibration and 3.0 after; `eta_cap` returns 2.0 before calibration, otherwise derived from `vol_std`; `eta_weights` returns uniform or mean-normalized precision weights clipped to `[0.5, 1.5]`; `summary` returns a dict.
  - Output: Int/bool/float/dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Negative precision values fall back to uniform weights.
  - Invariants/guards: Eta weights clipped; nonpositive mean precision falls back to uniform.

### Invariants Enforced
- Tensor shape is enforced by `SOC_PROFILE_CENTROIDS.reshape(N_CATEGORIES, N_ACTIONS, N_FACTORS)` (`app/domains/soc/config.py:122-199`).
- ProfileScorer scoring action list is A=4 and excludes `refer_to_analyst` (`app/domains/soc/config.py:45-56`, `app/domains/soc/config.py:672-689`).
- Temperature is fixed at `0.1` in `get_temperature()` (`app/domains/soc/config.py:744-745`).
- Unknown category names raise in `get_category_index()` (`app/domains/soc/config.py:646-654`).
- Unknown alert types log an error and fall back to `DEFAULT_CATEGORY` (`app/domains/soc/config.py:273-298`).
- `compute_theta_min()` returns infinity for nonpositive inputs (`app/domains/soc/config.py:782-795`).
- `compute_phase3_minimum()` enforces a 1000-decision floor (`app/domains/soc/config.py:802-812`).
- `GateConfig.eta_weights` clips calibrated weights to `[0.5, 1.5]` and falls back to uniform for invalid precision inputs (`app/domains/soc/config.py:855-874`).

### Potential Issues

#### P1
- Display/domain factor order in `SOCDomainConfig.factors` is `[privileged_identity_context, asset_criticality, threat_intel_enrichment, time_anomaly, device_trust, pattern_history]` (`app/domains/soc/config.py:348-395`), while scorer/tensor/factor-computer order is `[privileged_identity_context, asset_criticality, threat_intel_enrichment, pattern_history, time_anomaly, device_trust]` (`app/domains/soc/config.py:89-96`, `app/domains/soc/config.py:700-709`). Any consumer treating `config.factors` as the tensor order will mislabel factor values.
- `DeviceTrustFactor` computes higher values for less trusted devices (`app/domains/soc/factors.py:580-590`), but the centroid tensor comments and values treat low `device_trust` as risky/escalating and high `device_trust` as suppressing/trusted (`app/domains/soc/config.py:129-136`, `app/domains/soc/config.py:141-148`, `app/domains/soc/config.py:193-196`). This inversion can materially mis-score device trust.

#### P2
- `SOCDomainConfig.actions` exposes legacy action IDs (`false_positive_close`, `auto_remediate`, `enrich_and_wait`, `escalate_tier2`, `escalate_incident`) that do not match `SOC_ACTIONS`/`SCORER_ACTIONS` (`app/domains/soc/config.py:45-56`, `app/domains/soc/config.py:406-443`). Domain registry/UI consumers can receive a different action vocabulary than triage/scoring.
- `resolve_alert_category()` logs but still falls back to `credential_access` for unmapped alert types (`app/domains/soc/config.py:273-298`). That keeps demos alive but can route unknown production alerts into a specific category.
- Bootstrap weights claim "must sum to 1.0" but no assertion enforces sum or coverage against `SOC_CATEGORIES` (`app/domains/soc/config.py:72-83`).
- `MAX_ETA_DELTA` is declared locally but not enforced locally (`app/domains/soc/config.py:775`); the comment says enforcement lives in GAE.

#### P3
- Import `build_profile_scorer` and `CalibrationProfile` are unused in this file (`app/domains/soc/config.py:15-16`).
- The module docstring says constants are extracted from existing service files (`app/domains/soc/config.py:1-11`), but this file now defines active scorer geometry and gate formulas; the comment understates current ownership.
- `get_seed_queries()`, `get_graph_query_templates()`, and `get_narration_templates()` are TODO stubs returning empty structures (`app/domains/soc/config.py:751-761`).

### Cross-Module Dependencies
- `app/services/gae_state.py` consumes bootstrap constants, categories/actions, ProfileScorer construction, and initial W (`app/domains/soc/config.py:25-30`, `app/domains/soc/config.py:116-120`, `app/domains/soc/config.py:672-738`).
- `app/routers/triage.py` consumes thresholds, elevated categories, `LEARNING_ENABLED`, `SCORER_ACTIONS`, `resolve_alert_category()`, `get_category_index()`, factor computers, and campaign config (`app/domains/soc/config.py:213-230`, `app/domains/soc/config.py:276-298`, `app/domains/soc/config.py:646-718`).
- `app/services/feedback.py` consumes `get_pattern_for_category()` and category pattern mapping (`app/domains/soc/config.py:303-312`, `app/domains/soc/config.py:663-670`).
- `app/core/domain_registry.py` relies on `soc_config = SOCDomainConfig()` and properties such as factors/actions/situation_types/policies/prompt variants/metrics (`app/domains/soc/config.py:315-765`).
- GAE ProfileScorer requires the category/action/factor axis order to remain synchronized across `SOC_CATEGORIES`, `SCORER_ACTIONS`, `SOC_FACTORS`, `SCORER_PROFILE_CENTROIDS`, and factor-computer output (`app/domains/soc/config.py:50-100`, `app/domains/soc/config.py:122-205`, `app/domains/soc/config.py:672-709`).

## app/domains/soc/factors.py (884 lines)

### Architecture
- This module implements SOC factor computers and legacy decision-factor templates. Its active GAE path exposes factor classes for privileged identity, asset criticality, threat intel/campaign enrichment, pattern history/W2, time anomaly, and device trust (`app/domains/soc/factors.py:50-590`).
- Triage scoring depends on `SOCDomainConfig.get_factor_computers()` instantiating these classes in the order expected by `SOC_FACTORS`; explainability/legacy endpoints depend on `SOC_FACTOR_TEMPLATES`, `_contribution()`, and `compute_soc_factors()` (`app/domains/soc/config.py:700-709`, `app/domains/soc/factors.py:601-884`).
- It bridges to GAE through `gae.contracts.SchemaContract`, `PropertySpec`, and `gae.factors.FactorComputer` (`app/domains/soc/factors.py:17-18`). Comments claim four factors use Cypher traversal and two read properties (`app/domains/soc/factors.py:1-9`); active code includes a non-scorer `TravelMatchFactor` and both relationship-traversal and property-read paths.

### Function-by-Function Review

- **log** (line 20)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_get** (line 27-31)
  - Purpose: Unified dict/object value getter.
  - Inputs: Object/dict, key, default.
  - Logic: Uses `dict.get()` for dicts, otherwise `getattr()`.
  - Output: Value or default.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_S** (line 34-42)
  - Purpose: Serializes values into inline AGE Cypher literals.
  - Inputs: Any scalar-like value.
  - Logic: Handles `None`, bool, int/float, escaped string.
  - Output: Cypher literal string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Avoids `$param` when used; does not support list/tuple JSON unlike `gae_state._S`.

- **PrivilegedIdentityContextFactor constants** (line 58-68)
  - Purpose: Names factor and declares optional schema property default `0.5`.
  - Inputs: None.
  - Logic: Static `name` and `SchemaContract`.
  - Output: Class constants.
  - Side effects: Instantiates GAE contract objects at import.
  - GAE calls: `SchemaContract`, `PropertySpec`.
  - Error handling: None.
  - Invariants/guards: Default neutral value `0.5`.

- **PrivilegedIdentityContextFactor._clamp** (line 71-72)
  - Purpose: Bounds values to `[0, 1]`.
  - Inputs: Float-like value.
  - Logic: Converts to float, clamps min/max.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Conversion errors propagate.
  - Invariants/guards: Range clamp.

- **PrivilegedIdentityContextFactor._title_risk** (line 75-85)
  - Purpose: Converts user title into risk heuristic.
  - Inputs: Optional title.
  - Logic: Admin/service/system tokens -> 0.9; executive tokens -> 0.7; other nonempty title -> 0.2; missing/blank -> None.
  - Output: Float or None.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Case/whitespace normalization.

- **PrivilegedIdentityContextFactor._resolve_context / compute** (line 88-136)
  - Purpose: Computes privileged identity factor from resolved context.
  - Inputs: Entity/alert/context.
  - Logic: Selects context from explicit `context`, entity, or nested `security_context`; averages available user risk, title risk, MFA risk, and fingerprint risk; returns neutral `0.5` if no components.
  - Output: Float in `[0, 1]`.
  - Side effects: None.
  - GAE calls: Implements GAE `FactorComputer` protocol.
  - Error handling: Bad `risk_score` conversion is ignored.
  - Invariants/guards: Missing context -> 0.5; final clamp.

- **TravelMatchFactor constants / compute** (line 139-197)
  - Purpose: Computes travel-match factor from User->TravelRecord traversal.
  - Inputs: Alert-like object and graph client.
  - Logic: Requires user ID and source location; queries matching travel records; score is `cnt/(cnt+3)` plus recent travel boost capped at 1.0.
  - Output: Float in `[0, 1]` or 0.5 fallback.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects but does not subclass `FactorComputer`.
  - Error handling: Query errors log warning and return 0.5; recency conversion errors are swallowed.
  - Invariants/guards: Missing user/geo -> 0.5; count zero -> 0.5; clamp.

- **AssetCriticalityFactor constants / compute** (line 200-256)
  - Purpose: Computes asset criticality and data sensitivity factor.
  - Inputs: Alert-like object and graph client.
  - Logic: Requires alert ID; traverses Alert->Asset and optional Asset->DataClass; maps criticality to score and adds 0.1 sensitivity boost capped at 1.0.
  - Output: Float.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects.
  - Error handling: Query errors log warning and return 0.5.
  - Invariants/guards: Missing/no result -> 0.5; sensitivity cap.

- **ThreatIntelEnrichmentFactor constants** (line 268-282)
  - Purpose: Names factor, schema contract, and severity map.
  - Inputs: None.
  - Logic: Defines optional default `0.0` and severity map from info to critical.
  - Output: Class constants.
  - Side effects: Instantiates GAE contract objects.
  - GAE calls: `SchemaContract`, `PropertySpec`.
  - Error handling: None.
  - Invariants/guards: Default no-intel value 0.0.

- **ThreatIntelEnrichmentFactor.compute** (line 284-320)
  - Purpose: Combines IOC and internal campaign threat-intel scoring.
  - Inputs: Alert-like object and graph client.
  - Logic: Gets alert ID; pass 1 queries `HAS_INDICATOR` severities/sources, maps max severity plus multi-source boost; pass 3 calls `_internal_campaign_score`; returns the pass with the lowest `value`.
  - Output: Float.
  - Side effects: Graph reads.
  - GAE calls: Implements GAE factor protocol.
  - Error handling: Pass 1 errors log and continue with 0.0; campaign helper handles its own errors.
  - Invariants/guards: Missing alert ID -> 0.0.

- **ThreatIntelEnrichmentFactor._internal_campaign_score** (line 322-372)
  - Purpose: Scores campaign membership.
  - Inputs: Alert ID and graph client.
  - Logic: Queries Alert->Campaign membership, returns neutral 0.50 if absent; high severity -> 0.05, medium -> 0.20, low -> 0.40 plus provenance.
  - Output: Dict with `value`, `provenance_nodes`, `contribution`.
  - Side effects: Graph read.
  - GAE calls: None directly.
  - Error handling: Any exception logs and returns neutral 0.50.
  - Invariants/guards: Never raises by design.

- **PatternHistoryFactor constants / compute** (line 375-429)
  - Purpose: Legacy historical accuracy factor by alert type.
  - Inputs: Alert-like object and graph client.
  - Logic: Reads alert type/situation type; queries Decision->Alert outcomes for same alert type; returns 0.5 until at least 5 resolved, then correct/total clipped.
  - Output: Float in `[0, 1]`.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects.
  - Error handling: Query errors log and return 0.5.
  - Invariants/guards: Missing type -> 0.5; minimum decision count 5; clip.

- **PatternHistoryFactorComputer constants / compute / _fallback_compute** (line 432-523)
  - Purpose: W2 compounding pattern-history factor used in scorer order.
  - Inputs: Alert-like object, graph client, optional action index.
  - Logic: Reads category or alert type; if no category returns fallback 0.40; otherwise queries `TRIGGERED_EVOLUTION` decisions optionally by action, reads `d.factor_snapshot[3]` and `d.decision_number`, computes recency-weighted mean with half-life 30, clips to `[0,1]`; fallback returns 0.40.
  - Output: Float.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects.
  - Error handling: Query errors log and fallback; no guard around malformed result values after query succeeds.
  - Invariants/guards: Missing/no results -> 0.40; recency weighting; clip.

- **TimeAnomalyFactor constants / compute** (line 526-556)
  - Purpose: Scores time anomaly from alert properties.
  - Inputs: Alert-like object and unused graph client.
  - Logic: Weekend login -> 1.0; business hours true -> 0.0; business hours false -> 0.7; missing -> 0.7.
  - Output: Float.
  - Side effects: None.
  - GAE calls: Uses GAE contract objects.
  - Error handling: None.
  - Invariants/guards: Conservative missing-data default 0.7.

- **DeviceTrustFactor constants / compute** (line 559-590)
  - Purpose: Scores device trust/untrustedness from alert properties.
  - Inputs: Alert-like object and unused graph client.
  - Logic: Coerces MFA, fingerprint, and VPN flags to bool; missing VPN inferred from `vpn_provider`; returns count of untrusted flags divided by 3.
  - Output: Float from 0.0 to 1.0.
  - Side effects: None.
  - GAE calls: Uses GAE contract objects.
  - Error handling: None.
  - Invariants/guards: Missing flags count as untrusted except VPN provider inference.

- **SOC_FACTOR_TEMPLATES** (line 601-802)
  - Purpose: Backward-compatible static explainability templates.
  - Inputs: None.
  - Logic: Dict keyed by alert ID, alert type, and `_default`; each template has recommended action, confidence, and five static factors; `compute_soc_factors()` inserts threat-intel at position 2.
  - Output: Module constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `_default` exists; some template factor names are legacy/non-SOC names.

- **_contribution** (line 805-814)
  - Purpose: Maps `value * weight` to contribution label.
  - Inputs: Numeric value and weight.
  - Logic: >0.5 high, >0.25 medium, >0 low, otherwise none.
  - Output: String label.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Numeric errors propagate.
  - Invariants/guards: Threshold ordering.

- **compute_soc_factors** (line 817-884)
  - Purpose: Builds six-factor explainability breakdown for legacy/services route.
  - Inputs: `alert_id`, optional `ti_factor`, optional `alert_type`.
  - Logic: Chooses template by alert ID, alert type, or `_default`; computes contribution labels for static factors; creates default threat-intel factor if absent; returns static first two + threat-intel + remaining static factors plus recommendation/confidence/notes.
  - Output: Dict matching decision-factor endpoint shape.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Template structure errors propagate.
  - Invariants/guards: Fallback template and default threat-intel factor.

### Invariants Enforced
- Most factor `contract` objects define optional properties with default values (`app/domains/soc/factors.py:59-68`, `app/domains/soc/factors.py:211-216`, `app/domains/soc/factors.py:269-274`, `app/domains/soc/factors.py:451-456`, `app/domains/soc/factors.py:538-543`, `app/domains/soc/factors.py:573-578`).
- Factors generally return bounded scores: privileged identity clamps to `[0,1]`; travel clamps; asset caps sensitivity boost; pattern history clips; W2 weighted mean clips; time/device formulas are bounded by branch/math (`app/domains/soc/factors.py:71-136`, `app/domains/soc/factors.py:178-194`, `app/domains/soc/factors.py:245-253`, `app/domains/soc/factors.py:421-426`, `app/domains/soc/factors.py:509-516`, `app/domains/soc/factors.py:545-590`).
- Missing data fallbacks are explicit: privileged identity 0.5, travel 0.5, asset 0.5, threat intel 0.0 or campaign 0.5, legacy pattern history 0.5, W2 pattern history 0.40, time anomaly 0.7, device missing flags as untrusted (`app/domains/soc/factors.py:108-136`, `app/domains/soc/factors.py:156-197`, `app/domains/soc/factors.py:228-256`, `app/domains/soc/factors.py:284-372`, `app/domains/soc/factors.py:400-523`, `app/domains/soc/factors.py:545-590`).
- W2 factor uses recency decay with half-life 30 decisions (`app/domains/soc/factors.py:458`, `app/domains/soc/factors.py:506-515`).
- `compute_soc_factors()` always inserts a threat-intel factor at position 2 and has `_default` fallback (`app/domains/soc/factors.py:817-884`).

### Potential Issues

#### P1
- Multiple factor queries use Neo4j-style named `$param` parameters despite the repo AGE rule forbidding `$param`: `TravelMatchFactor` (`app/domains/soc/factors.py:162-170`), `AssetCriticalityFactor` (`app/domains/soc/factors.py:233-242`), campaign pass 3 (`app/domains/soc/factors.py:335-343`), legacy `PatternHistoryFactor` (`app/domains/soc/factors.py:408-416`), and W2 `PatternHistoryFactorComputer` (`app/domains/soc/factors.py:474-499`). On AGE these can fail or rely on unsafe substitution behavior.
- W2 `PatternHistoryFactorComputer` queries `d.factor_snapshot[3]` (`app/domains/soc/factors.py:480`, `app/domains/soc/factors.py:492`), while the outcome path writes `factor_snapshot` as a JSON string for AGE compatibility. AGE also does not support array properties per `CLAUDE.md`; this likely makes the W2 flywheel read path fail or return unusable values.
- `ThreatIntelEnrichmentFactor` returns the lowest pass value as strongest signal (`app/domains/soc/factors.py:314-320`) and campaign HIGH severity returns 0.05 (`app/domains/soc/factors.py:354-356`), but SOC centroids model higher `threat_intel_enrichment` values as stronger escalation/investigation signal (`app/domains/soc/config.py:141-148`, `app/domains/soc/config.py:189-196`). This polarity mismatch can invert threat-intel scoring.
- `DeviceTrustFactor` polarity appears inverted relative to centroid semantics, as noted in the config findings (`app/domains/soc/factors.py:580-590`, `app/domains/soc/config.py:129-136`).

#### P2
- `AssetCriticalityFactor` gets `alert_id = _get(alert, "id", "")` but queries `Alert {alert_id: ...}` (`app/domains/soc/factors.py:228-242`). If alert dicts carry `alert_id` but not `id`, this returns neutral 0.5.
- `TravelMatchFactor` does not subclass `FactorComputer` and is not included in `SOCDomainConfig.get_factor_computers()` (`app/domains/soc/factors.py:139-197`, `app/domains/soc/config.py:700-709`), despite being documented among factor-computer implementations.
- W2 result processing assumes every query row has numeric `pattern_value` and `decision_num`; malformed/null values can raise after a successful query and are not caught outside the query `try` block (`app/domains/soc/factors.py:501-516`).
- `compute_soc_factors()` legacy templates contain factor names that do not match `SOC_FACTORS` for several alert types, such as `failure_rate`, `source_reputation`, and `campaign_signature_match` (`app/domains/soc/factors.py:601-802`). These are explainability-only but can confuse consumers expecting the six SOC factor names.
- `PatternHistoryFactorComputer` uses `category = alert.category or alert.alert_type` without resolving alert type to canonical category (`app/domains/soc/factors.py:469-471`), so W2 category matching can miss rows written with canonical categories.

#### P3
- The top docstring says "Four use Cypher relationship traversal; two read alert properties" (`app/domains/soc/factors.py:1-9`), but active code includes `TravelMatchFactor` plus both `PatternHistoryFactor` and `PatternHistoryFactorComputer`, making the count ambiguous.
- Several query comments claim relationship traversal, but the active query style still uses `$param`, contrary to the repo's AGE guidance (`app/domains/soc/factors.py:139-170`, `app/domains/soc/factors.py:200-242`, `app/domains/soc/factors.py:375-416`).
- `SOC_FACTOR_TEMPLATES` is large static legacy data in the same file as live GAE factor computers (`app/domains/soc/factors.py:601-802`), increasing review and drift risk.

### Cross-Module Dependencies
- `SOCDomainConfig.get_factor_computers()` constructs `PrivilegedIdentityContextFactor`, `AssetCriticalityFactor`, `ThreatIntelEnrichmentFactor`, `PatternHistoryFactorComputer`, `TimeAnomalyFactor`, and `DeviceTrustFactor` in scorer factor order (`app/domains/soc/config.py:700-709`).
- `app.domains.soc.orchestrator.compute_factor_vector()` likely depends on each factor exposing `name`, `contract`, and async `compute()` with compatible arguments.
- `app/services/triage.py` and the decision-factor endpoint depend on `SOC_FACTOR_TEMPLATES`, `_contribution()`, and `compute_soc_factors()` for backward-compatible explainability (`app/domains/soc/factors.py:601-884`).
- W2/flywheel behavior depends on triage outcome writing `TRIGGERED_EVOLUTION`, `verified_correct`, `factor_snapshot`, `decision_number`, and `action_index` fields that this module reads (`app/domains/soc/factors.py:474-499`).
- Campaign scoring depends on campaign correlation writing `Alert-[:MEMBER_OF]->Campaign` with `confidence`, `severity`, `campaign_id`, `nl_summary`, and `trigger_rule` fields (`app/domains/soc/factors.py:322-372`).

### AGE Cypher Queries
- `TravelMatchFactor.compute()` uses `MATCH (u:User {id: $user})-[:HAS_TRAVEL]->(t:TravelRecord) WHERE t.destination = $geo RETURN count(t) AS cnt ...` (`app/domains/soc/factors.py:162-170`). It uses named `$user`/`$geo`, violating AGE no-`$param`; `cnt` alias is compliant.
- `AssetCriticalityFactor.compute()` uses `MATCH (a:Alert {alert_id: $alert})-[:DETECTED_ON]->(asset:Asset) OPTIONAL MATCH ...` (`app/domains/soc/factors.py:233-242`). It uses named `$alert`, violating AGE no-`$param`.
- `ThreatIntelEnrichmentFactor.compute()` IOC pass uses inline `_S(alert_id)` and `HAS_INDICATOR` traversal (`app/domains/soc/factors.py:292-296`). No listed AGE anti-pattern in that query.
- `ThreatIntelEnrichmentFactor._internal_campaign_score()` uses `MATCH (a:Alert {alert_id: $alert_id})-[:MEMBER_OF]->(c:Campaign)` with params (`app/domains/soc/factors.py:335-343`). It uses named `$alert_id`, violating AGE no-`$param`.
- `PatternHistoryFactor.compute()` uses `WHERE a.alert_type = $type` with params and returns `count(d) AS total` plus sum correct (`app/domains/soc/factors.py:408-416`). It uses named `$type`, violating AGE no-`$param`; alias is `total`, not reserved `count`.
- `PatternHistoryFactorComputer.compute()` uses `WHERE d.category = $category` and optional `d.action_index = $action_index`, and returns `d.factor_snapshot[3]` (`app/domains/soc/factors.py:474-499`). It uses named parameters and array-style indexing on a graph property; both are unsafe for AGE given repo rules and current JSON-string storage.
- No Cypher appears in `config.py`.
