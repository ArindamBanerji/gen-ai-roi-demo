# SOC External Proof Harness Design

Date: 2026-06-08
Model: gpt-5.3
Task Type: Design + focused harness refactor

## Purpose

The SOC proof runner is an external, manually executed runtime harness. It is not a backend endpoint and is not the canonical product implementation. Its job is to run deterministic live proof scenarios against a throwaway AGE graph while preserving proof honesty: analyze-only decisions never count as outcomes, and pass verdicts require the scenario's explicit graph readback criteria.

## Runtime Contract Model

The runner requires a backend contract before proof:

- backend graph name
- backend port
- redacted AGE DSN
- `SOC_LEARNING_ENABLED=true`
- source `ci-platform` import path
- launch timestamp

The contract is written by `scripts/diagnostics/run_soc_diag_backend.ps1`. Without the contract, the runner must fail with `BACKEND_RUNTIME_CONTRACT_UNVERIFIED` unless `--assume-backend-contract` is explicitly supplied. `--assume-backend-contract` is a user assertion, not proof of backend import path.

The backend contract validates the already-running backend. It is not a connection string for the runner. The runner owns its own direct AGE/PostgreSQL connection through `--graph-dsn`, defaulting to:

```text
host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres
```

Before constructing any `AGEClient`, the runner sets `GRAPH_BACKEND=age`, `GRAPH_DSN=<--graph-dsn>`, and `AGE_GRAPH_NAME=<--graph-name>` in its own process. Startup then performs a runner-side AGE readback with bounded retry. On Windows, Rule #40 applies: runner AGE/PostgreSQL DSNs must use `localhost`, not `127.0.0.1`; backend HTTP URLs are separate from AGE/PostgreSQL DSNs.

## Scenario Model

Each scenario is described by `ScenarioConfig`:

- `name`
- `target_category`
- `target_outcomes`
- `max_attempts`
- `allowed_actions`
- `skip_actions`
- `milestones`
- `input_provider`
- `pass_criteria`

Supported scenarios:

- `diagnostic-e-5-decision`
- `diagnostic-f-dk`
- `c9b-final-proof`
- `sanity-one-alert`
- `seed-only-smoke`
- `l5-centroid-proof`
- `dk-threshold-proof`

## Input Provider Model

The current provider is `fixed_c9b_stream`, which creates the known-good SOC C9B credential-access shape:

- `alert_type="anomalous_login"`
- `category="credential_access"`
- `severity="critical"`
- `risk_score=0.92`
- `Asset.criticality="critical"`
- `mfa_completed=false`
- `device_fingerprint_match=false`
- `Alert`, `User`, `Asset`, `INVOLVES`, and `DETECTED_ON`

`fixed_c9b_seed_only` seeds the same shape but does not analyze or post outcomes.

## Analyze Response Extraction Model

The extractor must tolerate known response shapes:

- category: top-level `category`, `alert_category`, `alert.category`, or `gae_scoring.category`
- action: top-level `action`, `recommended_action`, `recommendation.action`, or `recommendation.recommended_action`
- confidence: top-level `confidence`, `recommendation.confidence`, or `gae_scoring.confidence`
- decision ID: top-level `decision_id`, `recommendation.decision_id`, or `gae_scoring.decision_id`
- raw response is retained in loop records

## Outcome Posting Model

For a target-category non-referral scorer action, the runner posts:

```json
{
  "alert_id": "<alert id>",
  "decision_id": "<analyze decision id>",
  "outcome": "correct",
  "analyst_action": "<returned scorer action>"
}
```

The runner increments `valid_outcomes` only after the outcome POST succeeds.

Analyze and outcome HTTP timeouts are ambiguous because the backend may finish after the client times out. The runner must not blindly retry:

- analyze timeout recovery first queries AGE for the latest `Decision-[:DECIDED_ON]->Alert` for that alert; if present, the runner resumes from that real Decision and does not call analyze again for that alert
- outcome timeout recovery first queries the `Decision` by `decision_id`; if `correct=true` or `outcome="correct"` is present, the runner counts the outcome exactly once
- retries are bounded and only for transient timeout/connection errors
- semantic HTTP/schema failures remain hard failures

## Streaming Execution Loop

Default proof execution is streaming:

1. Seed the current attempt alert.
2. Analyze the same alert.
3. Skip and count non-target categories.
4. Skip and count `skip_actions` such as `refer_to_analyst`.
5. Skip and count unexpected actions.
6. Post outcome for valid target-category non-referral scorer actions.
7. Count a valid outcome only after outcome POST success.
8. Stop immediately when `valid_outcomes >= target_outcomes`.
9. Fail with `TARGET_CATEGORY_NOT_REACHED` when `max_attempts` is exhausted.

`--bulk-seed-first` is legacy stress mode only. It is not the default proof mode.

## Pass-Criteria Plugins

Scenario criteria are named checks:

- `target_outcomes`: `valid_outcomes >= target_outcomes`
- `seeded_alerts`: at least one alert was seeded
- `l5_centroid`: `L5Centroid > 0`
- `shaped_by`: `SHAPED_BY > 0`
- `l5_dk_weight`: `L5DKWeight > 0`
- `welford`: Welford JSON fields are present
- `dk_n_decisions_used`: maximum `L5DKWeight.n_decisions_used >= target_outcomes`

Diagnostic F and DK-threshold proof require `target_outcomes`, `l5_dk_weight`, `welford`, and `dk_n_decisions_used`.

Diagnostic E and L5 centroid proof require `target_outcomes`, `l5_centroid`, and `shaped_by`.

## Progress JSON Schema

`scratch/temp/soc_diag_f_progress.json` includes:

- `status`
- `scenario`
- `graph_name`
- `prefix`
- `phase`
- `max_attempts`
- `current_attempt_index`
- `seeded_alerts`
- `seed_failures`
- `analyze_attempts`
- `outcome_attempts`
- `valid_target_outcomes`
- `target_outcomes`
- `latest_alert_id`
- `latest_action`
- `latest_confidence`
- `skipped_refer_to_analyst`
- `other_categories`
- `other_action_skips`
- `failures`
- `seed_retries`
- `last_seed_error`
- `http_timeout_seconds`
- `http_max_retries`
- `http_retry_backoff_seconds`
- `analyze_retries`
- `outcome_retries`
- `analyze_timeout_recovered_by_readback`
- `outcome_timeout_recovered_by_readback`
- `latest_http_error`
- `latest_timeout_recovery_action`
- `latest_seed_seconds`
- `latest_analyze_seconds`
- `latest_outcome_seconds`
- `latest_readback_seconds`
- `avg_analyze_seconds`
- `avg_outcome_seconds`
- `max_analyze_seconds`
- `max_outcome_seconds`
- `runner_graph_dsn_redacted`
- `runner_age_readback_status`
- `runner_age_readback_attempts`
- `runner_age_error`
- `rule40_validated`
- `elapsed_seconds`
- `milestone`
- `report_json_path`
- `report_md_path`
- `verdict`
- `updated_at`

## Report JSON/Markdown Schema

Reports include:

- scenario and scenario config
- runtime contract and health evidence
- runner AGE DSN, redacted
- runner AGE readback status, attempts, and error
- Rule #40 validation status
- graph, prefix, mode, and proof parameters
- seed shape and input provider
- attempts, seeded alerts, seed failures
- analyze and outcome counts
- valid outcomes and skips
- milestone snapshots and AGE readbacks
- final readback
- verdict, exit code, proof boolean, and criteria failures
- graph hygiene notes

## Failure Verdict Taxonomy

Current failure verdicts:

- `ENV_VALIDATION_FAILED`
- `BACKEND_UNREACHABLE`
- `BACKEND_RUNTIME_CONTRACT_UNVERIFIED`
- `AGE_GRAPH_READBACK_FAILED`
- `SEED_RUNTIME_FAILURE`
- `SEED_DATA_ISSUE`
- `ANALYZE_HTTP_FAILURE`
- `OUTCOME_HTTP_FAILURE`
- `TARGET_CATEGORY_NOT_REACHED`
- `L5CENTROID_MISSING`
- `SHAPED_BY_MISSING`
- `L5DKWEIGHT_MISSING`
- `WELFORD_MISSING`
- `DK_DECISION_COUNT_MISSING`
- `INTERRUPTED`
- `UNEXPECTED_RUNTIME_ERROR`

## Graph Hygiene Rules

- Never use production/default SOC graphs for proof.
- Use a fresh graph for every failed proof attempt.
- `soc_graph_diag_f3` is contaminated by an analyze-only failed run.
- `soc_graph_diag_f4` is contaminated by a partial seed failure.
- `soc_graph_diag_f5` is contaminated by a partial seed failure.
- `soc_graph_diag_f6` is contaminated by a partial 160-outcome timeout run.
- Next clean Diagnostic F graph: `soc_graph_diag_f7`.

## Test And Sanity Modes

- `--dry-run` validates runner setup and writes a report, but cannot pass proof.
- `sanity-one-alert` proves one streaming seed/analyze/outcome pair.
- `seed-only-smoke` seeds one canonical alert and verifies the seed path.
- `--sanity-count N` counts successful sanity outcomes toward `valid_outcomes` because they mutate the same learning state. Reports carry the same aggregate count explicitly.
