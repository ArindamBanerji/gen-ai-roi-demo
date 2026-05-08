# TAB7-GOV Conservation Status Consistency — Expanded Architecture Design

## 1. Executive Summary

The core defect is split conservation-health ownership. `LearningHealthMonitor.evaluate()` is the raw producer and returns `RED` when in-memory learning history is empty but `decision_count` is above the calibration threshold: empty history produces `alpha=0.0`, `q=0.0`, `V=0.0`, and `n=0`, while the existing `CALIBRATING` branch only checks `decision_count < CALIBRATION_DECISIONS` (`backend/app/services/learning_health.py:81-82`, `backend/app/services/learning_health.py:173-189`, `backend/app/services/learning_health.py:216-244`). Evidence Room then overrides that raw `RED` through an IKS fallback, while governance report and `/api/soc/learning-health` use the raw result directly (`backend/app/services/evidence_room.py:181-204`, `backend/app/services/governance_report.py:106-109`, `backend/app/routers/framework_router.py:728-751`).

Recommended producer fix: `LearningHealthMonitor.evaluate()` should own pre-activation detection. When `LEARNING_ENABLED=False`, decision count is high, history components are zero, and live learning has not accumulated verified weight updates, it should return `status="CALIBRATING"` with explicit metadata rather than raw `RED` (`backend/app/domains/soc/config.py:58-61`, `backend/app/services/learning_health.py:173-185`). The metadata must make the status honest: this is pre-activation/frozen learning, not normal low-volume calibration.

Recommended status value: `CALIBRATING`. It is already part of the backend learning-health response contract and is accepted by Evidence Room and frontend status helpers, while `PRE_ACTIVATION` would require a new enum path across backend allow-lists and frontend renderers (`backend/app/services/learning_health.py:161-170`, `backend/app/services/evidence_room.py:14`, `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`, `frontend/src/components/tabs/GovernanceTab.tsx:124-139`).

Tab 5 changes are required. Current Tab 5 `what_system_knows.health_status` is IKS-derived, and `collect_tab_content.py` and Playwright cross-tab tests compare that field directly to Tab 7 Evidence Room conservation status (`backend/app/services/executive_narrative.py:400-440`, `backend/app/routers/soc.py:3173-3208`, `scripts/collect_tab_content.py:308-315`, `frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31`). The complete fix should make Tab 5 `health_status` represent canonical conservation health, add or preserve a separate IKS/knowledge status if needed, and update Tab 5 copy so pre-activation is not described as “degraded — learning paused automatically” (`backend/app/services/executive_narrative.py:406-418`, `backend/app/routers/soc.py:3173-3187`).

Frontend changes are required only for the Executive Narrative tab. `RuntimeEvolutionTab` already maps `CALIBRATING` to blue `Calibrating`, and `GovernanceTab` styles `CALIBRATING` as non-red (`frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`, `frontend/src/components/tabs/GovernanceTab.tsx:130-134`). `ExecutiveNarrativeTab` currently types `what_knows.health_status` as `GREEN | AMBER | RED`, maps non-GREEN/AMBER health to red, and maps governance summary statuses other than READY/GREEN/PAUSED/AMBER to red, so it must learn `CALIBRATING` (`frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:37-43`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:338-342`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:444-466`).

GO: implementation is ready. No blocker remains if the implementation includes the producer fix, Evidence Room metadata pass-through, governance report pre-activation copy, Tab 5 canonical conservation status, ExecutiveNarrativeTab status handling, sanity/E2E updates, and tests listed below.

## 2. Existing Design Summary

The approved starting design chose `LearningHealthMonitor.evaluate()` as the canonical producer, `CALIBRATING` as the pre-activation status, and an Evidence Room fallback that remains only as defense-in-depth. That direction remains correct because the direct raw callers are `governance_report._collect_learning_health()` and `/api/soc/learning-health`, while Evidence Room alone owns the IKS override today (`backend/app/services/governance_report.py:106-109`, `backend/app/routers/framework_router.py:728-751`, `backend/app/services/evidence_room.py:191-204`).

The expansion changes the blast radius conclusion: Tab 5 cannot be left as IKS-health-only because both the script sanity check and E2E cross-tab test compare Tab 5 health to Tab 7 conservation (`scripts/collect_tab_content.py:308-315`, `frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31`). The complete design therefore requires Tab 5 to expose canonical conservation status while preserving IKS as a separate score/knowledge metric.

## 3. Complete Consumer Map

| Consumer | File:Line | Calls evaluate() how | Uses status for | Own fallback? | Current behavior | Required change |
|---|---|---|---|---|---|---|
| LearningHealthMonitor producer | `backend/app/services/learning_health.py:151-245` | Producer itself reads `get_learning_state()`, history, and decision count (`backend/app/services/learning_health.py:173-176`). | Returns `status`, `signal`, `theta_min`, `conservation`, components, `auto_pause_active`, and interpretation (`backend/app/services/learning_health.py:187-244`). | N/A. | High decision count plus empty history bypasses calibration and can return `RED` (`backend/app/services/learning_health.py:187-221`). | Add pre-activation branch before baseline RED/AMBER/GREEN logic. |
| Evidence Room conservation | `backend/app/services/evidence_room.py:173-230` | Calls `LearningHealthMonitor.evaluate(neo4j_client)` (`backend/app/services/evidence_room.py:177-181`). | Returns Tab 7 conservation widget fields (`backend/app/services/evidence_room.py:222-230`). | Yes, zero-product IKS fallback (`backend/app/services/evidence_room.py:191-204`). | Converts zero-product raw `RED/UNKNOWN` to `GREEN/AMBER` from IKS. | Keep fallback as defense-in-depth only; pass through producer metadata such as `pre_activation`, `learning_enabled`, `status_reason`, and `health_source`. |
| Governance report | `backend/app/services/governance_report.py:106-109`, `backend/app/services/governance_report.py:186-250` | `_collect_learning_health()` returns raw evaluate (`backend/app/services/governance_report.py:106-109`). | Art. 9 and Art. 15 statuses are raw health status (`backend/app/services/governance_report.py:186-190`, `backend/app/services/governance_report.py:239-243`). | No. | Shows raw `RED` today. | Pass through `CALIBRATING`; update Art. 9/15 summaries when `pre_activation=true`. |
| Governance summary endpoint | `backend/app/routers/governance_router.py:15-56` | Calls `generate_governance_report()` and projects sections into summary (`backend/app/routers/governance_router.py:15-17`, `backend/app/routers/governance_router.py:38-56`). | Feeds Tab 7 governance summary and ExecutiveNarrativeTab governance cards. | No. | Propagates raw governance status. | No direct logic change if governance report changes; E2E must accept/display `CALIBRATING`. |
| Learning-health endpoint | `backend/app/routers/framework_router.py:728-751` | Directly returns evaluate (`backend/app/routers/framework_router.py:750-751`). | Feeds `fetchLearningHealth()` (`frontend/src/lib/api.ts:407-413`). | No. | Can expose raw `RED`. | Pass through new metadata; update docstring if changing response shape. |
| Verification health helper | `backend/app/services/learning_health.py:650-680` | Calls evaluate internally (`backend/app/services/learning_health.py:666-670`). | Condition 3 considers `GREEN` or `CALIBRATING` healthy (`backend/app/services/learning_health.py:666-675`). | No. | Raw pre-activation `RED` marks conservation unhealthy. | No logic change needed after producer fix; add regression. |
| Verification health endpoint | `backend/app/routers/soc.py:2350-2359` | Returns `compute_verification_health(neo4j_client)` (`backend/app/routers/soc.py:2350-2359`). | Exposes conservation health through helper. | No. | Indirectly inherits raw `RED`. | No endpoint change expected; test if practical. |
| Triage outcome learning gate | `backend/app/routers/triage.py:1059-1114` | Calls evaluate after outcome write (`backend/app/routers/triage.py:1065-1071`). | Sets scorer conservation status before guarded update; learning update still gated by `LEARNING_ENABLED` (`backend/app/routers/triage.py:1080-1114`). | No; exceptions fail closed (`backend/app/routers/triage.py:1072-1074`). | With `LEARNING_ENABLED=False`, update block is skipped. | No change expected; add assertion that `CALIBRATING` does not enable learning. |
| Balance sheet | `backend/app/services/balance_sheet.py:138-142`, `backend/app/services/balance_sheet.py:172-201`, `backend/app/services/balance_sheet.py:285-299` | `_safe_learning_health()` calls evaluate (`backend/app/services/balance_sheet.py:138-142`). | Exposes `health_status` and recommendation logic checks `RED/AMBER` (`backend/app/services/balance_sheet.py:188-191`, `backend/app/services/balance_sheet.py:285-299`). | No. | `CALIBRATING` would skip conservative health recommendation. | Explicitly handle `CALIBRATING`/`pre_activation` as validation/pre-activation, not degradation. |
| Promotion gate | `backend/app/services/promotion_gate.py:65-98`, `backend/app/services/promotion_gate.py:217-230` | Does not call evaluate; reads live learning history components with `LearningHealthMonitor._extract_components()` and treats missing/zero components as `COLD_START` fail-open (`backend/app/services/promotion_gate.py:65-83`, `backend/app/services/promotion_gate.py:217-230`). | Promotion conservation gate evidence. | No. | Not directly affected by evaluate status changes. | No source change; add no-regression note/test only if implementation touches learning-health component extraction. |
| Executive narrative service | `backend/app/services/executive_narrative.py:301-320`, `backend/app/services/executive_narrative.py:400-440` | Does not currently call evaluate in async narrative path; derives `health_status` from IKS thresholds (`backend/app/services/executive_narrative.py:301-320`, `backend/app/services/executive_narrative.py:400-404`). | Feeds Tab 5 `what_knows.health_status` and conservation narrative (`backend/app/services/executive_narrative.py:406-440`). | Separate IKS-derived health. | Can show `GREEN` while canonical conservation is `CALIBRATING` or raw `RED`. | Add canonical evaluate call; set `health_status` to conservation status; preserve IKS-derived status under a separate field such as `operational_knowledge_status`. |
| Tab 5 content adapter | `backend/app/routers/soc.py:3107-3219` | Does not call evaluate; reads `what_knows_raw.health_status` from executive narrative (`backend/app/routers/soc.py:3107-3112`, `backend/app/routers/soc.py:3173-3208`). | Builds Tab 5 `what_system_knows.health_status` and `conservation_narrative` (`backend/app/routers/soc.py:3173-3218`). | No. | Non-GREEN becomes “degraded — learning paused automatically” (`backend/app/routers/soc.py:3173-3187`). | Pass through canonical metadata and write specific pre-activation copy for `CALIBRATING`/`pre_activation`. |
| Executive narrative PDF | `backend/app/routers/soc.py:1529-1604` | Calls `build_executive_narrative_async()` directly (`backend/app/routers/soc.py:1539-1542`). | Writes `Health: {what_knows.health_status}` in PDF (`backend/app/routers/soc.py:1590-1596`). | No. | Follows IKS-derived health. | Follows service change automatically; optional copy if adding operational knowledge status. |
| Pydantic response models | `backend/app/models/responses.py:237-242` | No evaluate call. | `WhatKnows.health_status` is `str`, not a Literal/Enum (`backend/app/models/responses.py:237-242`). | N/A. | `CALIBRATING` serializes safely; extra fields would be dropped unless model is extended. | Add optional fields if API response validation uses this model for new metadata. |
| Simulation | `backend/app/services/simulation.py:26`, `backend/app/services/simulation.py:416-418`, `backend/app/services/simulation.py:496` | Does not call evaluate; imports `LEARNING_ENABLED`, gates scorer update, writes audit conservation_status `"unknown"` (`backend/app/services/simulation.py:26`, `backend/app/services/simulation.py:416-418`, `backend/app/services/simulation.py:496`). | Simulation-only update and audit record. | No. | Not affected by evaluate status. | No change. |
| collect_tab_content sanity | `scripts/collect_tab_content.py:308-315`, `scripts/collect_tab_content.py:354-361`, `scripts/collect_tab_content.py:378-383` | No evaluate call; consumes Tab 5 and Tab 7 API responses. | CX1 blocks refresh if Tab 5 health != Tab 7 conservation; CX5 only warns on `RED` with positive product (`scripts/collect_tab_content.py:308-315`, `scripts/collect_tab_content.py:354-361`, `scripts/collect_tab_content.py:378-383`). | No. | Would fail if Tab 5 stays `GREEN` and Tab 7 becomes `CALIBRATING`. | Prefer backend Tab 5 alignment so CX1 remains valid; no script change required if Tab 5 `health_status` is canonical. |
| Tab content contract tests | `backend/tests/test_tab_content.py:80-139`, `backend/tests/test_tab_content.py:367-407`, `backend/tests/test_tab_content.py:444-479`, `backend/tests/test_tab_content.py:556-604` | Tests mock Tab 5 narrative and assert fields/copy. | Several mocks use `health_status="GREEN"` and conservation narrative asserts `healthy` for GREEN (`backend/tests/test_tab_content.py:104-139`, `backend/tests/test_tab_content.py:444-479`). | N/A. | No pre-activation/CALIBRATING Tab 5 contract coverage. | Add CALIBRATING/pre-activation Tab 5 tests; keep GREEN tests. |
| RuntimeEvolutionTab | `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`, `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:2264-2288`, `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:3456-3465` | Uses `fetchLearningHealth()` and status helper. | Conservation Law and Learning State indicators. | UI fallback helper. | `CALIBRATING` is already mapped in helper; status badge currently falls through to gray for non-GREEN/AMBER/RED (`frontend/src/components/tabs/RuntimeEvolutionTab.tsx:2265-2273`). | Optional: make the Conservation Law badge blue for `CALIBRATING`; not required for correctness but useful. |
| ExecutiveNarrativeTab | `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:37-43`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:338-342`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:444-466` | No evaluate call; renders Tab 5 narrative and governance summary. | Health text and governance status badges. | No. | `CALIBRATING` would render red/default. | Required frontend change: type, color, statusTone, optional dual status field display. |
| Frontend API | `frontend/src/lib/api.ts:407-413`, `frontend/src/lib/api.ts:485-501` | Calls `/soc/learning-health` and governance endpoints. | Transport only. | No. | No enum constraints. | No API client behavior change. |
| Playwright cross-tab | `frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31` | API-level comparison. | Expects Tab 5 health exactly equals Tab 7 conservation. | No. | Will fail unless Tab 5 aligns. | Keep test unchanged by aligning backend; add assertion for `CALIBRATING` if fixture/mocking exists. |
| Playwright Evidence Room | `frontend/tests/e2e/feature_evidence_room.spec.ts:8-35` | API-level status allow-list. | Allows `CALIBRATING` already. | No. | Unaffected. | No change. |
| Playwright conservation/checklist narrative tests | `frontend/tests/e2e/checklist.spec.ts:972-981`, `frontend/tests/e2e/checklist.spec.ts:1059-1081`, `frontend/tests/e2e/conservation.spec.ts:56-80` | API/DOM tests consume Tab 5 conservation narrative. | Assert `Evidence Ledger`, `EU AI Act Art. 13`, and `Conservation` strings remain present. | No. | Unaffected if pre-activation copy preserves those required phrases. | Keep these phrases in new Tab 5 copy; no status assertion change required. |
| Governance UI E2E | `frontend/tests/e2e/governance_tab.spec.ts:16-29`, `frontend/tests/e2e/feature02_governance.spec.ts:36-96` | DOM smoke tests for governance panels/export. | No explicit GREEN/RED status assertion in the searched snippets. | No. | Likely unaffected. | Add targeted E2E only if frontend status styling changes are implemented. |

## 4. Evidence Room IKS Fallback Analysis

Evidence Room reads `health = await LearningHealthMonitor.evaluate(neo4j_client)` and normalizes `status`, `product`, and `threshold` (`backend/app/services/evidence_room.py:177-189`). The exact fallback condition is `product == 0.0 and status in {"RED", "UNKNOWN"}` (`backend/app/services/evidence_room.py:191`). It calls `compute_visible_iks(neo4j_client)` and maps `IKS >= 40.0` to `GREEN`, `20.0 <= IKS < 40.0` to `AMBER`, otherwise it leaves the raw status unchanged (`backend/app/services/evidence_room.py:192-204`). The IKS function first tries centroid drift when score is above 50, then falls back to graph-composite IKS v2 (`backend/app/services/iks.py:99-139`).

Recommendation: keep this fallback only as defense-in-depth. The producer fix means pre-activation will arrive as `CALIBRATING`, so the fallback will not activate unless a raw `RED/UNKNOWN` zero-product state still occurs (`backend/app/services/evidence_room.py:191-204`). Evidence Room should pass through producer metadata:

- `pre_activation`
- `learning_enabled`
- `health_source`
- `status_reason`
- `interpretation`

It should continue returning existing fields `status`, `product`, `threshold`, `verified_decisions`, and `frozen` for backward compatibility (`backend/app/services/evidence_room.py:222-230`). Do not include `iks_score` in `LearningHealthMonitor.evaluate()`; IKS belongs to operational knowledge/visibility and Evidence Room fallback, not conservation math (`backend/app/services/iks.py:193-327`).

## 5. Divergence Diagram

Before:

```text
LearningHealthMonitor.evaluate()
  empty history -> alpha/q/V/n = 0
  high decision_count bypasses low-count CALIBRATING
  signal = 0.0
  raw status = RED

Evidence Room:
  raw RED/product=0 -> IKS fallback -> GREEN

Governance report:
  raw RED -> Art 9 RED, Art 15 RED

Tab 5:
  IKS-derived health_status -> often GREEN

Cross-tab checks:
  Tab5 GREEN vs Tab7 GREEN may pass today only because Evidence Room masks raw RED
```

After:

```text
LearningHealthMonitor.evaluate()
  LEARNING_ENABLED=False + high decision_count + no live learning history
  -> status = CALIBRATING
  -> pre_activation=true metadata

Evidence Room:
  CALIBRATING passes through, metadata included

Governance report:
  Art 9/15 CALIBRATING with pre-activation summary copy

Tab 5:
  health_status = canonical conservation CALIBRATING
  operational_knowledge_status = IKS-derived GREEN/AMBER/RED if exposed

Cross-tab checks:
  Tab5 CALIBRATING == Tab7 CALIBRATING
```

## 6. Downstream Impact Table

| File | Current behavior | After core fix | Change needed | Risk if skipped |
|---|---|---|---|---|
| `backend/app/services/learning_health.py` | Empty history with high decision count can return `RED` (`backend/app/services/learning_health.py:173-221`). | Returns `CALIBRATING` plus metadata for pre-activation. | Required. | Root defect remains. |
| `backend/app/services/evidence_room.py` | Masks raw `RED` with IKS fallback (`backend/app/services/evidence_room.py:191-204`). | Passes producer `CALIBRATING` through. | Required metadata pass-through; fallback may stay. | Tab 7 widget may lack pre-activation explanation. |
| `backend/app/services/governance_report.py` | Art. 9/15 use raw status and generic summaries (`backend/app/services/governance_report.py:186-250`). | Art. 9/15 show `CALIBRATING` and pre-activation copy. | Required. | Governance may avoid RED but still use misleading generic copy. |
| `backend/app/services/executive_narrative.py` | `health_status` is IKS-derived (`backend/app/services/executive_narrative.py:400-440`). | `health_status` is canonical conservation; optional `operational_knowledge_status` preserves IKS health. | Required. | CX1 and E2E cross-tab fail or Tab 5 contradicts Tab 7. |
| `backend/app/routers/soc.py` Tab 5 | Rebuilds conservation narrative from `health_status`, non-GREEN means “degraded” (`backend/app/routers/soc.py:3173-3187`). | Pre-activation copy says learning is configured/frozen pending activation. | Required. | Tab 5 would say “degraded paused” for `CALIBRATING`. |
| `scripts/collect_tab_content.py` | CX1 requires exact Tab5/Tab7 health match (`scripts/collect_tab_content.py:308-315`). | Passes if Tab 5 aligns to canonical conservation. | No change if Tab 5 changes; otherwise update CX1 to compare canonical field. | Drive refresh blocked by warnings (`scripts/collect_tab_content.py:378-383`). |
| `frontend/tests/e2e/cross_tab_consistency.spec.ts` | Requires exact Tab5/Tab7 status match (`frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31`). | Passes if Tab 5 aligns. | No change if Tab 5 changes; otherwise update to compare new canonical field. | E2E failure. |
| `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx` | `CALIBRATING` renders as red/default (`frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`). | `CALIBRATING` renders as calibrating/blue or amber. | Required. | UI turns non-red pre-activation into red visual. |
| `backend/app/services/balance_sheet.py` | Only `RED/AMBER` trigger conservative health recommendation (`backend/app/services/balance_sheet.py:188-191`). | `CALIBRATING`/pre-activation gets explicit validation/conservative copy. | Required for complete downstream semantics. | Balance Sheet may imply readiness during pre-activation. |
| `backend/app/services/promotion_gate.py` | Promotion conservation gate uses `_extract_components()` from live learning history and returns `COLD_START` when alpha or volume are zero (`backend/app/services/promotion_gate.py:65-98`, `backend/app/services/promotion_gate.py:217-230`). | Core evaluate status change does not flow into promotion gate. | No change. | Low unless implementation unnecessarily changes shared component extraction. |
| `backend/app/models/responses.py` | `health_status` is plain `str` (`backend/app/models/responses.py:237-242`). | `CALIBRATING` is safe; new optional fields need model additions if validated. | Optional but recommended if adding `operational_knowledge_status` or metadata to modeled response. | Extra fields may be dropped by response-model serialization if endpoint uses this model. |
| `backend/app/services/simulation.py` | No evaluate call; `LEARNING_ENABLED` gates profile updates (`backend/app/services/simulation.py:416-418`). | Unaffected. | None. | None. |
| `backend/app/routers/triage.py` | Evaluate status only matters inside `LEARNING_ENABLED`-gated update path (`backend/app/routers/triage.py:1065-1114`). | `CALIBRATING` does not enable learning. | No source change; add test if practical. | Low. |
| `backend/app/routers/soc.py` PDF | Uses executive narrative `what_knows.health_status` (`backend/app/routers/soc.py:1539-1542`, `backend/app/routers/soc.py:1590-1596`). | Shows canonical conservation status. | No separate PDF change unless adding dual status copy. | PDF may omit operational knowledge status. |

## 7. Cross-Tab Consistency Matrix

| Surface | Status shown after fix | Source | Metadata shown or hidden | Consistent? | Change needed |
|---|---|---|---|---|---|
| Tab 2 RuntimeEvolution — Conservation Law card | `CALIBRATING` | `/api/soc/learning-health` -> `LearningHealthMonitor.evaluate()` (`backend/app/routers/framework_router.py:728-751`, `frontend/src/lib/api.ts:407-413`) | Can show status; metadata hidden unless UI expanded. | YES | Optional badge color improvement for `CALIBRATING` (`frontend/src/components/tabs/RuntimeEvolutionTab.tsx:2265-2273`). |
| Tab 2 RuntimeEvolution — Learning State card | `CALIBRATING` after Section D loads; fallback green before health loads | `healthData?.status` via `getLearningStatusMeta()` (`frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`, `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:3456-3465`) | Hidden. | YES after load; fallback is intentional lazy-load behavior. | No required change. |
| Tab 5 Executive — `what_system_knows.health_status` | `CALIBRATING` | Executive narrative canonical evaluate call, then Tab 5 adapter (`backend/app/services/executive_narrative.py:435-440`, `backend/app/routers/soc.py:3204-3208`) | Pre-activation metadata should be included in `what_system_knows`. | YES | Required backend and frontend changes. |
| Tab 5 Executive — conservation narrative/copy | “Pre-activation — conservation configured, live learning disabled pending validation” | Canonical health metadata | Visible copy. | YES | Required in service and/or Tab 5 adapter (`backend/app/services/executive_narrative.py:406-418`, `backend/app/routers/soc.py:3173-3187`). |
| Tab 7 Governance — Evidence Room conservation widget | `CALIBRATING` | Evidence Room pass-through from evaluate (`backend/app/services/evidence_room.py:181-230`) | Should expose `pre_activation`, `learning_enabled`, `health_source`, `status_reason`. | YES | Required metadata pass-through. |
| Tab 7 Governance — Governance summary Art. 9 | `CALIBRATING` | governance report learning health (`backend/app/services/governance_report.py:186-199`) | Metadata in evidence; summary visible. | YES | Required copy update. |
| Tab 7 Governance — Governance summary Art. 15 | `CALIBRATING` | governance report learning health (`backend/app/services/governance_report.py:239-250`) | Metadata in evidence; summary visible. | YES | Required copy update. |
| Tab 7 Governance — Art. 14 / auto-pause | `READY` unless auto-pause active | `auto_pause_active` mapping (`backend/app/services/governance_report.py:226-234`) | Hidden. | YES | No change; pre-activation should not set auto-pause. |
| PDF/export health line | `CALIBRATING` | `build_executive_narrative_async()` used by PDF (`backend/app/routers/soc.py:1539-1542`, `backend/app/routers/soc.py:1590-1596`) | Metadata hidden unless extra line added. | YES | Optional PDF copy for operational knowledge status. |
| collect_tab_content CX checks | CX1 passes; CX5 passes because status is not `RED` | Tab 5 and Tab 7 APIs (`scripts/collect_tab_content.py:308-361`) | Hidden. | YES | No script change if Tab 5 aligns; add script regression if practical. |

## 8. Design Options and Final Recommendation

| Choice | Option | Pros | Cons | Final decision |
|---|---|---|---|---|
| Producer design | `LearningHealthMonitor.evaluate()` owns pre-activation | Fixes every raw evaluate caller and preserves endpoint simplicity (`backend/app/services/evidence_room.py:181`, `backend/app/services/governance_report.py:109`, `backend/app/routers/framework_router.py:751`). | Adds SOC config awareness unless lazy and guarded. | Recommended. |
| Producer design | Canonical wrapper | Keeps evaluate mathematically raw. | Direct callers can bypass it, recreating the current bug. | Reject. |
| Producer design | `evaluate(..., learning_enabled=...)` parameter | Explicit at call sites. | Requires all callers to pass state; missed callers diverge. | Reject. |
| Status value | `CALIBRATING` | Existing enum path; frontend support mostly present; internal verification treats it healthy (`backend/app/services/learning_health.py:672-675`). | Needs metadata to avoid semantic ambiguity. | Recommended. |
| Status value | `PRE_ACTIVATION` | More precise. | New enum blast radius: Evidence Room known statuses and frontend helpers do not handle it (`backend/app/services/evidence_room.py:14`, `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`, `frontend/src/components/tabs/GovernanceTab.tsx:124-139`). | Reject for this fix. |
| Status value | `GREEN + metadata` | Minimal UI changes. | Hides learning-disabled truth; repeats Evidence Room’s current overstatement. | Reject. |
| Tab 5 behavior | Keep IKS-derived `GREEN` | Preserves old narrative. | Fails CX1/E2E and remains contradictory (`scripts/collect_tab_content.py:308-315`, `frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31`). | Reject. |
| Tab 5 behavior | Canonical `health_status` plus separate IKS/knowledge status | Aligns conservation while preserving IKS truth. | Requires backend and ExecutiveNarrativeTab changes. | Recommended. |

## 9. Recommended Architecture

1. `LearningHealthMonitor.evaluate()` is the single source of truth for conservation status. Add pre-activation detection after `signal` is computed and before the existing low-count calibration branch (`backend/app/services/learning_health.py:173-189`).
2. Exact producer metadata:
   - `pre_activation: bool`
   - `learning_enabled: bool`
   - `health_source: "learning_health_pre_activation"` for pre-activation, `"learning_health"` otherwise if adding consistently
   - `status_reason: "learning_disabled_no_live_history"` for pre-activation
   - keep `signal`/`theta_min`/`conservation` numeric values unchanged
   - do not add `iks_score` to evaluate; IKS remains separate (`backend/app/services/iks.py:193-327`)
3. Evidence Room passes metadata through and keeps IKS fallback only for unexpected raw `RED/UNKNOWN` zero-product results (`backend/app/services/evidence_room.py:191-230`).
4. Governance report passes `CALIBRATING` through for Art. 9 and Art. 15, and if `pre_activation=true`, uses copy that says monitoring is configured and learning is pending activation, not failed (`backend/app/services/governance_report.py:186-250`).
5. Executive narrative calls canonical evaluate. `what_knows.health_status` becomes canonical conservation status. Add `what_knows.operational_knowledge_status` or `what_knows.iks_health_status` for the old IKS-derived GREEN/AMBER/RED classification (`backend/app/services/executive_narrative.py:301-320`, `backend/app/services/executive_narrative.py:400-440`).
6. `_tab5_content()` passes through canonical health metadata and uses pre-activation copy for conservation narrative (`backend/app/routers/soc.py:3173-3218`).
7. ExecutiveNarrativeTab handles `CALIBRATING` in its TypeScript type and status styles (`frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:37-43`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`).
8. `collect_tab_content.py` does not need logic changes if Tab 5 aligns; leave CX1 strict because it now protects the canonical conservation contract (`scripts/collect_tab_content.py:308-315`).

## 10. Expanded Implementation Checklist

1. `backend/app/services/learning_health.py`: add lazy `_is_learning_enabled()` helper using `app.domains.soc.config.LEARNING_ENABLED`, failing open to `True` on import error (`backend/app/domains/soc/config.py:58-61`, `backend/app/services/learning_health.py:337-338`).
2. `backend/app/services/learning_health.py`: add pre-activation branch requiring `learning_enabled is False`, `decision_count >= CALIBRATION_DECISIONS`, `comps["n"] == 0`, and `signal == 0.0` (`backend/app/services/learning_health.py:173-185`).
3. `backend/app/services/learning_health.py`: return `CALIBRATING` with existing response fields plus metadata; update docstring to include metadata (`backend/app/services/learning_health.py:151-172`).
4. `backend/app/services/evidence_room.py`: pass through producer metadata and ensure fallback does not override `CALIBRATING` (`backend/app/services/evidence_room.py:185-230`).
5. `backend/app/services/governance_report.py`: update Art. 9/15 summaries when `learning_health.pre_activation` is true; keep status `CALIBRATING` (`backend/app/services/governance_report.py:186-250`).
6. `backend/app/routers/framework_router.py`: update `/soc/learning-health` docstring for metadata; logic remains direct evaluate (`backend/app/routers/framework_router.py:728-751`).
7. `backend/app/services/executive_narrative.py`: call canonical evaluate, set `what_knows.health_status` from conservation status, preserve IKS classification in a separate field, and write pre-activation conservation narrative copy (`backend/app/services/executive_narrative.py:301-320`, `backend/app/services/executive_narrative.py:400-440`).
8. `backend/app/routers/soc.py`: update `_tab5_content()` to pass through new `what_knows` metadata and avoid “degraded — learning paused automatically” for `CALIBRATING`/pre-activation (`backend/app/routers/soc.py:3173-3218`).
9. `backend/app/services/balance_sheet.py`: treat `CALIBRATING`/pre-activation explicitly in recommendation copy and preserve `health_status` serialization (`backend/app/services/balance_sheet.py:172-201`, `backend/app/services/balance_sheet.py:285-299`).
10. `backend/app/services/promotion_gate.py`: no source change; it does not consume evaluate status, and its COLD_START behavior should remain unchanged (`backend/app/services/promotion_gate.py:65-98`, `backend/app/services/promotion_gate.py:217-230`).
11. `backend/app/models/responses.py`: if response-model serialization is used for executive narrative, add optional fields for `operational_knowledge_status`, `pre_activation`, `learning_enabled`, `health_source`, and `status_reason`; `health_status` itself is already unconstrained `str` (`backend/app/models/responses.py:237-242`).
12. `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx`: expand `WhatKnows.health_status` type to include `CALIBRATING`; update `healthColor()` and `statusTone()` to render `CALIBRATING` as non-red; optionally display separate operational knowledge status (`frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:37-43`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:338-342`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:444-466`).
13. `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`: optional polish only: make the Conservation Law badge blue for `CALIBRATING`; the helper already handles the Learning State indicators (`frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`, `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:2265-2273`).
14. `scripts/collect_tab_content.py`: no source change required if Tab 5 aligns; add/update tests if any script-level tests exist for CX1 (`scripts/collect_tab_content.py:308-315`).
15. Do not change `backend/app/services/simulation.py`; it does not call evaluate and learning mutation is already gated by `LEARNING_ENABLED` (`backend/app/services/simulation.py:26`, `backend/app/services/simulation.py:416-418`).
16. Do not change `frontend/src/lib/api.ts`; it is transport-only for these endpoints (`frontend/src/lib/api.ts:407-413`, `frontend/src/lib/api.ts:485-501`).
17. Preserve required Tab 5 conservation narrative phrases for existing E2E/API tests: `Evidence Ledger`, `EU AI Act Art. 13`, and `Conservation` (`frontend/tests/e2e/checklist.spec.ts:972-981`, `frontend/tests/e2e/checklist.spec.ts:1059-1081`, `frontend/tests/e2e/conservation.spec.ts:56-80`).

## 11. Expanded Test Plan

Unit tests:

- `backend/tests/test_learning_health.py`: high decision count + empty history + `LEARNING_ENABLED=False` returns `CALIBRATING`, metadata, `auto_pause_active=False`, and zero signal.
- `backend/tests/test_learning_health.py`: active learning or non-empty failing history still returns `RED`.
- `backend/tests/test_learning_health.py`: existing low-count `CALIBRATING`, GREEN, AMBER, RED tests remain valid (`backend/tests/test_learning_health.py:84-166`).
- `backend/tests/test_evidence_room_conservation_fallback.py`: producer `CALIBRATING` passes through and is not converted to IKS `GREEN`; existing RED/product fallback cases remain covered.
- `backend/tests/test_governance_report.py`: Art. 9 and Art. 15 return `CALIBRATING` and pre-activation copy when metadata is present (`backend/app/services/governance_report.py:186-250`).
- `backend/tests/test_balance_sheet.py`: `CALIBRATING`/pre-activation health creates validation/pre-activation recommendation, not “degraded” and not over-ready; existing cold-start test already mocks `CALIBRATING` (`backend/tests/test_balance_sheet.py:231-241`).
- `backend/tests/test_tab_content.py`: add `CALIBRATING` to Tab 5 conservation narrative cases; existing tests use GREEN mocks and should remain (`backend/tests/test_tab_content.py:367-407`, `backend/tests/test_tab_content.py:444-479`).
- `backend/tests/test_verification_health.py`: add/keep explicit `CALIBRATING` conservation status coverage because `compute_verification_health()` treats `GREEN` and `CALIBRATING` as conservation-healthy (`backend/app/services/learning_health.py:666-675`, `backend/tests/test_verification_health.py:49-54`).
- `backend/tests/test_promotion_gate.py`: no source change required; add only a guard test if implementation touches `_extract_components()` or shared learning-health helpers that promotion gate uses (`backend/app/services/promotion_gate.py:65-98`).

Contract/integration tests:

- `/api/soc/learning-health`: returns `CALIBRATING` with metadata in pre-activation.
- `/api/soc/evidence-room`: `conservation.status == "CALIBRATING"`, metadata present, product and threshold numeric (`frontend/tests/e2e/feature_evidence_room.spec.ts:24-35` already allows `CALIBRATING`).
- `/api/governance/summary`: Art. 9 and Art. 15 statuses are `CALIBRATING` in pre-activation.
- `/api/soc/tab/5/content`: `what_system_knows.health_status == "CALIBRATING"` and includes pre-activation conservation copy.
- `compute_verification_health`: conservation condition healthy for `CALIBRATING` (`backend/app/services/learning_health.py:666-675`).

Script tests/manual validation:

- `scripts/collect_tab_content.py`: CX1 should pass because Tab 5 health matches Tab 7 conservation (`scripts/collect_tab_content.py:308-315`); CX5 should pass because status is not `RED` (`scripts/collect_tab_content.py:354-361`).

Frontend tests:

- `ExecutiveNarrativeTab`: render `CALIBRATING` health without red styling; governance summary `CALIBRATING` badge is non-red (`frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`, `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:444-466`).
- `RuntimeEvolutionTab`: no required test change; existing helper maps `CALIBRATING` (`frontend/src/components/tabs/RuntimeEvolutionTab.tsx:323-337`).
- Existing checklist/conservation E2E: preserve the required Tab 5 narrative strings rather than changing those tests (`frontend/tests/e2e/checklist.spec.ts:972-981`, `frontend/tests/e2e/checklist.spec.ts:1059-1081`, `frontend/tests/e2e/conservation.spec.ts:56-80`).
- Playwright `cross_tab_consistency.spec.ts`: keep strict X1 equality; it should pass after backend alignment (`frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31`).
- Playwright `feature_evidence_room.spec.ts`: no change required because `CALIBRATING` is already in `CONSERVATION_STATUSES` (`frontend/tests/e2e/feature_evidence_room.spec.ts:8-35`).

Validation commands:

- Backend targeted: `python -m pytest tests/test_learning_health.py tests/test_evidence_room_conservation_fallback.py tests/test_governance_report.py tests/test_balance_sheet.py tests/test_tab_content.py -q`
- Backend verification health: `python -m pytest tests/test_verification_health.py -q`
- Frontend build: `cd frontend; npm run build`
- E2E user-run if stack is live: `cd frontend; npx playwright test tests/e2e/cross_tab_consistency.spec.ts tests/e2e/feature_evidence_room.spec.ts tests/e2e/checklist.spec.ts tests/e2e/conservation.spec.ts --reporter=list`
- Script validation with backend live: `python scripts/collect_tab_content.py`

## 12. Risk Assessment

1. Tab 5 alignment risk: if Executive Narrative remains IKS-derived GREEN while Tab 7 becomes `CALIBRATING`, CX1 and E2E fail and the product still tells two stories (`scripts/collect_tab_content.py:308-315`, `frontend/tests/e2e/cross_tab_consistency.spec.ts:17-31`).
2. UI miscolor risk: ExecutiveNarrativeTab currently treats unknown statuses as red, so `CALIBRATING` must be handled there (`frontend/src/components/tabs/ExecutiveNarrativeTab.tsx:95-113`).
3. Semantic risk: `CALIBRATING` for high-decision pre-activation is not low-sample calibration. Metadata and copy must explicitly say pre-activation/frozen learning (`backend/app/domains/soc/config.py:58-61`).
4. Conservation fallback risk: leaving Evidence Room IKS fallback can still mask future raw zero-product failures. Keep tests around it and make producer pre-activation the normal path (`backend/app/services/evidence_room.py:191-204`).
5. Recommendation risk: Balance Sheet may understate caution if `CALIBRATING` is not explicitly handled (`backend/app/services/balance_sheet.py:188-191`).
6. Response-model risk: new fields may be dropped if response-model serialization is later attached; `WhatKnows.health_status` is safe as `str`, but optional new fields should be modeled if used (`backend/app/models/responses.py:237-242`).

## 13. Open Questions / Human Decisions

None. The recommended design is implementation-ready:

- Producer: `LearningHealthMonitor.evaluate()`
- Status: `CALIBRATING`
- Metadata: `pre_activation`, `learning_enabled`, `health_source`, `status_reason`
- Tab 5: canonical conservation in `health_status`, IKS classification preserved separately
- Frontend: update ExecutiveNarrativeTab only; RuntimeEvolutionTab and GovernanceTab are already mostly compatible

## Reading Log

- `CLAUDE.md`: lines 1-120.
- `docs/implementation_plans/tab7_gov_conservation_status_design.md`: full file.
- `scripts/collect_tab_content.py`: full file; key lines 300-365, 378-383.
- `backend/app/services/learning_health.py`: lines 57-82, 151-245, 650-680.
- `backend/app/services/evidence_room.py`: lines 173-230.
- `backend/app/services/governance_report.py`: lines 100-115, 180-200, 235-250.
- `backend/app/routers/framework_router.py`: lines 724-751.
- `backend/app/domains/soc/config.py`: lines 54-63.
- `backend/app/services/iks.py`: lines 99-139, 193-327.
- `backend/app/services/executive_narrative.py`: lines 301-320, 400-446.
- `backend/app/services/balance_sheet.py`: lines 138-201, 260-299.
- `backend/app/services/promotion_gate.py`: lines 1-230.
- `backend/app/models/responses.py`: lines 232-245.
- `backend/app/services/simulation.py`: full file; key lines 26, 416-418, 496.
- `backend/app/routers/triage.py`: lines 1059-1114.
- `backend/app/routers/soc.py`: lines 1528-1604, 2350-2359, 3107-3219, 3840-3865.
- `backend/tests/test_tab_content.py`: lines 60-140, 360-425, 430-480, 556-620, 700-820.
- `backend/tests/test_balance_sheet.py`: full file.
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`: lines 323-337, 2264-2315, 3456-3475.
- `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx`: lines 37-43, 90-115, 175-230, 330-346, 438-470.
- `frontend/src/components/tabs/GovernanceTab.tsx`: lines 120-140, 275-290, 450-466.
- `frontend/src/lib/api.ts`: lines 407-413, 480-505.
- `frontend/tests/e2e/cross_tab_consistency.spec.ts`: lines 1-180.
- `frontend/tests/e2e/feature_evidence_room.spec.ts`: lines 1-70.
- `frontend/tests/e2e/checklist.spec.ts`: lines 972-981, 1059-1081.
- `frontend/tests/e2e/conservation.spec.ts`: lines 31-49, 56-80, 105-145.
- `frontend/tests/e2e/governance_tab.spec.ts`: search/read for governance smoke coverage.
- `frontend/tests/e2e/feature02_governance.spec.ts`: search/read for governance section assertions.
