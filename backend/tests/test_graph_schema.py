"""
tests/test_graph_schema.py — Stress-test for GRAPH_CONTRACT and verify_graph().

Part 1 — Unit tests (no AGE required):
  • GRAPH_CONTRACT structural completeness
  • _S() serializer correctness
  • verify_graph() output schema with a mock client

Part 2 — Integration tests (GRAPH_BACKEND=age, live graph):
  Marked @pytest.mark.neo4j — skipped in CI when NEO4J_URI is not set.
  These tests actually query the live AGE database.
"""
from __future__ import annotations

import asyncio
import json
import pytest

from app.graph_schema import GRAPH_CONTRACT, _S, verify_graph, _DECISION_LABEL


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class _FakeClient:
    """Minimal mock client for verify_graph() unit tests."""

    def __init__(self, node_counts: dict, edge_counts: dict, invariant_values: dict):
        self._node_counts   = node_counts
        self._edge_counts   = edge_counts
        self._inv_values    = invariant_values
        self._sample_nodes  = {}  # label -> dict of properties

    def _set_sample(self, label: str, props: dict):
        self._sample_nodes[label] = props

    async def run_query(self, cypher: str):
        # Node count queries: "MATCH (n:Label) RETURN count(n) AS n"
        for label, cnt in self._node_counts.items():
            if "MATCH (n:" + label + ")" in cypher and "count(n)" in cypher:
                return [{"n": cnt}]

        # Sample node queries: "MATCH (n:Label) RETURN n LIMIT 1"
        for label, props in self._sample_nodes.items():
            if "MATCH (n:" + label + ")" in cypher and "RETURN n LIMIT" in cypher:
                return [{"n": props}]

        # Edge count queries: "MATCH ()-[r:TYPE]->()"
        for rel_type, cnt in self._edge_counts.items():
            if "[r:" + rel_type + "]" in cypher:
                return [{"n": cnt}]

        # Invariant queries — match by known substrings
        for key, val in self._inv_values.items():
            if key in cypher:
                return [{"n": val}]

        return [{"n": 0}]

    async def ensure_graph(self):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 — Unit tests (no AGE)
# ─────────────────────────────────────────────────────────────────────────────


class TestGraphContract:
    """GRAPH_CONTRACT structural completeness."""

    def test_has_required_top_level_keys(self):
        assert "nodes" in GRAPH_CONTRACT
        assert "edges" in GRAPH_CONTRACT
        assert "invariants" in GRAPH_CONTRACT

    def test_all_node_specs_have_min_count_and_fields(self):
        for label, spec in GRAPH_CONTRACT["nodes"].items():
            assert "min_count" in spec, f"{label}: missing min_count"
            assert "required_fields" in spec, f"{label}: missing required_fields"
            assert isinstance(spec["min_count"], int), f"{label}: min_count not int"
            assert isinstance(spec["required_fields"], list), f"{label}: fields not list"
            assert len(spec["required_fields"]) > 0, f"{label}: empty required_fields"

    def test_decision_label_is_correct(self):
        assert _DECISION_LABEL == "Decision"
        assert _DECISION_LABEL in GRAPH_CONTRACT["nodes"]

    def test_all_edge_specs_have_min_count(self):
        for rel_type, spec in GRAPH_CONTRACT["edges"].items():
            assert "min_count" in spec, f"{rel_type}: missing min_count"
            assert isinstance(spec["min_count"], int)

    def test_expected_node_labels_present(self):
        expected = {"Alert", "Decision", "User", "Asset",
                    "Campaign", "ThreatIndicator", "AttackPattern"}
        actual   = set(GRAPH_CONTRACT["nodes"].keys())
        assert expected == actual

    def test_expected_edge_types_present(self):
        expected = {
            "DECIDED_ON", "INVOLVES", "DETECTED_ON",
            "MEMBER_OF", "CLASSIFIED_AS", "HAS_INDICATOR",
        }
        actual = set(GRAPH_CONTRACT["edges"].keys())
        assert expected == actual

    def test_min_counts_are_positive(self):
        for label, spec in GRAPH_CONTRACT["nodes"].items():
            assert spec["min_count"] > 0, f"{label}: min_count must be > 0"
        for rel_type, spec in GRAPH_CONTRACT["edges"].items():
            assert spec["min_count"] > 0, f"{rel_type}: min_count must be > 0"

    def test_decided_on_min_matches_decision_min(self):
        dec_min = GRAPH_CONTRACT["nodes"][_DECISION_LABEL]["min_count"]
        edge_min = GRAPH_CONTRACT["edges"]["DECIDED_ON"]["min_count"]
        assert dec_min == edge_min, (
            f"DECIDED_ON min ({edge_min}) should equal Decision min ({dec_min})"
        )

    def test_invariants_have_required_keys(self):
        for inv in GRAPH_CONTRACT["invariants"]:
            assert "name"  in inv, f"invariant missing 'name': {inv}"
            assert "query" in inv, f"invariant missing 'query': {inv}"
            assert "expected" in inv or "expected_min" in inv, (
                f"invariant missing 'expected' or 'expected_min': {inv['name']}"
            )

    def test_invariant_names_unique(self):
        names = [inv["name"] for inv in GRAPH_CONTRACT["invariants"]]
        assert len(names) == len(set(names)), "Duplicate invariant names"

    def test_no_orphan_decisions_invariant_exists(self):
        names = {inv["name"] for inv in GRAPH_CONTRACT["invariants"]}
        assert "no_orphan_decisions" in names

    def test_demo_alerts_invariant_exists(self):
        names = {inv["name"] for inv in GRAPH_CONTRACT["invariants"]}
        assert "demo_alerts_exist" in names

    def test_alerts_have_users_and_assets_invariants_exist(self):
        names = {inv["name"] for inv in GRAPH_CONTRACT["invariants"]}
        assert "alerts_have_users" in names
        assert "alerts_have_assets" in names


class TestSerializer:
    """_S() fallback serializer matches AGEClient.serialize_for_age behaviour."""

    def test_none(self):
        assert _S(None) == "null"

    def test_bool_true(self):
        assert _S(True) == "true"

    def test_bool_false(self):
        assert _S(False) == "false"

    def test_int(self):
        assert _S(42) == "42"
        assert _S(0) == "0"
        assert _S(-7) == "-7"

    def test_float(self):
        result = _S(3.14)
        assert result == "3.14"

    def test_str_simple(self):
        assert _S("hello") == "'hello'"

    def test_str_with_single_quotes(self):
        result = _S("it's")
        assert result == r"'it\'s'"

    def test_list_serialized_as_json_string(self):
        result = _S(["a", "b"])
        # Should be a JSON string wrapped in single quotes
        inner = result[1:-1]  # strip surrounding ' '
        parsed = json.loads(inner)
        assert parsed == ["a", "b"]

    def test_list_of_floats(self):
        result = _S([0.1, 0.2, 0.3])
        inner = result[1:-1]
        parsed = json.loads(inner)
        assert len(parsed) == 3

    def test_empty_list(self):
        result = _S([])
        assert result == "'[]'"


class TestVerifyGraphUnit:
    """verify_graph() with a mock client."""

    def _make_healthy_client(self) -> _FakeClient:
        """Client that satisfies all contract requirements."""
        nc = {
            "Alert":          580,
            "Decision":       4860,
            "User":            20,
            "Asset":           15,
            "Campaign":         4,
            "ThreatIndicator":  5,
            "AttackPattern":    6,
        }
        ec = {
            "DECIDED_ON":    4860,
            "INVOLVES":       570,
            "DETECTED_ON":    570,
            "MEMBER_OF":       13,
            "CLASSIFIED_AS":  570,
            "HAS_INDICATOR":   54,
        }
        inv = {
            "NOT EXISTS((d)-[:DECIDED_ON]->())": 0,
            "d.correct IS NULL":                 0,
            "status: 'pending'":                 30,
            "d.category IS NULL":                0,
            "NOT EXISTS((a)-[:INVOLVES]->())":   0,
            "NOT EXISTS((a)-[:DETECTED_ON]->())": 0,
        }
        client = _FakeClient(nc, ec, inv)
        # Provide sample nodes with all required fields
        client._set_sample("Alert", {
            "alert_id": "SYN-CA-D001-001", "category": "credential_access",
            "severity": "high", "status": "decided",
            "origin": "zero_day_synthetic", "timestamp_epoch": 1741046400000,
        })
        client._set_sample("Decision", {
            "decision_id": "DEC-001", "category": "credential_access",
            "action": "escalate", "factor_vector": "[0.1,0.2,0.3,0.4,0.5,0.6]",
            "confidence": 0.82, "correct": True,
            "outcome": "correct", "origin": "zero_day_synthetic",
        })
        client._set_sample("User", {"user_id": "USR-001", "name": "Sarah K."})
        client._set_sample("Asset", {
            "asset_id": "AST-001", "hostname": "dc-prod-01.corp.local",
            "criticality": "critical",
        })
        client._set_sample("Campaign", {
            "campaign_id": "CAMP-001", "category_sequence": '["credential_access"]',
        })
        client._set_sample("ThreatIndicator", {
            "indicator": "103.15.42.17",
            "indicator_type": "ip", "severity": "high",
        })
        client._set_sample("AttackPattern", {
            "pattern_id": "T1078", "name": "Valid Accounts", "mitre_id": "T1078",
        })
        return client

    def test_healthy_graph_returns_healthy_true(self):
        client = self._make_healthy_client()
        report = _run(verify_graph(client))
        assert report["healthy"] is True, f"issues: {report['issues']}"
        assert report["issues"] == []

    def test_counts_always_populated(self):
        client = self._make_healthy_client()
        report = _run(verify_graph(client))
        assert "Alert" in report["counts"]
        assert "Decision" in report["counts"]
        assert "User" in report["counts"]
        assert "Asset" in report["counts"]
        assert "DECIDED_ON" in report["counts"]
        assert "INVOLVES" in report["counts"]

    def test_low_node_count_makes_unhealthy(self):
        client = self._make_healthy_client()
        client._node_counts["User"] = 5  # below min_count=20
        report = _run(verify_graph(client))
        assert report["healthy"] is False
        assert any("User" in issue for issue in report["issues"])

    def test_low_edge_count_makes_unhealthy(self):
        client = self._make_healthy_client()
        client._edge_counts["DECIDED_ON"] = 100  # below min_count=4860
        report = _run(verify_graph(client))
        assert report["healthy"] is False
        assert any("DECIDED_ON" in issue for issue in report["issues"])

    def test_orphan_decisions_violation(self):
        client = self._make_healthy_client()
        # Simulate 3 orphan decisions
        client._inv_values["NOT EXISTS((d)-[:DECIDED_ON]->())"] = 3
        report = _run(verify_graph(client))
        assert report["healthy"] is False
        assert any("no_orphan_decisions" in issue for issue in report["issues"])

    def test_missing_outcome_violation(self):
        client = self._make_healthy_client()
        client._inv_values["d.correct IS NULL"] = 12
        report = _run(verify_graph(client))
        assert report["healthy"] is False
        assert any("no_missing_outcomes" in issue for issue in report["issues"])

    def test_demo_alerts_below_min(self):
        client = self._make_healthy_client()
        client._inv_values["status: 'pending'"] = 5  # below expected_min=25
        report = _run(verify_graph(client))
        assert report["healthy"] is False
        assert any("demo_alerts_exist" in issue for issue in report["issues"])

    def test_alerts_missing_users_violation(self):
        client = self._make_healthy_client()
        client._inv_values["NOT EXISTS((a)-[:INVOLVES]->())"] = 20
        report = _run(verify_graph(client))
        assert report["healthy"] is False
        assert any("alerts_have_users" in issue for issue in report["issues"])

    def test_report_always_has_required_keys(self):
        client = self._make_healthy_client()
        report = _run(verify_graph(client))
        assert "healthy" in report
        assert "issues" in report
        assert "counts" in report
        assert isinstance(report["issues"], list)
        assert isinstance(report["counts"], dict)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 — Integration tests (live AGE, optional)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.neo4j
class TestVerifyGraphIntegration:
    """Live AGE queries — skipped when NEO4J_URI not set."""

    def test_verify_graph_returns_dict(self):
        """verify_graph() completes and returns the right shape."""
        report = _run(verify_graph())
        assert "healthy"  in report
        assert "issues"   in report
        assert "counts"   in report

    def test_decision_count_meets_minimum(self):
        """At least 4860 Decision nodes must exist (zero-day training data)."""
        report = _run(verify_graph())
        dec_count = report["counts"].get("Decision", 0)
        assert dec_count >= GRAPH_CONTRACT["nodes"][_DECISION_LABEL]["min_count"], (
            f"Only {dec_count} Decision nodes — run seed_zero_day.py --live"
        )

    def test_alert_count_meets_minimum(self):
        """At least 570 Alert nodes (540 training + 30 demo)."""
        report = _run(verify_graph())
        alert_count = report["counts"].get("Alert", 0)
        assert alert_count >= GRAPH_CONTRACT["nodes"]["Alert"]["min_count"], (
            f"Only {alert_count} Alert nodes — run seed_graph()"
        )

    def test_no_orphan_decisions_live(self):
        """Every Decision has a DECIDED_ON edge (invariant)."""
        import os
        from app.db.neo4j import neo4j_client
        result = _run(neo4j_client.run_query(
            "MATCH (d:" + _DECISION_LABEL + ") "
            "WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
            "RETURN count(d) AS n"
        ))
        orphans = int(result[0]["n"]) if result else -1
        assert orphans == 0, f"{orphans} orphan Decision nodes found"

    def test_decided_on_edge_count_matches_decisions(self):
        """DECIDED_ON edge count equals Decision node count."""
        report = _run(verify_graph())
        dec_count  = report["counts"].get("Decision", -1)
        edge_count = report["counts"].get("DECIDED_ON", -1)
        assert dec_count >= 0 and edge_count >= 0
        assert edge_count == dec_count, (
            f"Decision={dec_count} but DECIDED_ON={edge_count} — orphans present"
        )

    def test_graph_contract_all_checks_pass(self):
        """Full contract check — all nodes, edges, and invariants."""
        report = _run(verify_graph())
        assert report["healthy"], (
            f"Graph contract violations:\n" +
            "\n".join(f"  - {issue}" for issue in report["issues"])
        )
