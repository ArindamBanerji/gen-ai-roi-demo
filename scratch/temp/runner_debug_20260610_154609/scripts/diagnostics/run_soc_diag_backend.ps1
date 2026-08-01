param(
    [string]$GraphName = "soc_graph_diag_f2",
    [int]$Port = 8001,
    [bool]$SourceCiPlatform = $true,
    [switch]$AgeUsePool,
    [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ProjectsRoot = Resolve-Path (Join-Path $RepoRoot "..")
$DemoPath = Join-Path $ProjectsRoot "copilot-sdk\demo.py"
$ContractPath = Join-Path $RepoRoot "scratch\temp\soc_diag_backend_contract.json"
$GraphDsn = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"

if (-not (Test-Path $DemoPath)) {
    Write-Error "[SOC DIAG] canonical demo.py not found: $DemoPath"
    exit 1
}

Write-Host "[SOC DIAG] canonical launcher=$DemoPath"
Write-Host "[SOC DIAG] graph=$GraphName"
Write-Host "[SOC DIAG] port=$Port"
Write-Host "[SOC DIAG] GRAPH_DSN=$($GraphDsn -replace 'password=[^ ]+', 'password=***')"
Write-Host "[SOC DIAG] contract=$ContractPath"
Write-Host "[SOC DIAG] AGE_USE_POOL requested=$($AgeUsePool.IsPresent)"
if (-not $SourceCiPlatform) {
    Write-Host "[SOC DIAG] SourceCiPlatform=false ignored; demo.py diag mode always uses source ci-platform"
}

if ($PreflightOnly) {
    Write-Host "[SOC DIAG] preflight-only: showing SOC status via demo.py"
    & python $DemoPath --status --soc
    exit $LASTEXITCODE
}

$DemoArgs = @(
    $DemoPath,
    "--soc",
    "--diag-mode",
    "--diag-graph-name", $GraphName,
    "--diag-backend-port", "$Port",
    "--diag-graph-dsn", $GraphDsn,
    "--diag-contract", $ContractPath,
    "--no-browser"
)
if ($AgeUsePool) {
    $DemoArgs += "--age-use-pool"
}

Write-Host "[SOC DIAG] starting SOC diagnostic backend through demo.py"
& python @DemoArgs
exit $LASTEXITCODE
