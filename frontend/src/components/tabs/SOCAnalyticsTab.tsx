import { useState, useEffect } from 'react'
import CampaignIntelligencePanel from '../CampaignIntelligencePanel'
import {
  Shield,
  Search,
  CheckCircle,
  Clock,
  AlertTriangle,
  FileText,
  Database,
  Settings,
  Users,
  TrendingUp,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { queryMetric, getThreatLandscape, getAttackTacticBreakdown, fetchAnalystBenchmarking, fetchF9Report, fetchGraphSummary, fetchPrebuiltQueries, fetchNodeNeighbors, runPrebuiltQuery } from '../../lib/api'
import { ensureArray } from '../../lib/guards'
import { domainConfig } from '../../lib/domain'

const SOC_API = 'http://localhost:8001'

interface MetricContract {
  id: string
  name: string
  owner: string
  definition: string
  version: string
  status: string
}

interface DataPoint {
  label: string
  value: number
}

interface Provenance {
  sources: string[]
  freshness_hours: number
  query_preview: string
  last_updated: string
}

interface SprawlAlert {
  duplicate_rule: string
  active_in_pipelines: number
  monthly_alert_impact: number
  estimated_cost: number
  deprecated_date: string
}

interface QueryResult {
  matched_metric: MetricContract
  result: {
    data: DataPoint[]
    chart_type: 'bar' | 'line' | 'number' | 'table'
  }
  provenance: Provenance
  sprawl_alert: SprawlAlert | null
  confidence: number
}

const EXAMPLE_QUESTIONS = [
  "What's our MTTR by severity?",
  "Show me auto-close rate trend",
  "What's our false positive rate?",
  "Show escalation rate over time",
  "How efficient are our analysts?",
  // v3.1: Cross-context graph intelligence queries
  "Which users traveled internationally and triggered login anomalies this week?",
  "Show me unmanaged devices accessing sensitive assets",
  "What policy conflicts exist across my alert types?",
  "How much of my alert stream has threat intelligence coverage?",
]

// v4.0: Cross-source queries — span Pulsedive, GreyNoise, and CrowdStrike EDR
const CROSS_SOURCE_QUESTIONS = [
  "Show all indicators with critical consensus severity",
  "Which assets have CrowdStrike EDR with reduced prevention?",
  "Find alerts linked to malicious GreyNoise indicators",
  `What threat intel sources cover ${domainConfig.defaultAlertId}?`,
]

interface BenchmarkingCategoryEntry {
  agree_rate: number
  ai_accuracy: number
  override_count: number
  total: number
  analyst_agreement: number
  override_precision: number | null
  verified_decisions: number
  signal: string
  confidence: 'calibrated' | 'learning' | 'cold_start'
}

interface BenchmarkingData {
  status: 'ready' | 'accumulating'
  message?: string
  source?: string
  total_decisions?: number
  overall_agreement_rate?: number
  overall_ai_accuracy?: number
  lead_finding?: string
  per_category?: Record<string, BenchmarkingCategoryEntry>
  day_variance?: { min_daily_agree: number; max_daily_agree: number; trend: string }
}

interface F9ReportData {
  report_title: string
  generated_at: number
  status: 'ready' | 'accumulating'
  total_shadow_decisions: number
  lead_finding: string
  key_insight: string
  per_category: Record<string, BenchmarkingCategoryEntry>
  methodology: string
}

interface CategoryScore {
  category: string
  quality_score: number | null
  drift: number | null
  status: 'stable' | 'drifting' | 'diverged' | 'unavailable'
}

interface NoiseMapEntry {
  category: string
  fp_rate: number | null
  total_decisions: number
  estimated: boolean
}

interface DetectionEngineering {
  overall_quality_score: number | null
  category_scores: CategoryScore[]
  noise_map: NoiseMapEntry[]
  decisions_required_for_noise: number
  note: string
}

interface ThreatLandscape {
  threat_intel: {
    indicators_loaded: number
    sources: string[]
    high_severity_iocs: number
    last_refreshed_minutes_ago: number
  }
  active_alerts: {
    in_queue: number
    analyzed_today: number
    auto_closed_today: number
    escalated_today: number
  }
  governance: {
    policy_conflicts_detected: number
    decisions_today: number
    audit_chain_verified: boolean
    avg_confidence: number
  }
  graph_coverage: {
    nodes: number
    relationships: number
    alert_types_modeled: number
    patterns_learned: number
  }
  timestamp: string
}

export default function SOCAnalyticsTab() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<QueryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [threatLandscape, setThreatLandscape] = useState<ThreatLandscape | null>(null)
  const [threatLandscapeLoading, setThreatLandscapeLoading] = useState(true)
  const [tacticBreakdown, setTacticBreakdown] = useState<Array<{tactic: string; count: number}>>([])
  const [tacticBreakdownLoading, setTacticBreakdownLoading] = useState(true)
  const [detEng, setDetEng] = useState<DetectionEngineering | null>(null)
  const [detEngError, setDetEngError] = useState(false)
  const [benchmarking, setBenchmarking] = useState<BenchmarkingData | null>(null)
  const [f9Report, setF9Report] = useState<F9ReportData | null>(null)

  // WIRE-08: Graph Explorer
  const [graphExpanded, setGraphExpanded] = useState(false)
  const [graphInitialized, setGraphInitialized] = useState(false)
  const [graphSummary, setGraphSummary] = useState<any>(null)
  const [prebuiltList, setPrebuiltList] = useState<any[]>([])
  const [queryRows, setQueryRows] = useState<any[]>([])
  const [queryRunning, setQueryRunning] = useState(false)
  const [activeQueryKey, setActiveQueryKey] = useState<string | null>(null)
  const [queryError, setQueryError] = useState<string | null>(null)
  const [queryPage, setQueryPage] = useState(0)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [nodeNeighbors, setNodeNeighbors] = useState<any>(null)
  const [neighborsLoading, setNeighborsLoading] = useState(false)

  // Fetch threat landscape, tactic breakdown, detection engineering, and benchmarking on mount
  useEffect(() => {
    getThreatLandscape()
      .then((data) => setThreatLandscape(data as ThreatLandscape))
      .catch(() => {})
      .finally(() => setThreatLandscapeLoading(false))
    getAttackTacticBreakdown()
      .then((data: any) => setTacticBreakdown(data?.breakdown ?? []))
      .catch(() => {})
      .finally(() => setTacticBreakdownLoading(false))
    fetch(`${SOC_API}/api/soc/detection-engineering`)
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
      .then((data) => setDetEng(data as DetectionEngineering))
      .catch(() => setDetEngError(true))
    fetchAnalystBenchmarking()
      .then((data) => setBenchmarking(data as BenchmarkingData))
      .catch(() => {})
    fetchF9Report()
      .then((data) => setF9Report(data as F9ReportData))
      .catch(() => {})
  }, [])

  const handleQuery = async (queryText?: string) => {
    const query = queryText || question

    if (!query.trim()) {
      setError('Please enter a question')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await queryMetric(query)
      setResult(data as QueryResult)
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to process query')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  // Lazy-load graph summary + prebuilt list when explorer is first expanded
  useEffect(() => {
    if (!graphExpanded || graphInitialized) return
    setGraphInitialized(true)
    fetchGraphSummary().then((d: any) => setGraphSummary(d)).catch(() => {})
    fetchPrebuiltQueries()
      .then((d: any) => setPrebuiltList(ensureArray((d as any)?.queries)))
      .catch(() => {})
  }, [graphExpanded, graphInitialized])

  const handleRunPrebuilt = async (queryKey: string) => {
    setActiveQueryKey(queryKey)
    setQueryRunning(true)
    setQueryRows([])
    setQueryError(null)
    setQueryPage(0)
    setSelectedNodeId(null)
    setNodeNeighbors(null)
    try {
      const result: any = await runPrebuiltQuery(queryKey)
      if (result?.error) {
        setQueryError(result.error)
      } else {
        setQueryRows(ensureArray(result?.rows))
      }
    } catch {
      setQueryError('Query failed — check backend connection')
    } finally {
      setQueryRunning(false)
    }
  }

  const handleNodeClick = async (nodeId: string) => {
    if (selectedNodeId === nodeId) {
      setSelectedNodeId(null)
      setNodeNeighbors(null)
      return
    }
    setSelectedNodeId(nodeId)
    setNeighborsLoading(true)
    setNodeNeighbors(null)
    try {
      const data: any = await fetchNodeNeighbors(nodeId)
      setNodeNeighbors(data)
    } catch {
      setNodeNeighbors({ neighbors: [], total: 0, error: 'Failed to load neighbors' })
    } finally {
      setNeighborsLoading(false)
    }
  }

  const handleExampleClick = (exampleQuestion: string) => {
    setQuestion(exampleQuestion)
    handleQuery(exampleQuestion)
  }

  const formatValue = (value: number, metricId: string) => {
    if (metricId.includes('rate')) {
      return `${value.toFixed(1)}%`
    }
    if (metricId.includes('mttr') || metricId.includes('mttd')) {
      return value >= 60 ? `${(value / 60).toFixed(1)}h` : `${value.toFixed(1)}min`
    }
    return value.toFixed(1)
  }

  const getFreshnessColor = (hours: number) => {
    if (hours < 2) return 'text-soc-success'
    if (hours < 6) return 'text-yellow-400'
    return 'text-orange-400'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-soc-card rounded-lg p-6 border border-gray-800">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="w-6 h-6 text-soc-primary" />
          <h2 className="text-xl font-semibold">SOC Analytics</h2>
        </div>
        <p className="text-gray-400 text-sm">
          Ask anything about your security posture. Governed metrics with full
          provenance.
        </p>
        <div className="mt-3 text-sm text-soc-primary">
          "Instant answers with provenance showing exactly where the data came from."
        </div>
      </div>

      {/* Threat Landscape at a Glance — live graph snapshot */}
      {threatLandscapeLoading ? (
        <div className="bg-soc-card rounded-lg border border-gray-800 p-5 text-sm text-gray-500">
          Loading threat landscape...
        </div>
      ) : threatLandscape ? (
        <div className="bg-gradient-to-r from-soc-card via-soc-card to-blue-900/20 rounded-lg border border-blue-800/50 p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
              Threat Landscape at a Glance
            </span>
            <span className="ml-auto text-xs text-gray-600">
              live · {new Date(threatLandscape.timestamp).toLocaleTimeString()}
            </span>
          </div>

          <div className="grid grid-cols-4 gap-6">
            {/* Threat Intel */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-blue-400 mb-1">
                <Shield className="w-4 h-4" />
                <span className="text-xs font-semibold">Threat Intel</span>
              </div>
              <div className="text-2xl font-bold text-gray-100">
                {threatLandscape.threat_intel.indicators_loaded}
              </div>
              <div className="text-xs text-gray-500">IOCs loaded</div>
              <div className="text-xs text-red-400 font-semibold mt-1">
                {threatLandscape.threat_intel.high_severity_iocs} high severity
              </div>
              <div className="text-xs text-gray-600">
                {threatLandscape.threat_intel.sources.join(' + ')}
              </div>
            </div>

            {/* Active Alerts */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-orange-400 mb-1">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-xs font-semibold">Active Alerts</span>
              </div>
              <div className="text-2xl font-bold text-gray-100">
                {threatLandscape.active_alerts.in_queue}
              </div>
              <div className="text-xs text-gray-500">in queue now</div>
              <div className="text-xs text-green-400 font-semibold mt-1">
                {threatLandscape.active_alerts.auto_closed_today} auto-closed today
              </div>
              <div className="text-xs text-gray-600">
                {threatLandscape.active_alerts.escalated_today} escalated
              </div>
            </div>

            {/* Governance */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-green-400 mb-1">
                <FileText className="w-4 h-4" />
                <span className="text-xs font-semibold">Governance</span>
              </div>
              <div className="text-2xl font-bold text-gray-100">
                {(threatLandscape.governance.avg_confidence * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-500">avg decision confidence</div>
              <div className="text-xs text-yellow-400 font-semibold mt-1">
                {threatLandscape.governance.policy_conflicts_detected} policy conflicts
              </div>
              <div className="text-xs text-gray-600">audit chain verified</div>
            </div>

            {/* Graph Coverage */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-purple-400 mb-1">
                <Database className="w-4 h-4" />
                <span className="text-xs font-semibold">Graph Coverage</span>
              </div>
              <div className="text-2xl font-bold text-gray-100">
                {threatLandscape.graph_coverage.nodes}
              </div>
              <div className="text-xs text-gray-500">nodes indexed</div>
              <div className="text-xs text-purple-400 font-semibold mt-1">
                {threatLandscape.graph_coverage.patterns_learned} patterns learned
              </div>
              <div className="text-xs text-gray-600">
                {threatLandscape.graph_coverage.relationships.toLocaleString()} relationships
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-800 text-xs text-gray-500 italic">
            "This is what the graph knows before a single query. Your SIEM shows alerts. We show context."
          </div>
        </div>
      ) : (
        <div className="bg-soc-card rounded-lg border border-gray-800 p-5 text-sm text-gray-500">
          No data available
        </div>
      )}

      {/* By ATT&CK Tactic — alert distribution across MITRE tactics */}
      {tacticBreakdownLoading ? (
        <div className="text-sm text-gray-500 px-1">Loading ATT&CK tactic data...</div>
      ) : tacticBreakdown.length > 0 ? (
        <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-2">
            <Shield className="w-4 h-4 text-orange-400" />
            <span className="text-sm font-semibold">By ATT&CK Tactic</span>
            <span className="ml-auto text-xs text-gray-600">alert distribution</span>
          </div>
          <div className="p-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {tacticBreakdown.map(({ tactic, count }) => {
              const total = tacticBreakdown.reduce((s, t) => s + t.count, 0)
              const pct = total > 0 ? Math.round((count / total) * 100) : 0
              return (
                <div key={tactic} className="bg-soc-bg rounded-lg p-3 border border-gray-700">
                  <div className="text-xs font-semibold text-orange-300 mb-1 truncate">{tactic}</div>
                  <div className="text-2xl font-bold text-gray-100">{count}</div>
                  <div className="mt-1.5 h-1.5 rounded-full bg-gray-700 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-orange-500/70"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{pct}% of alerts</div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="text-sm text-gray-500 px-1">No data available</div>
      )}

      {/* Detection Engineering (F2) */}
      {detEngError ? (
        <div className="bg-soc-card rounded-lg border border-gray-800 p-5 text-sm text-gray-500">
          Detection engineering data unavailable
        </div>
      ) : detEng ? (
        <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-2">
            <Settings className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-semibold">Detection Engineering</span>
            <span className="ml-auto text-xs text-gray-600">F2 · rule quality + noise map</span>
          </div>

          <div className="p-5 grid grid-cols-2 gap-6">
            {/* Panel A — Rule Quality Score */}
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="text-4xl font-bold text-indigo-300">
                  {detEng.overall_quality_score !== null
                    ? detEng.overall_quality_score.toFixed(3)
                    : '—'}
                </div>
                <div>
                  <div className="text-xs font-semibold text-gray-300">Rule Quality Score</div>
                  <div className="text-xs text-gray-500">1.0 = baseline confirmed, &lt;0.85 = review rules</div>
                </div>
              </div>

              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left py-1 font-normal">Category</th>
                    <th className="text-right py-1 font-normal">Quality</th>
                    <th className="text-right py-1 font-normal">Drift</th>
                    <th className="text-right py-1 font-normal">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {ensureArray<CategoryScore>(detEng.category_scores).map((s) => (
                    <tr key={s.category} className="border-b border-gray-800/50">
                      <td className="py-1.5 text-gray-300 font-mono">{s.category}</td>
                      <td className="py-1.5 text-right text-gray-200">
                        {s.quality_score !== null ? s.quality_score.toFixed(3) : '—'}
                      </td>
                      <td className="py-1.5 text-right text-gray-400">
                        {s.drift !== null ? s.drift.toFixed(3) : '—'}
                      </td>
                      <td className="py-1.5 text-right">
                        <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-semibold ${
                          s.status === 'stable'
                            ? 'bg-green-500/20 text-green-400'
                            : s.status === 'drifting'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : s.status === 'diverged'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {s.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Panel B — Noise Map */}
            <div>
              <div className="text-xs font-semibold text-gray-300 mb-1">Noise Map</div>
              <div className="text-xs text-gray-500 mb-3">
                Per-category false positive rate from Decision outcomes
              </div>

              <div className="space-y-2">
                {ensureArray<NoiseMapEntry>(detEng.noise_map).map((entry) => {
                  const pct = entry.fp_rate !== null ? entry.fp_rate * 100 : null
                  const color =
                    pct === null
                      ? 'text-gray-500'
                      : pct < 10
                      ? 'text-green-400'
                      : pct < 25
                      ? 'text-yellow-400'
                      : 'text-red-400'
                  return (
                    <div key={entry.category} className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 font-mono w-40 truncate">
                        {entry.category}
                      </span>
                      <span
                        className={`text-xs font-semibold ${color}`}
                        title={
                          pct === null
                            ? `Requires ${detEng.decisions_required_for_noise}+ decisions`
                            : `${entry.total_decisions} decisions`
                        }
                      >
                        {pct !== null ? `${pct.toFixed(1)}%` : '—'}
                      </span>
                      {entry.estimated && (
                        <span className="text-xs text-gray-600 italic">
                          needs {detEng.decisions_required_for_noise}+ decisions
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="px-5 pb-3 text-xs text-gray-600 italic">{detEng.note}</div>
        </div>
      ) : null}

      {/* Team Performance — F9 Analyst Benchmarking (WIRE-02) */}
      {benchmarking && benchmarking.status === 'ready' && (
        <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-2">
            <Users className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-semibold">Team Performance</span>
            <span className="ml-auto text-xs text-gray-600">
              F9 · {(benchmarking.total_decisions ?? 0).toLocaleString()} shadow decisions
            </span>
          </div>

          <div className="p-5">
            {/* Key insight from f9Report */}
            {f9Report?.key_insight && (
              <div className="mb-4 bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3">
                <p className="text-xs text-indigo-300 leading-relaxed italic">"{f9Report.key_insight}"</p>
              </div>
            )}

            {/* Lead finding */}
            {benchmarking.lead_finding && (
              <div className="mb-5 flex items-start gap-2">
                <TrendingUp className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
                <p className="text-sm text-gray-300 leading-relaxed">{benchmarking.lead_finding}</p>
              </div>
            )}

            {/* Summary comparison cards */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              <div className="bg-soc-bg rounded-lg p-4 text-center border border-gray-700">
                <div className="text-2xl font-bold text-blue-300">
                  {((benchmarking.overall_ai_accuracy ?? 0) * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-gray-500 mt-1">AI Accuracy</div>
              </div>
              <div className="bg-soc-bg rounded-lg p-4 text-center border border-gray-700">
                <div className="text-2xl font-bold text-gray-300">
                  {((benchmarking.overall_agreement_rate ?? 0) * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-gray-500 mt-1">Analyst Agreement</div>
              </div>
              <div className="bg-soc-bg rounded-lg p-4 text-center border border-gray-700">
                <div className="text-2xl font-bold text-purple-300">100%</div>
                <div className="text-xs text-gray-500 mt-1">AI Consistency</div>
                <div className="text-xs text-gray-600 mt-0.5">vs ~65% analyst</div>
              </div>
            </div>

            {/* Per-category breakdown */}
            {benchmarking.per_category && Object.keys(benchmarking.per_category).length > 0 && (
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Per-Category Breakdown</div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-800">
                      <th className="text-left py-1.5 font-normal">Category</th>
                      <th className="text-right py-1.5 font-normal">AI Accuracy</th>
                      <th className="text-right py-1.5 font-normal">Agreement</th>
                      <th className="text-right py-1.5 font-normal">Override %</th>
                      <th className="text-right py-1.5 font-normal">N</th>
                      <th className="text-right py-1.5 font-normal">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(benchmarking.per_category).map(([cat, row]) => {
                      const overridePct = Math.round((1 - row.analyst_agreement) * 100)
                      const aiPct = Math.round(row.ai_accuracy * 100)
                      const agreePct = Math.round(row.analyst_agreement * 100)
                      const aiColor = aiPct >= 80 ? 'text-green-400' : aiPct >= 60 ? 'text-yellow-400' : 'text-red-400'
                      const overrideColor = overridePct >= 50 ? 'text-red-400' : overridePct >= 30 ? 'text-yellow-400' : 'text-gray-400'
                      return (
                        <tr key={cat} className="border-b border-gray-800/50 hover:bg-soc-bg/50 transition-colors">
                          <td className="py-2 text-gray-300 font-mono">{cat.replace(/_/g, ' ')}</td>
                          <td className={`py-2 text-right font-semibold ${aiColor}`}>{aiPct}%</td>
                          <td className="py-2 text-right text-gray-400">{agreePct}%</td>
                          <td className={`py-2 text-right font-semibold ${overrideColor}`}>{overridePct}%</td>
                          <td className="py-2 text-right text-gray-500">{row.verified_decisions}</td>
                          <td className="py-2 text-right">
                            <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-semibold ${
                              row.confidence === 'calibrated'
                                ? 'bg-green-500/20 text-green-400'
                                : row.confidence === 'learning'
                                ? 'bg-yellow-500/20 text-yellow-400'
                                : 'bg-gray-500/20 text-gray-500'
                            }`}>
                              {row.confidence}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Methodology footnote */}
            {f9Report?.methodology && (
              <div className="mt-4 text-xs text-gray-600 italic border-t border-gray-800 pt-3">
                Methodology: {f9Report.methodology}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Benchmarking — accumulating state */}
      {benchmarking && benchmarking.status === 'accumulating' && (
        <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-semibold">Team Performance</span>
          </div>
          <p className="text-xs text-gray-500">
            {benchmarking.message ?? 'Shadow decision data is still loading. Check back after Step 3 ingest.'}
          </p>
        </div>
      )}

      {/* Query Input */}
      <div className="bg-soc-card rounded-lg p-6 border border-gray-800">
        <label className="block text-sm font-semibold mb-3">
          Ask a security question:
        </label>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              placeholder="e.g., What was MTTR last week by severity?"
              className="w-full pl-10 pr-4 py-3 bg-soc-bg border border-gray-700 rounded-lg focus:outline-none focus:border-soc-primary text-gray-200 placeholder-gray-500"
            />
          </div>
          <button
            onClick={() => handleQuery()}
            disabled={loading}
            className="px-6 py-3 bg-soc-primary hover:bg-soc-primary/80 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <Clock className="w-4 h-4 animate-spin" />
                Querying...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Query
              </>
            )}
          </button>
        </div>

        {/* Example Questions */}
        <div className="mt-4">
          <div className="text-xs text-gray-500 mb-2">Try these examples:</div>
          <div className="flex flex-wrap gap-2">
            {/* Group 1 — SOC metrics */}
            {EXAMPLE_QUESTIONS.slice(0, 5).map((example, idx) => (
              <button
                key={idx}
                onClick={() => handleExampleClick(example)}
                className="px-3 py-1.5 bg-soc-bg hover:bg-soc-primary/20 border border-gray-700 hover:border-soc-primary rounded text-xs transition-colors"
              >
                {example}
              </button>
            ))}

            {/* Group 2 — Cross-context graph queries */}
            <div className="w-full mt-1 pt-2 border-t border-gray-800">
              <span className="text-xs text-slate-500">Cross-context queries:</span>
            </div>
            {EXAMPLE_QUESTIONS.slice(5).map((example, idx) => (
              <button
                key={`cc-${idx}`}
                onClick={() => handleExampleClick(example)}
                className="px-3 py-1.5 bg-soc-bg hover:bg-soc-primary/20 border border-gray-700 hover:border-soc-primary rounded text-xs transition-colors"
              >
                {example}
              </button>
            ))}

            {/* Group 3 — Cross-source queries (Pulsedive · GreyNoise · CrowdStrike) */}
            <div className="w-full mt-1 pt-2 border-t border-gray-800 flex items-center gap-2">
              <span className="text-xs text-sky-500 font-medium">Cross-source queries:</span>
              <span className="text-xs text-gray-600">Pulsedive · GreyNoise · CrowdStrike</span>
            </div>
            {CROSS_SOURCE_QUESTIONS.map((example, idx) => (
              <button
                key={`xs-${idx}`}
                onClick={() => handleExampleClick(example)}
                className="px-3 py-1.5 bg-sky-950/40 hover:bg-sky-900/40 border border-sky-800/60 hover:border-sky-500 rounded text-xs transition-colors text-sky-200"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-semibold">Query Error</span>
          </div>
          <p className="text-sm text-red-300 mt-2">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="grid grid-cols-3 gap-6">
          {/* Answer Panel */}
          <div className="col-span-2 bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{result.matched_metric.name}</h3>
                  <div className="text-xs text-gray-500 mt-1">
                    Matched: {result.matched_metric.id} • Confidence:{' '}
                    {(result.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <CheckCircle className="w-5 h-5 text-soc-success" />
              </div>
            </div>

            <div className="p-6">
              {result.result.chart_type === 'table' ? (
                /* Cross-context graph intelligence — narrative table rows */
                <div className="space-y-3">
                  {ensureArray<DataPoint>(result.result.data).map((row, idx) => {
                    const fields = row.label.split(' | ')
                    return (
                      <div
                        key={idx}
                        className="p-3 bg-soc-bg rounded-lg border border-gray-700"
                      >
                        <div className="font-semibold text-sm text-gray-200 mb-1.5">
                          {fields[0]}
                        </div>
                        <div className="space-y-0.5">
                          {fields.slice(1).map((field, fi) => (
                            <div key={fi} className="text-xs text-gray-400">
                              {field}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <>
                  {/* Chart */}
                  <div className="h-80 mb-4">
                    {result.result.chart_type === 'bar' ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={ensureArray<DataPoint>(result.result.data)}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis
                            dataKey="label"
                            stroke="#9ca3af"
                            style={{ fontSize: '12px' }}
                          />
                          <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1e293b',
                              border: '1px solid #374151',
                              borderRadius: '6px',
                            }}
                            labelStyle={{ color: '#f3f4f6' }}
                            formatter={(value: number) =>
                              formatValue(value, result.matched_metric.id)
                            }
                          />
                          <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={ensureArray<DataPoint>(result.result.data)}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis
                            dataKey="label"
                            stroke="#9ca3af"
                            style={{ fontSize: '12px' }}
                          />
                          <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1e293b',
                              border: '1px solid #374151',
                              borderRadius: '6px',
                            }}
                            labelStyle={{ color: '#f3f4f6' }}
                            formatter={(value: number) =>
                              formatValue(value, result.matched_metric.id)
                            }
                          />
                          <Line
                            type="monotone"
                            dataKey="value"
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={{ fill: '#10b981', r: 4 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>

                  {/* Data Table */}
                  <div className="text-xs text-gray-500">
                    <div className="font-semibold mb-2">Data Points:</div>
                    <div className="grid grid-cols-2 gap-2">
                      {ensureArray<DataPoint>(result.result.data).map((point, idx) => (
                        <div
                          key={idx}
                          className="flex justify-between p-2 bg-soc-bg rounded"
                        >
                          <span>{point.label}:</span>
                          <span className="font-bold text-gray-300">
                            {formatValue(point.value, result.matched_metric.id)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Governance Panel */}
          <div className="col-span-1 space-y-6">
            {/* Metric Contract */}
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-soc-primary" />
                <h3 className="font-semibold text-sm">Metric Contract</h3>
              </div>
              <div className="p-4 space-y-3 text-sm">
                <div>
                  <div className="text-gray-500 text-xs mb-1">Name</div>
                  <div className="font-semibold">
                    {result.matched_metric.name} ({result.matched_metric.version})
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-1">Owner</div>
                  <div className="text-xs font-mono">{result.matched_metric.owner}</div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-1">Status</div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                        result.matched_metric.status === 'active'
                          ? 'bg-soc-success/20 text-soc-success'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {result.matched_metric.status}
                    </span>
                    {result.matched_metric.status === 'active' && (
                      <CheckCircle className="w-3 h-3 text-soc-success" />
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-1">Definition</div>
                  <div className="text-xs text-gray-400 leading-relaxed">
                    {result.matched_metric.definition}
                  </div>
                </div>
              </div>
            </div>

            {/* Provenance */}
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <Database className="w-4 h-4 text-soc-primary" />
                <h3 className="font-semibold text-sm">Provenance</h3>
              </div>
              <div className="p-4 space-y-3 text-sm">
                <div>
                  <div className="text-gray-500 text-xs mb-1">Sources</div>
                  <div className="space-y-1">
                    {ensureArray<string>(result.provenance.sources).map((source, idx) => (
                      <div
                        key={idx}
                        className="text-xs bg-soc-bg px-2 py-1 rounded"
                      >
                        {source}
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-1">Freshness</div>
                  <div
                    className={`flex items-center gap-2 ${getFreshnessColor(
                      result.provenance.freshness_hours
                    )}`}
                  >
                    <Clock className="w-3 h-3" />
                    <span className="text-xs font-semibold">
                      {result.provenance.freshness_hours < 1
                        ? `${(result.provenance.freshness_hours * 60).toFixed(0)} minutes ago`
                        : `${result.provenance.freshness_hours.toFixed(1)} hours ago`}
                    </span>
                    <CheckCircle className="w-3 h-3" />
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 text-xs mb-2">Query Preview</div>
                  <div className="bg-soc-bg/50 rounded p-2 border border-gray-700">
                    <code className="text-xs text-gray-400 break-all">
                      {result.provenance.query_preview}
                    </code>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rule Sprawl Alert */}
      {result?.sprawl_alert && (
        <div className="bg-gradient-to-r from-orange-500/20 to-red-500/20 rounded-lg border-2 border-orange-500/50 overflow-hidden">
          <div className="px-6 py-4 border-b border-orange-500/50 flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-orange-400" />
            <h3 className="font-semibold text-orange-400 text-lg">
              ⚠️ DETECTION RULE SPRAWL DETECTED
            </h3>
          </div>
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-400 mb-1">Duplicate Rule</div>
                <div className="font-mono font-semibold text-orange-300">
                  {result.sprawl_alert.duplicate_rule}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Deprecated: {result.sprawl_alert.deprecated_date}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-400 mb-1">Still Active In</div>
                <div className="text-2xl font-bold text-orange-400">
                  {result.sprawl_alert.active_in_pipelines} pipelines
                </div>
              </div>
            </div>

            <div className="bg-soc-bg/50 rounded-lg p-4 border border-orange-500/30">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-gray-500 mb-1">Monthly Alert Impact</div>
                  <div className="text-xl font-bold text-red-400">
                    {result.sprawl_alert.monthly_alert_impact.toLocaleString()} alerts
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Est. Analyst Cost</div>
                  <div className="text-xl font-bold text-red-400">
                    ${(result.sprawl_alert.estimated_cost / 1000).toFixed(0)}K/mo
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button className="flex-1 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg font-semibold transition-colors">
                View Details
              </button>
              <button className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 rounded-lg font-semibold transition-colors">
                Deprecate Now
              </button>
            </div>

            <div className="text-xs text-gray-400 text-center">
              Removing this deprecated rule would save{' '}
              <span className="text-orange-400 font-bold">
                ~{(result.sprawl_alert.monthly_alert_impact / 30).toFixed(0)} alerts/day
              </span>{' '}
              and reduce analyst workload by{' '}
              <span className="text-orange-400 font-bold">~8 hours/week</span>
            </div>
          </div>
        </div>
      )}

      {/* F6 — Campaign Intelligence Panel */}
      <CampaignIntelligencePanel />

      {/* F7 — Graph Explorer Panel (WIRE-08) */}
      <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
        {/* Collapsible header */}
        <button
          onClick={() => setGraphExpanded(v => !v)}
          className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-purple-400" />
            <h3 className="font-semibold text-white text-sm">Graph Explorer</h3>
            <span className="text-xs text-gray-500 ml-1">Ask the Graph · 5 prebuilt queries</span>
          </div>
          {graphExpanded
            ? <ChevronDown className="w-4 h-4 text-gray-400" />
            : <ChevronRight className="w-4 h-4 text-gray-400" />
          }
        </button>

        {graphExpanded && (
          <div className="border-t border-gray-800 p-5 space-y-5">

            {/* Part A: Graph Summary */}
            {graphSummary ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-soc-bg rounded border border-gray-700 p-3">
                  <div className="text-gray-500 mb-0.5">Total Nodes</div>
                  <div className="font-mono font-semibold text-gray-200 text-base">
                    {(graphSummary.total_nodes ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="bg-soc-bg rounded border border-gray-700 p-3">
                  <div className="text-gray-500 mb-0.5">Relationships</div>
                  <div className="font-mono font-semibold text-gray-200 text-base">
                    {(graphSummary.total_relationships ?? 0).toLocaleString()}
                  </div>
                </div>
                <div className="bg-soc-bg rounded border border-gray-700 p-3 col-span-2">
                  <div className="text-gray-500 mb-1">Node Types</div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(graphSummary.node_types ?? {}).slice(0, 6).map(([label, cnt]: any) => (
                      <span key={label} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-700/60 text-gray-300 font-mono">
                        {label} <span className="text-gray-500">{cnt}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic">Loading graph summary…</div>
            )}

            {/* Part B: Prebuilt Query Selector */}
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-widest mb-2">Prebuilt Queries</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {prebuiltList.length > 0 ? prebuiltList.map((q: any) => (
                  <button
                    key={q.key}
                    onClick={() => handleRunPrebuilt(q.key)}
                    disabled={queryRunning}
                    className={`text-left rounded border px-3 py-2.5 text-xs transition-colors disabled:opacity-50 ${
                      activeQueryKey === q.key
                        ? 'border-purple-500/60 bg-purple-500/10 text-purple-200'
                        : 'border-gray-700 bg-soc-bg text-gray-300 hover:border-gray-600 hover:bg-gray-800/60'
                    }`}
                  >
                    <div className="font-semibold mb-0.5">{q.name}</div>
                    <div className="text-gray-500">{q.description}</div>
                  </button>
                )) : (
                  <div className="col-span-2 text-xs text-gray-600 italic py-2">Loading queries…</div>
                )}
              </div>
            </div>

            {/* Part C: Results */}
            {queryRunning && (
              <div className="text-xs text-gray-400 italic py-3 text-center">Running query…</div>
            )}
            {queryError && (
              <div className="text-xs text-red-300 bg-red-900/20 border border-red-500/30 rounded px-3 py-2">
                {queryError}
              </div>
            )}
            {queryRows.length > 0 && !queryRunning && (() => {
              const PAGE_SIZE = 20
              const totalPages = Math.ceil(queryRows.length / PAGE_SIZE)
              const pageRows = queryRows.slice(queryPage * PAGE_SIZE, (queryPage + 1) * PAGE_SIZE)
              const cols = Object.keys(queryRows[0] ?? {})
              const nodeIdCol = cols.find(c => c === 'id' || c === 'node_id' || c === 'alert_id')
              return (
                <div>
                  <div className="flex items-center justify-between mb-2 text-xs">
                    <span className="text-gray-500">{queryRows.length} result{queryRows.length !== 1 ? 's' : ''}</span>
                    {totalPages > 1 && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setQueryPage(p => Math.max(0, p - 1))}
                          disabled={queryPage === 0}
                          className="px-2 py-0.5 rounded border border-gray-700 disabled:opacity-40 hover:bg-gray-700"
                        >←</button>
                        <span className="text-gray-500">{queryPage + 1} / {totalPages}</span>
                        <button
                          onClick={() => setQueryPage(p => Math.min(totalPages - 1, p + 1))}
                          disabled={queryPage === totalPages - 1}
                          className="px-2 py-0.5 rounded border border-gray-700 disabled:opacity-40 hover:bg-gray-700"
                        >→</button>
                      </div>
                    )}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-gray-700 text-gray-500 uppercase tracking-wide">
                          {cols.map(col => (
                            <th key={col} className="text-left py-1.5 pr-4 font-medium whitespace-nowrap">
                              {col.replace(/_/g, ' ')}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {pageRows.map((row: any, i: number) => (
                          <tr key={i} className="border-b border-gray-800/60 last:border-0 hover:bg-gray-800/30">
                            {cols.map(col => {
                              const val = row[col]
                              const isClickable = col === nodeIdCol && val != null
                              return (
                                <td key={col} className="py-1.5 pr-4 align-top">
                                  {isClickable ? (
                                    <button
                                      onClick={() => handleNodeClick(String(val))}
                                      className={`font-mono hover:underline ${selectedNodeId === String(val) ? 'text-purple-300 underline' : 'text-purple-400 hover:text-purple-300'}`}
                                    >
                                      {String(val)}
                                    </button>
                                  ) : val == null ? (
                                    <span className="text-gray-600">—</span>
                                  ) : typeof val === 'number' ? (
                                    <span className="font-mono text-gray-200">
                                      {Number.isInteger(val) ? val.toLocaleString() : val.toFixed(3)}
                                    </span>
                                  ) : typeof val === 'boolean' ? (
                                    <span className={val ? 'text-green-400' : 'text-gray-500'}>{String(val)}</span>
                                  ) : (
                                    <span className="text-gray-300">{String(val)}</span>
                                  )}
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Neighbor drilldown */}
                  {selectedNodeId && (
                    <div className="mt-4 rounded border border-purple-500/30 bg-purple-900/10 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-purple-300">
                          Neighbors of <span className="font-mono">{selectedNodeId}</span>
                        </span>
                        <button
                          onClick={() => { setSelectedNodeId(null); setNodeNeighbors(null) }}
                          className="text-xs text-gray-500 hover:text-gray-300"
                        >✕</button>
                      </div>
                      {neighborsLoading ? (
                        <div className="text-xs text-gray-500 italic">Loading neighbors…</div>
                      ) : (nodeNeighbors as any)?.error ? (
                        <div className="text-xs text-red-300">{(nodeNeighbors as any).error}</div>
                      ) : ensureArray<any>((nodeNeighbors as any)?.neighbors).length === 0 ? (
                        <div className="text-xs text-gray-500 italic">No neighbors found.</div>
                      ) : (
                        <div className="space-y-1">
                          {ensureArray<any>((nodeNeighbors as any)?.neighbors).slice(0, 15).map((n: any, i: number) => (
                            <div key={i} className="flex items-center gap-3 text-xs">
                              <span className="text-gray-500 font-mono w-36 truncate shrink-0">{n.relationship}</span>
                              <span className="text-purple-400 font-semibold w-20 shrink-0">{n.neighbor_type}</span>
                              <span className="text-gray-300 truncate">{n.neighbor_name ?? n.neighbor_id ?? '—'}</span>
                            </div>
                          ))}
                          {((nodeNeighbors as any)?.total ?? 0) > 15 && (
                            <div className="text-xs text-gray-600 italic mt-1">
                              +{(nodeNeighbors as any).total - 15} more neighbors
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}
      </div>
    </div>
  )
}
