# RL Design v4.0 — Graded Rewards, Credit Assignment, Conservation-Bounded Exploration
**Date:** May 6, 2026
**Version:** 4.0 (incorporates v3.0 + Codex adversarial review: 3 P1s resolved, 7 phases, zero new dependencies)
**Authority:** MAP v5.65 · Framework v4 · S2P PD v1.3
**Audience:** Codex (phase implementation prompts), coding session (implementation)
**Supersedes:** rl_design_v3.md, rl_design_v2.md, rl_design_v1.md, rl_design_addendum_v1.md

---

## §0 — Change Summary (v3.0 → v4.0)

| Change | Source | Impact |
|---|---|---|
| **DESIGN-P1-1 resolved:** eta_weight API → backend-scoped temporary multiplier | Codex review: `ProfileScorer.update()` has no `eta_weight` param | No GAE API change. Follows existing triage.py:1104-1123 pattern. |
| **DESIGN-P1-2 resolved:** exploration insertion → post-referral SET | Codex review: Decision node written before referral veto | Post-write SET updates exploration metadata after referral resolution. |
| **DESIGN-P1-3 resolved:** chain-credit query reads Decision, not EvolutionEvent | Codex review: `factor_snapshot`, `action_index`, `decision_number` live on `d:Decision` | Query corrected: `RETURN d.action_index, d.decision_number`. |
| DuckDB → **PostgreSQL** (existing) | Existing PG+AGE on WSL2 port 5433 | Zero new dependency. Uses existing psycopg connection. Simple relational table. |
| scipy.stats.beta.rvs → **random.betavariate** | Codex review: scipy not in requirements.txt | Zero new dependency. Stdlib. |
| 3 phases → **7 phases** with feature flags | Codex review: integration risks require isolation | Each phase has own prompt + GPT-5.5 review gate. |
| 5 open questions ALL closed | Codex review + roadmap session | Zero ambiguity for implementation. |
| 5 feature flags defined | Codex review recommendation | Each RL capability defaults OFF, flips after phase review. |
| Exploration in demo: proposals LOGGED, not ACTED ON | Decision on Q3 | Conservative: no live action exploration when LEARNING_ENABLED=False. |
| S2P = DESIGN INTENT only | Codex review: supply_chain domain is stub | SOC-first. S2P paths are `supply_chain`, not `s2p`. |
| **Schedule: 5.5d → 7d** | P1 integration complexity + phased review gates | Honest increase. |

**Total new dependencies: ZERO.** numpy (existing), random (stdlib), psycopg (existing via AGEClient infrastructure).

---

## §1 — What CI's RL Actually Is

CI's RL is a **contextual bandit with conservation constraints**. Not deep RL. Not an MDP. Not policy gradients. Not neural networks.

The ProfileScorer IS the policy. The RL layer adds four capabilities around it:

1. **Reward shaping** — graded by severity/impact, modulates η
2. **Credit assignment** — factor attribution via finite-differences + chain credit via TRIGGERED_EVOLUTION edges
3. **Exploration** — Thompson sampling from Beta posteriors per (c,a) cell
4. **Conservation binding** — exploration rate bounded by conservation margin

**Core invariant:** Binary reward is a SPECIAL CASE of graded reward. The conservation law (binary q over 400 decisions) is UNCHANGED. Graded rewards modulate η only. q is never computed from graded rewards.

### 1.1 What This Is NOT

**(a)** NOT a replacement for ProfileScorer. The scorer IS the policy.
**(b)** NOT an MDP. Each decision is independent given centroid tensor state.
**(c)** NOT deep RL. Thompson sampling from conjugate Beta priors.
**(d)** NOT a change to the conservation law. q = binary. Always.

### 1.2 Correct Language

Say "contextual bandit overlay" and "posterior over action cells," not "RL agent policy."

---

## §2 — Architecture

### 2.1 Components

```
                    ┌──────────────────┐
                    │  RewardComputer  │  ← Phase 1
                    │  graded + binary │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐  ┌───▼────────────┐  ┌──▼──────────────┐
    │ CreditAssigner │  │ EtaModulation  │  │ ExplorationPolicy│
    │ (read-only)    │  │ Adapter        │  │ (Thompson + cons)│
    │ Phase 3        │  │ Phase 0+4      │  │ Phase 2          │
    └────────────────┘  └────────────────┘  └────────┬─────────┘
                                                      │
                                              ┌───────▼────────┐
                                              │ PosteriorStore │
                                              │ (PostgreSQL)   │
                                              │ Phase 2        │
                                              └────────────────┘
```

### 2.2 State Ownership (No Overlap)

| Component | Owns | Never touches |
|---|---|---|
| ProfileScorer | Centroids, scoring policy | Posteriors, reward ledger |
| LearningState | Binary verified history, conservation q | Graded rewards, posteriors |
| RewardLedger | Graded rewards, reward explanations | Centroids, q, posteriors |
| PosteriorStore | Exploration Beta parameters | Centroids, q, rewards |
| AgentEvolver ledger | Operational artifact lifecycle | Rewards, posteriors |

### 2.3 Integration Points (Live Codebase)

**Analyze path** (triage.py ~L111-638):

```
Step 1:  Compute factors
Step 2:  ProfileScorer.score(f, category_index) → probabilities
Step 3:  Confidence gate (may route to refer_to_analyst)
Step 4:  [NEW] ExplorationPolicy.propose() — only if candidate is SCORER_ACTION
Step 5:  ReferralEngine R1-R7 VETO (wins over exploration)
Step 6:  Write Decision node (with scorer action)
Step 7:  [NEW] Post-write SET: exploration metadata + final_action after referral
```

**Outcome path** (triage.py ~L865-1360):

```
Step 1:  [NEW] RewardComputer.compute() → RewardResult
            (ALWAYS fires, regardless of LEARNING_ENABLED)
Step 2:  [NEW] RewardLedger.append(decision_id, reward_result)
            (ALWAYS fires)
Step 3:  Conservation check → _conservation_block
Step 4:  LEARNING_ENABLED gate
Step 5:  [NEW] acquire_scorer() → temporary eta multiplier → guarded_update()
            (ONLY when LEARNING_ENABLED=True)
Step 6:  IKS update
Step 7:  TRIGGERED_EVOLUTION edge write (correct decisions only)
Step 8:  [NEW] CreditAssigner.assign_chain_credit() — async, non-blocking
Step 9:  [NEW] ExplorationPolicy.update_posterior() — ONLY if:
            - decision was explored AND
            - exploration was NOT referral-vetoed AND
            - outcome was verified
Step 10: [NEW] PosteriorStore.save()
```

### 2.4 File Structure

```
NEW FILES:
  backend/app/services/rl_engine.py          ← RewardComputer, RewardLedger,
                                                CreditAssigner, ExplorationPolicy
  backend/app/services/posterior_store.py     ← PostgreSQL persistence for posteriors
  support/setup/soc_severity_weights.json    ← Category base severity weights
  support/setup/s2p_impact_ranges.json       ← S2P financial impact (DESIGN INTENT)

MODIFIED FILES:
  backend/app/routers/triage.py              ← Wire all components (Phase 4 ONLY)
  backend/app/framework/feedback_base.py     ← Extend get_reward_summary() return shape
  backend/app/domains/soc/config.py          ← Feature flags + severity config

TEST FILES:
  tests/test_reward_computer.py              ← Phase 1 (~15 tests)
  tests/test_reward_ledger.py                ← Phase 1 (~8 tests)
  tests/test_posterior_store.py              ← Phase 2 (~6 tests)
  tests/test_exploration_policy.py           ← Phase 2 (~14 tests)
  tests/test_credit_assigner.py             ← Phase 3 (~12 tests)
  tests/test_rl_triage_integration.py        ← Phase 4 (~15 tests)
  tests/test_rl_feature_flags.py            ← Phase 4 (~5 tests)
  support/scripts/retroactive_grading.py     ← Phase 6 (validation)
  support/scripts/synthetic_bandit.py        ← Phase 0 (validation)
```

### 2.5 Dependencies

```
REQUIRED:   numpy (already installed)
            psycopg (already installed — AGEClient uses it)
            random (stdlib — betavariate for Thompson sampling)

NEW:        ZERO

FORBIDDEN:  tf-agents, stable-baselines3, ray, trl, d3rlpy, keras,
            shap, duckdb, scipy (for MVP)
```

---

## §3 — RewardComputer (Phase 1)

### 3.1 Interface

```python
class RewardComputer:
    """Pure function. Inputs: outcome context. Outputs: RewardResult.
    NEVER calls ProfileScorer.update() or mutates posterior state."""
    
    def __init__(self, domain: str, severity_weights: dict,
                 penalty_ratio: float, reference_reward: float):
        self.domain = domain
        self.severity_weights = severity_weights  # Category base weights only
        self.penalty_ratio = penalty_ratio
        self.reference_reward = reference_reward  # Bootstrap default
        self._reward_history: list[float] = []
        self._ROLLING_WINDOW = 400
    
    def compute(self, action: str, outcome: str, category: str,
                context: dict) -> RewardResult:
        """Returns graded_reward + binary_outcome. Never mutates state."""
```

### 3.2 SOC Reward Formula

```python
def _compute_soc(self, outcome: str, category: str, context: dict) -> float:
    # MVP: category base weight ONLY. No technique_id lookup.
    # Technique-specific weights are a future enrichment when SIEM provides
    # ATT&CK classification. Demo alerts don't carry technique_id.
    severity = self.severity_weights.get(category, {}).get("base", 0.50)
    campaign_multiplier = 1.5 if context.get("campaign_id") else 1.0

    if outcome == "correct":
        return +1.0 * severity * campaign_multiplier
    else:
        return -1.0 * self.penalty_ratio * severity * campaign_multiplier
```

### 3.3 S2P Reward Formula (DESIGN INTENT — SOC-first implementation)

```python
def _compute_s2p(self, outcome: str, category: str, context: dict) -> float:
    financial_impact = context.get("financial_impact", 0.0)
    reference = self.severity_weights.get(category, {}).get("reference", 45.0)
    impact_weight = min(financial_impact / reference, 1.0)
    cluster_multiplier = 1.3 if context.get("exception_cluster") else 1.0

    if outcome == "correct":
        return +1.0 * impact_weight * cluster_multiplier
    else:
        return -1.0 * self.penalty_ratio * impact_weight * cluster_multiplier
```

### 3.4 η Modulation — Backend-Scoped Temporary Multiplier (P1-1 Resolved)

**Problem:** `ProfileScorer.update()` has no `eta_weight` parameter. `guarded_update()` forwards kwargs directly — passing `eta_weight` would raise.

**Solution:** Temporarily multiply `CalibrationProfile.eta_confirm` and `eta_override` under `acquire_scorer()` lock, then restore in `finally`. This pattern already exists at triage.py:1104-1123.

```python
# Phase 4: Inside triage.py report_decision_outcome(), LEARNING_ENABLED branch:

async with acquire_scorer() as scorer:
    cal = scorer.calibration
    original_eta = cal.eta_confirm
    original_eta_neg = cal.eta_override
    try:
        cal.eta_confirm = original_eta * reward_result.reward_weight
        cal.eta_override = original_eta_neg * reward_result.reward_weight
        guarded_update(scorer, f, cat_idx, act_idx, correct)
    finally:
        cal.eta_confirm = original_eta
        cal.eta_override = original_eta_neg
```

**Tests MUST verify:**
- `original_eta` is restored even on exception
- Concurrent requests don't see modified eta (acquire_scorer lock protects)
- `reward_weight` clip [0.1, 3.0] means max eta_confirm = 0.15, max eta_override = 0.03

### 3.5 reward_weight Computation

```python
def _compute_reward_weight(self, graded_reward: float) -> float:
    reference = self._get_reference_reward()
    raw = abs(graded_reward) / reference if reference > 0 else 1.0
    return max(0.1, min(raw, 3.0))

def _get_reference_reward(self) -> float:
    """Rolling median after 400 decisions. Domain default before that."""
    if len(self._reward_history) >= self._ROLLING_WINDOW:
        sorted_abs = sorted(abs(r) for r in self._reward_history[-self._ROLLING_WINDOW:])
        return sorted_abs[len(sorted_abs) // 2]  # Median without numpy
    return self.reference_reward

# Bootstrap defaults:
#   SOC: 0.50 (median of category base severity weights)
#   S2P: 0.30 (median of impact_weight at median dollar amounts)
```

### 3.6 LEARNING_ENABLED Interaction

```python
# RewardComputer.compute() fires ALWAYS (regardless of LEARNING_ENABLED)
reward_result = reward_computer.compute(action, outcome, category, context)
reward_ledger.append(decision_id, reward_result)

# η modulation fires ONLY when LEARNING_ENABLED=True
if LEARNING_ENABLED and action_name in SCORER_ACTIONS:
    # ... temporary eta multiplier pattern from §3.4
```

### 3.7 RewardResult Dataclass

```python
@dataclass
class RewardResult:
    graded_reward: float       # Severity/impact-weighted
    binary_outcome: bool       # True = correct, False = incorrect
    reward_weight: float       # abs(graded) / reference, clipped [0.1, 3.0]
    breakdown: dict            # {severity, campaign_multiplier, ...}
    domain: str                # "soc" or "supply_chain"
```

### 3.8 Severity Weights (SOC — Category Base Only)

```json
{
  "credential_access":     {"base": 0.70},
  "lateral_movement":      {"base": 0.80},
  "data_exfiltration":     {"base": 0.90},
  "insider_threat":        {"base": 0.75},
  "malware_execution":     {"base": 0.85},
  "cloud_infrastructure":  {"base": 0.65}
}
```

### 3.9 Retroactive Grading Validation

```python
correlation = np.corrcoef(graded_q_series, binary_q_series)[0, 1]

if correlation >= 0.95:   # PASS
elif correlation >= 0.90:  # WARNING — investigate severity calibration
else:                      # FAIL — do NOT deploy graded rewards
```

**Why 0.95:** Below 0.95, severity weights distort the learning signal enough that η modulation could push centroids in qualitatively different directions than binary learning.

---

## §4 — CreditAssigner (Phase 3)

### 4.1 Chain Credit — Corrected Query (P1-3 Resolved)

```cypher
MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent)
WHERE d.rec_category = {_S(category)}
  AND d.action_index = {_S(action_index)}
  AND d.decision_number >= {_S(n_current - LOOKBACK)}
  AND d.verified_correct = true
RETURN d.decision_id, d.decision_number, d.factor_snapshot, d.action_index
ORDER BY d.decision_number DESC
```

**Key correction from v3.0:** Read `d.decision_number`, `d.factor_snapshot`, `d.action_index` from Decision nodes, NOT from EvolutionEvent nodes. Live code stores these on Decision (triage.py:1267, 1270, 1285, 1288).

**Tolerance:** Chain credit must handle absent TRIGGERED_EVOLUTION edges gracefully. If zero edges found, return empty list — do not error.

### 4.2 Recency-Weighted Chain Credit

```python
HALF_LIFE = 30   # Consistent with PatternHistoryFactorComputer
LOOKBACK = 100   # ~3× HALF_LIFE
CHAIN_DISCOUNT = 0.5  # Total chain credit ≤ 50% of direct reward

for k in historical_decisions:
    age = n_current - k.decision_number
    w_k = math.exp(-math.log(2) * age / HALF_LIFE)

total_weight = sum(weights)
for k, w_k in zip(historical, weights):
    gamma_k = w_k / total_weight
    chain_credit_k = abs(r_current) * gamma_k * CHAIN_DISCOUNT
    reward_ledger.add_chain_credit(source_id, k.decision_id, chain_credit_k)
```

**Chain credit is stored SEPARATELY from direct reward.** Economics/display can show both. Conservation q never uses chain credit. Posterior never uses chain credit.

### 4.3 Factor Attribution (Finite-Differences)

```python
def compute_factor_attribution(scorer, f, category_index, action_index, reward):
    """12 scorer calls, <2ms. Read-only — never calls update()."""
    delta = 0.01
    attribution = {}
    for i in range(len(f)):
        f_plus = f.copy(); f_plus[i] = min(f_plus[i] + delta, 1.0)
        f_minus = f.copy(); f_minus[i] = max(f_minus[i] - delta, 0.0)
        p_plus = scorer.score(f_plus, category_index).probabilities[action_index]
        p_minus = scorer.score(f_minus, category_index).probabilities[action_index]
        attribution[i] = ((p_plus - p_minus) / (2 * delta)) * reward
    return attribution
```

**Tests MUST verify:** `compute_factor_attribution` calls `score()` only, never `update()`. Centroid state is unchanged after attribution.

### 4.4 Tab 6 Contributing Decisions Panel (Phase 5 — after API stable)

Deferred to Phase 5. Backend endpoint first, then frontend. Not in Phase 3 scope.

---

## §5 — ExplorationPolicy (Phase 2)

### 5.1 Thompson Sampling with Beta Posteriors

```python
import random

class ExplorationPolicy:
    def __init__(self, n_categories: int, n_actions: int,
                 epsilon_base: float = 0.05,
                 target_headroom: float = 10.0,
                 posterior_store: PosteriorStore | None = None):
        self.n_categories = n_categories
        self.n_actions = n_actions
        self.epsilon_base = epsilon_base
        self.target_headroom = target_headroom
        self._store = posterior_store
        
        if self._store:
            saved = self._store.load(n_categories, n_actions)
            self.alphas = saved["alphas"]
            self.betas = saved["betas"]
        else:
            self.alphas = [[1.0] * n_actions for _ in range(n_categories)]
            self.betas = [[1.0] * n_actions for _ in range(n_categories)]
    
    def propose(self, probabilities: list[float],
                category_index: int,
                conservation_margin: float) -> ExplorationDecision:
        """Propose an alternative action via Thompson sampling.
        
        Returns ExplorationDecision with original and proposed actions.
        Does NOT finalize — referral veto may override.
        """
        rate = self._compute_rate(conservation_margin)
        if rate == 0.0 or random.random() > rate:
            return ExplorationDecision(
                original_action=_argmax(probabilities),
                explored_action=None,
                explored=False,
                exploration_rate=rate,
            )
        
        # Thompson sampling from Beta posteriors
        sampled = [
            random.betavariate(
                self.alphas[category_index][a],
                self.betas[category_index][a]
            )
            for a in range(len(probabilities))
        ]
        total = sum(sampled)
        sampled = [s / total for s in sampled] if total > 0 else probabilities
        
        return ExplorationDecision(
            original_action=_argmax(probabilities),
            explored_action=_argmax(sampled),
            explored=True,
            exploration_rate=rate,
            posterior_snapshot={
                "alphas": list(self.alphas[category_index]),
                "betas": list(self.betas[category_index]),
            },
        )
```

### 5.2 Conservation-Bounded Exploration Rate

```python
def _compute_rate(self, conservation_margin: float) -> float:
    """
    margin = health["conservation"]["headroom"] or (signal - theta_min)
    
    margin ≤ 0 (AMBER/RED): exploration = 0
    margin ≥ target_headroom: full exploration = ε_base
    Linear interpolation between.
    """
    if conservation_margin <= 0:
        return 0.0
    return self.epsilon_base * min(conservation_margin / self.target_headroom, 1.0)
```

### 5.3 Exploration + Referral — Post-Write SET (P1-2 Resolved)

**Problem:** The Decision node is written before referral veto. Exploration metadata would be inconsistent if embedded in the initial write.

**Solution:** Exploration proposes after score + confidence gate. Decision is written with the scorer's action. After referral resolution, a post-write SET updates exploration fields:

```python
# In analyze_alert():

# Step 2: Score
scoring_result = scorer.score(f, category_index)
candidate_action = scoring_result.action_index

# Step 3: Confidence gate (may route to refer_to_analyst)
if confidence < threshold:
    candidate_action = REFER_TO_ANALYST  # Not a scorer action
    
# Step 4: Exploration proposal (only for SCORER_ACTIONS)
exploration_decision = ExplorationDecision(explored=False)
if RL_EXPLORATION_ENABLED and candidate_action in SCORER_ACTION_INDICES:
    margin = health.get("conservation", {}).get("headroom", 0.0)
    exploration_decision = exploration_policy.propose(
        scoring_result.probabilities, category_index, margin
    )
    if exploration_decision.explored:
        candidate_action = exploration_decision.explored_action

# Step 5: Referral veto (wins over exploration)
referred = referral_engine.check(...)
if referred:
    final_action = REFER_TO_ANALYST
    explored_but_referred = exploration_decision.explored
else:
    final_action = candidate_action
    explored_but_referred = False

# Step 6: Write Decision node (with final_action)
# Step 7: Post-write SET for exploration metadata
if exploration_decision.explored:
    await neo4j_client.run_query(f"""
        MATCH (d:Decision {{decision_id: {_S(decision_id)}}})
        SET d.explored = true,
            d.exploration_rate = {exploration_decision.exploration_rate},
            d.original_action = {_S(original_action_name)},
            d.explored_action = {_S(explored_action_name)},
            d.explored_but_referred = {str(explored_but_referred).lower()}
    """)
```

### 5.4 Posterior Update Rules

```python
# In report_decision_outcome():

# Posterior update conditions (ALL must be true):
# 1. RL_EXPLORATION_ENABLED is True
# 2. Decision was explored (d.explored = true)
# 3. Exploration was NOT referral-vetoed (d.explored_but_referred = false)
# 4. Outcome was verified (binary_outcome is known)

if (RL_EXPLORATION_ENABLED
    and decision.explored
    and not decision.explored_but_referred):
    exploration_policy.update_posterior(
        category_index, action_index, correct
    )
    posterior_store.save(exploration_policy.alphas, exploration_policy.betas)
```

**When LEARNING_ENABLED=False:** Exploration proposals are LOGGED on Decision nodes but NOT ACTED ON. The candidate_action remains the scorer's action. Posteriors do NOT update because there's no verified outcome for an exploration that wasn't executed.

### 5.5 Posterior Reset on Disruption

```python
def on_conservation_transition(self, old_state, new_state):
    """Reset to weak priors (2,2). Simpler than decay.
    Decay preserves stale posteriors that caused the problem."""
    if new_state in ("AMBER", "RED"):
        self.alphas = [[2.0] * self.n_actions for _ in range(self.n_categories)]
        self.betas = [[2.0] * self.n_actions for _ in range(self.n_categories)]
        if self._store:
            self._store.save(self.alphas, self.betas)
            self._store.log_reset(new_state)  # Audit trail
```

### 5.6 ExplorationDecision Dataclass

```python
@dataclass
class ExplorationDecision:
    original_action: int
    explored_action: int | None
    explored: bool
    exploration_rate: float = 0.0
    posterior_snapshot: dict | None = None
    reason: str = ""
```

---

## §6 — PosteriorStore (PostgreSQL — Phase 2)

### 6.1 Design

Uses the existing PostgreSQL instance (PG 17, WSL2, port 5433) that AGE already runs on. Simple relational table — NOT a graph structure. Uses psycopg directly, not AGE Cypher.

```python
# backend/app/services/posterior_store.py

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)

class PosteriorStore:
    """PostgreSQL persistence for Beta posteriors. ~40 LOC.
    
    Uses the same PostgreSQL instance as AGE (port 5433).
    Simple relational table, not graph nodes.
    Fail-open: if DB unavailable, exploration disables itself.
    """
    
    def __init__(self, dsn: str | None = None):
        self._dsn = dsn  # From .env, same as AGE connection
        self._ensure_table()
    
    def _get_dsn(self) -> str:
        if self._dsn:
            return self._dsn
        import os
        return os.environ.get(
            "POSTERIOR_DSN",
            "postgresql://postgres:postgres@localhost:5433/soc_graph"
        )
    
    def _ensure_table(self):
        """Create table if not exists. Idempotent."""
        try:
            import psycopg
            with psycopg.connect(self._get_dsn()) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rl_posteriors (
                        category INTEGER NOT NULL,
                        action INTEGER NOT NULL,
                        alpha DOUBLE PRECISION DEFAULT 1.0,
                        beta DOUBLE PRECISION DEFAULT 1.0,
                        updated_epoch BIGINT,
                        PRIMARY KEY (category, action)
                    )
                """)
                conn.commit()
        except Exception as exc:
            log.warning("[PosteriorStore] table creation failed: %s", exc)
    
    def save(self, alphas: list[list[float]], betas: list[list[float]]):
        """Upsert all posteriors. Called after posterior update."""
        try:
            import psycopg
            import time
            epoch = int(time.time() * 1000)
            with psycopg.connect(self._get_dsn()) as conn:
                conn.execute("DELETE FROM rl_posteriors")
                for c in range(len(alphas)):
                    for a in range(len(alphas[c])):
                        conn.execute(
                            "INSERT INTO rl_posteriors (category, action, alpha, beta, updated_epoch) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (c, a, alphas[c][a], betas[c][a], epoch)
                        )
                conn.commit()
        except Exception as exc:
            log.warning("[PosteriorStore] save failed: %s", exc)
    
    def load(self, n_categories: int, n_actions: int) -> dict:
        """Load posteriors. Returns default (1,1) if not found.
        Fail-open: exploration uses uninformative priors on failure."""
        alphas = [[1.0] * n_actions for _ in range(n_categories)]
        betas = [[1.0] * n_actions for _ in range(n_categories)]
        try:
            import psycopg
            with psycopg.connect(self._get_dsn()) as conn:
                rows = conn.execute(
                    "SELECT category, action, alpha, beta FROM rl_posteriors"
                ).fetchall()
                for c, a, al, be in rows:
                    if c < n_categories and a < n_actions:
                        alphas[c][a] = al
                        betas[c][a] = be
        except Exception as exc:
            log.warning("[PosteriorStore] load failed: %s", exc)
        return {"alphas": alphas, "betas": betas}
    
    def log_reset(self, reason: str):
        """Audit log for posterior resets."""
        log.info("[PosteriorStore] posteriors reset: %s", reason)
```

### 6.2 Connection

Same DSN as AGE. Same `postgres:postgres@localhost:5433/soc_graph`. The `rl_posteriors` table coexists with AGE graph tables in the same database. No new server, no new port, no new credentials.

### 6.3 Failure Behavior

- Read failure: exploration disabled (uses uninformative priors = random exploration)
- Write failure: logged, triage continues, `posterior_update_failed=true` in reward ledger
- Table creation failure: logged at startup, all exploration defaults to disabled
- Corruption: load returns defaults, effectively a clean start

---

## §7 — RewardLedger (Phase 1)

### 7.1 Design

New append-only durable store. Separate from `FEEDBACK_GIVEN` (in-memory aggregate) and AgentEvolver `EvolutionEvent` (lifecycle records with fixed event types).

### 7.2 Schema

```python
@dataclass
class RewardLedgerEntry:
    decision_id: str
    alert_id: str
    category: str
    action: str
    binary_outcome: bool
    graded_reward: float
    reward_weight: float       # η multiplier
    explored: bool
    explored_but_referred: bool
    posterior_updated: bool
    chain_credits: list[ChainCredit]  # Added async in Phase 3
    timestamp_epoch: int
    domain: str
    schema_version: int = 1
```

### 7.3 Storage

MVP: in-memory list with JSON file backup. PostgreSQL table in Phase 5 if durability is needed beyond restart. The ledger is explanatory — its loss does not affect scoring or conservation.

---

## §8 — Feature Flags

```python
# backend/app/domains/soc/config.py (add alongside LEARNING_ENABLED)

RL_REWARD_LEDGER_ENABLED = False      # Phase 1: reward computation + ledger
RL_ETA_MODULATION_ENABLED = False     # Phase 4: η × reward_weight
RL_EXPLORATION_ENABLED = False        # Phase 4: Thompson sampling proposals
RL_CHAIN_CREDIT_ENABLED = False       # Phase 4: chain credit computation
RL_FORCE_NO_EXPLORE_PRE_ACTIVATION = True  # When LEARNING_ENABLED=False, no exploration
```

Each flag defaults False. Flip after the corresponding phase passes GPT-5.5 review. All flags readable at runtime — no restart required to disable a misbehaving component.

---

## §9 — Phased Implementation Plan

| Phase | Scope | Files touched | Exit criteria | Tests | Gate |
|---|---|---|---|---|---|
| **0** | Eta contract validation + synthetic bandit | Documentation + test scripts only | Temporary eta multiplier pattern works. Synthetic bandit converges within O(√T) regret. | ~5 | GPT-5.5 |
| **1** | RewardComputer + RewardLedger | New `rl_engine.py`, new test files. NO triage changes. | Pure reward computation works. Binary/graded separation proven. Ledger append/read works. | ~23 | GPT-5.5 |
| **2** | PosteriorStore + ExplorationPolicy | New `posterior_store.py`, extend `rl_engine.py`. NO triage changes. | PostgreSQL persistence round-trip. Thompson sampling correct. Conservation-bounded rate works. Referral-veto skip function works. | ~20 | GPT-5.5 |
| **3** | CreditAssigner | Extend `rl_engine.py`. NO triage changes. | Read-only factor attribution. Chain-credit query reads Decision nodes (corrected). Missing edges handled. | ~12 | GPT-5.5 |
| **4** | Triage integration | `triage.py` ONLY (plus feature flag config). Requires Phases 1-3 complete. | Reward + posterior + exploration run on verified outcomes behind flags. η adapter works. Existing tests unbroken. | ~20 | GPT-5.5 **required** |
| **5** | Read-only APIs + Tab visibility | Backend endpoints, then frontend if needed. | Reward summary, posterior summary, chain-credit endpoint. Non-mutating. | ~8 | GPT-5.5 recommended |
| **6** | Retroactive grading + synthetic bandit | Support scripts only. | graded_q correlates with binary_q at ≥0.95. Synthetic bandit converges. | ~6 | GPT-5.5 |

**Schedule: 7 working days total.**

| Phase | Effort |
|---|---|
| 0 | 0.5d |
| 1 | 1.5d |
| 2 | 1.5d |
| 3 | 1.0d |
| 4 | 1.5d |
| 5 | 0.5d |
| 6 | 0.5d |

### Stop Conditions (ANY triggers immediate halt)

- Graded reward feeds into conservation law q
- Exploration overrides referral/human-review safety
- Posterior updates without verified outcome
- Unknown kwargs passed to `ProfileScorer.update()`
- New dependency added without explicit approval
- AGE write uses unsafe interpolation without `_S()`
- Triage + frontend modified in the same phase

---

## §10 — Critical Design Invariants

1. **Binary q only.** `LearningHealthMonitor._extract_components()` computes q from `wu.outcome == 1`. Never from graded reward.
2. **Graded reward never enters conservation.** `graded_reward` never written into `LearningState.history.outcome` or `correct_bool`.
3. **Centroid mutation remains gated.** `ProfileScorer.update()` under `LEARNING_ENABLED and action_name in SCORER_ACTIONS`.
4. **Posterior ≠ centroid mutation.** Posterior and reward ledger updates may run while LEARNING_ENABLED=False. They never call `ProfileScorer.update()`.
5. **Referral veto wins.** Exploration never overrides referral to human review.
6. **Referral-vetoed exploration skip.** Posterior updates skip explored alternatives vetoed before execution.
7. **Exploration bounded.** Rate = 0 when health is RED/AMBER, margin ≤ 0, or health unavailable.
8. **No deep RL dependencies.** No policy gradients, replay buffers, neural policies.
9. **Credit assignment is non-mutating.** Finite-differences calls score() only. Never update().
10. **Chain credit is transparent.** Direct reward and chain credit stored separately. No double-counting in q or posteriors.
11. **AGE query safety.** `_S()` for strings, inline numerics, no `$params`, no `SET n = {}`.
12. **Persistence failure fail-open.** Posterior/ledger failures: log, disable exploration, don't crash triage.
13. **Eta restoration guaranteed.** Temporary eta multiplier always restored in `finally` block.

---

## §11 — Resolved Decisions

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | target_headroom | 10.0 | Conservative. Calibrate with pilot data. |
| Q2 | CHAIN_DISCOUNT | 0.5 | Meaningful for display without double-counting. |
| Q3 | Posterior reset vs decay | Reset to (2,2) | Simpler. Decay preserves stale posteriors. |
| Q4 | η clip range | [0.1, 3.0] | Max 0.15 confirms, 0.03 overrides. Within validated envelope. |
| Q5 | Exploration in demo | Proposals LOGGED, not acted on | Conservative. No live exploration when LEARNING_ENABLED=False. |
| Q6 | Eta integration | Backend-scoped temporary multiplier | No GAE API change. Existing triage.py pattern. |
| Q7 | Persistence backend | PostgreSQL (existing) | Zero new dependency. Same DB as AGE. |
| Q8 | Thompson sampling | random.betavariate (stdlib) | Zero new dependency. |
| Q9 | S2P timing | Design intent only. SOC-first. | supply_chain domain is stub. |
| Q10 | Action-space scope | SCORER_ACTIONS only (4 for SOC) | Never refer_to_analyst. |

---

## §12 — Codex Phase Prompt Guidance

```
Phase 0: Finalize eta contract. Write synthetic bandit validation.
         Stop if GAE API change required.
Phase 1: Implement RewardComputer + RewardLedger. NO triage edits.
Phase 2: Implement PosteriorStore + ExplorationPolicy. NO triage edits.
Phase 3: Implement CreditAssigner. NO triage edits.
Phase 4: Integrate into triage behind feature flags. GPT-5.5 REQUIRED.
Phase 5: Read-only APIs. Defer frontend until API stable.
Phase 6: Retroactive grading validation. No writes without explicit apply.
```

Each prompt references this document as design authority.

### Codex Review Verification (All Phases)

```
VERIFY:
1. RewardComputer returns BOTH graded_reward AND binary_outcome
2. Conservation q is NEVER computed from graded rewards
3. η_effective uses temporary multiplier pattern, not kwargs
4. Temporary eta is ALWAYS restored in finally block
5. CreditAssigner reads Decision nodes (d.), not EvolutionEvent (e.)
6. Chain credit sum ≤ 0.5 × abs(direct_reward)
7. Exploration rate = 0 when margin ≤ 0
8. Referral veto fires AFTER exploration proposal
9. Referral-vetoed explorations do NOT update posteriors
10. All AGE queries use _S(), no $param
11. Factor attribution calls score() only, never update()
12. RewardComputer fires regardless of LEARNING_ENABLED
13. Posterior updates require RL_EXPLORATION_ENABLED + explored + not referred
14. PosteriorStore uses existing PostgreSQL (port 5433)
15. Thompson sampling uses random.betavariate (stdlib)
16. No new dependencies beyond numpy + psycopg + random
17. Feature flags default False
18. Exploration metadata written via post-write SET

FLAG IF:
- Any graded_reward → conservation q path
- Any exploration → override referral path
- Any posterior update without verified outcome
- Any ProfileScorer.update() receiving unknown kwargs
- Any new pip dependency
- Any AGE query without _S()
- Any persistent write blocking triage response
```

---

*RL Design v4.0 · May 6, 2026*
*Contextual bandit overlay, not deep RL. Binary is a special case of graded.*
*Conservation unchanged. η modulated via temporary multiplier. Exploration bounded.*
*Posteriors persisted in existing PostgreSQL. Zero new dependencies.*
*7 phases. 5 feature flags. 13 invariants. 10 resolved decisions.*
*~110 tests across 7 phases. 7 working days.*
*"The system learns MORE from the decisions that matter most."*
