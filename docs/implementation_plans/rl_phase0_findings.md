# RL Phase 0 Findings — Eta Contract and Synthetic Bandit Validation

## 1. Design Authority

`docs/implementation_plans/rl_design_v4.md` was present and used as the design authority. It supersedes prior RL designs (`docs/implementation_plans/rl_design_v4.md:1-6`).

## 2. ProfileScorer.update() Contract

`ProfileScorer.update()` has this exact signature:

```python
def update(
    self,
    f: np.ndarray,
    category_index: int,
    action_index: int,
    correct: bool,
    gt_action_index: Optional[int] = None,
    confidence: Optional[float] = None,
) -> CentroidUpdate:
```

Evidence: `../graph-attention-engine-v50/gae/profile_scorer.py:780-788`.

There is no `eta_weight` parameter and no `**kwargs` in `ProfileScorer.update()` (`../graph-attention-engine-v50/gae/profile_scorer.py:780-788`). Passing `eta_weight` through `guarded_update()` would therefore be invalid because `guarded_update()` forwards kwargs directly to `scorer.update()` (`backend/app/services/gae_state.py:735-736`, `backend/app/services/gae_state.py:754`, `backend/app/services/gae_state.py:788-789`).

## 3. CalibrationProfile Fields and Defaults

`CalibrationProfile` is a mutable dataclass with public fields:

- `learning_rate: float = 0.02`
- `penalty_ratio: float = 20.0`
- `temperature: float = 0.25`
- `epsilon_default: float = 0.001`
- `discount_strength: float = 0.0`
- `decay_class_rates`
- `factor_decay_classes`
- `extensions`

Evidence: `../graph-attention-engine-v50/gae/calibration.py:20-63`.

The v4 pseudocode references `CalibrationProfile.eta_confirm` and `eta_override` (`docs/implementation_plans/rl_design_v4.md:231-241`), but those fields do not exist on `CalibrationProfile` (`../graph-attention-engine-v50/gae/calibration.py:20-63`).

## 4. Calibration Access Path from ProfileScorer

`ProfileScorer.__init__()` accepts an optional `profile`, but copies values into scorer attributes during construction:

- `self.tau = profile.temperature`
- `self.eta = profile.extensions.get("eta", 0.05)`
- `self.eta_neg = profile.extensions.get("eta_neg", 0.05)`
- `self.decay = profile.extensions.get("count_decay", 0.001)`

Evidence: `../graph-attention-engine-v50/gae/profile_scorer.py:160-164`, `../graph-attention-engine-v50/gae/profile_scorer.py:243-248`.

If no profile is provided, defaults are `tau=0.1`, `eta=0.05`, `eta_neg=0.05`, and `decay=0.001` (`../graph-attention-engine-v50/gae/profile_scorer.py:249-253`). `eta_override` is a constructor argument and is stored as `self.eta_override` (`../graph-attention-engine-v50/gae/profile_scorer.py:164`, `../graph-attention-engine-v50/gae/profile_scorer.py:273-274`).

Therefore the Phase 0 compatible temporary multiplier path is:

- multiply `scorer.eta` for confirmation updates;
- multiply `scorer.eta_neg` for incorrect push when `eta_override is None`;
- multiply `scorer.eta_override` for SOC override updates when non-null;
- restore all values in `finally`.

## 5. guarded_update() and acquire_scorer()

`guarded_update()` signature:

```python
def guarded_update(scorer, f, category_index: int, action_index: int,
                   correct: bool, category_name: str = "", **kwargs):
```

Evidence: `backend/app/services/gae_state.py:735-736`.

It performs volume-spike, category-freeze, conservation pause, and spike-cap guards before calling `scorer.update()` (`backend/app/services/gae_state.py:760-789`). It forwards kwargs directly into `scorer.update()` (`backend/app/services/gae_state.py:788-789`).

`acquire_scorer()` uses a module-level `asyncio.Lock()` and yields the live `ProfileScorer` only while holding that lock (`backend/app/services/gae_state.py:35`, `backend/app/services/gae_state.py:42-53`).

## 6. Existing Triage Temporary Eta Pattern

The current outcome path already uses a temporary eta pattern for `eta_override`:

- it enters `async with acquire_scorer()` (`backend/app/routers/triage.py:1097`, `backend/app/routers/triage.py:1104`);
- captures `_orig_eta_out = _ps_out.eta_override` (`backend/app/routers/triage.py:1105`);
- conditionally sets `_ps_out.eta_override = _analyst_eta` (`backend/app/routers/triage.py:1107-1108`);
- calls `guarded_update()` (`backend/app/routers/triage.py:1114-1122`);
- restores `_ps_out.eta_override = _orig_eta_out` in `finally` (`backend/app/routers/triage.py:1123-1124`).

This existing pattern does not modulate confirmation updates because the confirmation path uses `self.eta` (`../graph-attention-engine-v50/gae/profile_scorer.py:943-950`). The override path uses `self.eta_override` when `correct=False` and `eta_override is not None` (`../graph-attention-engine-v50/gae/profile_scorer.py:936-954`).

## 7. Conservation Margin Fields and Formula

`LearningHealthMonitor.evaluate()` returns:

- `signal`
- `theta_min`
- `conservation.passed`
- `conservation.status`
- `conservation.headroom`

Evidence: `backend/app/services/learning_health.py:283-291`.

`LearningHealthMonitor` computes components, then `theta_min`, then `cc = check_conservation(alpha, q, V, theta_min)`, then `signal = alpha*q*V` (`backend/app/services/learning_health.py:196-203`). `check_conservation()` computes `headroom = signal / theta_min` (`../graph-attention-engine-v50/gae/calibration.py:257-258`).

Phase 0 treats `conservation.headroom` as a ratio, not an additive margin. The synthetic script uses a generic positive/zero margin input for the proposed rate function, and the findings record that future production code must name ratio semantics explicitly if using `headroom`.

## 8. SOC Tensor / Action / Category Shape

SOC scorer actions are four actions: `["escalate", "investigate", "suppress", "monitor"]` (`backend/app/domains/soc/config.py:47-50`). `refer_to_analyst` is a routing action, not a scorer action (`backend/app/domains/soc/config.py:41-55`).

SOC categories are six ordered names (`backend/app/domains/soc/config.py:63-70`). `SOC_PROFILE_CENTROIDS` is shaped as `(N_CATEGORIES, N_ACTIONS, N_FACTORS)` and axis 1 matches `SCORER_ACTIONS` (`backend/app/domains/soc/config.py:85-100`, `backend/app/domains/soc/config.py:199-205`).

`SOCDomainConfig.build_profile_scorer()` builds a `ProfileScorer` with `SCORER_PROFILE_CENTROIDS`, `SCORER_ACTIONS`, SOC categories, `eta_override=0.01`, and `auto_pause_on_amber=True` (`backend/app/domains/soc/config.py:672-689`).

## 9. Synthetic Bandit Design Correction

The invalid validation target is a continuously feature-dependent optimal policy such as `argmax(W @ features)` while using only one Beta posterior per action. The MVP posterior described by v4 is per `(category, action)` cell (`docs/implementation_plans/rl_design_v4.md:38`, `docs/implementation_plans/rl_design_v4.md:384-406`). A single posterior per action cannot learn a continuously varying optimum unless the context is discretized into buckets that become posterior rows.

The Phase 0 script therefore uses a stationary known-best-action environment per category:

- `N_CATEGORIES = 3`
- `N_ACTIONS = 4`
- fixed success probability matrix `p_success[category][action]`
- Beta posterior arrays `alpha[category][action]`, `beta[category][action]`
- stdlib `random.betavariate`
- conservation-bounded exploration rate with `margin <= 0 -> 0.0`

This matches the MVP posterior shape and avoids validating against an impossible continuous-feature target.

## 10. Contradictions

Resolved contradictions:

1. v4 pseudocode references `scorer.calibration.eta_confirm`; live code has no such path. Phase 0 tests use `scorer.eta`, `scorer.eta_neg`, and `scorer.eta_override` instead.
2. v4 describes `headroom` as a margin in places, while live conservation computes ratio headroom. Phase 0 records this distinction and tests only the generic rate function.
3. continuous feature-dependent synthetic optimum is incompatible with per-action Beta posteriors. Phase 0 uses a stationary per-category bandit.

Unresolved contradictions: **None for Phase 0 validation.**

READY_FOR_PHASE1: YES, subject to GPT-5.5 review of these Phase 0 artifacts.
