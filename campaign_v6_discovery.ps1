# Campaign v6.0 Context Injection — Pre-Design Discovery Scan
# Run from: gen-ai-roi-demo-v4-v50 root (SOC repo)
# Usage: cd $env:CLAUDE_SOC; .\campaign_v6_discovery.ps1

$ErrorActionPreference = "Continue"

Write-Host ("=" * 70)
Write-Host "CAMPAIGN v6.0 CONTEXT INJECTION — DISCOVERY SCAN"
Write-Host ("=" * 70)

# ─────────────────────────────────────────────────────
# SCAN 1: CampaignMatch — what fields does it carry?
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 1: CampaignMatch class definition"
Write-Host ("-" * 50)

Select-String -Path "backend\app\domains\soc\campaigns.py" -Pattern "class CampaignMatch|CampaignMatch|@dataclass" |
    Select-Object -First 20

python -c "
import re
with open('backend/app/domains/soc/campaigns.py') as f:
    content = f.read()
match = re.search(r'class CampaignMatch.*?(?=\nclass |\Z)', content, re.DOTALL)
if match:
    print('--- CampaignMatch class body ---')
    print(match.group()[:800])
else:
    print('[MISS] CampaignMatch class not found')
"

# ─────────────────────────────────────────────────────
# SCAN 2: check_alert return type and value
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 2: check_alert return"
Write-Host ("-" * 50)

Select-String -Path "backend\app\domains\soc\campaigns.py" -Pattern "async def check_alert|def check_alert|return.*CampaignMatch|return.*match|-> Campaign" |
    Select-Object -First 15

# ─────────────────────────────────────────────────────
# SCAN 3: CampaignAsyncState — what's cached?
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 3: CampaignAsyncState cache structure"
Write-Host ("-" * 50)

Select-String -Path "backend\app\domains\soc\campaigns.py" -Pattern "class CampaignAsyncState|_materialized|_cache|_index|_pending" |
    Select-Object -First 20

python -c "
import re
with open('backend/app/domains/soc/campaigns.py') as f:
    content = f.read()
match = re.search(r'class CampaignAsyncState.*?(?=\nclass |\Z)', content, re.DOTALL)
if match:
    print('--- CampaignAsyncState class body (first 1200 chars) ---')
    print(match.group()[:1200])
else:
    print('[MISS] CampaignAsyncState not found')
"

# ─────────────────────────────────────────────────────
# SCAN 4: SOC situation context builder — where is it?
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 4: SOC situation context builder"
Write-Host ("-" * 50)

Get-ChildItem -Path "backend\app\services" -Filter "*.py" -Recurse |
    Select-String -Pattern "SituationContext|situation_context|TraversalNode|situation_pattern|context_builder" |
    Select-Object -First 20

Get-ChildItem -Path "backend\app\domains\soc" -Filter "*.py" -Recurse |
    Select-String -Pattern "SituationContext|situation_context|TraversalNode" |
    Select-Object -First 10

Get-ChildItem -Path "backend\app\routers" -Filter "*.py" -Recurse |
    Select-String -Pattern "SituationContext|situation_context|TraversalNode" |
    Select-Object -First 10

# ─────────────────────────────────────────────────────
# SCAN 5: Where does triage.py use campaign results?
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 5: triage.py campaign usage"
Write-Host ("-" * 50)

Select-String -Path "backend\app\routers\triage.py" -Pattern "campaign|check_alert|camp_match|CampaignMatch|situation" |
    Select-Object -First 20

# ─────────────────────────────────────────────────────
# SCAN 6: What NL evidence/advisory templates exist?
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 6: Evidence/advisory templates"
Write-Host ("-" * 50)

Get-ChildItem -Path "backend\app" -Filter "*.py" -Recurse |
    Select-String -Pattern "advisory|evidence.*template|narration|hero_insight|nl_template|campaign.*note|campaign.*context" |
    Select-Object -First 20

# ─────────────────────────────────────────────────────
# SCAN 7: Campaign node properties in AGE
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 7: Campaign node properties (what's stored in AGE)"
Write-Host ("-" * 50)

Select-String -Path "backend\app\domains\soc\campaigns.py" -Pattern "Campaign.*size|Campaign.*first_seen|Campaign.*category|Campaign.*member|campaign_id|\.size|\.first_seen|\.age" |
    Select-Object -First 20

# ─────────────────────────────────────────────────────
# SCAN 8: Current campaign count + edge types
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ">>> SCAN 8: Graph state"
Write-Host ("-" * 50)
Write-Host "(Skip if AGE not running — use Phase 3B closeout data instead)"
Write-Host "Campaign nodes: 259, MEMBER_OF: 520, CONTINUES: 0, BELONGS_TO: 0"
Write-Host "(from Phase 3B closeout)"

# ─────────────────────────────────────────────────────
# VERDICT
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ("=" * 70)
Write-Host "VERDICT GUIDE"
Write-Host ("=" * 70)

Write-Host @"

FINDING A - CampaignMatch has size/age/first_seen/category:
  v6.0 is ~30 lines + tests. Use check_alert result directly.

FINDING B - CampaignMatch is just an ID/key:
  v6.0 needs to enrich the match. Options:
    B1: Read from CampaignAsyncState cache (if it stores properties)
    B2: Read from AGE (adds latency, may need cache extension)
    B3: Extend CampaignMatch to carry properties from check_alert

FINDING C - No CampaignMatch class (result is a dict/tuple/str):
  v6.0 needs to define the response structure first.

"@

Write-Host ("=" * 70)
Write-Host "SCAN COMPLETE"
Write-Host ("=" * 70)
