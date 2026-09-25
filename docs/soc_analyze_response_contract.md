# SOC Analyze Response Contract

Verified against the running SOC backend on 2026-09-18 using the planted alert
`PL-SOC-1-NO-PRECEDENT-001` with:

```json
{"alert_id":"PL-SOC-1-NO-PRECEDENT-001"}
```

at `POST /api/alert/analyze`.

## Required request

| Field | Type | Notes |
|---|---|---|
| `alert_id` | string | Use a seeded Alert node identifier. |

## Response fields used by demo specs

| Need | Verified path | Notes |
|---|---|---|
| Recommended action | `recommendation.action` | The action is not a top-level field. |
| Confidence | `recommendation.confidence` | Numeric confidence. |
| Routing zone | `recommendation.routing_zone` | For example, `human_review`. |
| Decision identifier | `recommendation.decision_id` | Also present in `gae_scoring.decision_id` and `provenance.decision_id`. |
| Factor values | `gae_scoring.factor_vector` | Six-number scorer input vector. |
| Factor names | `gae_scoring.factor_names` | Positional names for `factor_vector`. |
| Action probabilities | `gae_scoring.action_probabilities` | Mapping by scorer action. |
| Novelty | `no_precedent.is_novel` | The verified field is `no_precedent`, not `novelty`. |
| Novelty distance | `no_precedent.min_distance` | Compare with `no_precedent.threshold`. |
| Analyst referral | `referral.should_refer` | Reasons are in `referral.reasons`. |
| Referral details | `referral.authority_veto` | Present when authority constrains automation. |
| Gate result | `composite_gate.auto_approve` | Supporting score and reason codes are adjacent. |
| Graph evidence | `graph_data.nodes`, `graph_data.relationships` | Traversed graph data. |
| Provenance | `provenance.factors` | Per-factor methods, nodes consulted, and explanations. |

## Top-level response shape

```text
alert, attack_technique, attack_tactic, analysis, context, recommendation,
gae_scoring, graph_data, situation_analysis, campaign_context, composite_gate,
provenance, referral, referral_debug, exploration_status, decision_method,
authority, no_precedent, cluster_history, narrative
```

`campaign_context` may be `null`; specs must treat it as optional.

## Verified planted IDs

| Alert ID | Scenario | `POST /api/alert/analyze` |
|---|---|---|
| `PL-SOC-1-NO-PRECEDENT-001` | SOC-02 | 200 |
| `PL-SOC-3-POLICY-CONFLICT-001` | SOC-06 | 200 |
| `PL-SOC-4-FROZEN-TWIN-001` | SOC-08 | 200 |

`PL-SOC-4-FROZEN-TWIN-001` is seeded as an analyzable Alert in addition to
its frozen-twin checkpoint setup. All planted records are marked
`planted=true` and `sample=true`.
