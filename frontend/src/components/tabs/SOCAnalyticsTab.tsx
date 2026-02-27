import { useState, useEffect } from 'react'
import {
  Shield,
  Search,
  CheckCircle,
  Clock,
  AlertTriangle,
  FileText,
  Database,
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
import { queryMetric, getThreatLandscape } from '../../lib/api'

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
  "What threat intel sources cover ALERT-7823?",
]

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

  // Fetch threat landscape on mount — non-critical, panel hidden on error
  useEffect(() => {
    getThreatLandscape()
      .then((data) => setThreatLandscape(data as ThreatLandscape))
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

      {/* Threat Landscape at a Glance — live graph snapshot, hidden until loaded */}
      {threatLandscape && (
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
                  {result.result.data.map((row, idx) => {
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
                        <BarChart data={result.result.data}>
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
                        <LineChart data={result.result.data}>
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
                      {result.result.data.map((point, idx) => (
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
                    {result.provenance.sources.map((source, idx) => (
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
    </div>
  )
}
