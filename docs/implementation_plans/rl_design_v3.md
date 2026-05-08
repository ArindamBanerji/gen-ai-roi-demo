# RL Design v3.0 — Graded Rewards, Credit Assignment, Conservation-Bounded Exploration
**Date:** May 6, 2026
**Version:** 3.0 (incorporates v2.0 + roadmap session review: 7 issues resolved, 5 open questions closed)
**Authority:** MAP v5.65 · Framework v4 · S2P PD v1.3
**Audience:** Codex (adversarial review), coding session (implementation)
**Supersedes:** rl_design_v2.md, rl_design_v1.md, rl_design_addendum_v1.md

---

## §0 — Change Summary (v2.0 → v3.0)

| Change | Source | Impact |
|---|---|---|
| Posterior persistence via DuckDB specified | Roadmap review Issue 1 | +20 LOC, +4 tests. Posteriors survive restart. |
| Referral-vetoed explorations don't update posteriors | Roadmap review Issue 2 | +5 LOC, +2 tests. Prevents phantom posterior updates. |
| Technique-specific severity removed from MVP | Roadmap review Issue 3 | -50 LOC. Category base weights only. Simpler. |
| Tab 6 "Contributing decisions" panel specified | Roadmap review Issue 4 | Chain credit becomes visible in the product. |
| Exploration fires in demo mode (posteriors update, centroids don't) | Roadmap review Issue 5 | Demo can show exploration events + rate changes. |
| Retroactive grading validation tiers specified | Roadmap review Issue 6 | 0.95=PASS, 0.90-0.95=WARNING, <0.90=FAIL. |
| reference_reward bootstrap with domain defaults | Roadmap review Issue 7 | SOC=0.50, S2P=0.30. Rolling median after 400 decisions. |
| All 5 open questions from v2.0 resolved | Roadmap review Part 4 | Zero ambiguity for implementation. |
| Net effort unchanged at 5.5 days | Simplifications offset additions | Technique removal saves what persistence adds. |

---

## §1 — What CI's RL Actually Is

CI's RL is a **contextual bandit with conservation constraints**, not deep RL. No neural networks, no policy gradients, no replay buffers, no GPU training. The ProfileScorer (~800 lines of numpy) is the policy. The RL layer adds four capabilities:

1. **Reward shaping** — graded by severity/impact, modulates η
2. **Credit assignment** — factor attribution via finite-differences + chain credit via TRIGGERED_EVOLUTION edges
3. **Exploration** — Thompson sampling from Beta posteriors per (c,a) cell
4. **Conservation binding** — exploration rate bounded by conservation margin

**Design philosophy:** Binary reward is a SPECIAL CASE of graded reward. The conservation law (binary q) is UNCHANGED. Graded rewards modulate η only. The conservation law — the property that every LLM-judge persona rated 5/5/5 — is untouched.

### 1.1 What This Is NOT

**(a)** NOT a replacement for ProfileScorer. The scorer IS the policy. RL shapes what feeds the scorer.
**(b)** NOT an MDP. Each decision is independent given the current centroid tensor.
**(c)** NOT deep RL. Thompson sampling from conjugate priors (Beta distributions).
**(d)** NOT a change to the conservation law. q = binary rolling accuracy over 400 decisions. Always.

---

## §2 — Architecture

### 2.1 Three New Components + One Persistence Layer

```
                    ┌──────────────────┐
                    │  RewardComputer  │  ← RL-01 (§3)
                    │  graded + binary │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐  ┌───▼────────┐  ┌──▼──────────────┐
    │ CreditAssigner │  │ η_effective │  │ ExplorationPolicy│
    │ (attribution)  │  │ modulation  │  │ (Thompson + cons)│
    │ RL-02 (§4)     │  │ (§3.4)      │  │ RL-03 (§5)       │
    └────────────────┘  └────────────┘  └────────┬─────────┘
                                                  │
                                          ┌───────▼────────┐
                                          │ PosteriorStore │
                                          │ (DuckDB)       │
                                          │ RL-03 (§5.7)   │
                                          └────────────────┘
```

### 2.2 Integration Points (Live Codebase References)

```
analyze_alert() [triage.py ~L111-638]:
  Step 3: ProfileScorer.score(f, category_index) → action probabilities
  Step 3.5 [NEW]: ExplorationPolicy.maybe_explore(probabilities, category, margin)
    → If explored AND referral vetoes: do NOT update posterior later
  Step 4: ReferralEngine R1-R7 VETO
  Step 5: AE-02 shadow comparison

report_decision_outcome() [triage.py ~L865-1360]:
  Step 1 [NEW, ~L1030]: RewardComputer.compute(action, outcome, category, context)
           → graded_reward + binary_outcome
           → stored in reward ledger (ALWAYS, regardless of LEARNING_ENABLED)
  Step 2: Conservation check → _conservation_block
  Step 3: LEARNING_ENABLED gate
  Step 4: acquire_scorer() → guarded_update()
           η_effective = η_base × clip(reward_weight, 0.1, 3.0)  [NEW]
  Step 5: IKS update
  Step 6: TRIGGERED_EVOLUTION edge write
  Step 7 [NEW]: CreditAssigner.assign_chain_credit(decision, graded_reward)
  Step 8 [NEW]: ExplorationPolicy.update(category, action, correct)
           → ONLY if decision was NOT referral-vetoed
           → PosteriorStore.save() after update
```

### 2.3 File Structure

```
NEW FILES:
  backend/app/services/rl_engine.py          ← RewardComputer, CreditAssigner,
                                                ExplorationPolicy, RewardLedger
  backend/app/services/posterior_store.py     ← DuckDB persistence for Beta posteriors
  backend/app/domains/soc/severity.py        ← SOC severity weights (category base only)
  backend/app/domains/s2p/impact.py          ← S2P financial impact ranges
  support/setup/soc_severity_weights.json    ← Lookup table (category base weights)
  support/setup/s2p_impact_ranges.json       ← Lookup table (Hackett benchmarks)

MODIFIED FILES:
  backend/app/routers/triage.py              ← Wire RewardComputer + ExplorationPolicy
  backend/app/framework/feedback_base.py     ← Extend get_reward_summary() return shape
  backend/app/domains/soc/config.py          ← Add severity config to SOCDomainConfig
  backend/app/domains/s2p/config.py          ← Add impact config to S2PDomainConfigV2

TEST FILES:
  tests/test_reward_computer.py              ← ~20 tests
  tests/test_credit_assigner.py              ← ~17 tests
  tests/test_exploration_policy.py           ← ~20 tests
  tests/test_posterior_store.py              ← ~4 tests
  tests/test_rl_integration.py              ← ~10 tests
```

### 2.4 Dependencies

```
REQUIRED:   numpy (already installed)
            scipy.stats (already installed — Beta distributions)
            duckdb (pip install duckdb — ~15MB, for posterior persistence)

OPTIONAL:   None for MVP

FORBIDDEN:  tf-agents, stable-baselines3, ray, trl, d3rlpy, keras, shap
```

**duckdb justification:** Posteriors take hundreds of decisions to become informative. Losing them on uvicorn restart means re-exploring everything from scratch — 537 decisions of calibration wasted. DuckDB is embedded (no server), ~15MB, and the persistence layer is ~20 LOC. SQLite is an acceptable alternative if duckdb presents issues.

---

## §3 — RewardComputer (RL-01)

### 3.1 Design

```python
class RewardComputer:
    """Computes graded rewards from decision outcomes.
    
    Returns BOTH:
      - graded_reward: severity/impact-weighted (for η modulation + economics)
      - binary_outcome: simple correct/incorrect (for conservation law q)
    
    Conservation law is UNCHANGED. It continues using binary q.
    """
    
    def __init__(self, domain: str, severity_weights: dict, penalty_ratio: float,
                 reference_reward: float):
        self.domain = domain  # "soc" or "s2p"
        self.severity_weights = severity_weights
        self.penalty_ratio = penalty_ratio  # SOC=20.0, S2P=5.0
        self.reference_reward = reference_reward  # Bootstrap default
        self._reward_history: list[float] = []  # For rolling median
        self._ROLLING_WINDOW = 400
    
    def compute(self, action: str, outcome: str, category: str,
                context: dict) -> RewardResult:
        """
        Args:
            action: selected action (e.g., "investigate", "auto_approve")
            outcome: "correct" or "incorrect"
            category: alert/invoice category
            context: {confidence, campaign_id, financial_impact, ...}
        
        Returns:
            RewardResult with graded_reward, binary_outcome, reward_weight,
            breakdown dict
        """
```

### 3.2 SOC Reward Formula

```python
def _compute_soc(self, outcome: str, category: str, context: dict) -> float:
    severity = self.severity_weights.get(category, {}).get("base", 0.50)
    # MVP: category base weight ONLY. No technique_id lookup.
    # Technique-specific weights are a future enrichment when SIEM
    # integration provides ATT&CK classification.

    campaign_multiplier = 1.5 if context.get("campaign_id") else 1.0

    if outcome == "correct":
        return +1.0 * severity * campaign_multiplier
        # Range: [0.0, 1.5]
    else:  # "incorrect"
        return -1.0 * self.penalty_ratio * severity * campaign_multiplier
        # Range: [-30.0, 0.0] for SOC (penalty_ratio=20.0)
```

### 3.3 S2P Reward Formula

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

### 3.4 η Modulation

```python
def _compute_reward_weight(self, graded_reward: float) -> float:
    """Convert graded reward to η multiplier.
    
    reward_weight = abs(graded) / reference_reward
    Clipped to [0.1, 3.0] to prevent extreme learning rate swings.
    
    Max η_effective = 0.05 × 3.0 = 0.15 (confirms)
    Max η_effective = 0.01 × 3.0 = 0.03 (overrides)
    Both within the validated 24-persona sweep envelope.
    """
    raw = abs(graded_reward) / self.reference_reward
    return max(0.1, min(raw, 3.0))
```

**reference_reward bootstrap (Issue 7 resolved):**

```python
def _get_reference_reward(self) -> float:
    """Rolling median after 400 decisions. Domain default before that."""
    if len(self._reward_history) >= self._ROLLING_WINDOW:
        return float(np.median(np.abs(self._reward_history[-self._ROLLING_WINDOW:])))
    return self.reference_reward  # Domain bootstrap default

# Domain defaults:
#   SOC: 0.50 (median of category base severity weights)
#   S2P: 0.30 (median of impact_weight at median dollar amounts)
```

### 3.5 LEARNING_ENABLED Interaction

```python
# In report_decision_outcome():

# ALWAYS fires (regardless of LEARNING_ENABLED)
reward_result = reward_computer.compute(action, outcome, category, context)
reward_ledger.record(decision_id, reward_result)

# Gated by LEARNING_ENABLED
if LEARNING_ENABLED and action_name in SCORER_ACTIONS:
    async with acquire_scorer() as scorer:
        guarded_update(scorer, f, cat_idx, act_idx, correct,
                       eta_weight=reward_result.reward_weight)  # NEW kwarg

# ALWAYS fires (regardless of LEARNING_ENABLED) — Issue 5 resolved
if not referred:  # Issue 2: don't update if referral vetoed
    exploration_policy.update(category_index, action_index, correct)
    posterior_store.save(exploration_policy)
```

### 3.6 RewardResult Dataclass

```python
@dataclass
class RewardResult:
    graded_reward: float       # Severity/impact-weighted reward
    binary_outcome: bool       # True = correct, False = incorrect
    reward_weight: float       # abs(graded) / reference, clipped [0.1, 3.0]
    breakdown: dict            # {severity, campaign_multiplier, ...} for transparency
    domain: str                # "soc" or "s2p"
```

### 3.7 Severity Weights Lookup (SOC) — Category Base Only

**MVP uses category base weight only.** technique_id lookup is a future enrichment
when SIEM integration provides ATT&CK classification.

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

Source: MITRE ATT&CK severity scores averaged across top techniques per category.

### 3.8 Financial Impact Lookup (S2P)

Source: Hackett Group AP Benchmarks + S2P PD v1.3 scenarios.

```json
{
  "price_variance":     {"min": 10, "median": 45,  "max": 500,  "reference": 45},
  "quantity_mismatch":  {"min": 5,  "median": 30,  "max": 200,  "reference": 30},
  "duplicate_risk":     {"min": 50, "median": 180, "max": 5000, "reference": 180},
  "contract_gap":       {"min": 20, "median": 95,  "max": 1000, "reference": 95},
  "format_compliance":  {"min": 2,  "median": 15,  "max": 100,  "reference": 15}
}
```

### 3.9 Validation: Graded q ≈ Binary q

Before deploying graded rewards, validate on existing 4,860 SOC decisions:

```python
# retroactive_grading.py
# 1. For each decision: assign severity from category base weight + noise
# 2. Compute graded_reward and binary_outcome
# 3. Compute rolling-400 graded_q and binary_q
# 4. Validate:

correlation = np.corrcoef(graded_q_series, binary_q_series)[0, 1]

if correlation >= 0.95:
    print("PASS — graded rewards calibrated correctly")
elif correlation >= 0.90:
    print("WARNING — investigate severity weight calibration")
    # Severity weights may be distorting the learning signal
    # enough that η modulation pushes centroids in qualitatively
    # different directions than binary learning
else:
    print("FAIL — do NOT deploy graded rewards")
    # Below 0.90 means severity weights fundamentally alter the
    # conservation signal. Recalibrate before deployment.
```

**Why 0.95:** Ensures severity weights don't introduce systematic bias.
Below 0.95, η modulation could push centroids in qualitatively different
directions than binary learning. 0.90 is the hard floor. 0.99 would reject
valid severity differentiation.

---

## §4 — CreditAssigner (RL-02)

### 4.1 Design

Credit assignment answers: "which earlier decisions enabled this outcome?"
Operates at the (category, action) cell level via TRIGGERED_EVOLUTION edges.

### 4.2 Chain Credit Mechanism

When reward r_current arrives for decision d_current in cell (c, a):

**Step 1 — Retrieve update history.**

```cypher
MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent)
WHERE e.category = {_S(category)}
  AND e.action_index = {_S(action_index)}
  AND e.decision_number >= {_S(n_current - LOOKBACK)}
  AND e.verified_correct = true
RETURN e.decision_number, d.decision_id, e.factor_snapshot
ORDER BY e.decision_number DESC
```

LOOKBACK = 100 decisions (covers ~3× HALF_LIFE_DECISIONS).
Only correct decisions create TRIGGERED_EVOLUTION edges (triage.py:1234).

**Step 2 — Compute recency weights.**

```python
HALF_LIFE = 30  # Consistent with PatternHistoryFactorComputer's existing decay
for k in historical_decisions:
    age = n_current - k.decision_number
    w_k = math.exp(-math.log(2) * age / HALF_LIFE)
    # age=0: w=1.0, age=15: w=0.71, age=30: w=0.50, age=45: w=0.35
```

**Step 3 — Normalize and distribute.**

```python
CHAIN_DISCOUNT = 0.5  # Total chain credit ≤ 50% of direct reward

total_weight = sum(w_k for k in historical)
if total_weight == 0:
    return []

chain_credits = []
for k in historical:
    gamma_k = w_k / total_weight
    chain_credit_k = r_current * gamma_k * CHAIN_DISCOUNT
    reward_ledger.add_chain_credit(k.decision_id, chain_credit_k)
    chain_credits.append(ChainCredit(
        source_decision_id=decision_id,
        target_decision_id=k.decision_id,
        chain_reward=chain_credit_k,
        gamma=gamma_k,
        age=age,
    ))
return chain_credits
```

**Step 4 — γ is derived, not fixed.** For decision 15 steps ago with 5 total
historical decisions: γ_effective ≈ 0.71 × 0.5 / 5 ≈ 0.071. The γ=0.7 in
demo scenarios was the raw recency weight before normalization and discount.

### 4.3 Factor Attribution (Finite-Differences)

```python
def compute_factor_attribution(scorer, f, category_index, action_index, reward):
    """12 scorer calls, <2ms. No external dependencies."""
    delta = 0.01
    attribution = {}
    for i in range(len(f)):
        f_plus = f.copy(); f_plus[i] = min(f_plus[i] + delta, 1.0)
        f_minus = f.copy(); f_minus[i] = max(f_minus[i] - delta, 0.0)
        p_plus = scorer.score(f_plus, category_index).probabilities[action_index]
        p_minus = scorer.score(f_minus, category_index).probabilities[action_index]
        gradient = (p_plus - p_minus) / (2 * delta)
        attribution[i] = gradient * reward
    return attribution
```

### 4.4 Tab 6 "Contributing Decisions" Panel

Chain credit becomes visible in the product through Tab 6 alert detail.
When showing an invoice/alert, the panel displays:

```
Contributing Decisions
─────────────────────────
INV-00045 (Rhine-Stahl, 18 decisions ago)
  Chain credit: 0.068  │  γ: 0.22  │  Original reward: +0.21
  "Your hold taught the system about contract_gap patterns"

INV-00039 (Rhine-Stahl, 27 decisions ago)
  Chain credit: 0.041  │  γ: 0.13  │  Original reward: +0.15
```

This requires a new API endpoint (`/api/soc/chain-credit/{decision_id}` or
`/api/s2p/preview/chain-credit/{invoice_id}`) that reads chain credit from
the reward ledger. Implementation: ~2h of UI work as part of or following RL-02.

### 4.5 CreditAssigner Interface

```python
class CreditAssigner:
    def __init__(self, graph_client, half_life: int = 30,
                 lookback: int = 100, chain_discount: float = 0.5):
        self.graph_client = graph_client
        self.half_life = half_life
        self.lookback = lookback
        self.chain_discount = chain_discount
    
    def assign_chain_credit(self, decision_id: str, category: str,
                            action_index: int, decision_number: int,
                            reward: float) -> list[ChainCredit]:
        """Distribute retroactive credit to prior decisions in same cell."""
    
    def compute_attribution(self, scorer, f, category_index: int,
                            action_index: int, reward: float) -> dict:
        """Per-factor attribution via finite-differences."""
```

### 4.6 ChainCredit Dataclass

```python
@dataclass
class ChainCredit:
    source_decision_id: str    # Current decision generating the reward
    target_decision_id: str    # Historical decision receiving credit
    chain_reward: float        # Discounted retroactive reward
    gamma: float               # Normalized recency weight
    age: int                   # Decision count gap
```

---

## §5 — ExplorationPolicy (RL-03)

### 5.1 Design

Thompson sampling within conservation bounds. Each (category, action) cell
maintains a Beta posterior. Posteriors persist across restarts via DuckDB.

### 5.2 Beta Posterior Per Cell

```python
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
        
        # Load from persistence or initialize with weak priors
        if self._store:
            saved = self._store.load(n_categories, n_actions)
            self.alphas = saved["alphas"]  # shape (n_categories, n_actions)
            self.betas = saved["betas"]
        else:
            self.alphas = np.ones((n_categories, n_actions))
            self.betas = np.ones((n_categories, n_actions))
    
    def update(self, category_index: int, action_index: int, correct: bool):
        """Update posterior with verified outcome.
        
        MUST NOT be called for referral-vetoed explorations — the
        exploration never reached the analyst and has no verified outcome.
        """
        if correct:
            self.alphas[category_index, action_index] += 1
        else:
            self.betas[category_index, action_index] += 1
        
        # Persist after every update
        if self._store:
            self._store.save(self.alphas, self.betas)
    
    def maybe_explore(self, probabilities: np.ndarray,
                      category_index: int,
                      conservation_margin: float) -> tuple[np.ndarray, bool]:
        """Possibly modify action probabilities via Thompson sampling."""
        exploration_rate = self._compute_rate(conservation_margin)
        if exploration_rate == 0.0 or np.random.random() > exploration_rate:
            return probabilities, False
        
        # Thompson sampling: sample from Beta posteriors
        sampled = np.array([
            scipy.stats.beta.rvs(
                self.alphas[category_index, a],
                self.betas[category_index, a]
            )
            for a in range(len(probabilities))
        ])
        sampled = sampled / sampled.sum()
        return sampled, True
```

### 5.3 Conservation-Bounded Exploration Rate

```python
def _compute_rate(self, conservation_margin: float) -> float:
    """
    margin = α·q·V - θ_min  (computed by LearningHealthMonitor)
    
    margin ≤ 0 (AMBER/RED): exploration = 0
    margin ≥ target_headroom: full exploration = ε_base
    Linear interpolation between.
    
    target_headroom = 10.0 means full exploration only when
    conservation signal is 10× the floor. Deliberately conservative.
    Calibrate with pilot data.
    """
    if conservation_margin <= 0:
        return 0.0
    return self.epsilon_base * min(conservation_margin / self.target_headroom, 1.0)
```

### 5.4 Integration — Exploration + Referral + Posterior Update

```python
# In analyze_alert(), AFTER ProfileScorer.score(), BEFORE referral VETO:

scoring_result = scorer.score(f, category_index)
probabilities = scoring_result.probabilities
margin = learning_health_monitor.last_margin

modified_probs, explored = exploration_policy.maybe_explore(
    probabilities, category_index, margin
)

if explored:
    selected_action = np.argmax(modified_probs)
    decision_method = "gae_scoring_explored"
else:
    selected_action = scoring_result.action_index
    decision_method = "gae_scoring"

# Referral VETO fires AFTER exploration
referred = referral_engine.check(...)

# ... later, in report_decision_outcome():

# Track whether this decision was explored AND referred
explored_but_referred = decision.explored and decision.referred

# Posterior update — Issue 2 resolved
if not explored_but_referred:
    exploration_policy.update(category_index, action_index, correct)
else:
    # Log but do NOT update posterior — no verified outcome for
    # the explored action because referral intercepted it
    log.info("Explored action %s vetoed by referral — posterior not updated",
             explored_action_name)
```

### 5.5 Exploration Logging on Decision Nodes

```python
decision_properties["explored"] = explored
decision_properties["exploration_rate"] = exploration_rate
decision_properties["conservation_margin"] = margin
decision_properties["explored_but_referred"] = explored_but_referred
if explored:
    decision_properties["original_action"] = scorer_action_name
    decision_properties["explored_action"] = explored_action_name
```

### 5.6 Posterior Reset on Disruption

```python
def on_conservation_transition(self, old_state, new_state):
    if new_state in ("AMBER", "RED"):
        # Reset to weak priors (2,2) — not uninformative (1,1)
        # (2,2) = "I've seen a couple outcomes, not confident"
        # Simpler than decay. Decay preserves stale posteriors
        # that caused the problem. Reset is cleaner.
        self.alphas = np.ones_like(self.alphas) * 2
        self.betas = np.ones_like(self.betas) * 2
        if self._store:
            self._store.save(self.alphas, self.betas)
```

### 5.7 Posterior Persistence (DuckDB)

```python
# backend/app/services/posterior_store.py

import duckdb
import numpy as np
from pathlib import Path

POSTERIOR_DB = Path("data/posteriors.duckdb")

class PosteriorStore:
    """Persist Beta posteriors across restarts. ~20 LOC."""
    
    def __init__(self, db_path: Path = POSTERIOR_DB):
        self.db_path = db_path
        self._ensure_table()
    
    def _ensure_table(self):
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posteriors (
                    category INTEGER,
                    action INTEGER,
                    alpha DOUBLE DEFAULT 1.0,
                    beta DOUBLE DEFAULT 1.0,
                    PRIMARY KEY (category, action)
                )
            """)
    
    def save(self, alphas: np.ndarray, betas: np.ndarray):
        """Upsert all posteriors. Called after every update."""
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM posteriors")
            for c in range(alphas.shape[0]):
                for a in range(alphas.shape[1]):
                    conn.execute(
                        "INSERT INTO posteriors VALUES (?, ?, ?, ?)",
                        [int(c), int(a), float(alphas[c, a]), float(betas[c, a])]
                    )
    
    def load(self, n_categories: int, n_actions: int) -> dict:
        """Load posteriors. Returns default (1,1) if not found."""
        alphas = np.ones((n_categories, n_actions))
        betas = np.ones((n_categories, n_actions))
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                rows = conn.execute(
                    "SELECT category, action, alpha, beta FROM posteriors"
                ).fetchall()
                for c, a, al, be in rows:
                    if c < n_categories and a < n_actions:
                        alphas[c, a] = al
                        betas[c, a] = be
        except Exception:
            pass  # First run — no table yet. Use defaults.
        return {"alphas": alphas, "betas": betas}
```

### 5.8 LEARNING_ENABLED Interaction for Exploration

**Exploration fires regardless of LEARNING_ENABLED.** This means:
- Demo mode shows exploration events in Decision nodes
- Exploration rate changes are visible as margin changes
- Posteriors update and converge (visible in Tab 7)
- Centroid mutation remains gated by LEARNING_ENABLED

```python
# In report_decision_outcome():
# This block fires ALWAYS — not gated by LEARNING_ENABLED
if not explored_but_referred:
    exploration_policy.update(category_index, action_index, correct)

# This block fires ONLY when LEARNING_ENABLED=True
if LEARNING_ENABLED and action_name in SCORER_ACTIONS:
    async with acquire_scorer() as scorer:
        guarded_update(scorer, f, cat_idx, act_idx, correct,
                       eta_weight=reward_result.reward_weight)
```

---

## §6 — Scenarios (Demo/Test Value)

### S1: Campaign Amplification (SOC — proportional learning)

```
Day 1:   ALERT-CA-047 (credential_access, no campaign)
         Correct: investigate. Severity: 0.70 (base). Campaign: none.
         Reward: +0.70. η_effective: 0.05 × 1.40 = 0.070

Day 45:  ALERT-CA-312 (credential_access, Campaign C-007)
         Override: investigate → escalate. Severity: 0.70. Campaign: 1.5×.
         Reward: -0.70 × 20.0 × 1.5 = -21.0
         η_effective: 0.01 × 3.0 (capped) = 0.030

Demo: "Same category. Different context. The system learned 3× faster
from the campaign miss because it mattered more."
```

### S3: Dollar-Weighted Invoice (S2P — financial impact)

```
INV-00048: $49,462 (contract_gap). Correct: flag_leakage. $12,400 recovered.
  impact_weight = min(12400/95, 1.0) = 1.0
  Reward: +1.0. η_effective: 0.05 × 2.0 = 0.10

INV-00103: $1,200 (contract_gap). Correct: auto_approve. ~$0 impact.
  impact_weight = min(0/95, 1.0) = 0.0
  Reward: +0.0. η_effective: 0.05 × 0.1 (floor) = 0.005

Demo: "The system learned 20× more from catching the $49K variance."
```

### S4: Chain Credit (S2P — attribution)

```
Week 1: INV-00045 → hold_for_review → correct. Reward: +0.21.
Week 3: INV-00048 → flag_leakage → correct ($12K). Reward: +1.0.
  Chain: INV-00045 is 18 decisions back. w=0.67. Normalized γ=0.22.
  Chain credit to INV-00045: 1.0 × 0.22 × 0.5 = 0.11.

Tab 6: "This catch was enabled by your hold on INV-00045.
Chain credit: 0.11 attributed back."
```

### S5: Tariff Shock — Exploration Auto-Pause

```
Day 0:  q=0.87, margin=12.7. Exploration: 5% (full).
Day 5:  q=0.65, margin=4.8.  Exploration: 2.4%.
Day 8:  margin→0. AMBER.     Exploration: 0%. Posteriors reset to (2,2).
Day 15: q recovers to 0.81.  Exploration resumes at 4.3%.

Demo: "The system was experimenting. When it became unsafe, it stopped.
No manual intervention. The math decided."
```

### S6: Policy Architecture Transfer (Cross-Domain — REFRAMED)

What transfers: policy DESIGN and AgentEvolver rule TEMPLATES.
What does NOT transfer: learned centroids, DK weights, factor computers.
Each copilot builds its own IKS. S6 does NOT claim knowledge transfer.

---

## §7 — Data Sources

### 7.1 Reward Calibration Data

| Source | Purpose | Status |
|---|---|---|
| MITRE ATT&CK | SOC category base severity weights | Parse into soc_severity_weights.json |
| Hackett Group AP | S2P financial impact per category | Extract into s2p_impact_ranges.json |
| Existing 4,860 SOC decisions | Retroactive grading validation | Script: retroactive_grading.py |
| Existing 50 S2P invoices | End-to-end validation | Tab 6 data |

### 7.2 Synthetic Bandit Validation (Replaces Yahoo R6)

```python
# 4 actions, 6 context features, known-optimal policy
# Run conservation-bounded Thompson sampling for 5000 steps
# Confirm: cumulative regret within O(sqrt(T)) bound
# Confirm: conservation constraint never violated
# Confirm: exploration rate correlates with margin
# 2 hours to construct + run
```

---

## §8 — Implementation Sequence

| Phase | Deliverable | Effort | Tests |
|---|---|---|---|
| RL-01a | RewardComputer + RewardResult + RewardLedger | 1 day | ~10 |
| RL-01b | Severity/impact lookups + wire into triage.py + bootstrap defaults | 1 day | ~10 |
| RL-02a | CreditAssigner chain credit + AGE query | 1 day | ~10 |
| RL-02b | Factor attribution + ChainCredit dataclass | 0.5 day | ~7 |
| RL-03a | ExplorationPolicy + conservation binding + referral-veto guard | 1 day | ~12 |
| RL-03b | PosteriorStore (DuckDB) + posterior reset + wire into triage.py | 0.75 day | ~8 |
| DATA | Severity JSON + impact JSON + retroactive grading + synthetic bandit | 0.25 day | ~4 |
| **Total** | | **5.5 days** | **~71 tests** |

---

## §9 — Standing Rules and Constraints

### 9.1 Architectural Invariants

1. **Conservation law unchanged.** q = binary rolling accuracy over 400 decisions.
2. **ProfileScorer.update() equation unchanged.** η modulation via multiplicative weight only.
3. **P16 separation.** RewardComputer reads scorer state. Never mutates directly.
4. **Chain credit is retrospective attribution.** Updates reward ledger, not centroids.
5. **Exploration bounded by conservation.** margin ≤ 0 → exploration = 0. No exceptions.
6. **Referral VETO overrides exploration.** Vetoed explorations don't update posteriors.
7. **LEARNING_ENABLED gates centroid mutation, not reward or exploration.** RewardComputer and ExplorationPolicy fire always.
8. **Posteriors persist.** DuckDB store. Lost posteriors = re-exploration churn.

### 9.2 AGE Query Constraints

All new AGE queries (CreditAssigner) MUST use `_S()` inline literals, NOT `$param`.
No `datetime()`, `HAVING`, `ON CREATE SET`, `ON MATCH SET`, `MERGE`, `SET n = {}`.

### 9.3 Test Constraints

- No test may call demo/reset-all, demo/reseed, or demo/seed
- Tests must mock graph state, not require live AGE instance
- Retroactive grading script is validation, not a test — runs manually

---

## §10 — Resolved Open Questions

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | target_headroom = 10.0 | **Keep for MVP.** | Deliberately conservative. Calibrate with pilot data. |
| Q2 | CHAIN_DISCOUNT = 0.5 | **Keep.** | 50% is meaningful for display without double-counting. |
| Q3 | Posterior reset vs decay | **Reset to (2,2).** | Simpler. Decay preserves stale posteriors that caused the problem. |
| Q4 | η clip [0.1, 3.0] | **Keep.** | Max η_effective=0.15 confirms, 0.03 overrides. Within validated envelope. |
| Q5 | Exploration in demo mode | **YES — fires always.** | Posteriors update. Centroids don't. Demo can show exploration. |

---

## §11 — Codex Review Prompt

```
Review rl_engine.py and posterior_store.py against this design.

VERIFY:
1. RewardComputer.compute() returns BOTH graded_reward AND binary_outcome
2. Conservation law q is NEVER computed from graded rewards
3. η_effective clip range is [0.1, 3.0]
4. CreditAssigner uses TRIGGERED_EVOLUTION edges (read-only)
5. CreditAssigner chain_discount ≤ 0.5
6. ExplorationPolicy._compute_rate() returns 0.0 when margin ≤ 0
7. ReferralEngine VETO fires AFTER exploration (not before)
8. Referral-vetoed explorations do NOT update posteriors
9. All AGE queries use _S() inline, no $param
10. Factor attribution uses finite-differences (12 calls), not SHAP
11. RewardComputer fires regardless of LEARNING_ENABLED
12. ExplorationPolicy.update() fires regardless of LEARNING_ENABLED
13. η modulation only fires when LEARNING_ENABLED=True
14. PosteriorStore saves after every update
15. PosteriorStore loads on initialization
16. reference_reward uses domain bootstrap default until 400 decisions
17. Severity lookup uses category base weight only (no technique_id)

FLAG IF:
- Any path where graded_reward feeds into conservation law q
- Any path where CreditAssigner mutates ProfileScorer directly
- Any path where exploration fires when margin ≤ 0
- Any path where referral-vetoed exploration updates posteriors
- Any AGE query using $param, datetime(), HAVING, MERGE
- Any new external dependency beyond numpy + scipy + duckdb
- Any posterior update without persistence
```

---

*RL Design v3.0 · May 6, 2026*
*Contextual bandit, not deep RL. Binary is a special case of graded.*
*Conservation unchanged. η modulated. Exploration bounded. Posteriors persisted.*
*Four components: RewardComputer, CreditAssigner, ExplorationPolicy, PosteriorStore.*
*5.5 days. ~71 tests. One new dependency (duckdb, ~15MB).*
*All 5 open questions resolved. All 7 review issues addressed.*
*"The system doesn't just learn from every decision. It learns MORE*
*from the decisions that matter most."*
