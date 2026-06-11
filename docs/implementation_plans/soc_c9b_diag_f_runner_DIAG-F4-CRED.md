# SOC C9B Diagnostic F Runner Result

- verdict: `SEED_RUNTIME_FAILURE`
- exit_code: `1`
- graph: `soc_graph_diag_f4`
- prefix: `DIAG-F4-CRED`
- dry_run: `False`
- seed_attempted_count: `112`
- seed_completed_count: `111`
- analyze_attempts: `0`
- outcome_attempts: `0`
- valid_outcomes: `0`
- skipped_refer_to_analyst: `0`
- other_categories: `0`
- last_successful_phase: `age_graph_ensured`
- criteria_failures: `['seed batch failed: connection timeout expired']`
- exception: `seed batch failed: connection timeout expired`
- backend_contract_statement: `Backend import path cannot be directly introspected without a debug endpoint; proof assumes backend was launched by run_soc_diag_backend.ps1 or demo.py --diag-mode with matching graph/env.`
- report_json: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\docs\implementation_plans\soc_c9b_diag_f_runner_DIAG-F4-CRED.json`
- report_md: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\docs\implementation_plans\soc_c9b_diag_f_runner_DIAG-F4-CRED.md`
- progress_json: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_diag_f_progress.json`

## Follow-up Seed Timeout Assessment

- graph_hygiene: `soc_graph_diag_f4` is contaminated by a partial seed failure and must not be reused for proof.
- next_graph: `soc_graph_diag_f5`
- next_prefix: `DIAG-F5-CRED`
- runner_fix: subsequent runner versions use smaller default batches, seed/batch pacing, preflight seeding, bounded transient retries, and batch-specific progress fields.
- proof_status: no Diagnostic F product conclusion can be drawn because the proof loop never started.
