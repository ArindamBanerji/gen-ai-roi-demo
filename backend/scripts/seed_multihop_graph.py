"""Seed Stage 1 SOC multi-hop scenario graph fixtures into an idempotent artifact.

Default mode writes data/multihop_graph_seed.json.  It is additive and does not
remove or mutate existing graph data.  The artifact is what the demo loader and
wiring tests use when a live AGE graph is not available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STAGE1_PATH = ROOT / "data" / "soc_multihop_stage1.json"
OUTPUT_PATH = ROOT / "data" / "multihop_graph_seed.json"
ORIGIN = "soc_multihop_stage1"


def load_scenarios(path: Path = STAGE1_PATH) -> list[dict[str, Any]]:
    return list(json.loads(path.read_text(encoding="utf-8"))["scenarios"])


def build_seed_payload(scenarios: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scenarios = scenarios or load_scenarios()
    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id"))
        alert = dict(scenario.get("alert", {}))
        for node in scenario.get("graph_nodes", []):
            node_id = str(node.get("id"))
            node_type = str(node.get("type"))
            props = {**dict(node.get("properties", {})), "id": node_id, "origin": ORIGIN, "scenario_id": scenario_id}
            if node_type == "Alert":
                props.update(alert)
                props.setdefault("alert_id", alert.get("alert_id", node_id))
            nodes[(node_type, node_id)] = {"type": node_type, "id": node_id, "properties": props}
        alert_id = str(alert.get("alert_id") or "")
        graph_alert_ids = [str(n.get("id")) for n in scenario.get("graph_nodes", []) if n.get("type") == "Alert"]
        if alert_id and alert_id not in graph_alert_ids:
            nodes[("Alert", alert_id)] = {"type": "Alert", "id": alert_id, "properties": {**alert, "id": alert_id, "origin": ORIGIN, "scenario_id": scenario_id}}
        for edge in scenario.get("graph_edges", []):
            src = str(edge.get("from"))
            dst = str(edge.get("to"))
            typ = str(edge.get("type"))
            edges[(src, typ, dst)] = {"from": src, "to": dst, "type": typ, "properties": {"origin": ORIGIN, "scenario_id": scenario_id}}
    return {
        "origin": ORIGIN,
        "scenario_count": len(scenarios),
        "nodes": sorted(nodes.values(), key=lambda n: (n["type"], n["id"])),
        "edges": sorted(edges.values(), key=lambda e: (e["type"], e["from"], e["to"])),
        "node_types": sorted({n["type"] for n in nodes.values()}),
        "edge_types": sorted({e["type"] for e in edges.values()}),
    }


def write_seed_artifact(output_path: Path = OUTPUT_PATH) -> dict[str, Any]:
    payload = build_seed_payload()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_seed_artifact()
    print(f"Seeded {len(payload['nodes'])} nodes, {len(payload['edges'])} edges from {payload['scenario_count']} multi-hop scenarios.")
    print(f"Node types: {payload['node_types']}")
    print(f"Edge types: {payload['edge_types']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
