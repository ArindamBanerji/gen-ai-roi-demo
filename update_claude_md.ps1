# update_claude_md.ps1 — Prepend grounding contract to all 5 repos
# Usage: .\update_claude_md.ps1

$grounding = @"
# ⚠️ GROUNDING CONTRACT (non-negotiable)

**These rules apply to every AI coding agent working in this repo.**

1. **Docs are aspirational until proven in code.** Never treat design docs,
   specs, or planning documents as implemented. Check the actual source files.

2. **Cite file + line for every behavioral claim.** "The reset endpoint filters
   by origin" is not acceptable. "triage.py:L142 filters by origin" is.

3. **Code and tests beat docs.** If a spec says "use MERGE" but the code uses
   CREATE, the code is correct. Report the discrepancy as DRIFT.

4. **DRIFT = stop.** If code and docs/specs disagree, label it DRIFT, report it
   to the user, and do not propose fixes based on the docs. The code is the
   source of truth.

5. **Check downstream consumers before changing data formats.** Before changing
   alert ID prefixes, field names, or response shapes: grep the frontend, E2E
   tests, and contract files for the current format. List all consumers.

6. **Verify after every change.** Run the verification ladder before claiming
   anything works: grep -> curl -> validate_contracts.py -> targeted test -> full suite.

---

"@

$repos = @(
    $env:CLAUDE_SOC,
    $env:CLAUDE_CI,
    $env:CLAUDE_GAE,
    $env:CLAUDE_S2P,
    $env:CLAUDE_SDK
)

foreach ($repo in $repos) {
    if (-not $repo) {
        Write-Host "[SKIP] Env var not set for a repo" -ForegroundColor Yellow
        continue
    }
    $claudeFile = Join-Path $repo "CLAUDE.md"
    $repoName = Split-Path $repo -Leaf

    if (Test-Path $claudeFile) {
        $existing = Get-Content $claudeFile -Raw
        if ($existing -match "GROUNDING CONTRACT") {
            Write-Host "[SKIP] $repoName — already has grounding contract" -ForegroundColor Yellow
            continue
        }
        $newContent = $grounding + $existing
        Set-Content $claudeFile $newContent -NoNewline
        Write-Host "[OK]   $repoName — prepended grounding contract" -ForegroundColor Green
    } else {
        Set-Content $claudeFile $grounding -NoNewline
        Write-Host "[NEW]  $repoName — created CLAUDE.md with grounding contract" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Done. Verify with:"
Write-Host '  Get-Content $env:CLAUDE_SOC\CLAUDE.md | Select-Object -First 5'
