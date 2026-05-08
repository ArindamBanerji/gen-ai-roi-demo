/**
 * Cross-Tab Consistency E2E Tests
 *
 * Automated regression for narrative contradictions.
 * Run: npx playwright test tests/e2e/cross_tab_consistency.spec.ts
 * Requires: Backend on :8001, frontend on :5173
 */

import { test, expect } from "@playwright/test";

const API = "http://localhost:8001";

// ===========================================================================
// X1: Conservation consistent across Tab 5 and Tab 7
// ===========================================================================

test("X1: conservation status matches Tab 5 and Tab 7", async ({ request }) => {
  const [tab5Resp, erResp] = await Promise.all([
    request.get(`${API}/api/soc/tab/5/content`),
    request.get(`${API}/api/soc/evidence-room`),
  ]);
  expect(tab5Resp.ok()).toBeTruthy();
  expect(erResp.ok()).toBeTruthy();

  const tab5 = await tab5Resp.json();
  const er = await erResp.json();

  const t5 = (tab5?.content?.what_system_knows?.health_status || "UNKNOWN").toUpperCase();
  const t7 = (er?.conservation?.status || "UNKNOWN").toUpperCase();
  expect(t5).toBe(t7);
});

// ===========================================================================
// X2: Tab 1 verified > 0 and <= Tab 2 total
// ===========================================================================

test("X2: Tab 1 verified decisions > 0", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/tab/1/content`);
  const tab1 = await resp.json();
  const total = (tab1?.content?.top_alert_types || []).reduce(
    (sum: number, t: any) => sum + (t.verified_decisions || 0), 0
  );
  expect(total).toBeGreaterThan(0);
});

test("CX6: Tab 1 verified sum <= Tab 2 total", async ({ request }) => {
  const [t1, t2] = await Promise.all([
    request.get(`${API}/api/soc/tab/1/content`).then(r => r.json()),
    request.get(`${API}/api/soc/tab/2/content`).then(r => r.json()),
  ]);
  const tab1Sum = (t1?.content?.top_alert_types || []).reduce(
    (sum: number, t: any) => sum + (t.verified_decisions || 0), 0
  );
  const tab2Str = t2?.content?.decision_count_glossary?.verified_decisions || "0";
  const tab2Total = parseInt(tab2Str.split(" ")[0].replace(/,/g, ""), 10);
  expect(tab1Sum).toBeLessThanOrEqual(tab2Total);
});

// ===========================================================================
// D1: No "unknown" categories in audit trail
// ===========================================================================

test("D1: no unknown categories in audit trail", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  const entries = er?.audit_trail?.entries || [];
  expect(entries.length).toBeGreaterThan(0);
  const unknowns = entries.filter((e: any) => e.category === "unknown");
  expect(unknowns).toHaveLength(0);
});

test("D1: all categories are canonical SOC categories", async ({ request }) => {
  const CANONICAL = new Set([
    "credential_access", "malware_execution", "lateral_movement",
    "data_exfiltration", "insider_threat", "cloud_infrastructure",
  ]);
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  for (const entry of (er?.audit_trail?.entries || [])) {
    if (entry.category) {
      expect(CANONICAL.has(entry.category)).toBeTruthy();
    }
  }
});

// ===========================================================================
// D2/CX3: Timestamps spread
// ===========================================================================

test("D2: audit timestamps are not identical", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  const entries = er?.audit_trail?.entries || [];
  if (entries.length < 2) { test.skip(); return; }
  const timestamps = new Set(entries.map((e: any) => e.timestamp));
  expect(timestamps.size).toBeGreaterThanOrEqual(Math.min(5, entries.length));
});

test("D2: audit total > 50 entries", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  expect(er?.audit_trail?.total || 0).toBeGreaterThan(50);
});

// ===========================================================================
// Tab 3 vs Tab 1 override rate consistency
// ===========================================================================

test("Tab 3 override rate does not contradict Tab 1", async ({ request }) => {
  const [t1, t3] = await Promise.all([
    request.get(`${API}/api/soc/tab/1/content`).then(r => r.json()),
    request.get(`${API}/api/soc/tab/3/content`).then(r => r.json()),
  ]);

  const rationale = t3?.content?.recommendation?.rationale || "";
  const types = t1?.content?.top_alert_types || [];

  for (const t of types) {
    const catDisplay = (t.type || "").replace(/_/g, " ");
    const signal = t.learning_signal || "";
    const match = signal.match(/(\d+\.?\d*)%/);
    if (!match) continue;
    const tab1Pct = parseFloat(match[1]);

    if (rationale.includes(catDisplay) && rationale.includes("0.0%") && tab1Pct > 0) {
      expect.soft(false, 
        `Override contradiction: Tab1 ${t.type}=${tab1Pct}%, Tab3 says 0.0%`
      ).toBeTruthy();
    }
  }
});

// ===========================================================================
// Governance & Evidence Room structure
// ===========================================================================

test("governance summary has >= 5 articles", async ({ request }) => {
  const resp = await request.get(`${API}/api/governance/summary`);
  expect(resp.ok()).toBeTruthy();
  const gs = await resp.json();
  expect(gs?.sections?.length || 0).toBeGreaterThanOrEqual(5);
});

test("evidence room has all four sections", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  for (const s of ["audit_trail", "conservation", "override_analysis", "hash_chain"]) {
    expect(er).toHaveProperty(s);
  }
});

test("hash chain is verified", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  expect(er?.hash_chain?.verified).toBe(true);
  expect(er?.hash_chain?.status).toBe("VERIFIED");
});

test("evolution summary has required fields", async ({ request }) => {
  const resp = await request.get(`${API}/api/evolution/summary`);
  const es = await resp.json();
  expect(es).toHaveProperty("variants_generated");
  expect(es).toHaveProperty("variants_promoted");
  expect(es).toHaveProperty("variants_rejected");
});

test("conservation verified decisions > 0", async ({ request }) => {
  const resp = await request.get(`${API}/api/soc/evidence-room`);
  const er = await resp.json();
  expect(er?.conservation?.verified_decisions || 0).toBeGreaterThan(0);
});

// ===========================================================================
// S2P Preview structure
// ===========================================================================

test("S2P preview has (5,5,7) tensor", async ({ request }) => {
  const resp = await request.get(`${API}/api/s2p/preview/config`);
  if (!resp.ok()) { test.skip(); return; }
  const data = await resp.json();
  expect(data?.tensor_shape).toBe("(5, 5, 7)");
});
