# SOC-05 Kill-Chain Correlation Contract

The SOC-05 Playwright spec should call:

```http
POST http://127.0.0.1:8001/api/alert/cross-correlate
Content-Type: application/json
```

```json
{
  "alert_ids": [
    "PL-SOC-5-KILLCHAIN-A",
    "PL-SOC-5-KILLCHAIN-B"
  ]
}
```

The planted pair is seeded by `scripts/preseed_demo_scenarios.py` from
`data/demo_fixtures/kill_chain_pair.json`. Both alerts are individually low
severity and share `user-admin-003` and `asset-dc-west-01`.

The successful response has these assertions:

```text
correlation.kill_chain_detected == true
correlation.kill_chain_pattern == "credential_access → lateral_movement"
correlation.combined_severity == "critical"
correlation.recommendation == "Escalate as coordinated attack"
correlation.shared_entities includes user-admin-003 and asset-dc-west-01
```

Known ordered patterns are credential access → lateral movement,
malware execution → credential access, credential access → data exfiltration,
and cloud infrastructure → insider threat. A pattern only elevates when the
pair also shares a user, asset, or network entity. Unmatched pairs return
`kill_chain_detected: false`, null combined severity/recommendation, and zero
confidence.
