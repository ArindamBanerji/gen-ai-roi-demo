# v5.5 Backend API Smoke Test
# Run with backend already started on localhost:8000
# Usage: .\v55_smoke_test.ps1

$BASE = "http://localhost:8000"
$pass_count = 0
$fail_count = 0
$failures = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method = "GET",
        [string]$Url,
        [string]$Body = $null,
        [scriptblock]$Validate
    )
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            ErrorAction = "Stop"
        }
        if ($Body) {
            $params.ContentType = "application/json"
            $params.Body = $Body
        }
        $response = Invoke-RestMethod @params
        
        $result = & $Validate $response
        if ($result -eq $true) {
            Write-Host "  PASS: $Name" -ForegroundColor Green
            $script:pass_count++
        } else {
            Write-Host "  FAIL: $Name — validation failed: $result" -ForegroundColor Red
            $script:fail_count++
            $script:failures += "$Name — $result"
        }
        return $response
    }
    catch {
        Write-Host "  FAIL: $Name — $($_.Exception.Message)" -ForegroundColor Red
        $script:fail_count++
        $script:failures += "$Name — $($_.Exception.Message)"
        return $null
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  v5.5 Backend API Smoke Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ============================================================
# STEP 1: SEED
# ============================================================
Write-Host "--- STEP 1: SEED ---" -ForegroundColor Yellow

Test-Endpoint -Name "Seed Neo4j" -Method POST -Url "$BASE/api/demo/seed" -Validate {
    param($r) if ($r.status -eq "success") { $true } else { "status=$($r.status)" }
}

Start-Sleep -Seconds 2

# ============================================================
# STEP 2: ANALYZE 6 ALERTS
# ============================================================
Write-Host "`n--- STEP 2: ANALYZE ALERTS ---" -ForegroundColor Yellow

$alerts = @(
    @{id="ALERT-7823"; desc="credential_access (travel)"},
    @{id="ALERT-7831"; desc="credential_access (brute force)"},
    @{id="ALERT-7827"; desc="cloud_infrastructure (S3)"},
    @{id="ALERT-7838"; desc="insider_threat (mass download)"},
    @{id="ALERT-7825"; desc="threat_intel (C2 beacon)"},
    @{id="ALERT-7826"; desc="data_exfiltration (dropbox)"}
)

$decision_ids = @()

foreach ($alert in $alerts) {
    $body = "{`"alert_id`": `"$($alert.id)`"}"
    $resp = Test-Endpoint -Name "Analyze $($alert.id) ($($alert.desc))" -Method POST `
        -Url "$BASE/api/alert/analyze" -Body $body -Validate {
        param($r)
        if (-not $r.recommendation) { return "missing recommendation" }
        if (-not $r.gae_scoring) { return "missing gae_scoring" }
        if (-not $r.composite_gate) { return "missing composite_gate" }
        if (-not $r.narrative) { return "missing narrative" }
        if ($r.composite_gate.auto_approve -isnot [bool]) { return "auto_approve not bool" }
        $true
    }
    if ($resp -and $resp.recommendation.decision_id) {
        $decision_ids += $resp.recommendation.decision_id
    }
}

# Check decision_method contains "5 actions"
if ($resp -and $resp.gae_scoring.decision_method) {
    $dm = $resp.gae_scoring.decision_method
    if ($dm -match "5 actions") {
        Write-Host "  PASS: decision_method contains '5 actions'" -ForegroundColor Green
        $pass_count++
    } else {
        Write-Host "  FAIL: decision_method says '$dm' (expected '5 actions')" -ForegroundColor Red
        $fail_count++
        $failures += "decision_method missing '5 actions'"
    }
}

# Check provenance on last response
if ($resp -and $resp.provenance -and $resp.provenance.factors) {
    $fc = ($resp.provenance.factors | Measure-Object).Count
    if ($fc -eq 6) {
        Write-Host "  PASS: provenance has 6 factors" -ForegroundColor Green
        $pass_count++
    } else {
        Write-Host "  FAIL: provenance has $fc factors (expected 6)" -ForegroundColor Red
        $fail_count++
        $failures += "provenance factor count=$fc"
    }
} else {
    Write-Host "  FAIL: provenance missing from analyze response" -ForegroundColor Red
    $fail_count++
    $failures += "provenance missing"
}

# ============================================================
# STEP 3: EXPLAIN EACH DECISION
# ============================================================
Write-Host "`n--- STEP 3: EXPLAIN DECISIONS ---" -ForegroundColor Yellow

foreach ($did in $decision_ids) {
    Test-Endpoint -Name "Explain $($did.Substring(0,8))..." -Url "$BASE/api/soc/explain/$did" -Validate {
        param($r)
        if (-not $r.nl_explanation) { return "missing nl_explanation" }
        if ($r.nl_explanation -match "\[user\]") { return "template var [user] not resolved" }
        if ($r.nl_explanation -match "\[asset\]") { return "template var [asset] not resolved" }
        if (-not $r.category) { return "missing category" }
        if (-not $r.similar_cases_message -and -not $r.similar_cases) { return "missing similar_cases info" }
        $true
    }
}

# ============================================================
# STEP 4: IKS + LEARNING STATE
# ============================================================
Write-Host "`n--- STEP 4: IKS + LEARNING STATE ---" -ForegroundColor Yellow

Test-Endpoint -Name "Learning State" -Url "$BASE/api/soc/learning-state" -Validate {
    param($r)
    if ($null -eq $r.iks_v2) { return "missing iks_v2" }
    if (-not $r.iks_components) { return "missing iks_components" }
    if (-not $r.iks_interpretation) { return "missing iks_interpretation" }
    $true
}

Test-Endpoint -Name "IKS Trend" -Url "$BASE/api/soc/iks-trend" -Validate {
    param($r)
    if (-not $r.current) { return "missing current" }
    if ($null -eq $r.current.iks_v2) { return "missing current.iks_v2" }
    $true
}

# ============================================================
# STEP 5: SHADOW MODE
# ============================================================
Write-Host "`n--- STEP 5: SHADOW MODE ---" -ForegroundColor Yellow

Test-Endpoint -Name "Shadow Enable" -Method POST -Url "$BASE/api/soc/shadow/toggle" `
    -Body '{"enabled": true}' -Validate {
    param($r) if ($r.shadow_mode -eq $true) { $true } else { "shadow_mode not true" }
}

if ($decision_ids.Count -gt 0) {
    $shadow_body = "{`"decision_id`": `"$($decision_ids[0])`", `"analyst_action`": `"escalate`"}"
    Test-Endpoint -Name "Shadow Analyst Action" -Method POST `
        -Url "$BASE/api/soc/shadow/analyst-action" -Body $shadow_body -Validate {
        param($r) if ($r.recorded -eq $true) { $true } else { "recorded not true" }
    }
}

Test-Endpoint -Name "Shadow Report" -Url "$BASE/api/soc/shadow/report" -Validate {
    param($r)
    if ($null -eq $r.overall_agreement) { return "missing overall_agreement" }
    if ($null -eq $r.total_shadow_decisions) { return "missing total_shadow_decisions" }
    $true
}

Test-Endpoint -Name "Shadow Disable" -Method POST -Url "$BASE/api/soc/shadow/toggle" `
    -Body '{"enabled": false}' -Validate {
    param($r) if ($r.shadow_mode -eq $false) { $true } else { "shadow_mode not false" }
}

# ============================================================
# STEP 6: CHECKPOINT + ROLLBACK
# ============================================================
Write-Host "`n--- STEP 6: CHECKPOINT + ROLLBACK ---" -ForegroundColor Yellow

$cp_resp = Test-Endpoint -Name "Create Checkpoint" -Method POST `
    -Url "$BASE/api/soc/checkpoint/create" -Body '{"reason": "smoke_test"}' -Validate {
    param($r) if ($r.checkpoint_id) { $true } else { "missing checkpoint_id" }
}

Test-Endpoint -Name "List Checkpoints" -Url "$BASE/api/soc/checkpoint/list" -Validate {
    param($r)
    $count = ($r | Measure-Object).Count
    if ($count -ge 1) { $true } else { "no checkpoints found" }
}

Test-Endpoint -Name "Freeze Scorer" -Method POST -Url "$BASE/api/soc/scorer/freeze" -Validate {
    param($r) if ($r.frozen -eq $true) { $true } else { "frozen not true" }
}

Test-Endpoint -Name "Unfreeze Scorer" -Method POST -Url "$BASE/api/soc/scorer/unfreeze" -Validate {
    param($r) if ($r.frozen -eq $false) { $true } else { "frozen not false" }
}

if ($cp_resp -and $cp_resp.checkpoint_id) {
    $rb_body = "{`"checkpoint_id`": `"$($cp_resp.checkpoint_id)`"}"
    Test-Endpoint -Name "Rollback to Checkpoint" -Method POST `
        -Url "$BASE/api/soc/checkpoint/rollback" -Body $rb_body -Validate {
        param($r) if ($r.frozen -eq $true) { $true } else { "frozen not true after rollback" }
    }

    # Unfreeze after rollback for subsequent tests
    Invoke-RestMethod -Uri "$BASE/api/soc/scorer/unfreeze" -Method POST | Out-Null
}

# ============================================================
# STEP 7: AUTO-APPROVE STATS
# ============================================================
Write-Host "`n--- STEP 7: AUTO-APPROVE STATS ---" -ForegroundColor Yellow

Test-Endpoint -Name "Auto-Approve Stats" -Url "$BASE/api/soc/auto-approve-stats" -Validate {
    param($r)
    if ($null -eq $r.total_decisions) { return "missing total_decisions" }
    if ($null -eq $r.by_category) { return "missing by_category" }
    $true
}

# ============================================================
# STEP 8: PROVENANCE
# ============================================================
Write-Host "`n--- STEP 8: PROVENANCE ---" -ForegroundColor Yellow

if ($decision_ids.Count -gt 0) {
    Test-Endpoint -Name "Provenance" -Url "$BASE/api/soc/provenance/$($decision_ids[0])" -Validate {
        param($r)
        if (-not $r.factors) { return "missing factors" }
        $fc = ($r.factors | Measure-Object).Count
        if ($fc -ne 6) { return "factor count=$fc (expected 6)" }
        $true
    }
}

# ============================================================
# STEP 9: THREAT INTEL
# ============================================================
Write-Host "`n--- STEP 9: THREAT INTEL ---" -ForegroundColor Yellow

Test-Endpoint -Name "Threat Intel ALERT-7824" -Url "$BASE/api/soc/threat-intel/ALERT-7824" -Validate {
    param($r)
    if ($r.total_matches -lt 1) { return "total_matches=$($r.total_matches) (expected >= 1)" }
    $true
}

Test-Endpoint -Name "Threat Intel ALERT-7825" -Url "$BASE/api/soc/threat-intel/ALERT-7825" -Validate {
    param($r)
    if ($r.total_matches -lt 1) { return "total_matches=$($r.total_matches) (expected >= 1)" }
    $true
}

Test-Endpoint -Name "Enrichment Summary" -Url "$BASE/api/graph/enrichment/summary" -Validate {
    param($r)
    if (-not $r.threat_indicators) { return "missing threat_indicators" }
    $true
}

# ============================================================
# STEP 10: GRAPH EXPLORER
# ============================================================
Write-Host "`n--- STEP 10: GRAPH EXPLORER ---" -ForegroundColor Yellow

Test-Endpoint -Name "Graph Summary" -Url "$BASE/api/soc/graph/summary" -Validate {
    param($r)
    if ($r.total_nodes -lt 1) { return "total_nodes=$($r.total_nodes)" }
    $true
}

Test-Endpoint -Name "Top Nodes" -Url "$BASE/api/soc/graph/top-nodes" -Validate {
    param($r)
    $count = ($r | Measure-Object).Count
    if ($count -lt 1) { return "no nodes returned" }
    $true
}

Test-Endpoint -Name "Prebuilt Queries List" -Url "$BASE/api/soc/graph/prebuilt-queries" -Validate {
    param($r)
    $count = ($r | Measure-Object).Count
    if ($count -lt 5) { return "only $count queries (expected 5)" }
    $true
}

Test-Endpoint -Name "Run Prebuilt: top_risk_users" -Method POST `
    -Url "$BASE/api/soc/graph/prebuilt/top_risk_users" -Validate {
    param($r)
    if (-not $r.rows) { return "missing rows" }
    $true
}

Test-Endpoint -Name "Run Prebuilt: critical_assets" -Method POST `
    -Url "$BASE/api/soc/graph/prebuilt/critical_assets" -Validate {
    param($r)
    if (-not $r.rows) { return "missing rows" }
    $true
}

Test-Endpoint -Name "Safe Cypher Query" -Method POST `
    -Url "$BASE/api/soc/graph/query" `
    -Body '{"cypher": "MATCH (u:User) RETURN u.name AS name LIMIT 5"}' -Validate {
    param($r)
    if (-not $r.rows) { return "missing rows" }
    $true
}

# Test mutation blocking
try {
    $mutation_resp = Invoke-RestMethod -Uri "$BASE/api/soc/graph/query" -Method POST `
        -ContentType "application/json" -Body '{"cypher": "MATCH (n) DELETE n"}' `
        -ErrorAction Stop
    # If we get here without error, check if error field present
    if ($mutation_resp.error) {
        Write-Host "  PASS: Mutation query blocked" -ForegroundColor Green
        $pass_count++
    } else {
        Write-Host "  FAIL: Mutation query NOT blocked" -ForegroundColor Red
        $fail_count++
        $failures += "Mutation query not blocked"
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host "  PASS: Mutation query blocked (400)" -ForegroundColor Green
        $pass_count++
    } else {
        Write-Host "  FAIL: Mutation query returned $statusCode (expected 400)" -ForegroundColor Red
        $fail_count++
        $failures += "Mutation query status=$statusCode"
    }
}

# ============================================================
# STEP 11: REGRESSION — EXISTING ENDPOINTS
# ============================================================
Write-Host "`n--- STEP 11: REGRESSION ---" -ForegroundColor Yellow

Test-Endpoint -Name "Health" -Url "$BASE/health" -Validate {
    param($r) $true
}

Test-Endpoint -Name "Alert Queue" -Url "$BASE/api/alerts/queue" -Validate {
    param($r) $true
}

Test-Endpoint -Name "Graph Stats" -Url "$BASE/api/soc/graph-stats" -Validate {
    param($r)
    if (-not $r) { return "empty response" }
    $true
}

Test-Endpoint -Name "Centroid Evolution" -Url "$BASE/api/soc/centroid-evolution" -Validate {
    param($r) $true
}

Test-Endpoint -Name "Detection Engineering" -Url "$BASE/api/soc/detection-engineering" -Validate {
    param($r) $true
}

Test-Endpoint -Name "SOC Metrics" -Url "$BASE/api/soc/metrics" -Validate {
    param($r) $true
}

Test-Endpoint -Name "Economics" -Url "$BASE/api/soc/economics" -Validate {
    param($r) $true
}

Test-Endpoint -Name "Operational Metrics" -Url "$BASE/api/soc/operational-metrics" -Validate {
    param($r) $true
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SMOKE TEST SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PASSED: $pass_count" -ForegroundColor Green
Write-Host "  FAILED: $fail_count" -ForegroundColor $(if ($fail_count -gt 0) { "Red" } else { "Green" })

if ($fail_count -gt 0) {
    Write-Host "`n  FAILURES:" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "    - $f" -ForegroundColor Red
    }
}

Write-Host "`n  Decision IDs created:" -ForegroundColor Gray
foreach ($did in $decision_ids) {
    Write-Host "    $did" -ForegroundColor Gray
}

Write-Host ""
if ($fail_count -eq 0) {
    Write-Host "  ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "  $fail_count FAILURES — review above" -ForegroundColor Red
}
Write-Host ""
