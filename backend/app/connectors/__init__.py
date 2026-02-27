"""
UCL Connector package — Universal Context Layer data source connectors.

Each connector implements UCLConnector (base.py) and is registered here so
that importing any sub-module of this package guarantees all connectors are
present in the registry singleton.

Connector registration order (matches build prompts):
  C3: PulsediveConnector   — live threat intel (Pulsedive API)
  C2: GreyNoiseConnector   — IP enrichment (GreyNoise community API)
  C5: CrowdStrikeMockConnector — simulated Falcon detections (no API key)
"""
from app.connectors.base import UCLConnector, ConnectorResult, HealthStatus
from app.connectors.registry import registry

# C3 — register Pulsedive connector
from app.connectors.pulsedive import PulsediveConnector
registry.register(PulsediveConnector())

# C2 — register GreyNoise connector
from app.connectors.greynoise import GreyNoiseConnector
registry.register(GreyNoiseConnector())

# C5 — register CrowdStrike mock connector
from app.connectors.crowdstrike_mock import CrowdStrikeMockConnector
registry.register(CrowdStrikeMockConnector())

__all__ = [
    "UCLConnector",
    "ConnectorResult",
    "HealthStatus",
    "registry",
    "PulsediveConnector",
    "GreyNoiseConnector",
    "CrowdStrikeMockConnector",
]
