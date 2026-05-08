# S2P Copilot Completion Audit

## 1. Executive Summary

Overall readiness is **PARTIAL**. The S2P preview path is usable: the S2P backend registers `s2p_preview_router`, the SOC frontend proxies `/api/s2p/preview` to the S2P backend, and Tab 6 fetches queue, conservation, compounding, suppliers, and config from `/api/s2p/preview/*` (`s2p-copilot/backend/app/main.py:4-9`, `gen-ai-roi-demo-v4-v50/frontend/vite.config.ts:26-33`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:531-547`).

The biggest technical gap is the split between the legacy S2P pipeline and the v2 preview path. The legacy `/api/s2p/score` router imports `S2PDomainConfig`, while the preview router imports `S2PDomainConfigV2`; legacy config is `(6,4,6)`, and v2 preview config is `(5,5,7)` (`s2p-copilot/backend/app/routers/s2p.py:11-13`, `s2p-copilot/backend/app/routers/s2p_preview.py:14-17`, `s2p-copilot/backend/app/domains/s2p/config.py:33-36`, `s2p-copilot/backend/app/domains/s2p/config.py:145-166`).

Story 4 is ready for a fixture-backed demo, not for a live S2P production claim. The preview compounding endpoint is explicitly labeled `s2p_preview_simulation`, platform evidence endpoints are fixture-backed, and chain-credit/warm-start panels are displayed from `/api/platform/*` fixtures (`s2p-copilot/backend/app/routers/s2p_preview.py:257-272`, `gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:188-207`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:664-666`).

Recommended next actions are: fix Tab 6 display gaps, then plan migration of the legacy `/api/s2p/score` and `/api/s2p/outcome` pipeline to the v2 invoice domain, then harden E2E tests so preview endpoint failures cannot silently skip assertions (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:35-37`, `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:14-17`, `s2p-copilot/backend/app/routers/s2p.py:44-154`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:25-27`).

## 2. Repo Structure Overview

The `s2p-copilot` repo contains 57 Python files and approximately 6,584 Python LOC as measured during the audit. Its router directory contains `framework_router.py`, `s2p.py`, and `s2p_preview.py`; its service directory contains `ols_status.py`, `s2p_learning_gate.py`, and `synthetic_invoices.py`; its domain directory contains the `s2p` domain package. Its repo rules say docs are aspirational until proven in code and require file-line citations for behavioral claims (`s2p-copilot/CLAUDE.md:5-9`).

The SOC frontend integration point is Tab 6, `S2PPreviewTab.tsx`. That component defines preview payload interfaces, fetches `/api/s2p/preview/*`, independently fetches `/api/platform/*` panels, and renders S2P preview plus platform evidence panels (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:4-148`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:531-595`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:650-846`).

The `ci-platform` repo is shared graph infrastructure, not an S2P domain owner. Its rules describe `AGEClient` as the shared graph choke point and list the stable API methods, while the S2P DomainConfig search found no S2P-specific DomainConfig implementation in `ci-platform` (`ci-platform/CLAUDE.md:26-46`).

## 3. Phase 0 Completion Matrix

| Item | Status | Evidence | Gap | Next Action |
|---|---|---|---|---|
| S2P-0.1 DomainConfig | PARTIAL | v2 has 5 categories, 5 actions, 7 factors, and penalty ratio 5.0 (`s2p-copilot/backend/app/domains/s2p/config.py:145-166`). | Legacy config remains `(6,4,6)` and is still used by `/api/s2p/score` (`s2p-copilot/backend/app/domains/s2p/config.py:33-36`, `s2p-copilot/backend/app/routers/s2p.py:11-13`). | Plan a legacy-to-v2 migration or formally keep legacy and preview as separate surfaces. |
| S2P-0.2 Synthetic invoices | COMPLETE for preview | `SyntheticInvoice` includes ground truth action, factors, factor vector, supplier, and amount fields (`s2p-copilot/backend/app/services/synthetic_invoices.py:13-27`). The generator enforces `(5,5,7)` centroids (`s2p-copilot/backend/app/services/synthetic_invoices.py:73-76`). | It is synthetic preview data, not persisted live invoice history (`s2p-copilot/backend/app/services/synthetic_invoices.py:47-63`). | Keep for preview; add live source only in a separate pipeline prompt. |
| S2P-0.3 Initial centroids | PARTIAL | v2 action centroids are non-uniform and returned as profile centroids (`s2p-copilot/backend/app/domains/s2p/config.py:136-178`). | Legacy config returns uniform 0.5 centroids (`s2p-copilot/backend/app/domains/s2p/config.py:67-80`), and v2 centroids are action-level reused across categories (`s2p-copilot/backend/app/domains/s2p/config.py:174-177`). | Decide whether category-specific v2 centroids are required before live activation. |
| S2P-0.3b ProfileScorer integration | REAL GAE SCORER | Preview constructs `gae.ProfileScorer` and calls `score` (`s2p-copilot/backend/app/routers/s2p_preview.py:56-68`, `s2p-copilot/backend/app/routers/s2p_preview.py:75-101`). | Preview scorer state is in-memory and resettable, not live persisted history (`s2p-copilot/backend/app/routers/s2p_preview.py:19-21`, `s2p-copilot/backend/app/routers/s2p_preview.py:204-209`). | Keep preview scorer; design persistent v2 scorer state separately. |
| S2P-0.4 Preview endpoints | COMPLETE for preview | Queue, conservation, compounding, suppliers, and config endpoints exist in the preview router (`s2p-copilot/backend/app/routers/s2p_preview.py:211-230`, `s2p-copilot/backend/app/routers/s2p_preview.py:233-254`, `s2p-copilot/backend/app/routers/s2p_preview.py:257-272`, `s2p-copilot/backend/app/routers/s2p_preview.py:275-285`, `s2p-copilot/backend/app/routers/s2p_preview.py:288-366`). | Endpoints are preview/simulation/fixture-backed, not live S2P APIs (`s2p-copilot/backend/app/routers/s2p_preview.py:1-3`, `s2p-copilot/backend/app/routers/s2p_preview.py:268`). | Preserve honest source labels and avoid “live” claims until persisted data exists. |
| S2P-0.4b Decision pipeline | PARTIAL | Legacy score and outcome endpoints exist (`s2p-copilot/backend/app/routers/s2p.py:44-154`). | Legacy pipeline uses `S2PDomainConfig`, while v2 preview uses `S2PDomainConfigV2` (`s2p-copilot/backend/app/routers/s2p.py:11-13`, `s2p-copilot/backend/app/routers/s2p_preview.py:14-17`). Learning is disabled by default (`s2p-copilot/backend/app/domains/s2p/config.py:38-43`, `s2p-copilot/backend/app/domains/s2p/scorer.py:55-68`). | Run a migration discovery for v2 score/outcome/verification. |
| S2P-0.4c Conservation source | PARTIAL | Preview conservation is computed from preview invoice auto-approve rate (`s2p-copilot/backend/app/routers/s2p_preview.py:233-254`). | It is not computed from persisted verified decision quality; the separate learning gate reads graph decisions if available (`s2p-copilot/backend/app/routers/s2p.py:195-224`). | Keep preview label; add live conservation only after live v2 decisions exist. |
| S2P-0.5 Preview Tab frontend | PARTIAL | Tab 6 renders preview queue, conservation, trajectory, suppliers, cross-copilot signals, warm-start evidence, and chain credit (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:664-846`). | Domain Applicability was not found in Tab 6, and supplier lead-time keys mismatch frontend expectations (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:35-37`, `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:14-17`). | Fix supplier key mismatch and add/relocate Domain Applicability display. |
| S2P-0.6 Supplier fixture | COMPLETE backend, PARTIAL frontend display | Chen-Lin has OTIF 0.94 to 0.72 and exception 0.03 to 0.11 (`s2p-copilot/backend/app/data/s2p_demo_suppliers.json:3-13`). Supplier endpoint reads the fixture (`s2p-copilot/backend/app/routers/s2p_preview.py:187-195`, `s2p-copilot/backend/app/routers/s2p_preview.py:275-285`). | Frontend expects `contractual_days` and `actual_q4_days`, but fixture uses `contractual` and `actual_q4` (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:35-37`, `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:14-17`). | Normalize frontend or endpoint field names. |
| S2P-0.7 Tests/E2E | PARTIAL | Backend collect-only found 136 tests, and preview tests cover endpoint shape and compounding source (`s2p-copilot/backend/tests/test_s2p_preview.py:25-239`). | Playwright preview tests return early when endpoint responses are not OK (`gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:25-27`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:48-50`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:58-60`). | Harden E2E tests for required backend paths. |

## 4. Cross-Repo Integration

Vite routes `/api/s2p/preview` to the S2P backend and generic `/api` to the SOC backend (`gen-ai-roi-demo-v4-v50/frontend/vite.config.ts:26-33`). This makes `/api/s2p/preview/*` S2P-owned and `/api/platform/*` SOC-owned by routing behavior (`gen-ai-roi-demo-v4-v50/frontend/vite.config.ts:26-33`, `gen-ai-roi-demo-v4-v50/backend/app/main.py:77-100`).

The S2P backend owns preview endpoints because `s2p-copilot/backend/app/main.py` imports `s2p_preview_router` and includes it in the FastAPI app (`s2p-copilot/backend/app/main.py:4-9`). The preview router itself defines prefix `/api/s2p/preview` (`s2p-copilot/backend/app/routers/s2p_preview.py:17`).

The SOC frontend Tab 6 fetches S2P preview data through `/api/s2p/preview/queue`, `/conservation`, `/compounding`, `/suppliers`, and `/config` (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:535-540`). The same component fetches platform evidence through relative `/api/platform/*` paths outside the S2P Promise.all (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:277-310`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:561-595`).

Failure handling is split correctly: S2P preview failure clears S2P preview state and sets the unavailable message, while platform fetch failures only null their own panel state (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:548-555`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:561-588`).

Port handling is partly env-driven and partly hardcoded in UI copy. Vite reads `BACKEND_PORT`, `S2P_BACKEND_PORT`, and `FRONTEND_PORT` with defaults (`gen-ai-roi-demo-v4-v50/frontend/vite.config.ts:9-12`), but the Tab 6 unavailable message and start command hardcode port `8002` (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:150-151`).

## 5. Story 4 Readiness

| Story Element | Status | Evidence | Gap |
|---|---|---|---|
| S2P tensor `(5,5,7)`, penalty 5:1 | READY for preview | `S2PDomainConfigV2` has 5 categories, 5 actions, 7 factors, and penalty 5.0 (`s2p-copilot/backend/app/domains/s2p/config.py:145-166`). | Legacy `/api/s2p/score` remains `(6,4,6)` (`s2p-copilot/backend/app/domains/s2p/config.py:33-36`, `s2p-copilot/backend/app/routers/s2p.py:11-13`). |
| Chen-Lin OTIF 94->72, exception 3->11 | READY backend | Fixture has OTIF `0.94` to `0.72` and exception `0.03` to `0.11` (`s2p-copilot/backend/app/data/s2p_demo_suppliers.json:3-13`). | Frontend lead-time key mismatch remains (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:35-37`, `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:14-17`). |
| Invoice scoring | READY preview | Preview scores generated invoices through `ProfileScorer` (`s2p-copilot/backend/app/routers/s2p_preview.py:75-110`). | Synthetic preview only, not live invoice scoring history (`s2p-copilot/backend/app/routers/s2p_preview.py:104-110`). |
| 4 signals converging, 3 invoices held, $45K catch | PARTIAL | Warm-start fixture has `invoices_caught: 3` and `largest_catch_usd: 45000` (`gen-ai-roi-demo-v4-v50/support/setup/s2p_warm_start_evidence.json:56-58`). | Four-signal convergence and three held invoices are not proven from S2P queue decisions. |
| Compounding trajectory not `synthetic_demo` | READY preview | Endpoint returns source `s2p_preview_simulation` and trajectory points (`s2p-copilot/backend/app/routers/s2p_preview.py:257-272`). | Not live persisted history. |
| Cross-copilot signal XC-01 | READY fixture | Platform cross-signals endpoint returns fixture response (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:152-168`), and Tab 6 renders the panel (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:319-390`). | Fixture-backed until live graph query replacement. |
| Warm-start evidence AE-SD | READY fixture | Platform warm-start endpoint and Tab 6 panel exist (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:188-196`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:392-468`). | Fixture-backed. |
| Chain credit attribution RL-SEED | READY fixture | Platform chain-credit endpoint and Tab 6 panel exist (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:199-207`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:470-517`). | Fixture-backed. |
| Domain table F-12 | PARTIAL | Platform endpoint exists (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:171-185`). | No Tab 6 frontend rendering was found for Domain Applicability. |
| ROI calculator | READY generic | ROI defaults and calculate endpoint exist (`gen-ai-roi-demo-v4-v50/backend/app/routers/roi.py:197-215`, `gen-ai-roi-demo-v4-v50/backend/app/routers/roi.py:76-146`). | No Priya-specific `$2.1M` S2P story was proven. |
| Switching cost F-11 | READY backend | Switching-cost trajectory service and metrics response wiring exist (`gen-ai-roi-demo-v4-v50/backend/app/services/switching_cost.py:106-197`, `gen-ai-roi-demo-v4-v50/backend/app/routers/metrics.py:616-637`). | Not shown as a Tab 6 panel. |

## 6. Test and E2E Coverage

Backend coverage in `s2p-copilot` is substantial for preview paths. Collect-only found 136 tests, including preview endpoint tests and v2 synthetic invoice tests. Preview tests assert queue status, factor vector length, scorer metadata, conservation status, compounding trajectory, source label, tensor shape, supplier fixture, and config shape (`s2p-copilot/backend/tests/test_s2p_preview.py:25-239`).

Synthetic invoice tests cover deterministic generation, 7-factor vectors, bounded factor values, v2 category/action use, supplier pool size, fixture serialization, and nearest-centroid oracle quality above 80% (`s2p-copilot/backend/tests/test_synthetic_invoices.py:43-224`).

Domain config tests cover v2 category/action/factor counts, centroid shape `(5,5,7)`, calibration profile validity, no SOC category/action/factor leakage, and legacy config unchanged (`s2p-copilot/backend/tests/test_s2p_domain_config.py:15-159`).

SOC frontend E2E has an S2P preview spec with tab visibility, endpoint checks, supplier checks, config checks, no SOC terms, and graceful backend-down behavior (`gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:9-139`).

The main E2E gap is permissive endpoint testing: several endpoint tests return early on non-OK responses, so those checks can pass without proving backend availability (`gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:25-27`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:48-50`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:58-60`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:74-76`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:92-94`).

## 7. Risks and Blockers

1. **Legacy/v2 split can mislead implementers.** The v2 preview is `(5,5,7)`, but legacy `/api/s2p/score` still uses `(6,4,6)` (`s2p-copilot/backend/app/domains/s2p/config.py:145-166`, `s2p-copilot/backend/app/domains/s2p/config.py:33-36`, `s2p-copilot/backend/app/routers/s2p.py:11-13`).

2. **Documentation drift exists on tensor shape.** `s2p-copilot/CLAUDE.md` says S2P tensor `(5,5,8)`, but v2 code and tests prove `(5,5,7)` (`s2p-copilot/CLAUDE.md:31-33`, `s2p-copilot/backend/app/domains/s2p/config.py:158-160`, `s2p-copilot/backend/tests/test_s2p_domain_config.py:60-63`).

3. **Tab 6 supplier display has a field mismatch.** Frontend expects `contractual_days` and `actual_q4_days`, while fixture supplies `contractual` and `actual_q4` (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:35-37`, `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:14-17`).

4. **Domain Applicability endpoint exists but no Tab 6 render was found.** Platform exposes `/domain-applicability`, but the Tab 6 component search found no Domain Applicability rendering (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:171-185`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:650-846`).

5. **E2E tests can silently skip backend assertions.** S2P preview E2E endpoint checks return early when responses are not OK (`gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:25-27`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:58-60`).

6. **Live claims are not supported by current preview code.** Compounding is labeled `s2p_preview_simulation`, supplier data is fixture-backed, and platform evidence is fixture-backed (`s2p-copilot/backend/app/routers/s2p_preview.py:257-272`, `s2p-copilot/backend/app/routers/s2p_preview.py:275-285`, `gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:90-144`).

## 8. Recommended Next Prompts

### Prompt 1: Fix Tab 6 Display Gaps
- repo: `gen-ai-roi-demo-v4-v50`
- scope: fix supplier lead-time field mismatch and add or intentionally place Domain Applicability outside Tab 6.
- why it matters: Tab 6 currently renders supplier lead time from field names that do not exist in the S2P supplier fixture (`gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:35-37`, `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:14-17`), and the Domain Applicability endpoint is not represented in Tab 6 (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:171-185`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:650-846`).
- model recommendation: GPT-5.3 for implementation, GPT-5.5 for review.
- whether Prompt 0 is needed: yes, to decide whether Domain Applicability belongs in Tab 6 or another frontend tab.

### Prompt 2: Discover v2 S2P Pipeline Migration
- repo: `s2p-copilot`
- scope: discovery only for migrating `/api/s2p/score` and `/api/s2p/outcome` from legacy `S2PDomainConfig` to `S2PDomainConfigV2`.
- why it matters: the current score/outcome pipeline imports legacy config, while v2 preview uses the invoice config (`s2p-copilot/backend/app/routers/s2p.py:11-13`, `s2p-copilot/backend/app/routers/s2p_preview.py:14-17`).
- model recommendation: GPT-5.3 for discovery, GPT-5.5 for review after any implementation.
- whether Prompt 0 is needed: yes.

### Prompt 3: Harden S2P Preview E2E
- repo: `gen-ai-roi-demo-v4-v50`
- scope: update `s2p_preview.spec.ts` so required endpoint failures fail tests rather than returning early.
- why it matters: existing E2E checks return early when endpoint responses are not OK (`gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:25-27`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:48-50`, `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:58-60`).
- model recommendation: GPT-5.3 for implementation, GPT-5.5 for review.
- whether Prompt 0 is needed: no, if the scope is limited to this test file.

### Prompt 4: Resolve Tensor Shape Documentation Drift
- repo: `s2p-copilot`
- scope: update repo guidance or add a documented distinction between legacy `(6,4,6)`, v2 preview `(5,5,7)`, and the stale `(5,5,8)` statement.
- why it matters: `CLAUDE.md` says `(5,5,8)`, while code and tests prove v2 `(5,5,7)` (`s2p-copilot/CLAUDE.md:31-33`, `s2p-copilot/backend/app/domains/s2p/config.py:158-160`, `s2p-copilot/backend/tests/test_s2p_domain_config.py:60-63`).
- model recommendation: GPT-5.3 for doc fix, GPT-5.5 for review.
- whether Prompt 0 is needed: no, if constrained to documentation.

## 9. Open Questions

1. Should legacy `/api/s2p/score` remain as a separate `(6,4,6)` compatibility endpoint, or should it migrate to v2 invoice scoring? The code proves both surfaces currently coexist (`s2p-copilot/backend/app/routers/s2p.py:44-154`, `s2p-copilot/backend/app/routers/s2p_preview.py:211-366`).

2. Should Domain Applicability render in Tab 6 or another frontend tab? The backend endpoint exists, but no Tab 6 render was found during the audit (`gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:171-185`, `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:650-846`).

3. What evidence is required before Story 4 can claim live S2P learning instead of preview simulation? Current compounding source is `s2p_preview_simulation`, and v2 preview data is generated in memory (`s2p-copilot/backend/app/routers/s2p_preview.py:132-184`, `s2p-copilot/backend/app/routers/s2p_preview.py:257-272`).

## Reading Log

- `s2p-copilot/CLAUDE.md:1-63`
- `gen-ai-roi-demo-v4-v50/CLAUDE.md:1-238`
- `ci-platform/CLAUDE.md:1-107`
- `s2p-copilot/backend/app/domains/s2p/config.py:1-233`
- `s2p-copilot/backend/app/routers/s2p_preview.py:1-366`
- `s2p-copilot/backend/app/routers/s2p.py:1-241`
- `s2p-copilot/backend/app/services/synthetic_invoices.py:1-185`
- `s2p-copilot/backend/app/domains/s2p/scorer.py:1-139`
- `s2p-copilot/backend/app/domains/s2p/factors.py:1-137`
- `s2p-copilot/backend/app/domains/s2p/graph.py:1-109`
- `s2p-copilot/backend/app/data/s2p_demo_suppliers.json:1-202`
- `s2p-copilot/backend/tests/test_s2p_preview.py:1-239`
- `s2p-copilot/backend/tests/test_synthetic_invoices.py:1-233`
- `s2p-copilot/backend/tests/test_s2p_domain_config.py:1-159`
- `gen-ai-roi-demo-v4-v50/frontend/src/components/tabs/S2PPreviewTab.tsx:1-848`
- `gen-ai-roi-demo-v4-v50/frontend/vite.config.ts:1-37`
- `gen-ai-roi-demo-v4-v50/frontend/tests/e2e/s2p_preview.spec.ts:1-139`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/platform.py:1-207`
- `gen-ai-roi-demo-v4-v50/backend/app/main.py:77-104`
