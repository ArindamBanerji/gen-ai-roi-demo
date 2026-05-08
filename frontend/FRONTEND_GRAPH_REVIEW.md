# Frontend Graph Review — gen-ai-roi-demo-v4-v50

**Root:** C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\frontend

## Summary

| Metric | Value |
|--------|-------|
| Total files | 40 |
| TSX components | 13 |
| TS modules | 27 |
| Test/spec files | 21 |
| Total lines | 17,979 |
| Total fetch calls | 18 |
| Total useState calls | 203 |

## Component Inventory

| File | Lines | State | Effects | Fetches | Children |
|------|-------|-------|---------|---------|----------|
| playwright.config.ts | 46 | 0 | 0 | 0 | 0 |
| src\App.tsx | 199 | 1 | 1 | 0 | 8 |
| src\components\CampaignIntelligencePanel.tsx | 103 | 3 | 1 | 1 | 1 |
| src\components\OutcomeFeedback.tsx | 336 | 4 | 1 | 0 | 8 |
| src\components\PolicyConflict.tsx | 258 | 2 | 1 | 0 | 6 |
| src\components\ROICalculator.tsx | 639 | 5 | 3 | 2 | 13 |
| src\components\SimulationPanel.tsx | 520 | 10 | 1 | 0 | 18 |
| src\components\tabs\AlertTriageTab.tsx | 1652 | 22 | 5 | 0 | 27 |
| src\components\tabs\CompoundingTab.tsx | 2684 | 41 | 14 | 6 | 52 |
| src\components\tabs\ExecutiveNarrativeTab.tsx | 532 | 10 | 2 | 1 | 18 |
| src\components\tabs\RuntimeEvolutionTab.tsx | 3570 | 74 | 19 | 6 | 44 |
| src\components\tabs\S2PPreviewTab.tsx | 454 | 7 | 1 | 0 | 5 |
| src\components\tabs\SOCAnalyticsTab.tsx | 1292 | 24 | 2 | 1 | 31 |
| src\lib\api.ts | 562 | 0 | 1 | 1 | 0 |
| src\lib\domain.ts | 60 | 0 | 0 | 0 | 0 |
| src\lib\guards.ts | 62 | 0 | 0 | 0 | 0 |
| src\main.tsx | 10 | 0 | 0 | 0 | 2 |
| src\types\roi.ts | 45 | 0 | 0 | 0 | 0 |
| vite.config.ts | 37 | 0 | 0 | 0 | 0 |

## API Call Map

### src\components\CampaignIntelligencePanel.tsx
- `/api/soc/campaigns`

### src\components\ROICalculator.tsx
- `{param}/roi/defaults`
- `{param}/roi/calculate`

### src\components\tabs\CompoundingTab.tsx
- `/api/soc/evidence-room`
- `/api/soc/evidence-room/export`
- `/api/metrics/decision-economics`
- `/api/soc/operational-metrics`
- `/api/soc/board-export`
- `/api/soc/economics`

### src\components\tabs\ExecutiveNarrativeTab.tsx
- `/api/soc/executive-narrative`

### src\components\tabs\RuntimeEvolutionTab.tsx
- `/api/soc/graph-stats`
- `/api/soc/centroid-evolution?n=200`
- `/api/soc/learning-state`
- `/api/soc/centroid-heatmap`
- `/api/soc/enrichment-status`
- `/api/soc/centroid-support`

### src\components\tabs\SOCAnalyticsTab.tsx
- `/api/soc/detection-engineering`

### src\lib\api.ts
- `{param}/eval/upload`

## State Management

### src\App.tsx
- useState: 1 calls
- useEffect: 1

### src\components\CampaignIntelligencePanel.tsx
- useState: 3 calls
- useEffect: 1

### src\components\OutcomeFeedback.tsx
- useState: 4 calls
- useEffect: 1

### src\components\PolicyConflict.tsx
- useState: 2 calls
- useEffect: 1

### src\components\ROICalculator.tsx
- useState: 5 calls
- useEffect: 3
- useCallback: 1

### src\components\SimulationPanel.tsx
- useState: 10 calls
- useEffect: 1

### src\components\tabs\AlertTriageTab.tsx
- useState: 22 calls
- useEffect: 5

### src\components\tabs\CompoundingTab.tsx
- useState: 41 calls
- useEffect: 14

### src\components\tabs\ExecutiveNarrativeTab.tsx
- useState: 10 calls
- useEffect: 2

### src\components\tabs\RuntimeEvolutionTab.tsx
- useState: 74 calls
- useEffect: 19

### src\components\tabs\S2PPreviewTab.tsx
- useState: 7 calls
- useEffect: 1

### src\components\tabs\SOCAnalyticsTab.tsx
- useState: 24 calls
- useEffect: 2

### src\lib\api.ts
- useEffect: 1

## Component Tree (JSX children)

- **App** → Shield, Zap, Activity, TrendingUp, FileText, ReceiptText, TabId, ActiveComponent
- **CampaignIntelligencePanel** → Campaign
- **OutcomeFeedback** → OutcomeResponse, Clock, CheckCircle, XCircle, AlertTriangle, TrendingUp, TrendingDown, ExternalLink
- **PolicyConflict** → PolicyConflictData, ShieldCheck, AlertTriangle, Shield, Award, Scale
- **ROICalculator** → ROIDefaults, ROIResponse, ROIRequest, ReturnType, Calculator, Heart, Users, TrendingUp, AlertCircle, ChevronRight, DollarSign, Clock, Download
- **SimulationPanel** → ProgressSnap, ChartPoint, SimResult, ReturnType, Activity, CheckCircle, AlertCircle, Square, Play, Download, ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis
- **AlertTriageTab** → Alert, AnalysisResult, ClosedLoopResult, PolicyResolutionData, ReturnType, ThreatIntelStatus, DecisionFactors, JudgmentExplain, AlertEnrichmentData, Activity, RefreshCw, ChevronUp, ChevronDown, Clock, Shield
- **CompoundingTab** → EvidenceRoomEntry, EvidenceRoomData, CompoundingData, AuditDecision, AuditVerification, GAEConfidenceTrajectory, GAETrustCurve, GAEBeforeAfter, ConvergenceData, CentroidEvolutionEntry, DecisionEconomics, EvolutionEventsState, AutoApproveStats, OperationalMetrics, EconomicsData
- **ExecutiveNarrativeTab** → Record, EvidenceValue, NarrativeData, GovernanceSummaryData, GovernanceReportData, GovernanceSummarySection, FileText, Download, MetricCard, TrendingUp, Shift, Search, Brain, Shield, ChevronDown
- **RuntimeEvolutionTab** → TrendingUp, ResponsiveContainer, AreaChart, CartesianGrid, XAxis, YAxis, Tooltip, Area, Line, ReferenceLine, Deployment, ProcessResult, RewardSummary, ProfileState, GraphStats
- **S2PPreviewTab** → TrajectoryPoint, ScoredInvoice, ConservationStatus, Supplier, Config
- **SOCAnalyticsTab** → QueryResult, ThreatLandscape, Array, DetectionEngineering, BenchmarkingData, F9ReportData, Shield, AlertTriangle, FileText, Database, Settings, CategoryScore, NoiseMapEntry, Users, TrendingUp
- **main** → React, App

## External Dependencies

- @
- @playwright
- @vitejs
- fs
- lucide-react
- path
- react
- react-dom
- recharts
- url
- vite
