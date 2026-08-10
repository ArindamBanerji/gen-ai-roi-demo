import asyncio
import importlib.util
import sys
from pathlib import Path

from app.domains.soc.config import SOCDomainConfig
from app.domains.soc.factors import AssetCriticalityFactor
from app.framework.composite_gate import CompositeDiscriminant


def _load_seed_module():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "scripts" / "soc_c9b_seed_alerts.py"
    spec = importlib.util.spec_from_file_location("soc_c9b_seed_alerts_for_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_c9b_credential_access_seed_scores_to_non_referral_action():
    seed = _load_seed_module()
    spec = seed.build_alert_spec("C9B-TEST", 1)

    assert spec.category == "credential_access"
    assert spec.alert_type == "anomalous_login"
    assert spec.criticality == "critical"
    assert spec.risk_score >= 0.90
    assert spec.mfa_completed is False
    assert spec.device_fingerprint_match is False

    privileged_identity_context = (spec.risk_score + 0.85 + 0.80) / 3.0
    factor_vector = [
        privileged_identity_context,
        1.0,  # AssetCriticalityFactor maps "critical" to 1.0.
        0.0,  # No threat indicator is required for the credential_access proof seed.
        0.40,  # PatternHistoryFactorComputer fallback when no W2 history exists.
        0.70,  # TimeAnomalyFactor conservative default when property is absent.
        2.0 / 3.0,  # MFA missing, fingerprint mismatch, VPN present.
    ]

    scorer = SOCDomainConfig().build_profile_scorer()
    result = scorer.score(factor_vector, category_index=0)
    threshold = CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS["credential_access"]

    assert result.action_name in {"escalate", "investigate", "suppress", "monitor"}
    assert result.action_name != "refer_to_analyst"
    assert result.confidence >= threshold


def test_c9b_seed_creates_required_alert_context_edges():
    seed = _load_seed_module()

    class FakeClient:
        def __init__(self):
            self.queries = []

        async def run_query(self, query):
            self.queries.append(query)
            if "RETURN count" in query:
                return [{"cnt": 0}]
            return []

    client = FakeClient()
    asyncio.run(
        seed.seed_alerts(
            client,
            count=1,
            prefix="C9B-TEST",
            graph_name="soc_graph_diag",
            database_url="host=127.0.0.1",
            dsn_source="test",
            dry_run=False,
        )
    )

    combined = "\n".join(client.queries)
    assert "alert_type: 'anomalous_login'" in combined
    assert "criticality: 'critical'" in combined
    assert "CREATE (a)-[:INVOLVES]->(b)" in combined
    assert "CREATE (a)-[:DETECTED_ON]->(b)" in combined


def test_asset_criticality_factor_contract_is_categorical():
    class FakeAGE:
        def __init__(self, criticality):
            self.criticality = criticality

        async def run_query(self, query):
            return [{"criticality": self.criticality, "sensitivity": None}]

    factor = AssetCriticalityFactor()

    assert asyncio.run(factor.compute({"id": "ALERT-CAT"}, FakeAGE("critical"))) == 1.0
    assert asyncio.run(factor.compute({"id": "ALERT-CAT"}, FakeAGE("high"))) == 0.8
    assert asyncio.run(factor.compute({"id": "ALERT-CAT"}, FakeAGE(0.92))) == 0.5


def test_low_confidence_credential_access_still_routes_to_analyst():
    factor_vector = [
        0.825,
        0.5,
        0.0,
        0.40,
        0.70,
        2.0 / 3.0,
    ]

    scorer = SOCDomainConfig().build_profile_scorer()
    result = scorer.score(factor_vector, category_index=0)
    threshold = CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS["credential_access"]
    selected_action = result.action_name
    if result.confidence < threshold:
        selected_action = "refer_to_analyst"

    assert result.confidence < threshold
    assert selected_action == "refer_to_analyst"
