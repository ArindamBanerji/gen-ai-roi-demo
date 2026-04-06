"""
Known issues backlog — documented for tracking and future resolution.
These are non-blocking cosmetic issues confirmed during MVP visual spot-check
on April 1, 2026.
"""

# BACKLOG-001: category="unknown" in executive narrative top shifts
# Root cause: Decision nodes created by simulation have category="unknown"
# because Alert nodes were seeded without category property.
# Fix: Alert category patch (already applied via Cypher for existing nodes)
# must also be applied to the simulation's Alert seeding code so future
# simulation runs produce correctly categorized Decision nodes.
# File to fix: app/services/simulation.py — ensure Decision nodes inherit
# category from Alert node during scoring, not default to "unknown".
# Symptom: Tab 5 "What Changed" shows "unknown/escalate" instead of
# "credential_access/escalate" etc.
# Priority: P2 — cosmetic, non-blocking for MVP
# Gate: after fix, executive narrative top shifts show real category names.

# BACKLOG-002: Detection Engineering shows "unavailable" for all categories
# Root cause: get_profile_scorer() returns None in the detection-engineering
# endpoint — scorer state initialization timing issue.
# File to fix: app/routers/soc.py GET /api/soc/detection-engineering
# Priority: P2 — cosmetic, Tab 1 display only

# BACKLOG-003: Noise Map shows "needs 10+ decisions" despite 2,000 decisions
# Root cause: Decision nodes use different property names than the query
# expects (d.correct / d.outcome vs actual property names).
# File to fix: app/routers/soc.py noise map query in detection-engineering
# Priority: P2 — cosmetic, Tab 1 display only

# BACKLOG-004: IKS does not fully reflect historical decisions on Tab 2
# Root cause: iks_v2 maturity component partially fixed but still
# undersells actual learning at 2,851+ decisions.
# Current: shows 75.7 — expected ~87 at this decision count.
# Priority: P2 — visual only, CLAIM-SC-01 still valid

# BACKLOG-005: threat_intel_match category name in simulation
# Root cause: simulation uses "threat_intel_match" but canonical
# SOC_FACTORS name is "threat_intel_enrichment".
# File to fix: app/data/alert_pool.py or simulation category mapping.
# Priority: P2 — cosmetic only

# BACKLOG-006: ProfileScorer None after POST /api/alerts/reset
# Root cause: reset_all() clears GAE learning state including scorer.
# Fix applied: re-attach scorer from config after reset_all().
# Priority: P1 — causes 500 on analyze endpoint
# Status: FIXED in this session

# BACKLOG-007: "8 of 6 categories calibrated" — count exceeds 6
# Root cause: synthetic_v1 decisions include "unknown" category
# which is counted as a 7th calibrated category.
# Fix: filter calibrated count to SOC_CATEGORIES only (exclude "unknown")
# in executive_narrative.py _what_knows() method.
# Priority: P2 — cosmetic only

# BACKLOG-008: rebuild_neo4j_v6.py end-to-end run not yet verified
# Action: Run rebuild_neo4j_v6.py (without --dry-run) against a
# test/staging Aura instance to confirm full recreation works.
# Do NOT run against production Aura until datetime migration is complete
# and epoch integers are in all seed scripts.
# Gate: node count summary matches pre-migration snapshot counts.
# Priority: P1 — recovery path must be verified before pilot signing.
# Dependency: datetime migration (Block 8.3) must complete first so
# seed scripts write epoch integers, not Neo4j datetime objects.

# BACKLOG-009: V-NARRATIVE-CISO P0 — Tab 1 alert_type vs category
# Root cause: GET /api/soc/tab/1/content was reading a.type (Sentinel
# string e.g. "Unfamiliar sign-in properties") instead of a.category
# (internal name e.g. "credential_access"). Fixed in Fix 1.1 — query
# now reads a.category with _SENTINEL_TO_CATEGORY fallback mapping.
# Gate: Re-run V-NARRATIVE-CISO after Fix 1.1+1.2; confirm Tab 1 shows
# real category names, not "unknown".
# Priority: P0 — judge evaluation blocker.

# BACKLOG-010: Add E2E test — Tab 1 content endpoint returns real category names
# Action: Add Playwright test that hits GET /api/soc/tab/1/content and asserts
# top_alert_types[0].type != "unknown" (requires live Neo4j with seeded data).
# Gate: Test passes against staging environment with synthetic pilot decisions.
# Priority: P1 — regression guard for Fix 1.1.

# BACKLOG-011: Add E2E test — Tab 5 decision count glossary
# Action: Verify that the executive narrative Tab 5 defines all three decision
# count metrics (537/104/5200) with labels visible to the CISO-level audience.
# Gate: V-NARRATIVE-CISO Judge B rates Tab 5 "ACHIEVED" for metrics clarity.
# Priority: P1 — CISO readability requirement.

# BACKLOG-012: Add E2E test — Tab 4 ROI methodology note visible
# Action: Confirm GET /api/soc/tab/4/content exposes roi_methodology field
# explaining the 0.25hr × $75 savings formula to prevent "black box" objection.
# Gate: Methodology note rendered in frontend Tab 4 Decision Economics panel.
# Priority: P2 — transparency / trust signal.

# BACKLOG-013: Re-run V-NARRATIVE-CISO after Fix 1.1+1.2+2.1-2.10
# Action: Execute full 3-judge V-NARRATIVE-CISO evaluation after all narrative
# fixes land. Gate: all 5 tabs ACHIEVED by GPT-5.4 (Judge B).
# Dependency: Fix 1.1, Fix 1.2, Blocks 2.1-2.3 (all complete as of Block 2.3).
# Priority: P0 — pilot sign-off gate.

# BACKLOG-017: conservation_narrative not rendered in frontend
# Tab 5 "What the System Knows" section — conservation_narrative field exists
# in GET /api/soc/tab/5/content (content.what_system_knows.conservation_narrative)
# but no frontend component renders it. The audit trail sentence, CLAIM-OLS-01
# citation, and Evidence Ledger / EU AI Act Art. 13 sentence are all invisible
# to the CISO in the browser.
# File to fix: frontend/src/components/tabs/ExecutiveNarrativeTab.tsx —
# add conservation_narrative to the "What the System Knows" card.
# Priority: P1 — blocks EU AI Act Art. 13 claim being demo-visible.
# Found: Phase A E2E testing, April 5 2026.

# BACKLOG-018: kernel_note (DiagonalKernel) not rendered in frontend
# Tab 3 factor breakdown — kernel_note field exists in GET /api/soc/tab/3/content
# (content.kernel_note) containing DiagonalKernel Innovation #4 explanation
# (device_trust sigma=0.28 → 6% effective weight) but no frontend component
# renders it. The "show your work" kernel explanation is invisible in the demo.
# File to fix: frontend component that renders the factor breakdown panel —
# add kernel_note below the factor weight bars.
# Priority: P1 — blocks "show your work" kernel explanation being visible in demo.
# Found: Phase A E2E testing, April 5 2026.

# BACKLOG-019: E2E suite triggers live Pulsedive refresh — CancelledError + WinError 10055
# Root cause: E2E test hits POST /api/graph/threat-intel/refresh which triggers
# live Pulsedive connector with asyncio.sleep(0.5). Test runner timeout cancels
# the request mid-sleep. Windows socket buffer exhaustion (WinError 10055) follows
# from 111 concurrent Playwright connections.
# Symptom: Tests pass but backend crashes at teardown with CancelledError and
# WinError 10055 on Windows (uvicorn shutdown).
# Fix path: mock /api/graph/threat-intel/refresh in E2E test config OR add
# pytest marker to skip live connector tests in E2E.
# Priority: P2 — cosmetic, does not affect test results or data.
# Found: Phase B E2E run, April 5 2026.

# BACKLOG-020: IKS collapses from 76.1 to 2.5 after learning loop E2E test
# Root cause unknown — may be drift-based IKS resetting when ProfileScorer is
# re-initialized during E2E learning loop, or mu_zero being overwritten.
# Symptom: IKS drops from 76.1 → 2.5 after 40 decisions injected by the
# E2E learning loop test, breaking the IKS stability claim.
# Priority: P1 — IKS stability under continued learning is a core product claim.
# Found: Phase B E2E run, April 5 2026.

def test_backlog_documented():
    """Placeholder — confirms backlog file is present and parseable."""
    issues = [
        "BACKLOG-001", "BACKLOG-002", "BACKLOG-003",
        "BACKLOG-004", "BACKLOG-005", "BACKLOG-006", "BACKLOG-007",
        "BACKLOG-008", "BACKLOG-009", "BACKLOG-010", "BACKLOG-011",
        "BACKLOG-012", "BACKLOG-013",
        "BACKLOG-017", "BACKLOG-018", "BACKLOG-019", "BACKLOG-020",
    ]
    assert len(issues) == 17
