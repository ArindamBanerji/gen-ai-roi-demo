# SOC Perf 02 Read-Only HTTP and Analyze Route Source Map

## Safety
- read_only: `True`
- graph_name: `soc_graph_diag_f8`
- prefix: `DIAG-F8-CRED`
- graph_dsn_redacted: `host=localhost port=5433 dbname=soc_copilot user=postgres password=***`
- Rule40 validated: `True`
- backend_url: `http://127.0.0.1:8001`
- network_split_warnings: `[]`
- no proof alert analyzed: `True`
- no outcome endpoint called: `True`
- no writes performed by script: `True`
- negative analyze alert id: `PERF-NONEXISTENT-DO-NOT-CREATE`

## Measurements
| label | reps | avg_s | p50_s | p95_s | max_s | error |
|---|---:|---:|---:|---:|---:|---|
| h1_get_health | 5 | 0.144997 | 0.092193 | 0.303776 | 0.353141 |  |
| h2_post_analyze_negative_missing_alert | 5 | 0.097515 | 0.081324 | 0.146844 | 0.159318 |  |
| h3_get_alerts_queue | 5 | 0.127994 | 0.123319 | 0.142957 | 0.143864 |  |
| h3_get_outcome_status_negative | 5 | 0.008487 | 0.005705 | 0.01587 | 0.016623 |  |
| h3_get_policy_history | 5 | 0.013413 | 0.015821 | 0.016687 | 0.016854 |  |
| h3_get_soc_profile | 5 | 0.101145 | 0.095483 | 0.143736 | 0.154352 |  |

## Source Map
```json
{
  "analyze_route": {
    "endpoint": "POST /api/alert/analyze",
    "definition": "backend/app/routers/triage.py:173",
    "sequence": [
      "scorer readiness guard: backend/app/routers/triage.py:184-197",
      "alert lookup via neo4j_client.get_alert: backend/app/routers/triage.py:202-208",
      "security context lookup: backend/app/routers/triage.py:210-216",
      "category resolution before scoring: backend/app/routers/triage.py:221-238",
      "factor/scorer pipeline: backend/app/routers/triage.py:240-354",
      "Decision write and DECIDED_ON edge: backend/app/routers/triage.py:435-464",
      "synchronous audit record and Decision hash SET: backend/app/routers/triage.py:466-483",
      "additional synchronous Decision metadata SETs/events: backend/app/routers/triage.py:509-667"
    ],
    "graph_reads": [
      "neo4j_client.get_alert(alert_id): backend/app/routers/triage.py:205",
      "neo4j_client.get_security_context(alert_id): backend/app/routers/triage.py:213",
      "Decision sequence/cross-category helper calls before referral: backend/app/routers/triage.py:366-373"
    ],
    "graph_writes": [
      "CREATE Decision and DECIDED_ON edge: backend/app/routers/triage.py:444-463",
      "SET entry_hash/decision_chain_index: backend/app/routers/triage.py:479-483",
      "additional Decision SETs for snapshots/provenance/exploration: backend/app/routers/triage.py:509-667"
    ],
    "negative_path_safety": "For a missing alert, source raises 404 immediately after get_alert returns empty at backend/app/routers/triage.py:205-208, before Decision creation at lines 442-463."
  },
  "outcome_route": {
    "endpoint": "POST /api/alert/outcome",
    "definition": "backend/app/routers/triage.py:1065",
    "sequence": [
      "feedback duplicate guard: backend/app/routers/triage.py:1082-1089",
      "Decision lookup and outcome/correct SET: backend/app/routers/triage.py:1125-1145",
      "outcome audit write and Decision hash SET: backend/app/routers/triage.py:1155-1170",
      "analyst history scan: backend/app/routers/triage.py:1174-1184",
      "learning_state/ProfileScorer update: backend/app/routers/triage.py:1261-1297",
      "conservation/DK/L5 centroid path: backend/app/routers/triage.py:1297-1459",
      "centroid metadata SET and snapshot/distance/evolution writes: backend/app/routers/triage.py:1496-1779"
    ],
    "graph_reads": [
      "Decision lookup by decision_id: backend/app/routers/triage.py:1125-1145",
      "analyst verified history scan: backend/app/routers/triage.py:1177-1180"
    ],
    "graph_writes": [
      "SET d.outcome/d.correct/d.verified_at_epoch: backend/app/routers/triage.py:1125-1133",
      "SET outcome_entry_hash/outcome_chain_index: backend/app/routers/triage.py:1166-1170",
      "persist_soc_centroid/L5 path: backend/app/routers/triage.py:1431-1459",
      "centroid_delta_norm Decision SET: backend/app/routers/triage.py:1496-1508",
      "evolution/log/snapshot writes: backend/app/routers/triage.py:1546-1779"
    ]
  },
  "safe_get_routes": [
    {
      "label": "h3_get_alerts_queue",
      "endpoint": "/api/alerts/queue",
      "source": "backend/app/routers/triage.py:117-137",
      "reason": "GET route performs MATCH-only pending alert read."
    },
    {
      "label": "h3_get_outcome_status_negative",
      "endpoint": "/api/alert/outcome/status?alert_id=PERF-NONEXISTENT-DO-NOT-CREATE",
      "source": "backend/app/routers/triage.py:1821-1838",
      "reason": "GET feedback status for non-proof alert id."
    },
    {
      "label": "h3_get_policy_history",
      "endpoint": "/api/alert/policy-history",
      "source": "backend/app/routers/triage.py:1964-1981",
      "reason": "GET in-memory policy conflict history."
    },
    {
      "label": "h3_get_soc_profile",
      "endpoint": "/api/soc/profile",
      "source": "backend/app/routers/triage.py:1995-2089",
      "reason": "GET ProfileScorer state; no source-level graph write in route."
    }
  ],
  "skipped_endpoints": [
    {
      "endpoint": "POST /api/alert/outcome",
      "reason": "Always a feedback/write route; forbidden for read-only benchmark."
    },
    {
      "endpoint": "POST /api/alert/analyze for proof alerts",
      "reason": "Normal analyze path writes Decision nodes and audit metadata."
    },
    {
      "endpoint": "GET /api/alert/policy-check",
      "reason": "Additional conflict-detection behavior is outside the minimal safe HTTP baseline."
    }
  ]
}
```

## Skipped Endpoints
```json
[
  {
    "endpoint": "POST /api/alert/outcome",
    "reason": "Always a feedback/write route; forbidden for read-only benchmark."
  },
  {
    "endpoint": "POST /api/alert/analyze for proof alerts",
    "reason": "Normal analyze path writes Decision nodes and audit metadata."
  },
  {
    "endpoint": "GET /api/alert/policy-check",
    "reason": "Additional conflict-detection behavior is outside the minimal safe HTTP baseline."
  }
]
```
