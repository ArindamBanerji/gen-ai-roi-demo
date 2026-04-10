# Frontend → Backend Bindings

Which frontend tab calls which API endpoint.
Source of truth: grep for `fetch(` and API helper calls in each tab component.

## AlertTriageTab.tsx
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/alerts/queue` | GET | Load alert queue |
| `/api/alert/analyze` | POST | Analyze selected alert |
| `/api/action/execute` | POST | Execute triage action |
| `/api/alerts/reset` | POST | Reset alert pool |
| `/api/triage/decision-factors/{id}` | GET | Factor breakdown |
| `/api/alert/policy-check` | GET | Policy conflict check |
| `/api/graph/threat-intel/refresh` | POST | Refresh threat intel |
| `/api/graph/enrichment/by-alert/{id}` | GET | Alert enrichment |
| `/api/soc/campaigns/{id}` | GET | Campaign detail |

## RuntimeEvolutionTab.tsx
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/deployments` | GET | Deployment list |
| `/api/rl/reward-summary` | GET | Reward summary |
| `/api/soc/profile` | GET | ProfileScorer state |
| `/api/soc/accuracy-trajectory` | GET | Accuracy trajectory |
| `/api/soc/graph-stats` | GET | Graph statistics |
| `/api/soc/centroid-evolution` | GET | Centroid drift |
| `/api/soc/learning-state` | GET | Weight matrix + step |
| `/api/soc/centroid-heatmap` | GET | Centroid heatmap |
| `/api/soc/enrichment-status` | GET | Enrichment status |
| `/api/soc/centroid-support` | GET | Centroid support |

## SOCAnalyticsTab.tsx
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/soc/query` | POST | Metric query |
| `/api/soc/threat-landscape` | GET | Threat landscape |
| `/api/soc/attack-tactic-breakdown` | GET | Tactic breakdown |
| `/api/soc/detection-engineering` | GET | Detection engineering |

## CompoundingTab.tsx
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/metrics/compounding` | GET | Compounding metrics |
| `/api/metrics/evolution-events` | GET | Evolution events |
| `/api/metrics/decision-economics` | GET | Decision economics |
| `/api/audit/decisions` | GET | Audit decisions |
| `/api/audit/verify` | GET | Audit chain verify |
| `/api/gae/convergence` | GET | GAE convergence |
| `/api/gae/confidence-trajectory` | GET | Confidence trajectory |
| `/api/gae/trust-curve` | GET | Trust curve |
| `/api/gae/before-after` | GET | Before/after comparison |
| `/api/soc/centroid-evolution` | GET | Centroid evolution |
| `/api/soc/profile` | GET | ProfileScorer state |
| `/api/soc/operational-metrics` | GET | Operational metrics |
| `/api/soc/board-export` | GET | Board export |
| `/api/soc/economics` | GET | Economics summary |
| `/api/demo/reset-all` | POST | Full demo reset |
| `/api/alerts/reset` | POST | Alert pool reset |
| `/api/demo/reseed` | POST | Reseed demo data |

## ExecutiveNarrativeTab.tsx
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/soc/executive-narrative` | GET | Narrative digest |
| `/api/soc/executive-narrative/pdf` | GET | PDF download |
