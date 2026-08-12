"""Cross-tab consistency tests -- automated regression for narrative contradictions.

Requires: backend running at 127.0.0.1:8001 with AGE seeded.
Run: python -m pytest tests/test_cross_tab_consistency.py -v --timeout=120 --run-live-backend
"""

import re
import warnings
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app

client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def _started_app():
    """Run the normal SOC lifespan so graph-backed read models are seeded."""
    global client
    from app.framework.audit import reset_audit_state
    asyncio.run(reset_audit_state())
    with TestClient(app) as started:
        client = started
        yield
    client = None

SOC_CATEGORIES = {
    "credential_access", "malware_execution", "lateral_movement",
    "data_exfiltration", "insider_threat", "cloud_infrastructure",
}


def _tab(n: int) -> dict:
    assert client is not None
    resp = client.get(f"/api/soc/tab/{n}/content")
    assert resp.status_code == 200, f"Tab {n} returned {resp.status_code}"
    return resp.json().get("content", {})


def _evidence_room() -> dict:
    assert client is not None
    resp = client.get("/api/soc/evidence-room")
    assert resp.status_code == 200
    return resp.json()


def _evolution_summary() -> dict:
    assert client is not None
    resp = client.get("/api/evolution/summary")
    assert resp.status_code == 200
    return resp.json()


def _governance_summary() -> dict:
    assert client is not None
    resp = client.get("/api/governance/summary")
    assert resp.status_code == 200
    return resp.json()


# ===========================================================================
# X1: Conservation consistent across Tab 5 and Tab 7
# ===========================================================================

class TestX1Conservation:

    def test_both_tabs_have_status(self):
        tab5 = _tab(5)
        er = _evidence_room()
        assert tab5.get("what_system_knows", {}).get("health_status")
        assert er.get("conservation", {}).get("status")

    def test_statuses_match(self):
        tab5 = _tab(5)
        er = _evidence_room()
        t5 = tab5["what_system_knows"]["health_status"].upper()
        t7 = er["conservation"]["status"].upper()
        assert t5 == t7, f"X1: Tab5={t5}, Tab7={t7}"


# ===========================================================================
# X2: Tab 1 verified > 0, Tab 1 sum <= Tab 2 total
# ===========================================================================

class TestX2Verified:

    def test_tab1_verified_positive(self):
        tab1 = _tab(1)
        total = sum(t.get("verified_decisions", 0)
                    for t in tab1.get("top_alert_types", []))
        assert total > 0, "X2: Tab 1 verified sum is 0"

    def test_tab1_le_tab2(self):
        tab1 = _tab(1)
        tab2 = _tab(2)
        tab1_sum = sum(t.get("verified_decisions", 0)
                       for t in tab1.get("top_alert_types", []))
        # Tab 2 glossary has "4,860 — ..." string
        glossary_str = tab2.get("decision_count_glossary", {}).get(
            "verified_decisions", "0")
        tab2_total = int(glossary_str.split()[0].replace(",", ""))
        assert tab1_sum <= tab2_total, (
            f"CX6: Tab1={tab1_sum} > Tab2={tab2_total}")


# ===========================================================================
# D1: No "unknown" categories in audit trail
# ===========================================================================

class TestD1Categories:

    def test_no_unknown(self):
        er = _evidence_room()
        entries = er.get("audit_trail", {}).get("entries", [])
        assert len(entries) > 0
        unknown = [e for e in entries if e.get("category") == "unknown"]
        assert len(unknown) == 0, f"D1: {len(unknown)} unknown entries"

    def test_all_canonical(self):
        er = _evidence_room()
        entries = er.get("audit_trail", {}).get("entries", [])
        bad = {e["category"] for e in entries
               if e.get("category") and e["category"] not in SOC_CATEGORIES}
        assert len(bad) == 0, f"D1: non-canonical: {bad}"


# ===========================================================================
# D2/CX3: Timestamps spread
# ===========================================================================

class TestD2Timestamps:

    def test_unique_timestamps(self):
        er = _evidence_room()
        entries = er.get("audit_trail", {}).get("entries", [])
        if len(entries) < 2:
            pytest.skip("Not enough entries")
        timestamps = set(e.get("timestamp", "") for e in entries)
        assert len(timestamps) >= min(5, len(entries)), (
            f"D2: only {len(timestamps)} unique timestamps")

    def test_total_gt_50(self):
        er = _evidence_room()
        total = er.get("audit_trail", {}).get("total", 0)
        assert total > 50, f"Audit total={total}, expected >> 50"


# ===========================================================================
# NEW: Tab 3 vs Tab 1 override rate
# ===========================================================================

class TestOverrideRateConsistency:

    def test_tab3_rationale_not_contradicts_tab1(self):
        """If Tab 3 says '0.0%' override for a category and
        Tab 1 says > 0%, that's a visible contradiction."""
        tab1 = _tab(1)
        tab3 = _tab(3)
        rationale = tab3.get("recommendation", {}).get("rationale", "")

        for t in tab1.get("top_alert_types", []):
            cat_display = t["type"].replace("_", " ")
            signal = t.get("learning_signal", "")
            match = re.search(r"(\d+\.?\d*)%", signal)
            if not match:
                continue
            tab1_pct = float(match.group(1))
            if cat_display in rationale and "0.0%" in rationale and tab1_pct > 0:
                pytest.fail(
                    f"Override contradiction: Tab1 {t['type']}={tab1_pct}%, "
                    f"Tab3 rationale says 0.0%")


# ===========================================================================
# Tab 4 learning_events_count vs Tab 7 evolution_summary
# ===========================================================================

class TestEvolutionLabelConsistency:

    def test_evolution_label_not_misleading(self):
        tab4 = _tab(4)
        evo = _evolution_summary()
        tab4_count = tab4.get("learning_events_count", 0)
        tab7_generated = evo.get("variants_generated", 0)
        if tab4_count > 0 and tab7_generated == 0:
            warnings.warn(
                f"Tab4 says {tab4_count} 'evolution events' but "
                f"Tab7 shows {tab7_generated} variants. Label misleading.")


# ===========================================================================
# Governance & Evidence Room structure
# ===========================================================================

class TestGovernance:

    def test_five_articles(self):
        gs = _governance_summary()
        assert len(gs.get("sections", [])) >= 5

    def test_evidence_room_sections(self):
        er = _evidence_room()
        for s in ("audit_trail", "conservation", "override_analysis", "hash_chain"):
            assert s in er, f"Missing: {s}"

    def test_hash_chain_verified(self):
        er = _evidence_room()
        assert er.get("hash_chain", {}).get("verified") is True
        assert er.get("hash_chain", {}).get("status") == "VERIFIED"

    def test_conservation_verified_positive(self):
        er = _evidence_room()
        assert er.get("conservation", {}).get("verified_decisions", 0) > 0
