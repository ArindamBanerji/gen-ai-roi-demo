import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.routers import platform

client = TestClient(app)

EXPECTED_DOMAINS = {
    "SOC": {"shape": (6, 4, 6), "tensor_size": 144, "penalty_ratio": 20, "status": "live"},
    "S2P": {"shape": (5, 5, 7), "tensor_size": 175, "penalty_ratio": 5, "status": "live"},
    "Trading": {"shape": (5, 3, 6), "tensor_size": 90, "penalty_ratio": 2, "status": "specified"},
    "Purchasing": {"shape": (5, 4, 6), "tensor_size": 120, "penalty_ratio": 3, "status": "specified"},
    "DataOps": {"shape": (6, 5, 6), "tensor_size": 180, "penalty_ratio": 10, "status": "specified"},
    "Fraud": {"shape": (6, 3, 7), "tensor_size": 126, "penalty_ratio": 25, "status": "designed"},
    "Clinical": {"shape": (5, 4, 6), "tensor_size": 120, "penalty_ratio": 50, "status": "designed"},
    "Hiring": {"shape": (4, 3, 5), "tensor_size": 60, "penalty_ratio": 8, "status": "designed"},
    "Legal": {"shape": (5, 4, 6), "tensor_size": 120, "penalty_ratio": 15, "status": "designed"},
}

EXPECTED_PENALTY_ORDER = [
    "Clinical",
    "Fraud",
    "SOC",
    "Legal",
    "DataOps",
    "Hiring",
    "S2P",
    "Purchasing",
    "Trading",
]


def _payload():
    response = client.get("/api/platform/domain-applicability")
    assert response.status_code == 200
    return response.json()


def _domain_key(domain):
    if domain["short"] in {"SOC", "S2P"}:
        return domain["short"]
    return domain["name"]


def _domains():
    return {_domain_key(domain): domain for domain in _payload()["domains"]}


def test_domain_table_returns_9_domains():
    payload = _payload()

    assert payload["total"] == 9
    assert len(payload["domains"]) == 9
    assert payload["live"] == 2
    assert payload["specified"] == 3
    assert payload["designed"] == 4


def test_domain_table_contains_required_domains_only():
    assert set(_domains()) == set(EXPECTED_DOMAINS)


def test_soc_s2p_are_live():
    domains = _domains()

    assert domains["SOC"]["status"] == "live"
    assert domains["SOC"]["tensor_size"] == 144
    assert (domains["SOC"]["categories"], domains["SOC"]["actions"], domains["SOC"]["factors"]) == (6, 4, 6)
    assert domains["SOC"]["penalty_ratio"] == 20
    assert domains["S2P"]["status"] == "live"
    assert domains["S2P"]["tensor_size"] == 175
    assert (domains["S2P"]["categories"], domains["S2P"]["actions"], domains["S2P"]["factors"]) == (5, 5, 7)
    assert domains["S2P"]["penalty_ratio"] == 5


def test_tensor_sizes_correct():
    for domain in _payload()["domains"]:
        assert domain["tensor_size"] == domain["categories"] * domain["actions"] * domain["factors"]


def test_domain_shapes_match_contract():
    domains = _domains()

    for name, expected in EXPECTED_DOMAINS.items():
        domain = domains[name]
        assert (domain["categories"], domain["actions"], domain["factors"]) == expected["shape"]
        assert domain["tensor_size"] == expected["tensor_size"]
        assert domain["penalty_ratio"] == expected["penalty_ratio"]
        assert domain["status"] == expected["status"]


def test_penalty_ratios_reflect_stakes():
    domains = _domains()
    ratios = {short: domain["penalty_ratio"] for short, domain in domains.items()}

    assert [name for name, _ in sorted(ratios.items(), key=lambda item: item[1], reverse=True)] == EXPECTED_PENALTY_ORDER
    assert all(0 < ratio <= 100 for ratio in ratios.values())
    assert ratios["Clinical"] > ratios["Fraud"] > ratios["SOC"] > ratios["Legal"] > ratios["DataOps"]
    assert ratios["DataOps"] > ratios["Hiring"] > ratios["S2P"] > ratios["Purchasing"] > ratios["Trading"]


def test_domain_lists_match_dimensions():
    for domain in _payload()["domains"]:
        assert len(domain["categories_list"]) == domain["categories"]
        assert len(domain["actions_list"]) == domain["actions"]
        assert len(domain["factors_list"]) == domain["factors"]


def test_specified_domain_contracts():
    domains = _domains()

    assert domains["Trading"]["short"] == "TRD"
    assert domains["Trading"]["status"] == "specified"
    assert domains["Trading"]["tensor_size"] == 90
    assert domains["Trading"]["penalty_ratio"] == 2

    assert domains["Purchasing"]["short"] == "PUR"
    assert domains["Purchasing"]["status"] == "specified"
    assert domains["Purchasing"]["tensor_size"] == 120
    assert domains["Purchasing"]["penalty_ratio"] == 3

    assert domains["DataOps"]["short"] == "DOP"
    assert domains["DataOps"]["status"] == "specified"
    assert domains["DataOps"]["tensor_size"] == 180
    assert domains["DataOps"]["penalty_ratio"] == 10


def test_domain_table_route_is_platform_not_s2p_preview():
    platform_response = client.get("/api/platform/domain-applicability")
    wrong_namespace_response = client.get("/api/s2p/preview/domain-applicability")

    assert platform_response.status_code == 200
    assert wrong_namespace_response.status_code == 404


def test_missing_fixture_fail_open(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing_domain_applicability.json"
    monkeypatch.setattr(platform, "_DOMAIN_TABLE_PATH", missing_path)
    platform._reset_domain_table_cache()

    try:
        response = client.get("/api/platform/domain-applicability")
    finally:
        platform._reset_domain_table_cache()

    assert response.status_code == 200
    payload = response.json()
    assert payload["domains"] == []
    assert payload["total"] == 0
    assert payload["live"] == 0
    assert payload["specified"] == 0
    assert payload["designed"] == 0
