# SOC C9B Diagnostic F Runner Result

- verdict: `SEED_RUNTIME_FAILURE`
- exit_code: `1`
- graph: `soc_graph_diag_f5`
- prefix: `DIAG-F5-CRED`
- dry_run: `False`
- seed_attempted_count: `295`
- seed_completed_count: `291`
- seed_strategy: `direct-age`
- seed_sleep_seconds: `0.15`
- batch_sleep_seconds: `2.0`
- preflight_seed_count: `5`
- current_batch_index: `30`
- current_batch_start: `286`
- current_batch_end: `295`
- seed_retries: `3`
- last_seed_error: `connection timeout expired`
- analyze_attempts: `0`
- outcome_attempts: `0`
- valid_outcomes: `0`
- skipped_refer_to_analyst: `0`
- other_categories: `0`
- last_successful_phase: `age_graph_ensured`
- criteria_failures: `['seed batch failed: batch=30 start=286 end=295 retries=3 error=connection timeout expired']`
- exception: `seed batch failed: batch=30 start=286 end=295 retries=3 error=connection timeout expired`
- backend_contract_statement: `Backend import path cannot be directly introspected without a debug endpoint; proof assumes backend was launched by run_soc_diag_backend.ps1 or demo.py --diag-mode with matching graph/env.`
- report_json: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\docs\implementation_plans\soc_c9b_diag_f_runner_DIAG-F5-CRED.json`
- report_md: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\docs\implementation_plans\soc_c9b_diag_f_runner_DIAG-F5-CRED.md`
- progress_json: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_diag_f_progress.json`

## Follow-up Harness Fix — streaming seed/analyze/outcome loop

- `soc_graph_diag_f5` is contaminated by a partial upfront seed failure and must not be reused for proof.
- The runner default has been redesigned to stream each attempt: seed one alert, analyze it, immediately post outcome for valid target-category non-referral actions, and stop when `target_outcomes` is reached.
- `max_attempts` is now the proof upper bound; upfront bulk seeding is only an explicit `--bulk-seed-first` legacy stress mode.
- Next clean proof graph: `soc_graph_diag_f6`.
- Next clean prefix: `DIAG-F6-CRED`.
