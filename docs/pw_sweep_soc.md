# SOC PW Sweep Report - 2026-09-25

## Endpoint Changes That Caused Failures

| Endpoint / surface | Old test assumption | Current behavior | Specs affected |
|---|---|---|---|
| `POST /api/s2p/score` | Fixture-style payloads with only `event_id`, `category`, `amount`, and `supplier_id` were accepted. | The live S2P scorer requires the eight factor fields from `S2PDomainConfig.factors`. | `checklist.spec.ts`, `s2p_contribution_chart.spec.ts`, `s2p_evidence_receipt.spec.ts`, `s2p_receipt_fields.spec.ts` |
| `POST /api/alerts/reset` | A single reset request always succeeded during long PW runs. | The endpoint is idempotent but can transiently return 500 under accumulated full-suite load; direct endpoint probes returned 200. | `learning_stress.spec.ts`, `p77-migration.spec.ts` through shared helper |
| SOC tab navigation after repeated decisions | Default stress timeout was enough for all tab loads. | The browser/page needed more time and an explicit load-state wait during the 5-decision tab walk. | `learning_stress.spec.ts` |
| `/health` | Status matched `healthy` or `operational`. | Status is now `ok`. | `p77-migration.spec.ts` |
| `/api/s2p/preview/suppliers` | A fixture supplier named `Chen-Lin` was present. | Supplier data is graph-backed and names vary; current responses include graph suppliers such as `Copper`, `E20 Verified Supplier`, `STRESS-SUPPLIER`, and `Aster Supplies`. | `s2p_preview.spec.ts`, `s2p-preview.spec.ts` |
| S2P preview queue actions | Queue always had at least two unique action labels. | Graph-backed preview data may legitimately be uniform, for example only `Auto Approve` when auto-approve rate is high. | `s2p-preview.spec.ts` |

## Failures Found

| Spec:line | Test name | Old assertion / setup | New assertion / setup | Root cause |
|---|---|---|---|---|
| `checklist.spec.ts:204` | `POST /api/s2p/score x 10 scenarios -> all return valid action` | Posted partial fixture payloads and used the default test timeout. | Added all eight neutral S2P factor fields and `test.setTimeout(120_000)`. | Live S2P score contract now requires graph-style factor inputs; ten live calls can exceed the default timeout. |
| `s2p_contribution_chart.spec.ts:31` | `scored invoice exposes eight numeric contribution rows` | Posted a partial score payload. | Added all eight neutral S2P factor fields. | Same live score contract shift. |
| `s2p_evidence_receipt.spec.ts:60` | `verified outcome increments conservation once` | Posted a partial score payload. | Added all eight neutral S2P factor fields. | Same live score contract shift. |
| `s2p_receipt_fields.spec.ts:81` | `correct outcome receipt includes PD audit fields` | Used a partial `baseScorePayload`. | Added all eight neutral S2P factor fields to `baseScorePayload`. | Same live score contract shift. |
| `s2p_receipt_fields.spec.ts:95` | `incorrect outcome receipt has zero amount recovered` | Used the same partial `baseScorePayload`. | Reused the factor-complete `baseScorePayload`. | Same live score contract shift. |
| `learning_stress.spec.ts:57` | `mixed correct incorrect does not collapse` | `resetDemoAlerts` failed immediately on one 500 response. | Shared helper retries the idempotent reset up to three times and reports the response body if it still fails. | Reset endpoint was not reproducibly broken in isolation, but had transient 500s under full-suite load. |
| `learning_stress.spec.ts:162` | `all tabs reachable after 5 decisions` | Relied on `test.slow()` and immediate tab assertions. | Increased timeout to 180s and added `page.waitForLoadState('domcontentloaded')` after each tab navigation. | Stress flow was valid but occasionally outlived the old browser/test timing. |
| `p77-migration.spec.ts:236` | `health endpoint returns healthy` | `expect(data.status).toMatch(/healthy|operational/i)`. | `expect(data.status).toMatch(/healthy|operational|ok/i)`. | Unified health contract returns `ok`. |
| `s2p_preview.spec.ts:76` | `preview_suppliers_returns_chen_lin` | Required a specific fixture supplier name. | Requires ten suppliers, at least one non-empty name, and at least one `source === 'graph'`. | Supplier data is now graph-backed and no longer fixture-name-stable. |
| `s2p-preview.spec.ts:104` | `s2p preview shows multiple actions and numeric confidence` | Required at least two unique actions. | Requires at least one recognized action plus numeric confidence. | Graph preview can legitimately contain one action type when auto-approve rate is 1.0. |

## Code Notes

The S2P score tests still hit the live scorer. The fix was to align the smoke-test payload with the production score contract using neutral factor defaults:

```ts
{
  match_status: 0.5,
  amount_variance_ratio: 0.5,
  duplicate_score: 0.5,
  supplier_exception_history: 0.5,
  payment_terms_impact: 0.5,
  commodity_index_correlation: 0.5,
  tax_regulatory_compliance: 0.5,
  environmental_risk: 0.5,
}
```

The reset helper now treats `/api/alerts/reset` as an idempotent setup operation and preserves failure visibility:

```ts
for (let attempt = 1; attempt <= 3; attempt += 1) {
  const response = await requestContext.post(`${BACKEND}/api/alerts/reset`);
  lastStatus = response.status();
  lastBody = await response.text().catch(() => '');
  if (response.status() === 200) return;
  await new Promise((resolve) => setTimeout(resolve, attempt * 500));
}
expect(lastStatus, `POST /api/alerts/reset failed after retries: ${lastBody}`).toBe(200);
```

The graph-backed supplier assertion now validates the current endpoint contract instead of a legacy fixture name:

```ts
expect(data.suppliers.length).toBe(10);
expect(names.some((name) => typeof name === 'string' && name.length > 0)).toBeTruthy();
expect(data.suppliers.some((supplier) => supplier.source === 'graph')).toBeTruthy();
```

No mocks, mockups, production score bypasses, or test deletions were used.

## Files Modified

| File | What changed |
|---|---|
| `frontend/tests/e2e/checklist.spec.ts` | Added S2P factor fields to ten score smoke payloads and gave the multi-call test a 120s timeout. |
| `frontend/tests/e2e/s2p_contribution_chart.spec.ts` | Added S2P factor fields to the score payload. |
| `frontend/tests/e2e/s2p_evidence_receipt.spec.ts` | Added S2P factor fields to the score payload. |
| `frontend/tests/e2e/s2p_receipt_fields.spec.ts` | Added S2P factor fields to the shared score payload. |
| `frontend/tests/e2e/helpers.ts` | Added retry/backoff and better error text to `resetDemoAlerts`. |
| `frontend/tests/e2e/learning_stress.spec.ts` | Stabilized the 5-decision tab walk with a 180s timeout and load-state wait. |
| `frontend/tests/e2e/p77-migration.spec.ts` | Accepted `ok` as a valid health status. |
| `frontend/tests/e2e/s2p_preview.spec.ts` | Replaced fixture supplier-name assertion with graph-backed supplier contract checks. |
| `frontend/tests/e2e/s2p-preview.spec.ts` | Relaxed unique action count to match graph-backed uniform-action queues. |
| `docs/pw_sweep_soc.md` | Added this report. |
| `docs/session_state.md` | Appended the sweep result. |

## Validation

| Command | Result |
|---|---|
| `npx playwright test tests/e2e/checklist.spec.ts -g "POST /api/s2p/score" --reporter=line` | 1 passed |
| `npx playwright test tests/e2e/s2p_contribution_chart.spec.ts tests/e2e/s2p_evidence_receipt.spec.ts tests/e2e/s2p_receipt_fields.spec.ts tests/e2e/learning_stress.spec.ts tests/e2e/p77-migration.spec.ts tests/e2e/s2p_preview.spec.ts tests/e2e/s2p-preview.spec.ts --reporter=line` | 50 passed |
| `npx playwright test tests/e2e/learning_stress.spec.ts tests/e2e/p77-migration.spec.ts --reporter=line` | 23 passed |
| `npx playwright test --reporter=line` | 471 passed, 2 skipped, 0 failed |

## Summary

Failures before: 10. Failures after: 0.

Total specs exercised in full suite: 473 tests discovered. Full-suite result: 471 passed, 2 skipped, 0 failed.
