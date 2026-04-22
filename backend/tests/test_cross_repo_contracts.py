"""
Cross-repo contract tests.

Verifies the interface contracts between:
  GAE → SOC  (ProfileScorer, ScoringResult, centroid setter)
  ci-platform → SOC  (EvidenceLedger, OutcomeEntry, SAMLService)
  SOC graph schema  (audit fields, verified_by)

9 tests. No live DB required.
"""
import warnings
import pytest
import numpy as np


# ---------------------------------------------------------------------------
# GAE → SOC contracts
# ---------------------------------------------------------------------------

def test_scoring_result_has_entropy():
    """ScoringResult from GAE carries an entropy float field."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from gae.profile_scorer import ProfileScorer
    scorer = ProfileScorer.for_soc(mu=np.full((6, 4, 6), 0.5))
    result = scorer.score(np.random.rand(6), category_index=0)
    assert hasattr(result, "entropy")
    assert isinstance(result.entropy, float)


def test_scoring_result_has_confidence_gap():
    """ScoringResult from GAE carries a confidence_gap float field."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from gae.profile_scorer import ProfileScorer
    scorer = ProfileScorer.for_soc(mu=np.full((6, 4, 6), 0.5))
    result = scorer.score(np.random.rand(6), category_index=0)
    assert hasattr(result, "confidence_gap")
    assert isinstance(result.confidence_gap, float)


def test_centroids_setter_validates_nan():
    """ProfileScorer.centroids setter rejects NaN arrays with ValueError."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from gae.profile_scorer import ProfileScorer
    scorer = ProfileScorer.for_soc(mu=np.full((6, 4, 6), 0.5))
    with pytest.raises(ValueError, match="NaN|Inf"):
        scorer.centroids = np.full((6, 4, 6), np.nan)


def test_checkpoint_restore_uses_setter_not_slice():
    """CheckpointService.rollback sets scorer.centroids = (not [:]=).

    centroids[:] = bypasses the setter validation; XR-BUG-2 was caused by
    that pattern.  The fixed code uses the property setter directly.
    """
    import inspect
    from app.framework.checkpoint import CheckpointService
    source = inspect.getsource(CheckpointService)
    # The slice-assignment "centroids[:] =" must NOT be used for centroids
    assert "scorer.centroids = " in source          # setter assignment exists
    assert "scorer.centroids[:] =" not in source    # bypass pattern is gone


# ---------------------------------------------------------------------------
# ci-platform → SOC contracts
# ---------------------------------------------------------------------------

def test_evidence_ledger_outcome_entry_importable():
    """ci-platform OutcomeEntry is importable and has the required interface."""
    from ci_platform.audit.evidence_ledger import OutcomeEntry
    assert "decision_entry_hash" in OutcomeEntry.__dataclass_fields__
    assert callable(getattr(OutcomeEntry, "compute_hash", None))
    assert callable(getattr(OutcomeEntry, "is_valid", None))


def test_saml_service_importable():
    """ci-platform SAMLService and SAMLConfig are importable from SOC."""
    from ci_platform.auth.saml import SAMLService, SAMLConfig
    assert callable(SAMLService)
    assert callable(SAMLConfig)


# ---------------------------------------------------------------------------
# SOC graph schema contracts
# ---------------------------------------------------------------------------

def test_graph_schema_has_audit_chain_fields():
    """GRAPH_CONTRACT Decision node lists all four audit-chain optional fields."""
    from app.graph_schema import GRAPH_CONTRACT
    optional = GRAPH_CONTRACT["nodes"]["Decision"]["optional_fields"]
    for field in ("entry_hash", "decision_chain_index",
                  "outcome_chain_index", "outcome_entry_hash"):
        assert field in optional, f"Missing optional field: {field}"


def test_graph_schema_has_verified_by_field():
    """GRAPH_CONTRACT Decision node lists verified_by for per-analyst η."""
    from app.graph_schema import GRAPH_CONTRACT
    optional = GRAPH_CONTRACT["nodes"]["Decision"]["optional_fields"]
    assert "verified_by" in optional


# ---------------------------------------------------------------------------
# Epistemic state endpoint
# ---------------------------------------------------------------------------

def test_epistemic_state_endpoint_returns_categories():
    """GET /api/soc/epistemic-state responds 200 with a 'categories' key."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/soc/epistemic-state")
    assert r.status_code == 200
    data = r.json()
    assert "categories" in data
