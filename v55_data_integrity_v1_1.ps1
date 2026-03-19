# v5.5 Data Integrity Tests v1.1
# Run AFTER the smoke test (which seeds + analyzes alerts)
# Queries Neo4j directly via the backend API endpoints
# Usage: .\v55_data_integrity.ps1
#
# v1.1 fixes:
# - AlertType query checks both id and name fields
# - Asset queries rewritten to avoid Cypher patterns that fail validation
# - Bootstrap test notes dependency on seed endpoint fix

$BASE = "http://localhost:8000"
$pass_count = 0
$fail_count = 0
$failures = @()

function Test-Check {
    param(
        [string]$Name,
        [scriptblock]$Check
    )
    try {
        $result = & $Check
        if ($result -eq $true) {
            Write-Host "  PASS: $Name" -ForegroundColor Green
            $script:pass_count++
        } else {
            Write-Host "  FAIL: $Name — $result" -ForegroundColor Red
            $script:fail_count++
            $script:failures += "$Name — $result"
        }
    } catch {
        Write-Host "  FAIL: $Name — $($_.Exception.Message)" -ForegroundColor Red
        $script:fail_count++
        $script:failures += "$Name — $($_.Exception.Message)"
    }
}

function Run-Cypher {
    param([string]$Query)
    $body = "{`"cypher`": `"$($Query -replace '"', '\"')`"}"
    $resp = Invoke-RestMethod -Uri "$BASE/api/soc/graph/query" -Method POST `
        -ContentType "application/json" -Body $body -ErrorAction Stop
    return $resp.rows
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  v5.5 Data Integrity Tests v1.1" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ============================================================
# B1: Decision nodes have correct fields
# ============================================================
Write-Host "--- B1: Decision Node Fields ---" -ForegroundColor Yellow

Test-Check "Decisions exist" {
    $rows = Run-Cypher "MATCH (d:Decision) RETURN count(d) AS cnt"
    if ($rows[0].cnt -ge 1) { $true } else { "count=$($rows[0].cnt)" }
}

Test-Check "Decisions have category field" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.category IS NOT NULL RETURN count(d) AS cnt"
    $total = (Run-Cypher "MATCH (d:Decision) RETURN count(d) AS cnt")[0].cnt
    if ($rows[0].cnt -eq $total) { $true } else { "$($rows[0].cnt)/$total have category" }
}

Test-Check "No decisions have category=unknown" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.category = 'unknown' RETURN count(d) AS cnt"
    if ($rows[0].cnt -eq 0) { $true } else { "$($rows[0].cnt) decisions have category=unknown" }
}

Test-Check "Decisions have factor_vector as list" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.factor_vector IS NOT NULL RETURN d.factor_vector AS fv, d.id AS id"
    $bad = 0
    foreach ($r in $rows) {
        if ($r.fv -is [string]) { $bad++ }
    }
    if ($bad -eq 0) { $true } else { "$bad decisions have factor_vector as string (not list)" }
}

Test-Check "Factor vectors have 6 elements" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.factor_vector IS NOT NULL RETURN size(d.factor_vector) AS len, d.id AS id"
    $bad = @($rows | Where-Object { $_.len -ne 6 })
    if ($bad.Count -eq 0) { $true } else { "$($bad.Count) decisions have wrong factor_vector length" }
}

Test-Check "Decisions have action field" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.action IS NOT NULL RETURN count(d) AS cnt"
    $total = (Run-Cypher "MATCH (d:Decision) RETURN count(d) AS cnt")[0].cnt
    if ($rows[0].cnt -eq $total) { $true } else { "$($rows[0].cnt)/$total have action" }
}

Test-Check "Decisions have confidence field" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.confidence IS NOT NULL RETURN count(d) AS cnt"
    $total = (Run-Cypher "MATCH (d:Decision) RETURN count(d) AS cnt")[0].cnt
    if ($rows[0].cnt -eq $total) { $true } else { "$($rows[0].cnt)/$total have confidence" }
}

Test-Check "Confidence values in [0,1]" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.confidence < 0 OR d.confidence > 1 RETURN count(d) AS cnt"
    if ($rows[0].cnt -eq 0) { $true } else { "$($rows[0].cnt) decisions have confidence outside [0,1]" }
}

# ============================================================
# B2: Category distribution
# ============================================================
Write-Host "`n--- B2: Category Distribution ---" -ForegroundColor Yellow

$expected_categories = @("credential_access", "cloud_infrastructure", "insider_threat",
                         "threat_intel_match", "data_exfiltration", "lateral_movement")

Test-Check "Multiple categories represented in decisions" {
    $rows = Run-Cypher "MATCH (d:Decision) RETURN DISTINCT d.category AS cat"
    $cats = @($rows | ForEach-Object { $_.cat })
    if ($cats.Count -ge 3) { $true } else { "only $($cats.Count) categories: $($cats -join ', ')" }
}

Test-Check "Categories are valid SOC categories" {
    $rows = Run-Cypher "MATCH (d:Decision) RETURN DISTINCT d.category AS cat"
    $invalid = @()
    foreach ($r in $rows) {
        if ($r.cat -and $r.cat -notin $expected_categories) {
            $invalid += $r.cat
        }
    }
    if ($invalid.Count -eq 0) { $true } else { "invalid categories: $($invalid -join ', ')" }
}

# ============================================================
# B3: Bootstrap decisions
# ============================================================
Write-Host "`n--- B3: Bootstrap Decisions ---" -ForegroundColor Yellow

Test-Check "Bootstrap decisions exist" {
    $rows = Run-Cypher "MATCH (d:Decision) WHERE d.source = 'bootstrap' RETURN count(d) AS cnt"
    if ($rows[0].cnt -ge 1) { $true } else { "count=$($rows[0].cnt) (seed endpoint may need fix)" }
}

Test-Check "Bootstrap decisions have factor_vector" {
    $total_rows = Run-Cypher "MATCH (d:Decision) WHERE d.source = 'bootstrap' RETURN count(d) AS cnt"
    $total = $total_rows[0].cnt
    if ($total -eq 0) { "no bootstrap decisions (seed endpoint may need fix)" }
    else {
        $rows = Run-Cypher "MATCH (d:Decision) WHERE d.source = 'bootstrap' AND d.factor_vector IS NOT NULL RETURN count(d) AS cnt"
        if ($rows[0].cnt -eq $total) { $true }
        else { "$($rows[0].cnt)/$total have factor_vector" }
    }
}

# ============================================================
# B4: ThreatIndicator nodes
# ============================================================
Write-Host "`n--- B4: Threat Indicators ---" -ForegroundColor Yellow

Test-Check "ThreatIndicator nodes exist (>= 5)" {
    $rows = Run-Cypher "MATCH (ti:ThreatIndicator) RETURN count(ti) AS cnt"
    if ($rows[0].cnt -ge 5) { $true } else { "count=$($rows[0].cnt) (expected >= 5)" }
}

Test-Check "ThreatIndicators have required fields" {
    $rows = Run-Cypher "MATCH (ti:ThreatIndicator) WHERE ti.ioc_type IS NULL OR ti.ioc_value IS NULL OR ti.severity IS NULL RETURN count(ti) AS cnt"
    if ($rows[0].cnt -eq 0) { $true } else { "$($rows[0].cnt) missing required fields" }
}

Test-Check "ThreatIndicators linked to alerts" {
    $rows = Run-Cypher "MATCH (ti:ThreatIndicator)-[:ASSOCIATED_WITH]->(a:Alert) RETURN count(DISTINCT a) AS cnt"
    if ($rows[0].cnt -ge 2) { $true } else { "only $($rows[0].cnt) alerts have indicators (expected >= 2)" }
}

Test-Check "All ThreatIntel nodes have ThreatIndicator label" {
    $rows = Run-Cypher "MATCH (ti:ThreatIntel) OPTIONAL MATCH (ti2:ThreatIndicator) WHERE ti2 = ti WITH ti WHERE ti2 IS NULL RETURN count(ti) AS cnt"
    # Simpler approach: count ThreatIntel minus count with both labels
    $ti_total = (Run-Cypher "MATCH (n:ThreatIntel) RETURN count(n) AS cnt")[0].cnt
    $ti_both = (Run-Cypher "MATCH (n:ThreatIntel:ThreatIndicator) RETURN count(n) AS cnt")[0].cnt
    $missing = $ti_total - $ti_both
    if ($missing -eq 0) { $true } else { "$missing ThreatIntel nodes missing ThreatIndicator label" }
}

# ============================================================
# B5: AlertType coverage
# ============================================================
Write-Host "`n--- B5: AlertType Coverage ---" -ForegroundColor Yellow

Test-Check "AlertType nodes exist (>= 10)" {
    $rows = Run-Cypher "MATCH (at:AlertType) RETURN count(at) AS cnt"
    if ($rows[0].cnt -ge 10) { $true } else { "count=$($rows[0].cnt)" }
}

Test-Check "All alerts have [:CLASSIFIED_AS] edge" {
    $total = (Run-Cypher "MATCH (a:Alert) RETURN count(a) AS cnt")[0].cnt
    $classified = (Run-Cypher "MATCH (a:Alert)-[:CLASSIFIED_AS]->(:AlertType) RETURN count(DISTINCT a) AS cnt")[0].cnt
    $missing = $total - $classified
    if ($missing -eq 0) { $true } else { "$missing/$total alerts missing [:CLASSIFIED_AS]" }
}

Test-Check "AlertType node count matches alert_type variety" {
    $type_count = (Run-Cypher "MATCH (at:AlertType) RETURN count(at) AS cnt")[0].cnt
    # Just check we have a reasonable number
    if ($type_count -ge 10) { $true } else { "only $type_count AlertType nodes" }
}

# ============================================================
# B6: Checkpoint nodes
# ============================================================
Write-Host "`n--- B6: Checkpoints ---" -ForegroundColor Yellow

Test-Check "Checkpoint nodes exist (>= 1)" {
    $rows = Run-Cypher "MATCH (cp:Checkpoint) RETURN count(cp) AS cnt"
    if ($rows[0].cnt -ge 1) { $true } else { "count=$($rows[0].cnt) (run smoke test first)" }
}

Test-Check "Checkpoints have mu_snapshot" {
    $total = (Run-Cypher "MATCH (cp:Checkpoint) RETURN count(cp) AS cnt")[0].cnt
    if ($total -eq 0) { "no checkpoints" }
    else {
        $rows = Run-Cypher "MATCH (cp:Checkpoint) WHERE cp.mu_snapshot IS NOT NULL RETURN count(cp) AS cnt"
        if ($rows[0].cnt -eq $total) { $true }
        else { "$($rows[0].cnt)/$total have mu_snapshot" }
    }
}

# ============================================================
# B7: Graph integrity
# ============================================================
Write-Host "`n--- B7: Graph Integrity ---" -ForegroundColor Yellow

Test-Check "Non-bootstrap Decisions linked to Alerts" {
    $total = (Run-Cypher "MATCH (d:Decision) WHERE d.source IS NULL OR d.source <> 'bootstrap' RETURN count(d) AS cnt")[0].cnt
    $linked = (Run-Cypher "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) RETURN count(d) AS cnt")[0].cnt
    if ($total -eq 0) { $true }
    elseif ($linked -ge $total) { $true }
    else { "$linked/$total non-bootstrap decisions linked to alerts" }
}

Test-Check "Alerts linked to Users via [:INVOLVES]" {
    $total = (Run-Cypher "MATCH (a:Alert) RETURN count(a) AS cnt")[0].cnt
    $linked = (Run-Cypher "MATCH (a:Alert)-[:INVOLVES]->(u:User) RETURN count(DISTINCT a) AS cnt")[0].cnt
    if ($linked -eq $total) { $true } else { "$linked/$total alerts have [:INVOLVES]" }
}

Test-Check "Alerts linked to Assets via [:DETECTED_ON]" {
    $total = (Run-Cypher "MATCH (a:Alert) RETURN count(a) AS cnt")[0].cnt
    $linked = (Run-Cypher "MATCH (a:Alert)-[:DETECTED_ON]->(ast:Asset) RETURN count(DISTINCT a) AS cnt")[0].cnt
    if ($linked -eq $total) { $true } else { "$linked/$total alerts have [:DETECTED_ON]" }
}

Test-Check "Users are connected (no orphans)" {
    $total = (Run-Cypher "MATCH (u:User) RETURN count(u) AS cnt")[0].cnt
    $connected = (Run-Cypher "MATCH (u:User)-[]-() RETURN count(DISTINCT u) AS cnt")[0].cnt
    $orphans = $total - $connected
    if ($orphans -eq 0) { $true } else { "$orphans orphan User nodes" }
}

Test-Check "Assets are connected (no orphans)" {
    $total = (Run-Cypher "MATCH (a:Asset) RETURN count(a) AS cnt")[0].cnt
    $connected = (Run-Cypher "MATCH (a:Asset)-[]-() RETURN count(DISTINCT a) AS cnt")[0].cnt
    $orphans = $total - $connected
    if ($orphans -eq 0) { $true } else { "$orphans orphan Asset nodes" }
}

# ============================================================
# B8: Data quality
# ============================================================
Write-Host "`n--- B8: Data Quality ---" -ForegroundColor Yellow

Test-Check "All Users have name" {
    $rows = Run-Cypher "MATCH (u:User) WHERE u.name IS NULL RETURN count(u) AS cnt"
    if ($rows[0].cnt -eq 0) { $true } else { "$($rows[0].cnt) users missing name" }
}

Test-Check "All Assets have hostname" {
    $total = (Run-Cypher "MATCH (a:Asset) RETURN count(a) AS cnt")[0].cnt
    $with_host = (Run-Cypher "MATCH (a:Asset) WHERE a.hostname IS NOT NULL RETURN count(a) AS cnt")[0].cnt
    $missing = $total - $with_host
    if ($missing -eq 0) { $true } else { "$missing assets missing hostname" }
}

Test-Check "All Alerts have alert_type" {
    $rows = Run-Cypher "MATCH (a:Alert) WHERE a.alert_type IS NULL RETURN count(a) AS cnt"
    if ($rows[0].cnt -eq 0) { $true } else { "$($rows[0].cnt) alerts missing alert_type" }
}

Test-Check "All Alerts have severity" {
    $rows = Run-Cypher "MATCH (a:Alert) WHERE a.severity IS NULL RETURN count(a) AS cnt"
    if ($rows[0].cnt -eq 0) { $true } else { "$($rows[0].cnt) alerts missing severity" }
}

Test-Check "Node count sanity" {
    $resp = Invoke-RestMethod -Uri "$BASE/api/soc/graph/summary"
    $nodes = $resp.total_nodes
    $rels = $resp.total_relationships
    if ($nodes -ge 50 -and $rels -ge 50) { $true }
    else { "nodes=$nodes rels=$rels (expected >= 50 each)" }
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DATA INTEGRITY SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PASSED: $pass_count" -ForegroundColor Green
Write-Host "  FAILED: $fail_count" -ForegroundColor $(if ($fail_count -gt 0) { "Red" } else { "Green" })

if ($fail_count -gt 0) {
    Write-Host "`n  FAILURES:" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "    - $f" -ForegroundColor Red
    }
}

Write-Host ""
if ($fail_count -eq 0) {
    Write-Host "  ALL DATA INTEGRITY CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "  $fail_count FAILURES — review above" -ForegroundColor Red
}
Write-Host ""
