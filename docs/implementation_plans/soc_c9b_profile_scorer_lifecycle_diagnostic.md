# SOC C9B ProfileScorer Construction + Lifecycle Diagnostic

Date: 2026-06-08
Model: gpt-5.3
Task Type: Broken-code-friendly diagnostic audit only
Repo: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50

## Executive Summary
- ProfileScorer lifecycle verdict: LEARNING_DISABLED.
- build_profile_scorer found: YES, backend/app/domains/soc/config.py:705-727.
- learning_strategy present: YES.
- DecisionCountPolicy: PRESENT, n=200.
- CoordinateDescentEstimator: PRESENT.
- FixedAlpha: PRESENT, alpha=0.5.
- eta_override: PRESENT, 0.01.
- auto_pause_on_amber: PRESENT, True.
- LEARNING_ENABLED: False by default; SOC_LEARNING_ENABLED can override it.
- centroid shape: Expected and actual constructor tensor shape is (6, 4, 6), derived from 6 SOC categories, 4 scorer actions, and 6 factors.
- scorer storage: module-level LearningState singleton in app.services.gae_state, with profile_scorer attached during startup.
- startup vs per-request: Normal path constructs once during FastAPI lifespan startup_event(); no active handler constructs a scorer on every request. The analyze route has a fallback that calls init_learning_state() only if get_profile_scorer() returns None.
- Blocks 5-decision proof: YES under current default runtime config because live ProfileScorer.update() is disabled unless SOC_LEARNING_ENABLED enables it.
- Blocks 210 DK proof: YES under current default runtime config for the same reason.
- Non-blocking risks: route-level fallback reinitialization after missing scorer; in-memory ProfileScorer state resets on backend restart; L5 persistence still depends on Diagnostic C graph-store prerequisites.
- Future fixer needed: YES for runtime proof setup, not for constructor components.
- Recommended next step: start diagnostic runs with SOC_LEARNING_ENABLED=true and verify the app process is using that setting before Diagnostic E/F.

## Path Resolution
- Repo path: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50.
- config.py found: YES, backend/app/domains/soc/config.py.
- main.py found: YES, backend/app/main.py.
- gae_state.py found: YES, backend/app/services/gae_state.py.
- build_profile_scorer call sites: backend/app/domains/soc/config.py:705 and backend/app/services/gae_state.py:191.
- Route-level scorer access: backend/app/routers/triage.py, framework_router.py, soc.py, judgment.py, evaluation.py, and services use get_profile_scorer(); the active analyze route uses get_profile_scorer and has a fallback init path.

## Q1 - Full build_profile_scorer Source

Source: backend/app/domains/soc/config.py:705-727.

```python
    def build_profile_scorer(self) -> ProfileScorer:
        """
        Build a ProfileScorer from this domain config.
        Uses L2 kernel (EXP-E1 validated), τ=0.1 (V3B validated, default).

        Phase 0b: scorer uses SCORER_ACTIONS (A=4) and SCORER_PROFILE_CENTROIDS
        shaped as (N_CATEGORIES, N_ACTIONS, N_FACTORS). refer_to_analyst is handled by the confidence gate in
        triage.py, not by centroid proximity.  SOC_ACTIONS (A=5) is kept
        for the API response and NL templates.
        """
        return ProfileScorer(
            mu=SCORER_PROFILE_CENTROIDS.copy(),
            actions=list(SCORER_ACTIONS),
            kernel=KernelType.L2,
            categories=list(SOC_CATEGORIES),
            eta_override=0.01,       # P0 fix: attenuate override learning 5x
            auto_pause_on_amber=True,  # DRIFT-01: enable conservation RED/AMBER freeze
            learning_strategy=LearningStrategy(
                phase_policy=DecisionCountPolicy(n=200),
                dk_estimator=CoordinateDescentEstimator(),
                shrinkage_schedule=FixedAlpha(0.5),
            ),
        )
```

## Q2 - learning_strategy
- Present: YES.
- Evidence: backend/app/domains/soc/config.py:722 passes learning_strategy=LearningStrategy(...).
- Import evidence: backend/app/domains/soc/config.py:18 imports LearningStrategy from gae.profile_scorer.
- Missing/wrong component: None.

## Q3 - DecisionCountPolicy
- Present: YES.
- Expected: DecisionCountPolicy(n=200).
- Actual: backend/app/domains/soc/config.py:723 passes phase_policy=DecisionCountPolicy(n=200).
- Import evidence: backend/app/domains/soc/config.py:20 imports DecisionCountPolicy.
- Missing/wrong component: None.

## Q4 - CoordinateDescentEstimator
- Present: YES.
- Evidence: backend/app/domains/soc/config.py:724 passes dk_estimator=CoordinateDescentEstimator().
- Import evidence: backend/app/domains/soc/config.py:17 imports CoordinateDescentEstimator.
- Missing/wrong component: None.

## Q5 - FixedAlpha
- Present: YES.
- Expected: FixedAlpha(0.5).
- Actual: backend/app/domains/soc/config.py:725 passes shrinkage_schedule=FixedAlpha(0.5).
- Import evidence: backend/app/domains/soc/config.py:19 imports FixedAlpha.
- Missing/wrong component: None.

## Q6 - eta_override
- Present: YES.
- Expected: eta_override=0.01.
- Actual: backend/app/domains/soc/config.py:720 passes eta_override=0.01.
- Additional startup assertion: backend/app/services/gae_state.py:191-196 builds the scorer and asserts eta_override is not None with SOC-specific error text.
- Missing/wrong component: None.

## Q7 - auto_pause_on_amber
- Present: YES.
- Expected: auto_pause_on_amber=True.
- Actual: backend/app/domains/soc/config.py:721 passes auto_pause_on_amber=True.
- Missing/wrong component: None.

## Q8 - LEARNING_ENABLED
- Definition: backend/app/domains/soc/config.py:63-66 documents the live ProfileScorer.update gate and sets LEARNING_ENABLED = False.
- Current default value: False.
- Env override: backend/app/domains/soc/config.py:69-74 defines is_learning_enabled(); if SOC_LEARNING_ENABLED is absent, it returns bool(LEARNING_ENABLED), otherwise it treats 1/true/yes/on as enabled.
- Route gate: backend/app/routers/triage.py:49-55 defines _soc_learning_enabled(); backend/app/routers/triage.py:1277-1281 gates ProfileScorer.update on _soc_learning_enabled().
- Classification: LEARNING_DISABLED under default runtime config.

## Q9 - Centroid Tensor Shape
- Expected: (6, 4, 6).
- Actual: (N_CATEGORIES, N_ACTIONS, N_FACTORS) where N_CATEGORIES=6, N_ACTIONS=4, N_FACTORS=6.
- Category evidence: backend/app/domains/soc/config.py:92-99 defines 6 SOC_CATEGORIES.
- Action evidence: backend/app/domains/soc/config.py:55 defines 4 SCORER_ACTIONS; backend/app/domains/soc/config.py:61 sets SOC_N_ACT = len(SCORER_ACTIONS).
- Factor evidence: backend/app/domains/soc/config.py:120-127 defines 6 SOC_FACTORS.
- Dimension constants: backend/app/domains/soc/config.py:129-131 sets N_FACTORS, N_CATEGORIES, and N_ACTIONS from those lists.
- Tensor reshape: backend/app/domains/soc/config.py:153-230 defines SOC_PROFILE_CENTROIDS and reshapes it to (N_CATEGORIES, N_ACTIONS, N_FACTORS); backend/app/domains/soc/config.py:231 documents the shape.
- Constructor tensor: backend/app/domains/soc/config.py:716 passes mu=SCORER_PROFILE_CENTROIDS.copy(); backend/app/domains/soc/config.py:234-236 aliases SCORER_PROFILE_CENTROIDS = SOC_PROFILE_CENTROIDS.
- Classification: no CENTROID_SHAPE_MISMATCH.

## Q10 - Scorer Storage
- Storage classification: module-level LearningState singleton, with ProfileScorer attached to _learning_state.profile_scorer.
- Evidence: backend/app/services/gae_state.py:1-11 describes the module-level singleton design across the backend process.
- Construction: backend/app/services/gae_state.py:176-191 defines init_learning_state() and calls SOCDomainConfig().build_profile_scorer().
- Attachment: backend/app/services/gae_state.py:260 attaches the ProfileScorer to _learning_state.
- Access: backend/app/services/gae_state.py:402-407 defines get_profile_scorer() returning get_learning_state().profile_scorer.
- Mutation lock: backend/app/services/gae_state.py:47-58 defines acquire_scorer(), locking and yielding _learning_state.profile_scorer.
- No app.state.profile_scorer storage was found in the searched files.

## Q11 - Scorer Lifecycle
- Normal construction lifecycle: once at FastAPI startup.
- FastAPI lifespan: backend/app/main.py:22-33 defines lifespan(app) and passes it to FastAPI.
- Startup call: backend/app/main.py:143 defines startup_event(); backend/app/main.py:268-270 imports init_learning_state(), calls it, and logs LearningState readiness.
- init_learning_state documentation: backend/app/services/gae_state.py:176-185 says it is called once in main.py startup_event().
- Persistent across requests: YES within one backend process, because route/service callers use get_profile_scorer() or acquire_scorer() against the module-level LearningState.
- Not per request: The active source does not show normal request handlers creating a fresh SOCDomainConfig().build_profile_scorer() per request.
- Non-blocking lifecycle risk: backend/app/routers/triage.py:157-163 has a fallback that calls init_learning_state() if get_profile_scorer() returns None during analyze. This is not per-request when the scorer is healthy, but if startup/reset leaves the scorer missing, the route can reinitialize state in request context.
- Restart persistence caveat: backend/app/routers/triage.py:1968 and 1974 annotate that in-memory ProfileScorer counts/centroids reset on restart for profile display. Checkpoint/bootstrap code may restore baseline state, but this diagnostic did not run startup to prove continuity of live learned centroid state across process restarts.

## Q12 - Missing Components Summary
- learning_strategy: present.
- DecisionCountPolicy(n=200): present.
- CoordinateDescentEstimator(): present.
- FixedAlpha(0.5): present.
- eta_override=0.01: present.
- auto_pause_on_amber=True: present.
- centroid shape (6,4,6): present.
- persistent in-process scorer: present.
- per-request scorer construction: not present in normal path.
- missing/wrong constructor components: None.
- blocking lifecycle/config issue: LEARNING_ENABLED defaults False, so live ProfileScorer.update is disabled unless SOC_LEARNING_ENABLED enables it for the running app.

## Lifecycle Matrix
| Component | Expected | Actual | Present? | Evidence | Risk |
| --- | --- | --- | --- | --- | --- |
| learning_strategy | yes | LearningStrategy(...) | YES | config.py:722-726 | None |
| DecisionCountPolicy | n=200 | DecisionCountPolicy(n=200) | YES | config.py:723 | None |
| CoordinateDescentEstimator | present | CoordinateDescentEstimator() | YES | config.py:724 | None |
| FixedAlpha | 0.5 | FixedAlpha(0.5) | YES | config.py:725 | None |
| eta_override | 0.01 | eta_override=0.01 | YES | config.py:720 | None |
| auto_pause_on_amber | True | auto_pause_on_amber=True | YES | config.py:721 | None |
| LEARNING_ENABLED | True for live proof, unless explicitly disabled | False by default; env override available | NO for default runtime proof | config.py:63-74; triage.py:1277-1281 | Blocks 5-decision and 210-DK proof unless enabled |
| centroid shape | (6,4,6) | (N_CATEGORIES,N_ACTIONS,N_FACTORS) = (6,4,6) | YES | config.py:92-131; config.py:153-231 | None |
| scorer storage | persistent across requests | _learning_state.profile_scorer singleton | YES | gae_state.py:1-11; gae_state.py:260; gae_state.py:402-407 | In-process only |
| construction lifecycle | once at startup/import cache | startup_event() -> init_learning_state() | YES | main.py:22-33; main.py:268-270; gae_state.py:176-185 | Fallback reinit possible if missing |
| per-request scorer | should not happen | normal path does not; analyze fallback only when scorer is None | YES, normal path safe | triage.py:157-163 | Non-blocking risk |

## Proof Readiness Impact
- BLOCKS_5_DECISION: YES under current default runtime config. The scorer construction is correct, but the route does not call ProfileScorer.update unless _soc_learning_enabled() returns true.
- BLOCKS_210_DK_PROOF: YES under current default runtime config. DecisionCountPolicy(n=200) and DK components are configured, but they cannot be exercised while live learning is disabled.
- NON_BLOCKING_RISKS:
  - The analyze route can call init_learning_state() in request context if the scorer is missing, which could mask startup lifecycle faults.
  - ProfileScorer state is in-process and profile endpoints explicitly describe in-memory counts/centroids as resetting on restart.
  - L5 persistence and graph proof still depend on Diagnostic C prerequisites such as GRAPH_DSN, AGE_GRAPH_NAME, and learning store availability.

## Lifecycle Verdict
- Verdict labels: LEARNING_DISABLED.
- Rationale: SOC ProfileScorer is constructed with the required LearningStrategy, phase policy, DK estimator, shrinkage, eta override, auto-pause setting, and expected centroid shape. The scorer is attached to a module-level LearningState at startup and reused by routes. The blocking issue for live learning proofs is that LEARNING_ENABLED defaults False and ProfileScorer.update is gated by that runtime setting.
- Future fixer scope: for diagnostic proof runs, start the backend with SOC_LEARNING_ENABLED=true and assert that the running process sees the enabled value before running Diagnostic E/F. Separately decide whether the analyze-route fallback init should remain or be converted into a clearer startup failure.

## Diagnostic Limitations
- No code was modified.
- No tests were run.
- No app server was run.
- No seed scripts were run.
- No smoke scripts were run.
- Analysis is source-level only.
