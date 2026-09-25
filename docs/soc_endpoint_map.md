# SOC Endpoint Map for Demo Specs

The standard aliases below are mounted by `backend/app/routers/compat_router.py`.
Restart the SOC backend after deploying this change before probing the aliases.

| Standard SDK path | SOC path | Status | Notes |
|---|---|---|---|
| `/api/fingerprint` | `/api/fingerprint` | Alias added | Returns standard fingerprint fields plus `categories`, `actions`, `factor_names`, `tensor_shape`, and `geometry`. |
| `/api/trajectory` | `/api/trajectory` | Alias added | Delegates to the SOC compound scorer trajectory. |
| `/api/conservation/status` | `/api/conservation/status` | Alias added | Delegates to the SOC learning-health calculation, including G-ABS/G-REL/G-RATE. |
| `/api/self/accuracy-by-category` | `/api/self/accuracy-by-category` | Available | Native shared self-computation route. |
| `/api/self/centroid-history` | `/api/self/centroid-history` | Available | Native shared self-computation route; checkpoint `shape` is `[6, 4, 6]`. |
| `/api/evolution/recent-events` | `/api/evolution/recent-events` | Available and seeded | SOC-03 fixture adds 47 created variants, 12 promotions, and 35 rejections. |
| `POST /api/alert/analyze` | `POST /api/alert/analyze` | Available | Native SOC triage route. Use planted alert `PL-SOC-1-NO-PRECEDENT-001` for a replayable request. |

## SOC-specific paths

| Path | What it returns |
|---|---|
| `/api/soc/learning-state` | SOC IKS state, decision totals, active categories, and bootstrap category weights. |
| `/api/soc/learning-health` | SOC conservation status with G-ABS, G-REL, and G-RATE details. |
| `/api/soc/evolution/rejection-summary` | SOC-03 aggregate tested/promoted/rejected counts and rejection reasons. |
| `/api/triage/learning-state` | Per-category two-phase learning state. |
| `/api/metrics/decision-economics` | SOC economic metrics and switching-cost trajectory; there is no standalone `/api/metrics/switching-cost` route. |

## MACH-04 geometry contract

SOC's scorer geometry is **6 categories × 4 scorer actions × 6 factors**.
The standard fingerprint alias exposes this in `geometry.category_count`,
`geometry.action_count`, `geometry.factor_count`, and `geometry.tensor_shape`
as well as top-level `tensor_shape`. The action list intentionally contains the
four centroid-scored actions; `refer_to_analyst` is a confidence-gated routing
action and is not a centroid tensor axis.
