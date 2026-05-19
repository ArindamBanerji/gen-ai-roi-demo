# AE Context-Aware Variant Selection Plan

## 1. Executive Summary

Classification: PLAN_READY.

Current state: SOC backend AgentEvolver prompt selection is centralized in `app/services/evolver.py`: `get_prompt_variant(alert_type: str)` first resolves an alert type to a SOC category and checks `variant_registry.get_active_variant_for_category`, then falls back to `ACTIVE_PROMPTS.get(alert_type, "DEFAULT_v1")` (`app/services/evolver.py:76-108`). Outcome recording updates global `PROMPT_STATS` by `prompt_variant`, not per category (`app/services/evolver.py:144-176`). The requested "global UCB" premise is not implemented literally in current code: a search for UCB/bandit terms found no UCB implementation in the AgentEvolver path, while the actual selection path is registry lookup plus `ACTIVE_PROMPTS` fallback (`app/services/evolver.py:76-108`; `app/services/variant_registry.py:212-228`).

Target state: add Part A context/category-aware UCB variant selection while preserving backward compatibility. `get_prompt_variant(category=None)` and `record_decision_outcome(..., category=None)` should support category-scoped selection stats, use a category-local UCB score after a category has enough local observations, fall back to global behavior for missing or cold-start category data, and leave existing no-arg/legacy call behavior intact. Step-level attribution is deferred and not part of this plan.

Promotion gate stays global and unchanged. The legacy `check_for_promotion(alert_type)` uses `ACTIVE_PROMPTS`, same-family global `PROMPT_STATS`, minimum 10 samples, and `> 0.05` improvement (`app/services/evolver.py:192-257`). The conservation-bounded AE-03 promotion path uses global shadow summaries and fixed thresholds `DELTA_MIN=0.05`, `Q_FLOOR=0.80`, `SIGMA_MAX=0.10`, `MIN_SHADOW_SAMPLES=50`, and `MIN_SHADOW_BATCHES=3` (`app/services/promotion_gate.py:38-43`, `app/services/promotion_gate.py:111-205`). This plan does not change either gate.

## 2. Current Architecture

### `get_prompt_variant()` signature and behavior

Current signature is `def get_prompt_variant(alert_type: str) -> str` (`app/services/evolver.py:76`). It resolves `alert_type` through `_resolve_registry_category`, checks `get_active_variant_for_category(resolved_category, ARTIFACT_PROMPT_MODULE)`, then optionally checks the raw `alert_type` if category lookup misses (`app/services/evolver.py:86-100`). If a registry variant exists, the returned prompt id comes from `prompt_id_variant`, `prompt_variant`, or `variant_id` (`app/services/evolver.py:101-106`). If no registry variant exists, it returns `ACTIVE_PROMPTS.get(alert_type, "DEFAULT_v1")` (`app/services/evolver.py:108`).

`_resolve_registry_category` uses `ALERT_TYPE_CATEGORY_MAP.get(alert_type or "")` (`app/services/evolver.py:67-73`). The canonical SOC resolver maps alert types to categories in `ALERT_TYPE_CATEGORY_MAP` and documents that new alert type mapping belongs there (`app/domains/soc/config.py:250-318`).

### `record_decision_outcome()` signature and behavior

Current signature is `record_decision_outcome(decision_id: str, prompt_variant: str, success: bool, alert_type: str = "unknown") -> None` (`app/services/evolver.py:144-149`). It initializes a missing `prompt_variant` in `PROMPT_STATS`, increments global `total`, increments global `success` on success, recomputes global `success_rate`, and appends a global weight-history snapshot keyed by `alert_type` (`app/services/evolver.py:161-186`).

### `check_for_promotion()` signature and behavior

Current signature is `check_for_promotion(alert_type: str) -> Optional[Dict[str, Any]]` (`app/services/evolver.py:192`). It reads the active prompt from `ACTIVE_PROMPTS`, derives a family prefix from the active variant name, compares same-family global `PROMPT_STATS`, requires candidate total samples `>= 10`, and promotes only when improvement is greater than `0.05` (`app/services/evolver.py:203-257`).

### Selection logic and active variant inventory

The legacy in-memory active variant inventory has two active alert-type entries: `anomalous_login -> TRAVEL_CONTEXT_v2` and `phishing -> PHISHING_RESPONSE_v1` (`app/services/evolver.py:25-29`). The legacy global stats inventory has four prompt variants: `TRAVEL_CONTEXT_v1`, `TRAVEL_CONTEXT_v2`, `PHISHING_RESPONSE_v1`, and `PHISHING_RESPONSE_v2` (`app/services/evolver.py:17-22`). The SOC domain config documents the same four prompt variants as the domain-level prompt variant inventory (`app/domains/soc/config.py:595-629`).

The registry projection stores `VariantRecord.category` and validates/returns active variants by category or global category `None` (`app/services/variant_registry.py:60-70`, `app/services/variant_registry.py:212-228`). Registry rebuild extracts category from `after_state`, `metadata`, or `graph_context` (`app/services/variant_registry.py:149-197`).

### EvolutionLedger stats structures and reset behavior

`app/framework/evolution_ledger.py` is a shim that re-exports all ledger APIs from `gae.evolution`; new code is instructed to import from `gae.evolution` directly (`app/framework/evolution_ledger.py:1-7`, `app/framework/evolution_ledger.py:9-30`). The canonical ledger is in `graph-attention-engine-v50/gae/evolution.py`, which keeps an in-memory `_SHADOW_INDEX` for shadow summaries (`graph-attention-engine-v50/gae/evolution.py:86-89`) and updates that index on `SHADOW_STARTED` and `SHADOW_RESULT` (`graph-attention-engine-v50/gae/evolution.py:390-394`). `reset_evolution_ledger()` is exercised by current tests to clear the shadow index without issuing delete queries (`tests/test_evolution_ledger.py:365-377`).

Current ledger APIs track lifecycle events and shadow outcomes but do not expose per-category prompt outcome stats; `record_evolution_event` accepts `metadata` and `graph_context` dictionaries but no dedicated category-stat structure (`graph-attention-engine-v50/gae/evolution.py:329-347`). Because `app/framework/evolution_ledger.py` is only a shim to external `gae.evolution` (`app/framework/evolution_ledger.py:1-7`) and this implementation must not change GAE, Part A category selection stats should live in `app/services/evolver.py` module state beside the existing global `PROMPT_STATS`, and should be reset by `reset_evolver_state()` (`app/services/evolver.py:17-35`, `app/services/evolver.py:437-469`).

### Triage Step 8c integration and available category field

The main triage analyze path gets `alert_type` from graph context, resolves it to `alert_category` with `resolve_alert_category`, and rejects unclassified categories before scoring (`app/routers/triage.py:181-201`). ProfileScorer uses the resolved `alert_category` to get a category index (`app/routers/triage.py:222-227`). The Decision node written during analyze stores `category: alert_category` (`app/routers/triage.py:405-418`).

Step 8c is a per-variant shadow comparison, not prompt variant selection. It filters shadow variants by `(variant.category == alert_category or variant.category is None)` and starts `maybe_shadow_compare(...)` with `category=alert_category` via `asyncio.create_task`, making it fire-and-forget/non-blocking (`app/routers/triage.py:651-672`). `maybe_shadow_compare` documents that it handles its own errors because it is used fire-and-forget from the triage response path (`app/services/shadow_runner.py:96-107`).

The outcome path retrieves `a.category AS category`, falls back to resolving alert type only when category is absent, and uses `_resolved_category` in downstream reward/learning/feedback paths (`app/routers/triage.py:1078-1097`, `app/routers/triage.py:1160-1169`, `app/routers/triage.py:1627-1632`).

### Existing tests

Current evolver migration tests cover registry fallthrough, active registry variant lookup, raw alert type resolution to SOC category, unknown alert fallthrough, legacy stats update, legacy promotion behavior, and reset calling ledger reset (`tests/test_evolver_migration.py:33-120`). Variant registry tests already cover latest active variant selection and global `category=None` fallback (`tests/test_variant_registry.py:60-85`) plus no active result when absent (`tests/test_variant_registry.py:154-160`). Ledger tests cover event writes and reset behavior (`tests/test_evolution_ledger.py:49-68`, `tests/test_evolution_ledger.py:365-377`).

## 3. Target Architecture: Context-Aware Selection

Add category-aware prompt outcome stats without changing promotion gates.

Proposed API:

- `get_prompt_variant(category: str | None = None) -> str`
- backward-compatible adapter behavior: existing callers that pass an alert type positionally should continue to work by normalizing through `resolve_alert_category`/`ALERT_TYPE_CATEGORY_MAP` where needed (`app/services/evolver.py:67-73`; `app/domains/soc/config.py:295-318`).
- `record_decision_outcome(decision_id, prompt_variant, success, alert_type="unknown", category=None) -> None`.

Stats model:

- Keep existing global `PROMPT_STATS` for backward compatibility and promotion (`app/services/evolver.py:17-22`, `app/services/evolver.py:192-257`).
- Add `CATEGORY_PROMPT_STATS` in `app/services/evolver.py` as `category -> variant_id -> {success,total,success_rate}`. This is the repo-local Part A category ledger for selection. It must not be added to `gae.evolution` in this prompt because the backend shim re-exports an external canonical ledger (`app/framework/evolution_ledger.py:1-7`) and the allowed implementation scope excludes GAE.
- Update `record_decision_outcome(..., category=None)` to keep updating global `PROMPT_STATS` exactly as today and additionally update `CATEGORY_PROMPT_STATS[category][prompt_variant]` when category normalizes to an allowed SOC category (`app/services/evolver.py:144-186`; `app/domains/soc/config.py:250-318`).
- Clear `CATEGORY_PROMPT_STATS` in `reset_evolver_state()` alongside `RECENT_PROMOTIONS` and `WEIGHT_HISTORY` so category-local selection cannot survive demo reset (`app/services/evolver.py:459-469`). `app/main.py` should not need a new state-manager registration because `"evolver"` is already registered to `reset_evolver_state` (`app/main.py:396-417`).

Selection:

- If `category` is provided and has enough category stats, select the category-local prompt variant with the highest UCB score:
  - `mean = success / total`
  - `bonus = exploration_c * sqrt(log(category_total) / total)`
  - `ucb = mean + bonus`
  - candidates with `total == 0` should not be chosen by infinite score; use global fallback until the category has sufficient local observations, then evaluate only variants with finite category totals. This avoids creating an unbounded/infinite path and matches the requested global fallback for cold-start categories.
- If `category` is `None`, unexpected, empty, or cold-start/insufficient, fall back to current global behavior: registry active variant for resolved category/raw alert type, then `ACTIVE_PROMPTS`, then `"DEFAULT_v1"` (`app/services/evolver.py:86-108`).
- Normalize category safely using the same canonical mapping already used by triage, where `alert_type` comes from context and resolves to `alert_category` (`app/routers/triage.py:184-187`; `app/domains/soc/config.py:295-318`).

Exact triage mapping for future integration:

- Analyze path category source: `alert_category = resolve_alert_category(alert_type)` (`app/routers/triage.py:184-187`).
- Step 8c already passes `category=alert_category` to shadow comparison (`app/routers/triage.py:664-668`).
- Outcome path category source: `record.get("category") or _resolve_cat_po(alert_type_for_cat)` (`app/routers/triage.py:1160-1169`).

## 4. What Does NOT Change

- Legacy promotion unchanged: `check_for_promotion(alert_type)` keeps its current signature, global `PROMPT_STATS`, same-family comparison, minimum 10 samples, and `> 0.05` improvement (`app/services/evolver.py:192-257`).
- AE-03 promotion gate unchanged: the four substantive gates remain superiority (`win_rate >= 0.50 + DELTA_MIN`), correctness floor (`projected_q >= Q_FLOOR`), conservation pass, and variance (`batch_std <= SIGMA_MAX`) with the same supporting sample/batch minimums (`MIN_SHADOW_SAMPLES`, `MIN_SHADOW_BATCHES`) (`app/services/promotion_gate.py:38-43`, `app/services/promotion_gate.py:126-205`).
- Promotion uses global stats/shadow summaries only; no category-local promotion gate in Part A (`app/services/evolver.py:219-232`; `app/services/promotion_gate.py:122-205`).
- Level 1 / Level 2 separation preserved: promotion gate explicitly reads ProfileScorer/learning health without mutating Level 1 scorer, centroid, or GAE state (`app/services/promotion_gate.py:1-5`).
- Triage Step 8c remains non-blocking fire-and-forget via `asyncio.create_task` (`app/routers/triage.py:651-672`).
- Variant generator unchanged: it creates graph-signal variants and records lifecycle events, not prompt-selection outcome stats (`app/services/variant_generator.py:1-22`, `app/services/variant_generator.py:119-132`).
- `get_prompt_variant()` with no args must remain backward compatible after the signature changes; existing tests currently call it with one alert-type arg and assert legacy fallbacks (`tests/test_evolver_migration.py:33-64`).
- No SDK, S2P, ci-platform, or GAE implementation changes in this SOC Part A plan.
- Step-level attribution is deferred and not part of this plan.

## 5. Integration Points

### `app/services/evolver.py`

In scope for future implementation because it owns current prompt stats, active prompts, selection, outcome recording, promotion check, and reset (`app/services/evolver.py:17-35`, `app/services/evolver.py:76-108`, `app/services/evolver.py:144-189`, `app/services/evolver.py:192-257`, `app/services/evolver.py:437-469`).

Future changes:

- Add `CATEGORY_PROMPT_STATS`.
- Add category normalization helper.
- Add a small private UCB helper in this file only; no existing UCB helper exists in the current AgentEvolver selection path, whose live implementation is registry lookup plus `ACTIVE_PROMPTS` fallback (`app/services/evolver.py:76-108`; `app/services/variant_registry.py:212-228`).
- Change `get_prompt_variant` to accept optional category while preserving current positional alert-type behavior.
- Change `record_decision_outcome` to accept optional category and update both global and category stats.
- Reset category stats in `reset_evolver_state()`.

### `app/framework/evolution_ledger.py`

Out of scope for source edits in Part A. It is a shim to `gae.evolution`, not the real implementation (`app/framework/evolution_ledger.py:1-7`). Because this prompt forbids GAE changes, do not add required ledger persistence there in Part A. If later persistent category selection stats are required, they need a separate cross-repo GAE plan. The repo-local Part A category ledger is `CATEGORY_PROMPT_STATS` inside `app/services/evolver.py`.

### `app/routers/triage.py`

In scope only if implementation chooses to pass category into selection/outcome recording on the triage path. Triage already has the exact category field as `alert_category` in analyze (`app/routers/triage.py:184-187`) and `_resolved_category` in outcome (`app/routers/triage.py:1160-1169`). Step 8c already demonstrates non-blocking category-aware variant filtering (`app/routers/triage.py:651-672`).

### `app/routers/evolution.py`

In scope because it currently calls the legacy evolver APIs with `alert_type`: `get_prompt_variant(alert_type)`, `record_decision_outcome(..., alert_type=alert_type)`, and `check_for_promotion(alert_type)` (`app/routers/evolution.py:309-317`). Future implementation must either leave these calls backward compatible or pass a resolved category if this route is still used for decisions.

### `app/main.py`

Probably no direct change needed. It already registers `reset_evolver_state` with `state_manager` under `"evolver"` (`app/main.py:396-417`). Category stats should be cleared by `reset_evolver_state()`, preserving current registration.

### Tests

Add focused tests in `tests/test_evolver_migration.py` or a new focused `tests/test_evolver_context_selection.py`. Existing tests already exercise legacy behavior and reset expectations (`tests/test_evolver_migration.py:33-120`), so new tests should extend rather than replace them.

## 6. Risks and Mitigations

- Silent category mismatch causing global fallback: normalize with `resolve_alert_category`/`ALERT_TYPE_CATEGORY_MAP`, and test unknown categories fall back safely (`app/domains/soc/config.py:295-318`).
- Cold-start categories: fall back to global current behavior until category stats reach a minimum sample count; existing registry fallback behavior already supports global `category=None` variants (`app/services/variant_registry.py:212-228`, `tests/test_variant_registry.py:75-85`).
- Unexpected/category explosion: reject or normalize empty/unclassified categories and cap stats keys to known SOC categories from config (`app/domains/soc/config.py:250-318`).
- Reset behavior: add category stats reset to `reset_evolver_state()` because state manager already calls that handler (`app/services/evolver.py:437-469`; `app/main.py:396-417`).
- Non-blocking triage hot path: any category pass-through must avoid new awaits or network calls in Step 8c; current Step 8c uses `asyncio.create_task` (`app/routers/triage.py:651-672`).
- Promotion-gate drift: keep `check_for_promotion` global and test its existing behavior remains unchanged (`app/services/evolver.py:192-257`; `tests/test_evolver_migration.py:91-109`).
- Level 1/Level 2 violation: do not touch ProfileScorer, centroid tensors, or Level 1 learning; promotion gate currently documents read-only Level 1 access (`app/services/promotion_gate.py:1-5`).
- Backward compatibility: keep existing `get_prompt_variant("anomalous_login")` and unknown fallback tests passing (`tests/test_evolver_migration.py:33-64`).

## 7. Test Plan

- `test_get_prompt_variant_accepts_category`: calling `get_prompt_variant(category="credential_access")` returns a valid prompt and no-arg/legacy calls still work.
- `test_category_specific_selection_can_differ_from_global`: seeded category stats can choose a category-local UCB winner while global `PROMPT_STATS` still favors a different prompt.
- `test_category_selection_uses_ucb_not_raw_success_rate_only`: construct two variants where the lower mean with fewer trials wins under the documented finite UCB bonus, proving selection is not simple max success rate.
- `test_no_category_falls_back_to_global`: `category=None` uses current registry/`ACTIVE_PROMPTS` fallback.
- `test_cold_start_category_falls_back_to_global`: a category with no category stats does not fail or select arbitrary variants.
- `test_record_decision_outcome_tracks_category_stats`: outcome recording updates global `PROMPT_STATS` and category-local stats.
- `test_promotion_gate_unchanged_global`: current `check_for_promotion("migration")` behavior from `tests/test_evolver_migration.py:91-109` remains valid.
- `test_evolver_reset_clears_category_stats`: `reset_evolver_state()` clears `CATEGORY_PROMPT_STATS` and still calls ledger reset, matching current reset expectations (`tests/test_evolver_migration.py:112-120`).
- `test_triage_passes_correct_category_field_non_blocking`: monkeypatch evolver/shadow hooks and assert `alert_category` is the value passed without adding blocking awaits, using current `alert_category` source lines (`app/routers/triage.py:184-187`, `app/routers/triage.py:651-672`).

No Part B or step-attribution tests are included.

## 8. Files to Modify in Future Implementation

Production files:

- `app/services/evolver.py`: owns prompt stats, selection, outcome recording, promotion, reset (`app/services/evolver.py:17-35`, `app/services/evolver.py:76-108`, `app/services/evolver.py:144-189`, `app/services/evolver.py:192-257`, `app/services/evolver.py:437-469`).
- `app/routers/evolution.py`: currently calls `get_prompt_variant`, `record_decision_outcome`, and `check_for_promotion` with `alert_type` (`app/routers/evolution.py:309-317`), so either no change due to backward compatibility or minimal category threading.
- `app/routers/triage.py`: only if category-aware prompt selection/outcome recording is integrated into the primary analyze/outcome path; it already has `alert_category` and `_resolved_category` (`app/routers/triage.py:184-187`, `app/routers/triage.py:1160-1169`).

Test files:

- `tests/test_evolver_migration.py` or new `tests/test_evolver_context_selection.py`.
- `tests/test_evolution_ledger.py` should not need changes for repo-local Part A because category selection stats live in `app/services/evolver.py`; current ledger reset behavior is already covered there (`tests/test_evolution_ledger.py:365-377`).

Forbidden files/repos:

- `frontend/**`, SDK, S2P, ci-platform, and GAE for this Part A implementation.
- ProfileScorer, centroid tensor, reward, conservation, graph persistence, and variant generator logic.

## 9. Future Implementation Sequence

1. Prompt 1: implement Part A only in SOC backend with focused tests.
2. Prompt 2: GPT-5.5 line-by-line plus architecture review.
3. Prompt 3: targeted fixer only if P1/P2 findings remain.

No Part B implementation is part of this sequence.

## 10. Validation Commands for Future Implementation

Targeted evolver tests:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m pytest tests\test_evolver_migration.py tests\test_evolver_context_selection.py -v --timeout=300
```

Targeted ledger/reset tests if ledger-facing changes are made:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m pytest tests\test_evolution_ledger.py -v --timeout=300
```

Relevant triage/AE subset:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m pytest tests -q --timeout=300 -k "evolver or evolution_ledger or variant_registry or shadow or triage"
```

Backend regression if implementation touches triage:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m pytest tests/ -q --timeout=300 --run-live-backend
```

## 11. Reading Log

- `../CLAUDE.md:1-120`: grounding contract and architecture rules.
- `app/services/evolver.py:1-547`: current prompt stats, active prompts, selection, recording, promotion, reset, history.
- `app/framework/evolution_ledger.py:1-30`: shim to canonical `gae.evolution`.
- `graph-attention-engine-v50/gae/evolution.py:1-520`: canonical ledger event types, shadow index, record/rebuild/history/summary behavior.
- `app/services/variant_generator.py:1-260`: generator role and variant record creation; no Part A selection change needed.
- `app/services/variant_registry.py:1-230,300-370`: registry storage, category matching, active/global fallback, reset.
- `app/services/promotion_gate.py:1-80,100-220,440-500`: promotion thresholds, gate checks, reset.
- `app/routers/triage.py:136-260,640-675,1050-1190,1570-1655`: category source, scoring path, Step 8c shadow integration, outcome category fallback.
- `app/routers/evolution.py:280-330`: legacy evolver API calls.
- `app/main.py:380-425`: reset registration.
- `tests/test_evolver_migration.py:1-140`: existing evolver behavior tests.
- `tests/test_evolution_ledger.py:1-70,365-382,599-608`: ledger event/reset tests.
- `tests/test_variant_registry.py:60-88,145-160`: registry category/global fallback and reset tests.

## Prompt Verification Pass

- All referenced paths exist: verified by direct `Test-Path` and file reads.
- Category field name is proven from triage as `alert_category` in analyze and `_resolved_category` in outcome (`app/routers/triage.py:184-187`, `app/routers/triage.py:1160-1169`).
- Promotion gate conditions and thresholds were read and preserved (`app/services/evolver.py:192-257`; `app/services/promotion_gate.py:38-43`, `app/services/promotion_gate.py:126-205`).
- Step attribution is explicitly deferred and not planned.
- No SDK/S2P/ci-platform/GAE changes are included for implementation.
- Reset/state-manager implications are covered by `reset_evolver_state()` and `state_manager.register("evolver", reset_evolver_state)` (`app/services/evolver.py:437-469`; `app/main.py:396-417`).
- Triage fire-and-forget behavior is covered (`app/routers/triage.py:651-672`; `app/services/shadow_runner.py:96-107`).
- Backward compatibility is covered by existing tests and planned no-arg/legacy behavior (`tests/test_evolver_migration.py:33-64`).
- The plan contains enough detail for a later Part A implementation prompt.
